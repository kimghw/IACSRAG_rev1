"""
Qdrant 인프라 모듈 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from qdrant_client.http.models import Distance, PointStruct, CollectionsResponse, CollectionInfo
from qdrant_client.http.exceptions import UnexpectedResponse

from src.core.config import Settings
from src.core.exceptions import VectorStoreConnectionError, VectorStoreOperationError
from src.infrastructure.vectordb.qdrant_client import (
    QdrantVectorClient,
    QdrantManager,
    qdrant_manager,
    initialize_qdrant_collections,
    qdrant_health_check,
    create_point_struct,
    create_filter_condition
)


class TestQdrantVectorClient:
    """Qdrant 벡터 클라이언트 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 설정 초기화"""
        self.settings = Settings(
            qdrant_url="http://localhost:6333",
            qdrant_api_key="test_api_key",
            qdrant_collection_name="test_collection",
            qdrant_vector_size=1536
        )
        self.client = QdrantVectorClient(self.settings)
    
    def test_initialization(self):
        """클라이언트 초기화 테스트"""
        assert self.client.settings == self.settings
        assert self.client._client is None
        assert self.client._is_connected is False
    
    @pytest.mark.asyncio
    async def test_connect_with_api_key(self):
        """API 키가 있는 연결 테스트"""
        # API 키가 있는 설정으로 새 클라이언트 생성
        # 환경 변수 없이 직접 값 설정
        import os
        os.environ['QDRANT_URL'] = 'http://localhost:6333'
        os.environ['QDRANT_API_KEY'] = 'test_api_key'
        os.environ['QDRANT_COLLECTION_NAME'] = 'test_collection'
        os.environ['MONGODB_URL'] = 'mongodb://localhost:27017'
        os.environ['MONGODB_DATABASE'] = 'test_db'
        os.environ['KAFKA_BOOTSTRAP_SERVERS'] = 'localhost:9092'
        os.environ['KAFKA_TOPIC_DOCUMENT_UPLOADED'] = 'test_topic'
        os.environ['KAFKA_TOPIC_TEXT_EXTRACTED'] = 'test_topic'
        os.environ['KAFKA_TOPIC_CHUNKS_CREATED'] = 'test_topic'
        os.environ['KAFKA_TOPIC_EMBEDDINGS_GENERATED'] = 'test_topic'
        os.environ['KAFKA_CONSUMER_GROUP_ID'] = 'test_group'
        os.environ['OPENAI_API_KEY'] = 'test_key'
        os.environ['SECRET_KEY'] = 'test_secret'
        
        try:
            settings_with_key = Settings()
            client_with_key = QdrantVectorClient(settings_with_key)
            
            # API 키가 제대로 설정되었는지 확인
            assert settings_with_key.qdrant_api_key == "test_api_key"
            
            mock_qdrant_client = MagicMock()
            mock_collections = MagicMock()
            mock_collections.collections = []
            
            with patch('src.infrastructure.vectordb.qdrant_client.QdrantClient') as mock_client_class:
                with patch('asyncio.to_thread') as mock_to_thread:
                    mock_client_class.return_value = mock_qdrant_client
                    mock_to_thread.return_value = mock_collections
                    
                    await client_with_key.connect()
                    
                    # API 키와 함께 클라이언트가 생성되었는지 확인
                    mock_client_class.assert_called_once_with(
                        url="http://localhost:6333",
                        api_key="test_api_key",
                        timeout=30
                    )
                    
                    assert client_with_key._is_connected is True
                    assert client_with_key._client == mock_qdrant_client
        finally:
            # 환경 변수 정리
            for key in ['QDRANT_URL', 'QDRANT_API_KEY', 'QDRANT_COLLECTION_NAME', 
                       'MONGODB_URL', 'MONGODB_DATABASE', 'KAFKA_BOOTSTRAP_SERVERS',
                       'KAFKA_TOPIC_DOCUMENT_UPLOADED', 'KAFKA_TOPIC_TEXT_EXTRACTED',
                       'KAFKA_TOPIC_CHUNKS_CREATED', 'KAFKA_TOPIC_EMBEDDINGS_GENERATED',
                       'KAFKA_CONSUMER_GROUP_ID', 'OPENAI_API_KEY', 'SECRET_KEY']:
                os.environ.pop(key, None)
    
    @pytest.mark.asyncio
    async def test_connect_without_api_key(self):
        """API 키가 없는 연결 테스트"""
        settings = Settings(
            qdrant_url="http://localhost:6333",
            qdrant_collection_name="test_collection",
            qdrant_vector_size=1536
        )
        client = QdrantVectorClient(settings)
        
        mock_qdrant_client = MagicMock()
        mock_collections = MagicMock()
        mock_collections.collections = []
        
        with patch('src.infrastructure.vectordb.qdrant_client.QdrantClient') as mock_client_class:
            with patch('asyncio.to_thread') as mock_to_thread:
                mock_client_class.return_value = mock_qdrant_client
                mock_to_thread.return_value = mock_collections
                
                await client.connect()
                
                # API 키 없이 클라이언트가 생성되었는지 확인
                mock_client_class.assert_called_once_with(
                    url="http://localhost:6333",
                    timeout=30
                )
                
                assert client._is_connected is True
    
    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """연결 실패 테스트"""
        with patch('src.infrastructure.vectordb.qdrant_client.QdrantClient') as mock_client_class:
            mock_client_class.side_effect = Exception("Connection failed")
            
            with pytest.raises(VectorStoreConnectionError, match="Qdrant 연결 실패"):
                await self.client.connect()
            
            assert self.client._is_connected is False
    
    @pytest.mark.asyncio
    async def test_disconnect(self):
        """연결 해제 테스트"""
        # 먼저 연결 상태로 설정
        mock_client = AsyncMock()
        self.client._client = mock_client
        self.client._is_connected = True
        
        with patch('asyncio.to_thread') as mock_to_thread:
            await self.client.disconnect()
            
            mock_to_thread.assert_called_once_with(mock_client.close)
            assert self.client._client is None
            assert self.client._is_connected is False
    
    def test_client_property_connected(self):
        """연결된 상태에서 클라이언트 속성 테스트"""
        mock_client = MagicMock()
        self.client._client = mock_client
        self.client._is_connected = True
        
        assert self.client.client == mock_client
    
    def test_client_property_not_connected(self):
        """연결되지 않은 상태에서 클라이언트 속성 테스트"""
        with pytest.raises(VectorStoreConnectionError, match="Qdrant에 연결되지 않음"):
            _ = self.client.client
    
    def test_is_connected_property(self):
        """연결 상태 속성 테스트"""
        assert self.client.is_connected is False
        
        self.client._is_connected = True
        assert self.client.is_connected is True
    
    @pytest.mark.asyncio
    async def test_create_collection_new(self):
        """새 컬렉션 생성 테스트"""
        mock_client = MagicMock()
        mock_collections = MagicMock()
        mock_collections.collections = []  # 기존 컬렉션 없음
        
        self.client._client = mock_client
        self.client._is_connected = True
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = [mock_collections, None]  # get_collections, create_collection
            
            result = await self.client.create_collection(
                collection_name="test_collection",
                vector_size=1536,
                distance=Distance.COSINE
            )
            
            assert result is True
            assert mock_to_thread.call_count == 2
    
    @pytest.mark.asyncio
    async def test_create_collection_exists_no_recreate(self):
        """기존 컬렉션이 있고 재생성하지 않는 경우 테스트"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        
        self.client._client = mock_client
        self.client._is_connected = True
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = mock_collections
            
            result = await self.client.create_collection(
                collection_name="test_collection",
                vector_size=1536,
                force_recreate=False
            )
            
            assert result is True
            # get_collections만 호출되고 create_collection은 호출되지 않음
            assert mock_to_thread.call_count == 1
    
    @pytest.mark.asyncio
    async def test_create_collection_exists_with_recreate(self):
        """기존 컬렉션이 있고 재생성하는 경우 테스트"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        
        self.client._client = mock_client
        self.client._is_connected = True
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = [mock_collections, None, None]  # get, delete, create
            
            result = await self.client.create_collection(
                collection_name="test_collection",
                vector_size=1536,
                force_recreate=True
            )
            
            assert result is True
            assert mock_to_thread.call_count == 3
    
    @pytest.mark.asyncio
    async def test_create_collection_failure(self):
        """컬렉션 생성 실패 테스트"""
        mock_client = MagicMock()
        self.client._client = mock_client
        self.client._is_connected = True
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = Exception("Creation failed")
            
            with pytest.raises(VectorStoreOperationError, match="컬렉션 생성 실패"):
                await self.client.create_collection("test_collection", 1536)
    
    @pytest.mark.asyncio
    async def test_upsert_points_success(self):
        """포인트 업서트 성공 테스트"""
        mock_client = MagicMock()
        self.client._client = mock_client
        self.client._is_connected = True
        
        points = [
            PointStruct(id="1", vector=[0.1, 0.2, 0.3], payload={"text": "test1"}),
            PointStruct(id="2", vector=[0.4, 0.5, 0.6], payload={"text": "test2"})
        ]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = None
            
            result = await self.client.upsert_points("test_collection", points)
            
            assert result is True
            mock_to_thread.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upsert_points_failure(self):
        """포인트 업서트 실패 테스트"""
        mock_client = MagicMock()
        self.client._client = mock_client
        self.client._is_connected = True
        
        points = [PointStruct(id="1", vector=[0.1, 0.2, 0.3])]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = Exception("Upsert failed")
            
            with pytest.raises(VectorStoreOperationError, match="포인트 업서트 실패"):
                await self.client.upsert_points("test_collection", points)
    
    @pytest.mark.asyncio
    async def test_search_points_success(self):
        """벡터 검색 성공 테스트"""
        mock_client = MagicMock()
        self.client._client = mock_client
        self.client._is_connected = True
        
        # 모의 검색 결과
        mock_point1 = MagicMock()
        mock_point1.id = "1"
        mock_point1.score = 0.95
        mock_point1.payload = {"text": "test1"}
        
        mock_point2 = MagicMock()
        mock_point2.id = "2"
        mock_point2.score = 0.85
        mock_point2.payload = {"text": "test2"}
        
        mock_search_result = [mock_point1, mock_point2]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = mock_search_result
            
            results = await self.client.search_points(
                collection_name="test_collection",
                query_vector=[0.1, 0.2, 0.3],
                limit=10
            )
            
            assert len(results) == 2
            assert results[0]["id"] == "1"
            assert results[0]["score"] == 0.95
            assert results[0]["payload"]["text"] == "test1"
            assert results[1]["id"] == "2"
            assert results[1]["score"] == 0.85
    
    @pytest.mark.asyncio
    async def test_search_points_failure(self):
        """벡터 검색 실패 테스트"""
        mock_client = MagicMock()
        self.client._client = mock_client
        self.client._is_connected = True
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = Exception("Search failed")
            
            with pytest.raises(VectorStoreOperationError, match="벡터 검색 실패"):
                await self.client.search_points("test_collection", [0.1, 0.2, 0.3])
    
    @pytest.mark.asyncio
    async def test_delete_points_success(self):
        """포인트 삭제 성공 테스트"""
        mock_client = MagicMock()
        self.client._client = mock_client
        self.client._is_connected = True
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = None
            
            result = await self.client.delete_points("test_collection", ["1", "2"])
            
            assert result is True
            mock_to_thread.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_points_failure(self):
        """포인트 삭제 실패 테스트"""
        mock_client = MagicMock()
        self.client._client = mock_client
        self.client._is_connected = True
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = Exception("Delete failed")
            
            with pytest.raises(VectorStoreOperationError, match="포인트 삭제 실패"):
                await self.client.delete_points("test_collection", ["1"])
    
    @pytest.mark.asyncio
    async def test_get_collection_info_success(self):
        """컬렉션 정보 조회 성공 테스트"""
        mock_client = MagicMock()
        self.client._client = mock_client
        self.client._is_connected = True
        
        # 모의 컬렉션 정보
        mock_collection_info = MagicMock()
        mock_collection_info.config.params.vectors.size = 1536
        mock_collection_info.config.params.vectors.distance.value = "Cosine"
        mock_collection_info.points_count = 100
        mock_collection_info.status.value = "green"
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = mock_collection_info
            
            info = await self.client.get_collection_info("test_collection")
            
            assert info["vector_size"] == 1536
            assert info["distance"] == "Cosine"
            assert info["points_count"] == 100
            assert info["status"] == "green"
    
    @pytest.mark.asyncio
    async def test_get_collection_info_failure(self):
        """컬렉션 정보 조회 실패 테스트"""
        mock_client = MagicMock()
        self.client._client = mock_client
        self.client._is_connected = True
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = Exception("Info retrieval failed")
            
            with pytest.raises(VectorStoreOperationError, match="컬렉션 정보 조회 실패"):
                await self.client.get_collection_info("test_collection")
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """정상 상태 헬스체크 테스트"""
        mock_client = MagicMock()
        self.client._client = mock_client
        self.client._is_connected = True
        
        mock_collections = MagicMock()
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        mock_collections.collections = [mock_collection]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = mock_collections
            
            result = await self.client.health_check()
            
            assert result["status"] == "healthy"
            assert result["url"] == "http://localhost:6333"
            assert result["collections_count"] == 1
            assert "test_collection" in result["collections"]
    
    @pytest.mark.asyncio
    async def test_health_check_disconnected(self):
        """연결 해제 상태 헬스체크 테스트"""
        result = await self.client.health_check()
        
        assert result["status"] == "disconnected"
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_health_check_error(self):
        """헬스체크 오류 테스트"""
        mock_client = MagicMock()
        self.client._client = mock_client
        self.client._is_connected = True
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = Exception("Health check failed")
            
            result = await self.client.health_check()
            
            assert result["status"] == "unhealthy"
            assert "Health check failed" in result["error"]


class TestQdrantManager:
    """Qdrant 매니저 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 매니저 초기화"""
        # 싱글톤 인스턴스 초기화
        QdrantManager._instance = None
        QdrantManager._client = None
    
    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        manager1 = QdrantManager()
        manager2 = QdrantManager()
        
        assert manager1 is manager2
    
    def test_initialize(self):
        """매니저 초기화 테스트"""
        settings = Settings(
            qdrant_url="http://localhost:6333",
            qdrant_collection_name="test_collection",
            qdrant_vector_size=1536
        )
        manager = QdrantManager()
        
        manager.initialize(settings)
        
        assert manager._client is not None
        assert isinstance(manager._client, QdrantVectorClient)
        assert manager._client.settings == settings
    
    def test_initialize_already_initialized(self):
        """이미 초기화된 매니저 재초기화 테스트"""
        settings = Settings(
            qdrant_url="http://localhost:6333",
            qdrant_collection_name="test_collection",
            qdrant_vector_size=1536
        )
        manager = QdrantManager()
        
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
        
        manager = QdrantManager()
        manager._client = mock_client
        
        await manager.connect()
        
        mock_client.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_no_client(self):
        """클라이언트가 없는 상태에서 연결 테스트"""
        manager = QdrantManager()
        
        # 클라이언트가 없어도 예외가 발생하지 않아야 함
        await manager.connect()
    
    @pytest.mark.asyncio
    async def test_disconnect(self):
        """매니저 연결 해제 테스트"""
        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()
        
        manager = QdrantManager()
        manager._client = mock_client
        
        await manager.disconnect()
        
        mock_client.disconnect.assert_called_once()
    
    def test_client_property(self):
        """클라이언트 속성 테스트"""
        mock_client = MagicMock()
        manager = QdrantManager()
        manager._client = mock_client
        
        assert manager.client == mock_client
    
    def test_client_property_not_initialized(self):
        """초기화되지 않은 클라이언트 속성 테스트"""
        manager = QdrantManager()
        
        with pytest.raises(VectorStoreConnectionError, match="Qdrant 클라이언트가 초기화되지 않음"):
            _ = manager.client


class TestUtilityFunctions:
    """유틸리티 함수 테스트"""
    
    @pytest.mark.asyncio
    async def test_initialize_qdrant_collections_success(self):
        """Qdrant 컬렉션 초기화 성공 테스트"""
        # 환경 변수로 설정
        import os
        os.environ['QDRANT_COLLECTION_NAME'] = 'test_collection'
        os.environ['QDRANT_VECTOR_SIZE'] = '1536'
        os.environ['QDRANT_URL'] = 'http://localhost:6333'
        os.environ['MONGODB_URL'] = 'mongodb://localhost:27017'
        os.environ['MONGODB_DATABASE'] = 'test_db'
        os.environ['KAFKA_BOOTSTRAP_SERVERS'] = 'localhost:9092'
        os.environ['KAFKA_TOPIC_DOCUMENT_UPLOADED'] = 'test_topic'
        os.environ['KAFKA_TOPIC_TEXT_EXTRACTED'] = 'test_topic'
        os.environ['KAFKA_TOPIC_CHUNKS_CREATED'] = 'test_topic'
        os.environ['KAFKA_TOPIC_EMBEDDINGS_GENERATED'] = 'test_topic'
        os.environ['KAFKA_CONSUMER_GROUP_ID'] = 'test_group'
        os.environ['OPENAI_API_KEY'] = 'test_key'
        os.environ['SECRET_KEY'] = 'test_secret'
        
        try:
            settings = Settings()
            
            mock_client = AsyncMock()
            mock_client.create_collection.return_value = True
            
            with patch('src.infrastructure.vectordb.qdrant_client.qdrant_manager') as mock_manager:
                mock_manager.client = mock_client
                
                await initialize_qdrant_collections(settings)
                
                mock_client.create_collection.assert_called_once_with(
                    collection_name="test_collection",
                    vector_size=1536,
                    distance=Distance.COSINE
                )
        finally:
            # 환경 변수 정리
            for key in ['QDRANT_COLLECTION_NAME', 'QDRANT_VECTOR_SIZE', 'QDRANT_URL',
                       'MONGODB_URL', 'MONGODB_DATABASE', 'KAFKA_BOOTSTRAP_SERVERS',
                       'KAFKA_TOPIC_DOCUMENT_UPLOADED', 'KAFKA_TOPIC_TEXT_EXTRACTED',
                       'KAFKA_TOPIC_CHUNKS_CREATED', 'KAFKA_TOPIC_EMBEDDINGS_GENERATED',
                       'KAFKA_CONSUMER_GROUP_ID', 'OPENAI_API_KEY', 'SECRET_KEY']:
                os.environ.pop(key, None)
    
    @pytest.mark.asyncio
    async def test_initialize_qdrant_collections_failure(self):
        """Qdrant 컬렉션 초기화 실패 테스트"""
        settings = Settings(
            qdrant_collection_name="test_collection",
            qdrant_vector_size=1536
        )
        
        mock_client = AsyncMock()
        mock_client.create_collection.side_effect = Exception("Collection creation failed")
        
        with patch('src.infrastructure.vectordb.qdrant_client.qdrant_manager') as mock_manager:
            mock_manager.client = mock_client
            
            with pytest.raises(Exception, match="Collection creation failed"):
                await initialize_qdrant_collections(settings)
    
    @pytest.mark.asyncio
    async def test_qdrant_health_check_success(self):
        """Qdrant 헬스체크 성공 테스트"""
        mock_client = AsyncMock()
        mock_client.health_check.return_value = {"status": "healthy"}
        
        with patch('src.infrastructure.vectordb.qdrant_client.qdrant_manager') as mock_manager:
            mock_manager.client = mock_client
            
            result = await qdrant_health_check()
            
            assert result["status"] == "healthy"
            mock_client.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_qdrant_health_check_error(self):
        """Qdrant 헬스체크 오류 테스트"""
        with patch('src.infrastructure.vectordb.qdrant_client.qdrant_manager') as mock_manager:
            mock_manager.client.health_check.side_effect = Exception("Health check failed")
            
            result = await qdrant_health_check()
            
            assert result["status"] == "error"
            assert "Health check failed" in result["error"]
    
    def test_create_point_struct(self):
        """PointStruct 생성 헬퍼 함수 테스트"""
        point = create_point_struct(
            point_id="test_id",
            vector=[0.1, 0.2, 0.3],
            payload={"text": "test"}
        )
        
        assert point.id == "test_id"
        assert point.vector == [0.1, 0.2, 0.3]
        assert point.payload == {"text": "test"}
    
    def test_create_point_struct_no_payload(self):
        """페이로드 없는 PointStruct 생성 테스트"""
        point = create_point_struct(
            point_id="test_id",
            vector=[0.1, 0.2, 0.3]
        )
        
        assert point.id == "test_id"
        assert point.vector == [0.1, 0.2, 0.3]
        assert point.payload == {}
    
    def test_create_filter_condition(self):
        """필터 조건 생성 헬퍼 함수 테스트"""
        filter_condition = create_filter_condition("field", "value")
        
        assert len(filter_condition.must) == 1
        condition = filter_condition.must[0]
        assert condition.key == "field"
        assert condition.match.value == "value"


class TestIntegration:
    """통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """전체 생명주기 테스트"""
        settings = Settings(
            qdrant_url="http://localhost:6333",
            qdrant_collection_name="test_collection",
            qdrant_vector_size=1536
        )
        
        # 매니저 초기화
        manager = QdrantManager()
        manager.initialize(settings)
        
        # 클라이언트 모킹
        mock_qdrant_client = MagicMock()
        mock_collections = MagicMock()
        mock_collections.collections = []
        
        with patch('src.infrastructure.vectordb.qdrant_client.QdrantClient') as mock_client_class:
            with patch('asyncio.to_thread') as mock_to_thread:
                mock_client_class.return_value = mock_qdrant_client
                mock_to_thread.return_value = mock_collections
                
                # 연결
                await manager.connect()
                
                # 클라이언트 사용
                client = manager.client
                assert client.is_connected is True
                
                # 컬렉션 생성
                mock_to_thread.side_effect = [mock_collections, None]  # get_collections, create_collection
                result = await client.create_collection("test_collection", 1536)
                assert result is True
                
                # 헬스체크
                mock_to_thread.side_effect = [mock_collections]  # get_collections for health check
                health = await client.health_check()
                assert health["status"] == "healthy"
                
                # 연결 해제
                mock_to_thread.side_effect = [None]  # close
                await manager.disconnect()
                assert client.is_connected is False
