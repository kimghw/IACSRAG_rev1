"""
Qdrant 벡터 데이터베이스 클라이언트
"""

from typing import List, Dict, Any, Optional, Union
import asyncio
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import (
    Distance, VectorParams, CreateCollection, PointStruct,
    Filter, FieldCondition, MatchValue, SearchRequest
)
from qdrant_client.http.exceptions import UnexpectedResponse

from src.core.config import Settings
from src.core.logging import LoggerMixin, get_logger
from src.core.exceptions import VectorStoreConnectionError, VectorStoreOperationError

logger = get_logger(__name__)


class QdrantVectorClient(LoggerMixin):
    """Qdrant 벡터 데이터베이스 클라이언트"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: Optional[QdrantClient] = None
        self._is_connected = False
    
    async def connect(self) -> None:
        """Qdrant에 연결"""
        try:
            # Qdrant 클라이언트 생성
            if self.settings.qdrant_api_key:
                self._client = QdrantClient(
                    url=self.settings.qdrant_url,
                    api_key=self.settings.qdrant_api_key,
                    timeout=30
                )
            else:
                self._client = QdrantClient(
                    url=self.settings.qdrant_url,
                    timeout=30
                )
            
            # 연결 테스트
            collections = await asyncio.to_thread(self._client.get_collections)
            
            self._is_connected = True
            self.logger.info(
                "Qdrant 연결 성공",
                url=self.settings.qdrant_url,
                collections_count=len(collections.collections)
            )
            
        except Exception as e:
            self.logger.error("Qdrant 연결 실패", error=str(e))
            raise VectorStoreConnectionError(f"Qdrant 연결 실패: {e}")
    
    async def disconnect(self) -> None:
        """Qdrant 연결 해제"""
        if self._client:
            try:
                await asyncio.to_thread(self._client.close)
            except Exception as e:
                self.logger.warning("Qdrant 연결 해제 중 오류", error=str(e))
            finally:
                self._client = None
                self._is_connected = False
                self.logger.info("Qdrant 연결 해제 완료")
    
    @property
    def client(self) -> QdrantClient:
        """클라이언트 인스턴스 반환"""
        if not self._is_connected or not self._client:
            raise VectorStoreConnectionError("Qdrant에 연결되지 않음")
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._is_connected
    
    async def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
        force_recreate: bool = False
    ) -> bool:
        """컬렉션 생성"""
        try:
            # 기존 컬렉션 확인
            collections = await asyncio.to_thread(self.client.get_collections)
            existing_collections = [col.name for col in collections.collections]
            
            if collection_name in existing_collections:
                if force_recreate:
                    await asyncio.to_thread(
                        self.client.delete_collection,
                        collection_name=collection_name
                    )
                    self.logger.info(
                        "기존 컬렉션 삭제",
                        collection=collection_name
                    )
                else:
                    self.logger.info(
                        "컬렉션이 이미 존재함",
                        collection=collection_name
                    )
                    return True
            
            # 컬렉션 생성
            await asyncio.to_thread(
                self.client.create_collection,
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance
                )
            )
            
            self.logger.info(
                "컬렉션 생성 완료",
                collection=collection_name,
                vector_size=vector_size,
                distance=distance.value
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "컬렉션 생성 실패",
                collection=collection_name,
                error=str(e)
            )
            raise VectorStoreOperationError(f"컬렉션 생성 실패: {e}")
    
    async def upsert_points(
        self,
        collection_name: str,
        points: List[PointStruct]
    ) -> bool:
        """포인트 업서트"""
        try:
            await asyncio.to_thread(
                self.client.upsert,
                collection_name=collection_name,
                points=points
            )
            
            self.logger.info(
                "포인트 업서트 완료",
                collection=collection_name,
                points_count=len(points)
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "포인트 업서트 실패",
                collection=collection_name,
                points_count=len(points),
                error=str(e)
            )
            raise VectorStoreOperationError(f"포인트 업서트 실패: {e}")
    
    async def search_points(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Filter] = None
    ) -> List[Dict[str, Any]]:
        """벡터 검색"""
        try:
            search_result = await asyncio.to_thread(
                self.client.search,
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=filter_conditions
            )
            
            # 결과 변환
            results = []
            for point in search_result:
                results.append({
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload or {}
                })
            
            self.logger.info(
                "벡터 검색 완료",
                collection=collection_name,
                results_count=len(results),
                limit=limit
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                "벡터 검색 실패",
                collection=collection_name,
                error=str(e)
            )
            raise VectorStoreOperationError(f"벡터 검색 실패: {e}")
    
    async def delete_points(
        self,
        collection_name: str,
        point_ids: List[Union[str, int]]
    ) -> bool:
        """포인트 삭제"""
        try:
            await asyncio.to_thread(
                self.client.delete,
                collection_name=collection_name,
                points_selector=models.PointIdsList(
                    points=point_ids
                )
            )
            
            self.logger.info(
                "포인트 삭제 완료",
                collection=collection_name,
                deleted_count=len(point_ids)
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "포인트 삭제 실패",
                collection=collection_name,
                error=str(e)
            )
            raise VectorStoreOperationError(f"포인트 삭제 실패: {e}")
    
    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """컬렉션 정보 조회"""
        try:
            collection_info = await asyncio.to_thread(
                self.client.get_collection,
                collection_name=collection_name
            )
            
            return {
                "name": collection_info.config.params.vectors.size,
                "vector_size": collection_info.config.params.vectors.size,
                "distance": collection_info.config.params.vectors.distance.value,
                "points_count": collection_info.points_count,
                "status": collection_info.status.value
            }
            
        except Exception as e:
            self.logger.error(
                "컬렉션 정보 조회 실패",
                collection=collection_name,
                error=str(e)
            )
            raise VectorStoreOperationError(f"컬렉션 정보 조회 실패: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Qdrant 상태 확인"""
        try:
            if not self._is_connected:
                return {"status": "disconnected", "error": "Not connected"}
            
            # 컬렉션 목록 조회로 연결 상태 확인
            collections = await asyncio.to_thread(self.client.get_collections)
            
            return {
                "status": "healthy",
                "url": self.settings.qdrant_url,
                "collections_count": len(collections.collections),
                "collections": [col.name for col in collections.collections]
            }
            
        except Exception as e:
            self.logger.error("Qdrant 상태 확인 실패", error=str(e))
            return {"status": "unhealthy", "error": str(e)}


