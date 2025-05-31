"""
Kafka 클라이언트 단위 테스트
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from dataclasses import dataclass
from typing import Dict, Any

from src.core.config import Settings
from src.core.exceptions import MessagingError, MessagingConnectionError
from src.infrastructure.messaging.kafka_client import (
    KafkaProducer,
    KafkaConsumer,
    KafkaManager,
    kafka_manager,
    initialize_kafka_producer,
    kafka_health_check,
    create_event_message
)


@dataclass
class TestEventData:
    """테스트용 이벤트 클래스"""
    type: str
    data: str


class TestKafkaProducer:
    """KafkaProducer 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            kafka_consumer_group_id="test_group"
        )
        self.producer = KafkaProducer(self.settings)

    def test_initialization(self):
        """Producer 초기화 테스트"""
        assert self.producer.settings == self.settings
        assert self.producer._producer is None
        assert self.producer._is_connected is False

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Producer 연결 성공 테스트"""
        mock_aiokafka_producer = AsyncMock()

        with patch('src.infrastructure.messaging.kafka_client.AIOKafkaProducer') as mock_producer_class:
            mock_producer_class.return_value = mock_aiokafka_producer

            await self.producer.connect()

            # Producer 생성 확인 (key_serializer는 lambda이므로 정확한 비교 제외)
            mock_producer_class.assert_called_once()
            call_args = mock_producer_class.call_args
            assert call_args[1]['bootstrap_servers'] == "localhost:9092"
            assert call_args[1]['compression_type'] == 'gzip'
            assert call_args[1]['acks'] == 'all'

            # start 호출 확인
            mock_aiokafka_producer.start.assert_called_once()
            assert self.producer._is_connected is True

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Producer 연결 실패 테스트"""
        with patch('src.infrastructure.messaging.kafka_client.AIOKafkaProducer') as mock_producer_class:
            mock_producer_class.side_effect = Exception("Connection failed")

            with pytest.raises(MessagingConnectionError, match="Kafka Producer 연결 실패"):
                await self.producer.connect()

            assert self.producer._is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Producer 연결 해제 테스트"""
        mock_producer = AsyncMock()
        self.producer._producer = mock_producer
        self.producer._is_connected = True

        await self.producer.disconnect()

        mock_producer.stop.assert_called_once()
        assert self.producer._producer is None
        assert self.producer._is_connected is False

    def test_is_connected_property(self):
        """연결 상태 속성 테스트"""
        assert self.producer.is_connected is False
        
        # 실제 구현에서는 _producer도 None이 아니어야 함
        mock_producer = AsyncMock()
        self.producer._producer = mock_producer
        self.producer._is_connected = True
        assert self.producer.is_connected is True

    def test_producer_property_connected(self):
        """Producer 속성 테스트 (연결됨)"""
        mock_producer = AsyncMock()
        self.producer._producer = mock_producer
        self.producer._is_connected = True

        assert self.producer.producer == mock_producer

    def test_producer_property_not_connected(self):
        """Producer 속성 테스트 (연결 안됨)"""
        with pytest.raises(MessagingConnectionError, match="Kafka Producer에 연결되지 않음"):
            _ = self.producer.producer

    @pytest.mark.asyncio
    async def test_send_event_success(self):
        """이벤트 발행 성공 테스트"""
        mock_producer = AsyncMock()
        mock_metadata = MagicMock()
        mock_metadata.partition = 0
        mock_metadata.offset = 123
        
        # Future 객체 생성
        mock_future = asyncio.Future()
        mock_future.set_result(mock_metadata)
        mock_producer.send.return_value = mock_future
        
        self.producer._producer = mock_producer
        self.producer._is_connected = True
        
        event = {"type": "test", "data": "test_data"}
        
        result = await self.producer.send_event("test_topic", event, "test_key")
        
        assert result is True
        mock_producer.send.assert_called_once()
        
        # 호출 인자 확인
        call_args = mock_producer.send.call_args
        assert call_args[1]["topic"] == "test_topic"
        assert call_args[1]["key"] == "test_key"
        assert "timestamp" in call_args[1]["value"]
        assert "producer_id" in call_args[1]["value"]

    @pytest.mark.asyncio
    async def test_send_event_failure(self):
        """이벤트 발행 실패 테스트"""
        mock_producer = AsyncMock()
        mock_producer.send.side_effect = Exception("Send failed")
        
        self.producer._producer = mock_producer
        self.producer._is_connected = True
        
        event = {"type": "test", "data": "test_data"}
        
        with pytest.raises(MessagingError, match="이벤트 발행 실패"):
            await self.producer.send_event("test_topic", event)

    @pytest.mark.asyncio
    async def test_send_batch_events_success(self):
        """배치 이벤트 발행 성공 테스트"""
        mock_producer = AsyncMock()
        mock_metadata = MagicMock()
        mock_metadata.partition = 0
        mock_metadata.offset = 123
        
        # Future 객체 생성
        mock_future = asyncio.Future()
        mock_future.set_result(mock_metadata)
        mock_producer.send.return_value = mock_future
        
        self.producer._producer = mock_producer
        self.producer._is_connected = True
        
        events = [
            {"type": "test1", "data": "data1"},
            {"type": "test2", "data": "data2"}
        ]
        keys = ["key1", "key2"]
        
        result = await self.producer.send_batch_events("test_topic", events, keys)
        
        assert result is True
        assert mock_producer.send.call_count == 2

    @pytest.mark.asyncio
    async def test_send_batch_events_partial_failure(self):
        """배치 이벤트 발행 부분 실패 테스트"""
        mock_producer = AsyncMock()
        
        # 첫 번째는 성공, 두 번째는 실패
        mock_metadata = MagicMock()
        mock_metadata.partition = 0
        mock_metadata.offset = 123
        
        success_future = asyncio.Future()
        success_future.set_result(mock_metadata)
        
        fail_future = asyncio.Future()
        fail_future.set_exception(Exception("Send failed"))
        
        mock_producer.send.side_effect = [success_future, fail_future]
        
        self.producer._producer = mock_producer
        self.producer._is_connected = True
        
        events = [
            {"type": "test1", "data": "data1"},
            {"type": "test2", "data": "data2"}
        ]
        keys = ["key1", "key2"]
        
        result = await self.producer.send_batch_events("test_topic", events, keys)
        
        assert result is False
        assert mock_producer.send.call_count == 2

    def test_serialize_message_dict(self):
        """딕셔너리 메시지 직렬화 테스트"""
        message = {"key": "value", "number": 123}
        result = self.producer._serialize_message(message)
        
        expected = json.dumps(message, ensure_ascii=False, default=str).encode('utf-8')
        assert result == expected

    def test_serialize_message_dataclass(self):
        """데이터클래스 메시지 직렬화 테스트"""
        message = TestEventData(type="test", data="data")
        result = self.producer._serialize_message(message)
        
        expected_dict = {"type": "test", "data": "data"}
        expected = json.dumps(expected_dict, ensure_ascii=False, default=str).encode('utf-8')
        assert result == expected

    def test_serialize_message_failure(self):
        """메시지 직렬화 실패 테스트"""
        # 실제로 직렬화가 실패하는 케이스를 만들기 어려우므로 패치 사용
        with patch('json.dumps') as mock_dumps:
            mock_dumps.side_effect = TypeError("Object not serializable")
            
            message = {"key": "value"}
            
            with pytest.raises(MessagingError, match="메시지 직렬화 실패"):
                self.producer._serialize_message(message)


class TestKafkaConsumer:
    """KafkaConsumer 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            kafka_consumer_group_id="test_group"
        )
        self.consumer = KafkaConsumer(self.settings, group_id="test_group")

    def test_initialization(self):
        """Consumer 초기화 테스트"""
        assert self.consumer.settings == self.settings
        assert self.consumer.group_id == "test_group"
        assert self.consumer._consumer is None
        assert self.consumer._is_connected is False

    def test_initialization_custom_group_id(self):
        """Consumer 초기화 테스트 (커스텀 그룹 ID)"""
        consumer = KafkaConsumer(self.settings, group_id="custom_group")
        assert consumer.group_id == "custom_group"

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Consumer 연결 성공 테스트"""
        mock_aiokafka_consumer = AsyncMock()
        topics = ["topic1", "topic2"]

        with patch('src.infrastructure.messaging.kafka_client.AIOKafkaConsumer') as mock_consumer_class:
            mock_consumer_class.return_value = mock_aiokafka_consumer

            await self.consumer.connect(topics)

            # Consumer 생성 확인
            mock_consumer_class.assert_called_once()
            call_args = mock_consumer_class.call_args
            assert call_args[0] == ("topic1", "topic2")
            assert call_args[1]['bootstrap_servers'] == "localhost:9092"
            assert call_args[1]['group_id'] == "test_group"

            # start 호출 확인
            mock_aiokafka_consumer.start.assert_called_once()
            assert self.consumer._is_connected is True

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Consumer 연결 실패 테스트"""
        with patch('src.infrastructure.messaging.kafka_client.AIOKafkaConsumer') as mock_consumer_class:
            mock_consumer_class.side_effect = Exception("Connection failed")

            with pytest.raises(MessagingConnectionError, match="Kafka Consumer 연결 실패"):
                await self.consumer.connect(["topic1"])

            assert self.consumer._is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Consumer 연결 해제 테스트"""
        mock_consumer = AsyncMock()
        self.consumer._consumer = mock_consumer
        self.consumer._is_connected = True

        await self.consumer.disconnect()

        mock_consumer.stop.assert_called_once()
        assert self.consumer._consumer is None
        assert self.consumer._is_connected is False

    def test_is_connected_property(self):
        """연결 상태 속성 테스트"""
        assert self.consumer.is_connected is False
        
        # 실제 구현에서는 _consumer도 None이 아니어야 함
        mock_consumer = AsyncMock()
        self.consumer._consumer = mock_consumer
        self.consumer._is_connected = True
        assert self.consumer.is_connected is True

    def test_consumer_property_connected(self):
        """Consumer 속성 테스트 (연결됨)"""
        mock_consumer = AsyncMock()
        self.consumer._consumer = mock_consumer
        self.consumer._is_connected = True

        assert self.consumer.consumer == mock_consumer

    def test_consumer_property_not_connected(self):
        """Consumer 속성 테스트 (연결 안됨)"""
        with pytest.raises(MessagingConnectionError, match="Kafka Consumer에 연결되지 않음"):
            _ = self.consumer.consumer

    @pytest.mark.asyncio
    async def test_consume_single_event_success(self):
        """단일 이벤트 소비 성공 테스트"""
        mock_consumer = AsyncMock()
        mock_message = MagicMock()
        mock_message.topic = "test_topic"
        mock_message.partition = 0
        mock_message.offset = 123
        mock_message.key = "test_key"  # 이미 디코딩된 상태
        mock_message.value = {"type": "test", "data": "test_data"}  # 이미 역직렬화된 상태
        mock_message.timestamp = 1234567890
        mock_message.headers = []

        mock_consumer.getone.return_value = mock_message
        
        self.consumer._consumer = mock_consumer
        self.consumer._is_connected = True
        
        result = await self.consumer.consume_single_event(timeout_ms=1000)
        
        assert result is not None
        assert result["topic"] == "test_topic"
        assert result["partition"] == 0
        assert result["offset"] == 123
        assert result["key"] == "test_key"
        assert result["value"]["type"] == "test"

    @pytest.mark.asyncio
    async def test_consume_single_event_timeout(self):
        """단일 이벤트 소비 타임아웃 테스트"""
        mock_consumer = AsyncMock()
        mock_consumer.getone.side_effect = asyncio.TimeoutError()
        
        self.consumer._consumer = mock_consumer
        self.consumer._is_connected = True
        
        result = await self.consumer.consume_single_event(timeout_ms=1000)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_consume_single_event_failure(self):
        """단일 이벤트 소비 실패 테스트"""
        mock_consumer = AsyncMock()
        mock_consumer.getone.side_effect = Exception("Consume failed")
        
        self.consumer._consumer = mock_consumer
        self.consumer._is_connected = True
        
        # 실제 구현에서는 예외를 발생시키지 않고 None을 반환
        result = await self.consumer.consume_single_event()
        assert result is None

    def test_stop_consuming(self):
        """소비 중단 테스트"""
        self.consumer._is_consuming = True
        
        self.consumer.stop_consuming()
        
        assert self.consumer._is_consuming is False

    @pytest.mark.asyncio
    async def test_process_message_sync_handler(self):
        """동기 핸들러로 메시지 처리 테스트"""
        def sync_handler(value, topic, key):
            return f"processed: {value['data']}"
        
        mock_message = MagicMock()
        mock_message.topic = "test_topic"
        mock_message.partition = 0
        mock_message.offset = 123
        mock_message.key = "test_key"
        mock_message.value = {"type": "test", "data": "test_data"}
        mock_message.timestamp = 1234567890
        mock_message.headers = []
        
        result = await self.consumer._process_message(mock_message, sync_handler)
        
        assert result == "processed: test_data"

    @pytest.mark.asyncio
    async def test_process_message_async_handler(self):
        """비동기 핸들러로 메시지 처리 테스트"""
        async def async_handler(value, topic, key):
            return f"async processed: {value['data']}"
        
        mock_message = MagicMock()
        mock_message.topic = "test_topic"
        mock_message.partition = 0
        mock_message.offset = 123
        mock_message.key = "test_key"
        mock_message.value = {"type": "test", "data": "test_data"}
        mock_message.timestamp = 1234567890
        mock_message.headers = []
        
        result = await self.consumer._process_message(mock_message, async_handler)
        
        assert result == "async processed: test_data"

    @pytest.mark.asyncio
    async def test_process_message_handler_exception(self):
        """핸들러 예외 처리 테스트"""
        def failing_handler(value, topic, key):
            raise Exception("Handler failed")
        
        mock_message = MagicMock()
        mock_message.topic = "test_topic"
        mock_message.partition = 0
        mock_message.offset = 123
        mock_message.key = "test_key"
        mock_message.value = {"type": "test", "data": "test_data"}
        mock_message.timestamp = 1234567890
        mock_message.headers = []
        
        # 실제 구현에서는 예외를 발생시키지 않고 False를 반환
        result = await self.consumer._process_message(mock_message, failing_handler)
        assert result is False

    def test_deserialize_message_success(self):
        """메시지 역직렬화 성공 테스트"""
        message_bytes = b'{"type": "test", "data": "test_data"}'
        result = self.consumer._deserialize_message(message_bytes)
        
        expected = {"type": "test", "data": "test_data"}
        assert result == expected

    def test_deserialize_message_failure(self):
        """메시지 역직렬화 실패 테스트"""
        invalid_json = b'{"invalid": json}'
        
        with pytest.raises(MessagingError, match="메시지 역직렬화 실패"):
            self.consumer._deserialize_message(invalid_json)


class TestKafkaManager:
    """KafkaManager 테스트"""

    def setup_method(self):
        """테스트 설정"""
        # 싱글톤 인스턴스 초기화
        KafkaManager._instance = None
        KafkaManager._producer = None
        KafkaManager._consumers = {}

    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        manager1 = KafkaManager()
        manager2 = KafkaManager()
        
        assert manager1 is manager2

    def test_initialize(self):
        """매니저 초기화 테스트"""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            kafka_consumer_group_id="test_group"
        )
        manager = KafkaManager()
        manager.initialize(settings)
        
        assert manager.settings == settings
        assert manager._producer is not None  # 실제 구현에서는 Producer가 생성됨
        assert len(manager._consumers) == 0

    @pytest.mark.asyncio
    async def test_connect_producer(self):
        """Producer 연결 테스트"""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            kafka_consumer_group_id="test_group"
        )
        manager = KafkaManager()
        manager.initialize(settings)
        
        with patch.object(manager._producer, 'connect') as mock_connect:
            await manager.connect_producer()
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_producer(self):
        """Producer 연결 해제 테스트"""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            kafka_consumer_group_id="test_group"
        )
        manager = KafkaManager()
        manager.initialize(settings)
        
        with patch.object(manager._producer, 'disconnect') as mock_disconnect:
            await manager.disconnect_producer()
            mock_disconnect.assert_called_once()

    def test_create_consumer(self):
        """Consumer 생성 테스트"""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            kafka_consumer_group_id="test_group"
        )
        manager = KafkaManager()
        manager.initialize(settings)
        
        consumer = manager.create_consumer("test_consumer")
        
        assert "test_consumer" in manager._consumers
        assert isinstance(consumer, KafkaConsumer)
        # 실제 구현에서는 settings의 기본값을 사용 (iacsrag-dev)
        assert consumer.group_id == "iacsrag-dev"

    def test_create_consumer_custom_group(self):
        """Consumer 생성 테스트 (커스텀 그룹)"""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            kafka_consumer_group_id="test_group"
        )
        manager = KafkaManager()
        manager.initialize(settings)
        
        consumer = manager.create_consumer("test_consumer", group_id="custom_group")
        
        assert consumer.group_id == "custom_group"

    @pytest.mark.asyncio
    async def test_disconnect_consumer(self):
        """Consumer 연결 해제 테스트"""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            kafka_consumer_group_id="test_group"
        )
        manager = KafkaManager()
        manager.initialize(settings)
        
        # Mock consumer 생성
        mock_consumer = AsyncMock()
        manager._consumers["test_consumer"] = mock_consumer
        
        await manager.disconnect_consumer("test_consumer")
        
        mock_consumer.disconnect.assert_called_once()
        assert "test_consumer" not in manager._consumers

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """모든 연결 해제 테스트"""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            kafka_consumer_group_id="test_group"
        )
        manager = KafkaManager()
        manager.initialize(settings)
        
        # Mock consumer 설정
        mock_consumer = AsyncMock()
        manager._consumers["test_consumer"] = mock_consumer
        
        with patch.object(manager._producer, 'disconnect') as mock_producer_disconnect:
            await manager.disconnect_all()
            
            mock_producer_disconnect.assert_called_once()
            mock_consumer.disconnect.assert_called_once()
            assert len(manager._consumers) == 0

    def test_producer_property(self):
        """Producer 속성 테스트"""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            kafka_consumer_group_id="test_group"
        )
        manager = KafkaManager()
        manager.initialize(settings)
        
        assert manager.producer is not None

    def test_producer_property_not_initialized(self):
        """Producer 속성 테스트 (초기화 안됨)"""
        manager = KafkaManager()
        
        with pytest.raises(MessagingConnectionError, match="Kafka Producer가 초기화되지 않음"):
            _ = manager.producer

    def test_get_consumer(self):
        """Consumer 조회 테스트"""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            kafka_consumer_group_id="test_group"
        )
        manager = KafkaManager()
        manager.initialize(settings)
        
        mock_consumer = MagicMock()
        manager._consumers["test_consumer"] = mock_consumer
        
        result = manager.get_consumer("test_consumer")
        assert result == mock_consumer

    def test_get_consumer_not_found(self):
        """Consumer 조회 테스트 (없음)"""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            kafka_consumer_group_id="test_group"
        )
        manager = KafkaManager()
        manager.initialize(settings)
        
        with pytest.raises(MessagingConnectionError, match="Consumer 'nonexistent'가 생성되지 않음"):
            manager.get_consumer("nonexistent")


class TestUtilityFunctions:
    """유틸리티 함수 테스트"""

    def setup_method(self):
        """테스트 설정"""
        # 매니저 초기화
        KafkaManager._instance = None
        KafkaManager._producer = None
        KafkaManager._consumers = {}

    @pytest.mark.asyncio
    async def test_initialize_kafka_producer_success(self):
        """Kafka Producer 초기화 성공 테스트"""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            kafka_consumer_group_id="test_group"
        )
        
        with patch('src.infrastructure.messaging.kafka_client.kafka_manager') as mock_manager:
            mock_manager.initialize = MagicMock()
            mock_manager.connect_producer = AsyncMock()
            
            await initialize_kafka_producer(settings)
            
            mock_manager.initialize.assert_called_once_with(settings)
            mock_manager.connect_producer.assert_called_once()

    @pytest.mark.asyncio
    async def test_kafka_health_check_healthy(self):
        """Kafka 헬스체크 정상 테스트"""
        mock_producer = AsyncMock()
        mock_producer.is_connected = True
        mock_producer.send_event = AsyncMock(return_value=True)
        mock_producer.settings.kafka_bootstrap_servers = "localhost:9092"
        
        with patch('src.infrastructure.messaging.kafka_client.kafka_manager') as mock_manager:
            mock_manager.producer = mock_producer
            
            result = await kafka_health_check()
            
            assert result["status"] == "healthy"
            assert result["producer_connected"] is True
            mock_producer.send_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_kafka_health_check_disconnected(self):
        """Kafka 헬스체크 연결 해제 테스트"""
        mock_producer = AsyncMock()
        mock_producer.is_connected = False
        
        with patch('src.infrastructure.messaging.kafka_client.kafka_manager') as mock_manager:
            mock_manager.producer = mock_producer
            
            result = await kafka_health_check()
            
            assert result["status"] == "disconnected"
            assert result["producer_connected"] is False

    @pytest.mark.asyncio
    async def test_kafka_health_check_unhealthy(self):
        """Kafka 헬스체크 비정상 테스트"""
        mock_producer = AsyncMock()
        mock_producer.is_connected = True
        mock_producer.send_event = AsyncMock(side_effect=Exception("Send failed"))
        
        with patch('src.infrastructure.messaging.kafka_client.kafka_manager') as mock_manager:
            mock_manager.producer = mock_producer
            
            result = await kafka_health_check()
            
            assert result["status"] == "unhealthy"
            assert "Send failed" in result["error"]

    @pytest.mark.asyncio
    async def test_kafka_health_check_error(self):
        """Kafka 헬스체크 오류 테스트"""
        with patch('src.infrastructure.messaging.kafka_client.kafka_manager') as mock_manager:
            # producer 속성 접근 시 예외 발생하도록 설정
            type(mock_manager).producer = PropertyMock(side_effect=Exception("Manager error"))
            
            result = await kafka_health_check()
            
            assert result["status"] == "error"
            assert "Manager error" in result["error"]

    def test_create_event_message(self):
        """이벤트 메시지 생성 테스트"""
        event_type = "test_event"
        data = {"key": "value"}
        correlation_id = "test_correlation"
        
        result = create_event_message(event_type, data, correlation_id=correlation_id)
        
        assert result["event_type"] == event_type
        assert result["data"] == data
        assert result["correlation_id"] == correlation_id
        assert "timestamp" in result
        assert result["source"] == "iacsrag"

    def test_create_event_message_defaults(self):
        """이벤트 메시지 생성 테스트 (기본값)"""
        event_type = "test_event"
        data = {"key": "value"}
        
        result = create_event_message(event_type, data)
        
        assert result["event_type"] == event_type
        assert result["data"] == data
        assert result["correlation_id"] is None
        assert "timestamp" in result
        assert result["source"] == "iacsrag"


class TestIntegration:
    """통합 테스트"""

    def setup_method(self):
        """테스트 설정"""
        # 매니저 초기화
        KafkaManager._instance = None
        KafkaManager._producer = None
        KafkaManager._consumers = {}

    @pytest.mark.asyncio
    async def test_producer_consumer_integration(self):
        """Producer-Consumer 통합 테스트"""
        settings = Settings(
            kafka_bootstrap_servers="localhost:9092",
            kafka_consumer_group_id="test_group"
        )
        
        # Manager 초기화
        manager = KafkaManager()
        manager.initialize(settings)
        
        # Mock 설정
        mock_aiokafka_producer = AsyncMock()
        mock_aiokafka_consumer = AsyncMock()
        
        with patch('src.infrastructure.messaging.kafka_client.AIOKafkaProducer') as mock_producer_class:
            with patch('src.infrastructure.messaging.kafka_client.AIOKafkaConsumer') as mock_consumer_class:
                mock_producer_class.return_value = mock_aiokafka_producer
                mock_consumer_class.return_value = mock_aiokafka_consumer
                
                # Producer 연결
                await manager.connect_producer()
                producer = manager.producer
                assert producer.is_connected is True
                
                # Consumer 생성 및 연결
                consumer = manager.create_consumer("test_consumer")
                await consumer.connect(["test_topic"])
                assert consumer.is_connected is True
                
                # 이벤트 발행
                event = {"type": "test", "data": "integration_test"}
                
                # Future 객체 생성
                mock_metadata = MagicMock()
                mock_metadata.partition = 0
                mock_metadata.offset = 123
                mock_future = asyncio.Future()
                mock_future.set_result(mock_metadata)
                mock_aiokafka_producer.send.return_value = mock_future
                
                result = await producer.send_event("test_topic", event)
                assert result is True
                
                # 정리
                await manager.disconnect_all()
