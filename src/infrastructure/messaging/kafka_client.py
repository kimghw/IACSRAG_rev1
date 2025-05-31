"""
Kafka 메시징 클라이언트 구현

이 모듈은 Kafka Producer와 Consumer를 제공하며,
이벤트 기반 아키텍처의 핵심 메시징 인프라를 담당합니다.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable, AsyncGenerator
from datetime import datetime
from dataclasses import asdict

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError, KafkaConnectionError
import structlog

from src.core.config import Settings
from src.core.exceptions import MessagingError, MessagingConnectionError


logger = structlog.get_logger(__name__)


class KafkaProducer:
    """
    Kafka Producer 클라이언트
    
    이벤트를 Kafka 토픽으로 발행하는 기능을 제공합니다.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._producer: Optional[AIOKafkaProducer] = None
        self._is_connected = False
    
    async def connect(self) -> None:
        """Kafka Producer 연결"""
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
                value_serializer=self._serialize_message,
                key_serializer=lambda x: x.encode('utf-8') if x else None,
                compression_type='gzip',
                max_batch_size=16384,
                linger_ms=10,
                acks='all',
                retries=3,
                retry_backoff_ms=100
            )
            
            await self._producer.start()
            self._is_connected = True
            
            logger.info(
                "Kafka Producer 연결 성공",
                bootstrap_servers=self.settings.kafka_bootstrap_servers
            )
            
        except Exception as e:
            logger.error("Kafka Producer 연결 실패", error=str(e))
            raise MessagingConnectionError(f"Kafka Producer 연결 실패: {e}")
    
    async def disconnect(self) -> None:
        """Kafka Producer 연결 해제"""
        if self._producer:
            try:
                await self._producer.stop()
                self._producer = None
                self._is_connected = False
                logger.info("Kafka Producer 연결 해제 완료")
            except Exception as e:
                logger.error("Kafka Producer 연결 해제 실패", error=str(e))
    
    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._is_connected and self._producer is not None
    
    @property
    def producer(self) -> AIOKafkaProducer:
        """Producer 인스턴스 반환"""
        if not self.is_connected or not self._producer:
            raise MessagingConnectionError("Kafka Producer에 연결되지 않음")
        return self._producer
    
    async def send_event(
        self,
        topic: str,
        event: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        이벤트를 Kafka 토픽으로 발행
        
        Args:
            topic: 대상 토픽
            event: 이벤트 데이터
            key: 파티션 키 (선택)
            headers: 메시지 헤더 (선택)
            
        Returns:
            발행 성공 여부
        """
        try:
            # 이벤트에 메타데이터 추가
            enriched_event = {
                **event,
                "timestamp": datetime.utcnow().isoformat(),
                "producer_id": "iacsrag-producer"
            }
            
            # 헤더 준비
            kafka_headers = []
            if headers:
                kafka_headers = [(k, v.encode('utf-8')) for k, v in headers.items()]
            
            # 메시지 발행
            future = await self.producer.send(
                topic=topic,
                value=enriched_event,
                key=key,
                headers=kafka_headers
            )
            
            # 발행 완료 대기
            record_metadata = await future
            
            logger.info(
                "이벤트 발행 성공",
                topic=topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
                key=key
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "이벤트 발행 실패",
                topic=topic,
                key=key,
                error=str(e)
            )
            raise MessagingError(f"이벤트 발행 실패: {e}")
    
    async def send_batch_events(
        self,
        topic: str,
        events: List[Dict[str, Any]],
        keys: Optional[List[str]] = None
    ) -> bool:
        """
        여러 이벤트를 배치로 발행
        
        Args:
            topic: 대상 토픽
            events: 이벤트 리스트
            keys: 파티션 키 리스트 (선택)
            
        Returns:
            발행 성공 여부
        """
        try:
            tasks = []
            
            for i, event in enumerate(events):
                key = keys[i] if keys and i < len(keys) else None
                task = self.send_event(topic, event, key)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 실패한 이벤트 확인
            failed_count = sum(1 for result in results if isinstance(result, Exception))
            
            if failed_count > 0:
                logger.warning(
                    "배치 이벤트 발행 중 일부 실패",
                    total=len(events),
                    failed=failed_count
                )
            
            return failed_count == 0
            
        except Exception as e:
            logger.error("배치 이벤트 발행 실패", error=str(e))
            raise MessagingError(f"배치 이벤트 발행 실패: {e}")
    
    def _serialize_message(self, message: Dict[str, Any]) -> bytes:
        """메시지 직렬화"""
        try:
            # dataclass 객체 처리
            if hasattr(message, '__dataclass_fields__'):
                message = asdict(message)
            
            return json.dumps(message, ensure_ascii=False, default=str).encode('utf-8')
        except Exception as e:
            raise MessagingError(f"메시지 직렬화 실패: {e}")


class KafkaConsumer:
    """
    Kafka Consumer 클라이언트
    
    Kafka 토픽에서 이벤트를 구독하고 처리하는 기능을 제공합니다.
    """
    
    def __init__(self, settings: Settings, group_id: Optional[str] = None):
        self.settings = settings
        self.group_id = group_id or settings.kafka_consumer_group_id
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._is_connected = False
        self._is_consuming = False
    
    async def connect(self, topics: List[str]) -> None:
        """
        Kafka Consumer 연결 및 토픽 구독
        
        Args:
            topics: 구독할 토픽 리스트
        """
        try:
            self._consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=self._deserialize_message,
                key_deserializer=lambda x: x.decode('utf-8') if x else None,
                auto_offset_reset='earliest',
                enable_auto_commit=False,
                max_poll_records=100,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000
            )
            
            await self._consumer.start()
            self._is_connected = True
            
            logger.info(
                "Kafka Consumer 연결 성공",
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
                group_id=self.group_id,
                topics=topics
            )
            
        except Exception as e:
            logger.error("Kafka Consumer 연결 실패", error=str(e))
            raise MessagingConnectionError(f"Kafka Consumer 연결 실패: {e}")
    
    async def disconnect(self) -> None:
        """Kafka Consumer 연결 해제"""
        if self._consumer:
            try:
                self._is_consuming = False
                await self._consumer.stop()
                self._consumer = None
                self._is_connected = False
                logger.info("Kafka Consumer 연결 해제 완료")
            except Exception as e:
                logger.error("Kafka Consumer 연결 해제 실패", error=str(e))
    
    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._is_connected and self._consumer is not None
    
    @property
    def consumer(self) -> AIOKafkaConsumer:
        """Consumer 인스턴스 반환"""
        if not self.is_connected or not self._consumer:
            raise MessagingConnectionError("Kafka Consumer에 연결되지 않음")
        return self._consumer
    
    async def consume_events(
        self,
        handler: Callable[[Dict[str, Any], str, Optional[str]], bool]
    ) -> None:
        """
        이벤트를 지속적으로 소비하고 처리
        
        Args:
            handler: 이벤트 처리 함수 (event, topic, key) -> success
        """
        if not self.is_connected:
            raise MessagingConnectionError("Consumer가 연결되지 않음")
        
        self._is_consuming = True
        
        try:
            logger.info("이벤트 소비 시작", group_id=self.group_id)
            
            async for message in self.consumer:
                if not self._is_consuming:
                    break
                
                try:
                    # 이벤트 처리
                    success = await self._process_message(message, handler)
                    
                    if success:
                        # 수동 커밋
                        await self.consumer.commit()
                        logger.debug(
                            "이벤트 처리 완료",
                            topic=message.topic,
                            partition=message.partition,
                            offset=message.offset
                        )
                    else:
                        logger.warning(
                            "이벤트 처리 실패",
                            topic=message.topic,
                            partition=message.partition,
                            offset=message.offset
                        )
                
                except Exception as e:
                    logger.error(
                        "이벤트 처리 중 오류",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                        error=str(e)
                    )
                    # 오류 발생 시에도 커밋하여 무한 재처리 방지
                    await self.consumer.commit()
        
        except Exception as e:
            logger.error("이벤트 소비 중 오류", error=str(e))
            raise MessagingError(f"이벤트 소비 실패: {e}")
        
        finally:
            self._is_consuming = False
            logger.info("이벤트 소비 종료")
    
    async def consume_single_event(self, timeout_ms: int = 5000) -> Optional[Dict[str, Any]]:
        """
        단일 이벤트 소비
        
        Args:
            timeout_ms: 타임아웃 (밀리초)
            
        Returns:
            이벤트 데이터 또는 None
        """
        try:
            message = await self.consumer.getone(timeout_ms=timeout_ms)
            
            if message:
                await self.consumer.commit()
                return {
                    "topic": message.topic,
                    "partition": message.partition,
                    "offset": message.offset,
                    "key": message.key,
                    "value": message.value,
                    "timestamp": message.timestamp,
                    "headers": dict(message.headers) if message.headers else {}
                }
            
            return None
            
        except Exception as e:
            logger.error("단일 이벤트 소비 실패", error=str(e))
            return None
    
    def stop_consuming(self) -> None:
        """이벤트 소비 중단"""
        self._is_consuming = False
        logger.info("이벤트 소비 중단 요청")
    
    async def _process_message(
        self,
        message,
        handler: Callable[[Dict[str, Any], str, Optional[str]], bool]
    ) -> bool:
        """메시지 처리"""
        try:
            # 핸들러가 비동기 함수인지 확인
            if asyncio.iscoroutinefunction(handler):
                return await handler(message.value, message.topic, message.key)
            else:
                return handler(message.value, message.topic, message.key)
        except Exception as e:
            logger.error("메시지 핸들러 실행 실패", error=str(e))
            return False
    
    def _deserialize_message(self, message: bytes) -> Dict[str, Any]:
        """메시지 역직렬화"""
        try:
            return json.loads(message.decode('utf-8'))
        except Exception as e:
            logger.error("메시지 역직렬화 실패", error=str(e))
            raise MessagingError(f"메시지 역직렬화 실패: {e}")


class KafkaManager:
    """
    Kafka 클라이언트 매니저 (싱글톤)
    
    Producer와 Consumer 인스턴스를 중앙에서 관리합니다.
    """
    
    _instance: Optional['KafkaManager'] = None
    _producer: Optional[KafkaProducer] = None
    _consumers: Dict[str, KafkaConsumer] = {}
    
    def __new__(cls) -> 'KafkaManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, settings: Settings) -> None:
        """매니저 초기화"""
        if self._producer is None:
            self._producer = KafkaProducer(settings)
            self.settings = settings
            logger.info("Kafka 매니저 초기화 완료")
    
    async def connect_producer(self) -> None:
        """Producer 연결"""
        if self._producer:
            await self._producer.connect()
    
    async def disconnect_producer(self) -> None:
        """Producer 연결 해제"""
        if self._producer:
            await self._producer.disconnect()
    
    def create_consumer(self, consumer_id: str, group_id: Optional[str] = None) -> KafkaConsumer:
        """Consumer 생성"""
        if consumer_id not in self._consumers:
            self._consumers[consumer_id] = KafkaConsumer(self.settings, group_id)
        return self._consumers[consumer_id]
    
    async def disconnect_consumer(self, consumer_id: str) -> None:
        """Consumer 연결 해제"""
        if consumer_id in self._consumers:
            await self._consumers[consumer_id].disconnect()
            del self._consumers[consumer_id]
    
    async def disconnect_all(self) -> None:
        """모든 연결 해제"""
        # Producer 연결 해제
        if self._producer:
            await self._producer.disconnect()
        
        # 모든 Consumer 연결 해제
        for consumer_id in list(self._consumers.keys()):
            await self.disconnect_consumer(consumer_id)
        
        logger.info("모든 Kafka 연결 해제 완료")
    
    @property
    def producer(self) -> KafkaProducer:
        """Producer 인스턴스 반환"""
        if not self._producer:
            raise MessagingConnectionError("Kafka Producer가 초기화되지 않음")
        return self._producer
    
    def get_consumer(self, consumer_id: str) -> KafkaConsumer:
        """Consumer 인스턴스 반환"""
        if consumer_id not in self._consumers:
            raise MessagingConnectionError(f"Consumer '{consumer_id}'가 생성되지 않음")
        return self._consumers[consumer_id]


# 전역 매니저 인스턴스
kafka_manager = KafkaManager()


# 유틸리티 함수들
async def initialize_kafka_producer(settings: Settings) -> None:
    """Kafka Producer 초기화"""
    kafka_manager.initialize(settings)
    await kafka_manager.connect_producer()
    logger.info("Kafka Producer 초기화 완료")


async def kafka_health_check() -> Dict[str, Any]:
    """Kafka 헬스체크"""
    try:
        producer = kafka_manager.producer
        
        if producer.is_connected:
            # 테스트 메시지 발행 시도
            test_topic = "health-check"
            test_event = {"type": "health_check", "timestamp": datetime.utcnow().isoformat()}
            
            try:
                await producer.send_event(test_topic, test_event)
                return {
                    "status": "healthy",
                    "producer_connected": True,
                    "bootstrap_servers": producer.settings.kafka_bootstrap_servers
                }
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "producer_connected": True,
                    "error": f"메시지 발행 실패: {e}"
                }
        else:
            return {
                "status": "disconnected",
                "producer_connected": False,
                "error": "Producer가 연결되지 않음"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def create_event_message(
    event_type: str,
    data: Dict[str, Any],
    source: str = "iacsrag",
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    표준 이벤트 메시지 생성
    
    Args:
        event_type: 이벤트 타입
        data: 이벤트 데이터
        source: 이벤트 소스
        correlation_id: 상관관계 ID
        
    Returns:
        표준화된 이벤트 메시지
    """
    return {
        "event_type": event_type,
        "source": source,
        "correlation_id": correlation_id,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }
