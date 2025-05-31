"""
MongoDB 인프라 모듈 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from src.core.config import Settings
from src.core.exceptions import DatabaseConnectionError
from src.infrastructure.database.mongodb import (
    MongoDBClient,
    MongoDBManager,
    mongodb_manager,
    Collections,
    DOCUMENT_INDEXES,
    CHUNK_INDEXES,
    EMBEDDING_INDEXES,
    USER_INDEXES,
    initialize_collections,
    mongodb_health_check
)


class TestMongoDBClient:
    """MongoDB 클라이언트 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 설정 초기화"""
        self.settings = Settings(
            mongodb_host="localhost",
            mongodb_port=27017,
            mongodb_database="test_db",
            mongodb_username="test_user",
            mongodb_password="test_pass",
            mongodb_max_pool_size=10,
            mongodb_min_pool_size=1
        )
        self.client = MongoDBClient(self.settings)
    
    def test_initialization(self):
        """클라이언트 초기화 테스트"""
        assert self.client.settings == self.settings
        assert self.client._client is None
        assert self.client._database is None
        assert self.client._is_connected is False
    
    def test_build_connection_string_with_auth(self):
        """인증 정보가 있는 연결 문자열 생성 테스트"""
        # 직접 속성을 설정하여 테스트
        client = MongoDBClient(self.settings)
        client.settings.mongodb_username = "test_user"
        client.settings.mongodb_password = "test_pass"
        client.settings.mongodb_host = "localhost"
        client.settings.mongodb_port = 27017
        
        # mongodb_url을 None으로 설정하여 개별 필드 사용하도록 함
        with patch.object(client.settings, 'mongodb_url', None):
            connection_string = client._build_connection_string()
            expected = "mongodb://test_user:test_pass@localhost:27017"
            assert connection_string == expected
    
    def test_build_connection_string_without_auth(self):
        """인증 정보가 없는 연결 문자열 생성 테스트"""
        settings = Settings(
            mongodb_host="localhost",
            mongodb_port=27017,
            mongodb_database="test_db"
        )
        client = MongoDBClient(settings)
        connection_string = client._build_connection_string()
        expected = "mongodb://localhost:27017"
        assert connection_string == expected
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """성공적인 연결 테스트"""
        client = MongoDBClient(self.settings)
        client.settings.mongodb_username = "test_user"
        client.settings.mongodb_password = "test_pass"
        client.settings.mongodb_host = "localhost"
        client.settings.mongodb_port = 27017
        client.settings.mongodb_max_pool_size = 10
        client.settings.mongodb_min_pool_size = 1
        
        mock_client = AsyncMock()
        mock_database = AsyncMock()
        
        with patch('src.infrastructure.database.mongodb.AsyncIOMotorClient') as mock_motor_client:
            with patch.object(client.settings, 'mongodb_url', None):
                mock_motor_client.return_value = mock_client
                mock_client.admin.command = AsyncMock(return_value={"ok": 1})
                mock_client.__getitem__.return_value = mock_database
                
                await client.connect()
                
                assert client._is_connected is True
                assert client._client == mock_client
                assert client._database == mock_database
                
                # 연결 설정 확인
                mock_motor_client.assert_called_once()
                call_args = mock_motor_client.call_args
                assert call_args[0][0] == "mongodb://test_user:test_pass@localhost:27017"
                assert call_args[1]['maxPoolSize'] == 10
                assert call_args[1]['minPoolSize'] == 1
    
    @pytest.mark.asyncio
    async def test_connect_connection_failure(self):
        """연결 실패 테스트"""
        with patch('src.infrastructure.database.mongodb.AsyncIOMotorClient') as mock_motor_client:
            mock_client = AsyncMock()
            mock_motor_client.return_value = mock_client
            mock_client.admin.command.side_effect = ConnectionFailure("Connection failed")
            
            with pytest.raises(DatabaseConnectionError, match="MongoDB 연결 실패"):
                await self.client.connect()
            
            assert self.client._is_connected is False
    
    @pytest.mark.asyncio
    async def test_connect_server_selection_timeout(self):
        """서버 선택 타임아웃 테스트"""
        with patch('src.infrastructure.database.mongodb.AsyncIOMotorClient') as mock_motor_client:
            mock_client = AsyncMock()
            mock_motor_client.return_value = mock_client
            mock_client.admin.command.side_effect = ServerSelectionTimeoutError("Timeout")
            
            with pytest.raises(DatabaseConnectionError, match="MongoDB 연결 실패"):
                await self.client.connect()
    
    @pytest.mark.asyncio
    async def test_disconnect(self):
        """연결 해제 테스트"""
        # 먼저 연결 상태로 설정
        mock_client = AsyncMock()
        self.client._client = mock_client
        self.client._database = AsyncMock()
        self.client._is_connected = True
        
        await self.client.disconnect()
        
        mock_client.close.assert_called_once()
        assert self.client._client is None
        assert self.client._database is None
        assert self.client._is_connected is False
    
    def test_database_property_connected(self):
        """연결된 상태에서 데이터베이스 속성 테스트"""
        mock_database = AsyncMock()
        self.client._database = mock_database
        self.client._is_connected = True
        
        assert self.client.database == mock_database
    
    def test_database_property_not_connected(self):
        """연결되지 않은 상태에서 데이터베이스 속성 테스트"""
        with pytest.raises(DatabaseConnectionError, match="MongoDB에 연결되지 않음"):
            _ = self.client.database
    
    def test_client_property_connected(self):
        """연결된 상태에서 클라이언트 속성 테스트"""
        mock_client = AsyncMock()
        self.client._client = mock_client
        self.client._is_connected = True
        
        assert self.client.client == mock_client
    
    def test_client_property_not_connected(self):
        """연결되지 않은 상태에서 클라이언트 속성 테스트"""
        with pytest.raises(DatabaseConnectionError, match="MongoDB에 연결되지 않음"):
            _ = self.client.client
    
    def test_is_connected_property(self):
        """연결 상태 속성 테스트"""
        assert self.client.is_connected is False
        
        self.client._is_connected = True
        assert self.client.is_connected is True
    
    def test_get_collection(self):
        """컬렉션 가져오기 테스트"""
        mock_database = AsyncMock()
        mock_collection = AsyncMock()
        mock_database.__getitem__.return_value = mock_collection
        
        self.client._database = mock_database
        self.client._is_connected = True
        
        collection = self.client.get_collection("test_collection")
        
        mock_database.__getitem__.assert_called_once_with("test_collection")
        assert collection == mock_collection
    
    @pytest.mark.asyncio
    async def test_create_indexes_success(self):
        """인덱스 생성 성공 테스트"""
        mock_collection = AsyncMock()
        mock_database = AsyncMock()
        mock_database.__getitem__.return_value = mock_collection
        
        self.client._database = mock_database
        self.client._is_connected = True
        
        indexes = [("field1", 1), ("field2", -1)]
        
        await self.client.create_indexes("test_collection", indexes)
        
        assert mock_collection.create_index.call_count == 2
        mock_collection.create_index.assert_any_call(("field1", 1))
        mock_collection.create_index.assert_any_call(("field2", -1))
    
    @pytest.mark.asyncio
    async def test_create_indexes_failure(self):
        """인덱스 생성 실패 테스트"""
        mock_collection = AsyncMock()
        mock_collection.create_index.side_effect = Exception("Index creation failed")
        mock_database = AsyncMock()
        mock_database.__getitem__.return_value = mock_collection
        
        self.client._database = mock_database
        self.client._is_connected = True
        
        indexes = [("field1", 1)]
        
        with pytest.raises(Exception, match="Index creation failed"):
            await self.client.create_indexes("test_collection", indexes)
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """정상 상태 헬스체크 테스트"""
        mock_client = AsyncMock()
        mock_client.admin.command.return_value = {
            "version": "5.0.0",
            "uptime": 12345,
            "connections": {"current": 10, "available": 90}
        }
        
        # 데이터베이스 이름을 명시적으로 설정
        self.client.settings.mongodb_database = "test_db"
        self.client._client = mock_client
        self.client._is_connected = True
        
        result = await self.client.health_check()
        
        assert result["status"] == "healthy"
        assert result["database"] == "test_db"
        assert result["version"] == "5.0.0"
        assert result["uptime"] == 12345
        assert result["connections"]["current"] == 10
    
    @pytest.mark.asyncio
    async def test_health_check_disconnected(self):
        """연결 해제 상태 헬스체크 테스트"""
        result = await self.client.health_check()
        
        assert result["status"] == "disconnected"
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_health_check_error(self):
        """헬스체크 오류 테스트"""
        mock_client = AsyncMock()
        mock_client.admin.command.side_effect = Exception("Health check failed")
        
        self.client._client = mock_client
        self.client._is_connected = True
        
        result = await self.client.health_check()
        
        assert result["status"] == "unhealthy"
        assert "Health check failed" in result["error"]


class TestMongoDBManager:
    """MongoDB 매니저 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 매니저 초기화"""
        # 싱글톤 인스턴스 초기화
        MongoDBManager._instance = None
        MongoDBManager._client = None
    
    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        manager1 = MongoDBManager()
        manager2 = MongoDBManager()
        
        assert manager1 is manager2
    
    def test_initialize(self):
        """매니저 초기화 테스트"""
        settings = Settings(mongodb_database="test_db")
        manager = MongoDBManager()
        
        manager.initialize(settings)
        
        assert manager._client is not None
        assert isinstance(manager._client, MongoDBClient)
        assert manager._client.settings == settings
    
    def test_initialize_already_initialized(self):
        """이미 초기화된 매니저 재초기화 테스트"""
        settings = Settings(mongodb_database="test_db")
        manager = MongoDBManager()
        
        manager.initialize(settings)
        first_client = manager._client
        
        # 다시 초기화 시도
        manager.initialize(settings)
        
        # 같은 클라이언트 인스턴스여야 함
        assert manager._client is first_client
    
    @pytest.mark.asyncio
    async def test_connect(self):
        """매니저 연결 테스트"""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        
        manager = MongoDBManager()
        manager._client = mock_client
        
        await manager.connect()
        
        mock_client.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_no_client(self):
        """클라이언트가 없는 상태에서 연결 테스트"""
        manager = MongoDBManager()
        
        # 클라이언트가 없어도 예외가 발생하지 않아야 함
        await manager.connect()
    
    @pytest.mark.asyncio
    async def test_disconnect(self):
        """매니저 연결 해제 테스트"""
        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()
        
        manager = MongoDBManager()
        manager._client = mock_client
        
        await manager.disconnect()
        
        mock_client.disconnect.assert_called_once()
    
    def test_client_property(self):
        """클라이언트 속성 테스트"""
        mock_client = MagicMock()
        manager = MongoDBManager()
        manager._client = mock_client
        
        assert manager.client == mock_client
    
    def test_client_property_not_initialized(self):
        """초기화되지 않은 클라이언트 속성 테스트"""
        manager = MongoDBManager()
        
        with pytest.raises(DatabaseConnectionError, match="MongoDB 클라이언트가 초기화되지 않음"):
            _ = manager.client


class TestCollections:
    """컬렉션 상수 테스트"""
    
    def test_collection_names(self):
        """컬렉션 이름 상수 테스트"""
        assert Collections.DOCUMENTS == "documents"
        assert Collections.CHUNKS == "chunks"
        assert Collections.EMBEDDINGS == "embeddings"
        assert Collections.USERS == "users"
        assert Collections.PROCESSING_LOGS == "processing_logs"
        assert Collections.SEARCH_LOGS == "search_logs"


class TestIndexes:
    """인덱스 정의 테스트"""
    
    def test_document_indexes(self):
        """문서 인덱스 정의 테스트"""
        assert len(DOCUMENT_INDEXES) == 5
        assert [("document_id", 1)] in DOCUMENT_INDEXES
        assert [("user_id", 1)] in DOCUMENT_INDEXES
        assert [("file_hash", 1)] in DOCUMENT_INDEXES
        assert [("created_at", -1)] in DOCUMENT_INDEXES
        assert [("status", 1)] in DOCUMENT_INDEXES
    
    def test_chunk_indexes(self):
        """청크 인덱스 정의 테스트"""
        assert len(CHUNK_INDEXES) == 4
        assert [("document_id", 1)] in CHUNK_INDEXES
        assert [("chunk_index", 1)] in CHUNK_INDEXES
        assert [("content_hash", 1)] in CHUNK_INDEXES
        assert [("document_id", 1), ("chunk_index", 1)] in CHUNK_INDEXES
    
    def test_embedding_indexes(self):
        """임베딩 인덱스 정의 테스트"""
        assert len(EMBEDDING_INDEXES) == 3
        assert [("chunk_id", 1)] in EMBEDDING_INDEXES
        assert [("document_id", 1)] in EMBEDDING_INDEXES
        assert [("embedding_model", 1)] in EMBEDDING_INDEXES
    
    def test_user_indexes(self):
        """사용자 인덱스 정의 테스트"""
        assert len(USER_INDEXES) == 2
        assert [("email", 1)] in USER_INDEXES
        assert [("created_at", -1)] in USER_INDEXES


class TestUtilityFunctions:
    """유틸리티 함수 테스트"""
    
    @pytest.mark.asyncio
    async def test_initialize_collections_success(self):
        """컬렉션 초기화 성공 테스트"""
        mock_client = AsyncMock()
        
        with patch('src.infrastructure.database.mongodb.mongodb_manager') as mock_manager:
            mock_manager.client = mock_client
            
            await initialize_collections()
            
            # 각 컬렉션에 대해 인덱스 생성이 호출되었는지 확인
            assert mock_client.create_indexes.call_count == 4
            mock_client.create_indexes.assert_any_call(Collections.DOCUMENTS, DOCUMENT_INDEXES)
            mock_client.create_indexes.assert_any_call(Collections.CHUNKS, CHUNK_INDEXES)
            mock_client.create_indexes.assert_any_call(Collections.EMBEDDINGS, EMBEDDING_INDEXES)
            mock_client.create_indexes.assert_any_call(Collections.USERS, USER_INDEXES)
    
    @pytest.mark.asyncio
    async def test_initialize_collections_failure(self):
        """컬렉션 초기화 실패 테스트"""
        mock_client = AsyncMock()
        mock_client.create_indexes.side_effect = Exception("Index creation failed")
        
        with patch('src.infrastructure.database.mongodb.mongodb_manager') as mock_manager:
            mock_manager.client = mock_client
            
            with pytest.raises(Exception, match="Index creation failed"):
                await initialize_collections()
    
    @pytest.mark.asyncio
    async def test_mongodb_health_check_success(self):
        """MongoDB 헬스체크 성공 테스트"""
        mock_client = AsyncMock()
        mock_client.health_check.return_value = {"status": "healthy"}
        
        with patch('src.infrastructure.database.mongodb.mongodb_manager') as mock_manager:
            mock_manager.client = mock_client
            
            result = await mongodb_health_check()
            
            assert result["status"] == "healthy"
            mock_client.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mongodb_health_check_error(self):
        """MongoDB 헬스체크 오류 테스트"""
        with patch('src.infrastructure.database.mongodb.mongodb_manager') as mock_manager:
            mock_manager.client.health_check.side_effect = Exception("Health check failed")
            
            result = await mongodb_health_check()
            
            assert result["status"] == "error"
            assert "Health check failed" in result["error"]


class TestIntegration:
    """통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """전체 생명주기 테스트"""
        settings = Settings(
            mongodb_host="localhost",
            mongodb_port=27017,
            mongodb_database="test_db"
        )
        
        # 매니저 초기화
        manager = MongoDBManager()
        manager.initialize(settings)
        
        # 클라이언트 모킹
        mock_client = AsyncMock()
        mock_database = AsyncMock()
        mock_collection = AsyncMock()
        
        with patch('src.infrastructure.database.mongodb.AsyncIOMotorClient') as mock_motor_client:
            mock_motor_client.return_value = mock_client
            mock_client.admin.command = AsyncMock(return_value={"ok": 1})
            mock_client.__getitem__.return_value = mock_database
            mock_database.__getitem__.return_value = mock_collection
            
            # 연결
            await manager.connect()
            
            # 클라이언트 사용
            client = manager.client
            assert client.is_connected is True
            
            # 컬렉션 가져오기
            collection = client.get_collection("test_collection")
            assert collection == mock_collection
            
            # 헬스체크
            mock_client.admin.command.return_value = {
                "version": "5.0.0",
                "uptime": 12345,
                "connections": {"current": 10}
            }
            
            health = await client.health_check()
            assert health["status"] == "healthy"
            
            # 연결 해제
            await manager.disconnect()
            assert client.is_connected is False