class QdrantManager:
    """Qdrant 연결 관리자 (싱글톤)"""
    
    _instance: Optional['QdrantManager'] = None
    _client: Optional[QdrantVectorClient] = None
    
    def __new__(cls) -> 'QdrantManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, settings: Settings) -> None:
        """Qdrant 클라이언트 초기화"""
        if self._client is None:
            self._client = QdrantVectorClient(settings)
    
    async def connect(self) -> None:
        """연결 시작"""
        if self._client:
            await self._client.connect()
    
    async def disconnect(self) -> None:
        """연결 종료"""
        if self._client:
            await self._client.disconnect()
    
    @property
    def client(self) -> QdrantVectorClient:
        """클라이언트 인스턴스 반환"""
        if self._client is None:
            raise VectorStoreConnectionError("Qdrant 클라이언트가 초기화되지 않음")
        return self._client


# 전역 매니저 인스턴스
qdrant_manager = QdrantManager()


# 유틸리티 함수들
async def initialize_qdrant_collections(settings: Settings) -> None:
    """Qdrant 컬렉션 초기화"""
    try:
        client = qdrant_manager.client
        
        # 기본 컬렉션 생성
        await client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.qdrant_vector_size,
            distance=Distance.COSINE
        )
        
        logger.info("Qdrant 컬렉션 초기화 완료")
        
    except Exception as e:
        logger.error("Qdrant 컬렉션 초기화 실패", error=str(e))
        raise


async def qdrant_health_check() -> Dict[str, Any]:
    """Qdrant 헬스체크"""
    try:
        return await qdrant_manager.client.health_check()
    except Exception as e:
        return {"status": "error", "error": str(e)}


# 의존성 주입용 함수들
async def get_qdrant_client() -> QdrantVectorClient:
    """Qdrant 클라이언트 반환 (의존성 주입용)"""
    return qdrant_manager.client


def create_point_struct(
    point_id: Union[str, int],
    vector: List[float],
    payload: Optional[Dict[str, Any]] = None
) -> PointStruct:
    """PointStruct 생성 헬퍼 함수"""
    return PointStruct(
        id=point_id,
        vector=vector,
        payload=payload or {}
    )


def create_filter_condition(
    field: str,
    value: Any,
    match_type: str = "value"
) -> Filter:
    """필터 조건 생성 헬퍼 함수"""
    if match_type == "value":
        condition = FieldCondition(
            key=field,
            match=MatchValue(value=value)
        )
    else:
        # 추후 다른 매치 타입 지원 확장 가능
        condition = FieldCondition(
            key=field,
            match=MatchValue(value=value)
        )
    
    return Filter(must=[condition])
