"""
MongoDB 연결 관리 및 클라이언트 설정
"""

from typing import Optional, Dict, Any
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from contextlib import asynccontextmanager

from src.core.config import Settings
from src.core.logging import LoggerMixin, get_logger
from src.core.exceptions import DatabaseConnectionError

logger = get_logger(__name__)


class MongoDBClient(LoggerMixin):
    """MongoDB 비동기 클라이언트 관리"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[AsyncIOMotorDatabase] = None
        self._is_connected = False
    
    async def connect(self) -> None:
        """MongoDB에 연결"""
        try:
            # 연결 문자열 구성
            connection_string = self._build_connection_string()
            
            # 클라이언트 생성
            self._client = AsyncIOMotorClient(
                connection_string,
                maxPoolSize=self.settings.mongodb_max_pool_size,
                minPoolSize=self.settings.mongodb_min_pool_size,
                maxIdleTimeMS=30000,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=20000,
                retryWrites=True,
                retryReads=True
            )
            
            # 연결 테스트
            await self._client.admin.command('ping')
            
            # 데이터베이스 선택
            self._database = self._client[self.settings.mongodb_database]
            
            self._is_connected = True
            self.logger.info(
                "MongoDB 연결 성공",
                database=self.settings.mongodb_database,
                host=self.settings.mongodb_host,
                port=self.settings.mongodb_port
            )
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            self.logger.error("MongoDB 연결 실패", error=str(e))
            raise DatabaseConnectionError(f"MongoDB 연결 실패: {e}")
        except Exception as e:
            self.logger.error("MongoDB 연결 중 예상치 못한 오류", error=str(e))
            raise DatabaseConnectionError(f"MongoDB 연결 오류: {e}")
    
    async def disconnect(self) -> None:
        """MongoDB 연결 해제"""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            self._is_connected = False
            self.logger.info("MongoDB 연결 해제 완료")
    
    def _build_connection_string(self) -> str:
        """MongoDB 연결 문자열 생성"""
        # mongodb_url이 설정되어 있고 비어있지 않으면 그것을 사용
        try:
            if self.settings.mongodb_url and self.settings.mongodb_url.strip():
                return self.settings.mongodb_url
        except (AttributeError, ValueError):
            # mongodb_url이 없거나 유효하지 않은 경우 개별 필드 사용
            pass
        
        # 개별 필드로 연결 문자열 구성
        if self.settings.mongodb_username and self.settings.mongodb_password:
            # 인증이 필요한 경우
            auth_part = f"{self.settings.mongodb_username}:{self.settings.mongodb_password}@"
        else:
            auth_part = ""
        
        connection_string = (
            f"mongodb://{auth_part}"
            f"{self.settings.mongodb_host}:{self.settings.mongodb_port}"
        )
        
        return connection_string
    
    @property
    def database(self) -> AsyncIOMotorDatabase:
        """데이터베이스 인스턴스 반환"""
        if not self._is_connected or not self._database:
            raise DatabaseConnectionError("MongoDB에 연결되지 않음")
        return self._database
    
    @property
    def client(self) -> AsyncIOMotorClient:
        """클라이언트 인스턴스 반환"""
        if not self._is_connected or not self._client:
            raise DatabaseConnectionError("MongoDB에 연결되지 않음")
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._is_connected
    
    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        """컬렉션 인스턴스 반환"""
        return self.database[collection_name]
    
    async def create_indexes(self, collection_name: str, indexes: list) -> None:
        """인덱스 생성"""
        try:
            collection = self.get_collection(collection_name)
            
            for index in indexes:
                await collection.create_index(index)
            
            self.logger.info(
                "인덱스 생성 완료",
                collection=collection_name,
                indexes_count=len(indexes)
            )
            
        except Exception as e:
            self.logger.error(
                "인덱스 생성 실패",
                collection=collection_name,
                error=str(e)
            )
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """MongoDB 상태 확인"""
        try:
            if not self._is_connected:
                return {"status": "disconnected", "error": "Not connected"}
            
            # ping 테스트
            await self._client.admin.command('ping')
            
            # 서버 상태 정보
            server_status = await self._client.admin.command('serverStatus')
            
            return {
                "status": "healthy",
                "database": self.settings.mongodb_database,
                "version": server_status.get("version"),
                "uptime": server_status.get("uptime"),
                "connections": server_status.get("connections", {})
            }
            
        except Exception as e:
            self.logger.error("MongoDB 상태 확인 실패", error=str(e))
            return {"status": "unhealthy", "error": str(e)}


class MongoDBManager:
    """MongoDB 연결 관리자 (싱글톤)"""
    
    _instance: Optional['MongoDBManager'] = None
    _client: Optional[MongoDBClient] = None
    
    def __new__(cls) -> 'MongoDBManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, settings: Settings) -> None:
        """MongoDB 클라이언트 초기화"""
        if self._client is None:
            self._client = MongoDBClient(settings)
    
    async def connect(self) -> None:
        """연결 시작"""
        if self._client:
            await self._client.connect()
    
    async def disconnect(self) -> None:
        """연결 종료"""
        if self._client:
            await self._client.disconnect()
    
    @property
    def client(self) -> MongoDBClient:
        """클라이언트 인스턴스 반환"""
        if self._client is None:
            raise DatabaseConnectionError("MongoDB 클라이언트가 초기화되지 않음")
        return self._client


# 전역 매니저 인스턴스
mongodb_manager = MongoDBManager()


@asynccontextmanager
async def get_mongodb_client():
    """MongoDB 클라이언트 컨텍스트 매니저"""
    try:
        yield mongodb_manager.client
    except Exception as e:
        logger.error("MongoDB 클라이언트 사용 중 오류", error=str(e))
        raise


async def get_database() -> AsyncIOMotorDatabase:
    """데이터베이스 인스턴스 반환 (의존성 주입용)"""
    return mongodb_manager.client.database


async def get_collection(collection_name: str) -> AsyncIOMotorCollection:
    """컬렉션 인스턴스 반환 (의존성 주입용)"""
    return mongodb_manager.client.get_collection(collection_name)


# 컬렉션 이름 상수
class Collections:
    """MongoDB 컬렉션 이름 상수"""
    DOCUMENTS = "documents"
    CHUNKS = "chunks"
    EMBEDDINGS = "embeddings"
    USERS = "users"
    PROCESSING_LOGS = "processing_logs"
    SEARCH_LOGS = "search_logs"


# 인덱스 정의
DOCUMENT_INDEXES = [
    [("document_id", 1)],  # 문서 ID 인덱스
    [("user_id", 1)],      # 사용자 ID 인덱스
    [("file_hash", 1)],    # 파일 해시 인덱스 (중복 방지)
    [("created_at", -1)],  # 생성일 인덱스 (최신순 정렬)
    [("status", 1)],       # 상태 인덱스
]

CHUNK_INDEXES = [
    [("document_id", 1)],     # 문서 ID 인덱스
    [("chunk_index", 1)],     # 청크 인덱스
    [("content_hash", 1)],    # 내용 해시 인덱스 (중복 방지)
    [("document_id", 1), ("chunk_index", 1)],  # 복합 인덱스
]

EMBEDDING_INDEXES = [
    [("chunk_id", 1)],        # 청크 ID 인덱스
    [("document_id", 1)],     # 문서 ID 인덱스
    [("embedding_model", 1)], # 임베딩 모델 인덱스
]

USER_INDEXES = [
    [("email", 1)],           # 이메일 인덱스 (유니크)
    [("created_at", -1)],     # 생성일 인덱스
]


async def initialize_collections() -> None:
    """컬렉션 및 인덱스 초기화"""
    try:
        client = mongodb_manager.client
        
        # 문서 컬렉션 인덱스
        await client.create_indexes(Collections.DOCUMENTS, DOCUMENT_INDEXES)
        
        # 청크 컬렉션 인덱스
        await client.create_indexes(Collections.CHUNKS, CHUNK_INDEXES)
        
        # 임베딩 컬렉션 인덱스
        await client.create_indexes(Collections.EMBEDDINGS, EMBEDDING_INDEXES)
        
        # 사용자 컬렉션 인덱스
        await client.create_indexes(Collections.USERS, USER_INDEXES)
        
        logger.info("MongoDB 컬렉션 및 인덱스 초기화 완료")
        
    except Exception as e:
        logger.error("MongoDB 컬렉션 초기화 실패", error=str(e))
        raise


# 헬스체크 함수
async def mongodb_health_check() -> Dict[str, Any]:
    """MongoDB 헬스체크"""
    try:
        return await mongodb_manager.client.health_check()
    except Exception as e:
        return {"status": "error", "error": str(e)}
