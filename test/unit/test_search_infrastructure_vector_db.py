"""
Vector Database 테스트
"""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import UUID, uuid4
from datetime import datetime

from src.modules.search.infrastructure.vector_db import VectorDatabase
from src.modules.search.domain.entities import SearchResult
from src.core.exceptions import SearchError


class TestVectorDatabase:
    """Vector Database 테스트"""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant Client"""
        return Mock()
    
    @pytest.fixture
    def vector_db(self, mock_qdrant_client):
        """Vector Database 인스턴스"""
        return VectorDatabase(mock_qdrant_client)
    
    @pytest.fixture
    def sample_embedding(self):
        """샘플 임베딩 벡터"""
        return [0.1, 0.2, 0.3, 0.4, 0.5] * 100  # 500차원 벡터
    
    @pytest.fixture
    def mock_search_results(self):
        """Mock Qdrant 검색 결과"""
        return [
            Mock(
                id=str(uuid4()),
                score=0.95,
                payload={
                    "document_id": str(uuid4()),
                    "content": "Python은 프로그래밍 언어입니다.",
                    "source": "python_guide.pdf",
                    "page": 1,
                    "chunk_index": 0,
                    "created_at": "2024-01-01T00:00:00Z",
                    "metadata": {"author": "John Doe"}
                }
            ),
            Mock(
                id=str(uuid4()),
                score=0.87,
                payload={
                    "document_id": str(uuid4()),
                    "content": "Python은 간단하고 읽기 쉬운 문법을 가지고 있습니다.",
                    "source": "python_guide.pdf",
                    "page": 2,
                    "chunk_index": 1,
                    "created_at": "2024-01-01T00:00:00Z",
                    "metadata": {"author": "John Doe"}
                }
            )
        ]
    
    @pytest.mark.asyncio
    async def test_search_similar_chunks_success(self, vector_db, mock_qdrant_client, sample_embedding, mock_search_results):
        """정상적인 유사도 검색 테스트"""
        # Given
        mock_qdrant_client.search = AsyncMock(return_value=mock_search_results)
        
        # When
        results = await vector_db.search_similar_chunks(
            query_embedding=sample_embedding,
            limit=5,
            threshold=0.7
        )
        
        # Then
        assert len(results) == 2
        assert all(isinstance(result, SearchResult) for result in results)
        assert results[0].score == 0.95
        assert results[1].score == 0.87
        assert "Python은 프로그래밍 언어입니다." in results[0].content
        
        # Qdrant 클라이언트가 올바른 파라미터로 호출되었는지 확인
        mock_qdrant_client.search.assert_called_once_with(
            collection_name="document_chunks",
            query_vector=sample_embedding,
            limit=5,
            score_threshold=0.7,
            query_filter=None
        )
    
    @pytest.mark.asyncio
    async def test_search_similar_chunks_with_filters(self, vector_db, mock_qdrant_client, sample_embedding, mock_search_results):
        """필터가 있는 유사도 검색 테스트"""
        # Given
        filters = {"source": "python_guide.pdf", "page": {"gte": 1, "lte": 10}}
        mock_qdrant_client.search = AsyncMock(return_value=mock_search_results)
        
        # When
        results = await vector_db.search_similar_chunks(
            query_embedding=sample_embedding,
            limit=5,
            threshold=0.7,
            filters=filters
        )
        
        # Then
        assert len(results) == 2
        
        # 필터가 올바르게 구성되었는지 확인
        call_args = mock_qdrant_client.search.call_args
        query_filter = call_args.kwargs["query_filter"]
        assert query_filter is not None
        assert "must" in query_filter
        assert len(query_filter["must"]) == 2
    
    @pytest.mark.asyncio
    async def test_search_similar_chunks_error(self, vector_db, mock_qdrant_client, sample_embedding):
        """검색 오류 테스트"""
        # Given
        mock_qdrant_client.search = AsyncMock(side_effect=Exception("Qdrant connection error"))
        
        # When & Then
        with pytest.raises(SearchError) as exc_info:
            await vector_db.search_similar_chunks(sample_embedding)
        
        assert "Vector search failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_by_keywords_success(self, vector_db, mock_qdrant_client):
        """키워드 검색 테스트"""
        # Given
        keywords = ["Python", "프로그래밍"]
        mock_chunks = [
            Mock(
                id=str(uuid4()),
                payload={
                    "document_id": str(uuid4()),
                    "content": "Python은 프로그래밍 언어입니다. Python을 배우면 좋습니다.",
                    "source": "python_guide.pdf",
                    "page": 1,
                    "chunk_index": 0,
                    "created_at": "2024-01-01T00:00:00Z",
                    "metadata": {}
                }
            ),
            Mock(
                id=str(uuid4()),
                payload={
                    "document_id": str(uuid4()),
                    "content": "Java는 다른 프로그래밍 언어입니다.",
                    "source": "java_guide.pdf",
                    "page": 1,
                    "chunk_index": 0,
                    "created_at": "2024-01-01T00:00:00Z",
                    "metadata": {}
                }
            )
        ]
        mock_qdrant_client.scroll = AsyncMock(return_value=(mock_chunks, None))
        
        # When
        results = await vector_db.search_by_keywords(keywords, limit=10)
        
        # Then
        assert len(results) > 0
        # Python이 포함된 첫 번째 청크가 더 높은 점수를 가져야 함
        assert results[0].score > 0
        assert "Python" in results[0].content
    
    @pytest.mark.asyncio
    async def test_hybrid_search_success(self, vector_db, mock_qdrant_client, sample_embedding, mock_search_results):
        """하이브리드 검색 테스트"""
        # Given
        keywords = ["Python", "프로그래밍"]
        mock_qdrant_client.search = AsyncMock(return_value=mock_search_results)
        mock_qdrant_client.scroll = AsyncMock(return_value=(mock_search_results, None))
        
        # When
        results = await vector_db.hybrid_search(
            query_embedding=sample_embedding,
            keywords=keywords,
            limit=5
        )
        
        # Then
        assert len(results) <= 5
        assert all(isinstance(result, SearchResult) for result in results)
        
        # 벡터 검색과 키워드 검색이 모두 호출되었는지 확인
        mock_qdrant_client.search.assert_called_once()
        mock_qdrant_client.scroll.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_chunk_by_id_success(self, vector_db, mock_qdrant_client):
        """ID로 청크 조회 성공 테스트"""
        # Given
        chunk_id = uuid4()
        mock_point = Mock(
            id=str(chunk_id),
            payload={
                "document_id": str(uuid4()),
                "content": "Test content",
                "source": "test.pdf",
                "page": 1,
                "chunk_index": 0,
                "created_at": "2024-01-01T00:00:00Z",
                "metadata": {}
            }
        )
        mock_qdrant_client.retrieve = AsyncMock(return_value=[mock_point])
        
        # When
        result = await vector_db.get_chunk_by_id(chunk_id)
        
        # Then
        assert result is not None
        assert result.chunk_id == chunk_id
        assert result.content == "Test content"
        assert result.score == 1.0
        
        mock_qdrant_client.retrieve.assert_called_once_with(
            collection_name="document_chunks",
            ids=[str(chunk_id)],
            with_payload=True,
            with_vectors=False
        )
    
    @pytest.mark.asyncio
    async def test_get_chunk_by_id_not_found(self, vector_db, mock_qdrant_client):
        """ID로 청크 조회 실패 테스트"""
        # Given
        chunk_id = uuid4()
        mock_qdrant_client.retrieve = AsyncMock(return_value=[])
        
        # When
        result = await vector_db.get_chunk_by_id(chunk_id)
        
        # Then
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_chunks_by_document_success(self, vector_db, mock_qdrant_client, mock_search_results):
        """문서별 청크 조회 테스트"""
        # Given
        document_id = uuid4()
        mock_qdrant_client.scroll = AsyncMock(return_value=(mock_search_results, None))
        
        # When
        results = await vector_db.get_chunks_by_document(document_id)
        
        # Then
        assert len(results) == 2
        assert all(result.score == 1.0 for result in results)  # 문서별 조회는 스코어 1.0
        
        # scroll이 올바른 파라미터로 호출되었는지 확인
        call_args = mock_qdrant_client.scroll.call_args
        assert call_args.kwargs["collection_name"] == "document_chunks"
        assert call_args.kwargs["limit"] == 1000
        assert call_args.kwargs["with_payload"] is True
        assert call_args.kwargs["with_vectors"] is False
    
    @pytest.mark.asyncio
    async def test_check_collection_health_success(self, vector_db, mock_qdrant_client):
        """컬렉션 상태 확인 테스트"""
        # Given
        mock_collection_info = Mock()
        mock_collection_info.config.name = "document_chunks"
        mock_collection_info.config.params.vectors.size = 512
        mock_collection_info.config.params.vectors.distance.name = "COSINE"
        mock_collection_info.points_count = 1000
        mock_collection_info.indexed_vectors_count = 1000
        mock_collection_info.status.name = "GREEN"
        mock_qdrant_client.get_collection = AsyncMock(return_value=mock_collection_info)
        
        # When
        health = await vector_db.check_collection_health()
        
        # Then
        assert health["name"] == "document_chunks"
        assert health["vector_size"] == 512
        assert health["distance"] == "COSINE"
        assert health["points_count"] == 1000
        assert health["status"] == "GREEN"
        assert health["health"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_check_collection_health_error(self, vector_db, mock_qdrant_client):
        """컬렉션 상태 확인 오류 테스트"""
        # Given
        mock_qdrant_client.get_collection = AsyncMock(side_effect=Exception("Connection failed"))
        
        # When
        health = await vector_db.check_collection_health()
        
        # Then
        assert health["health"] == "unhealthy"
        assert "error" in health
    
    def test_build_filter_empty(self, vector_db):
        """빈 필터 테스트"""
        # When
        result = vector_db._build_filter({})
        
        # Then
        assert result is None
    
    def test_build_filter_document_id(self, vector_db):
        """문서 ID 필터 테스트"""
        # Given
        document_id = uuid4()
        filters = {"document_id": document_id}
        
        # When
        result = vector_db._build_filter(filters)
        
        # Then
        assert result is not None
        assert "must" in result
        assert len(result["must"]) == 1
        assert result["must"][0]["key"] == "document_id"
        assert result["must"][0]["match"]["value"] == str(document_id)
    
    def test_build_filter_source(self, vector_db):
        """소스 필터 테스트"""
        # Given
        filters = {"source": "python_guide.pdf"}
        
        # When
        result = vector_db._build_filter(filters)
        
        # Then
        assert result is not None
        assert result["must"][0]["key"] == "source"
        assert result["must"][0]["match"]["value"] == "python_guide.pdf"
    
    def test_build_filter_page_exact(self, vector_db):
        """페이지 정확 매칭 필터 테스트"""
        # Given
        filters = {"page": 5}
        
        # When
        result = vector_db._build_filter(filters)
        
        # Then
        assert result is not None
        assert result["must"][0]["key"] == "page"
        assert result["must"][0]["match"]["value"] == 5
    
    def test_build_filter_page_range(self, vector_db):
        """페이지 범위 필터 테스트"""
        # Given
        filters = {"page": {"gte": 1, "lte": 10}}
        
        # When
        result = vector_db._build_filter(filters)
        
        # Then
        assert result is not None
        assert result["must"][0]["key"] == "page"
        assert "range" in result["must"][0]
        assert result["must"][0]["range"]["gte"] == 1
        assert result["must"][0]["range"]["lte"] == 10
    
    def test_build_filter_date_range(self, vector_db):
        """날짜 범위 필터 테스트"""
        # Given
        filters = {
            "created_after": "2024-01-01T00:00:00Z",
            "created_before": "2024-12-31T23:59:59Z"
        }
        
        # When
        result = vector_db._build_filter(filters)
        
        # Then
        assert result is not None
        assert len(result["must"]) == 2
        
        # created_after 조건 확인
        after_condition = next(c for c in result["must"] if c["key"] == "created_at" and "gte" in c["range"])
        assert after_condition["range"]["gte"] == "2024-01-01T00:00:00Z"
        
        # created_before 조건 확인
        before_condition = next(c for c in result["must"] if c["key"] == "created_at" and "lte" in c["range"])
        assert before_condition["range"]["lte"] == "2024-12-31T23:59:59Z"
    
    def test_build_filter_metadata(self, vector_db):
        """메타데이터 필터 테스트"""
        # Given
        filters = {"metadata.author": "John Doe", "metadata.category": "tutorial"}
        
        # When
        result = vector_db._build_filter(filters)
        
        # Then
        assert result is not None
        assert len(result["must"]) == 2
        
        author_condition = next(c for c in result["must"] if c["key"] == "metadata.author")
        assert author_condition["match"]["value"] == "John Doe"
        
        category_condition = next(c for c in result["must"] if c["key"] == "metadata.category")
        assert category_condition["match"]["value"] == "tutorial"
    
    def test_build_filter_multiple_conditions(self, vector_db):
        """복합 필터 테스트"""
        # Given
        filters = {
            "source": "python_guide.pdf",
            "page": {"gte": 1, "lte": 10},
            "metadata.author": "John Doe"
        }
        
        # When
        result = vector_db._build_filter(filters)
        
        # Then
        assert result is not None
        assert len(result["must"]) == 3
    
    def test_merge_and_rerank(self, vector_db):
        """검색 결과 병합 및 재순위화 테스트"""
        # Given
        chunk_id_1 = uuid4()
        chunk_id_2 = uuid4()
        chunk_id_3 = uuid4()
        
        vector_results = [
            SearchResult(
                chunk_id=chunk_id_1,
                document_id=uuid4(),
                content="Vector result 1",
                score=0.9,
                metadata={}
            ),
            SearchResult(
                chunk_id=chunk_id_2,
                document_id=uuid4(),
                content="Vector result 2",
                score=0.8,
                metadata={}
            )
        ]
        
        keyword_results = [
            SearchResult(
                chunk_id=chunk_id_1,  # 벡터 검색과 중복
                document_id=uuid4(),
                content="Keyword result 1",
                score=0.7,
                metadata={}
            ),
            SearchResult(
                chunk_id=chunk_id_3,  # 키워드 검색에서만 발견
                document_id=uuid4(),
                content="Keyword result 3",
                score=0.6,
                metadata={}
            )
        ]
        
        # When
        merged_results = vector_db._merge_and_rerank(
            vector_results, keyword_results, 
            vector_weight=0.7, keyword_weight=0.3
        )
        
        # Then
        assert len(merged_results) == 3
        
        # chunk_id_1은 벡터 + 키워드 점수를 가져야 함
        chunk_1_result = next(r for r in merged_results if r.chunk_id == chunk_id_1)
        expected_score_1 = 0.9 * 0.7 + 0.7 * 0.3  # 0.63 + 0.21 = 0.84
        assert abs(chunk_1_result.score - expected_score_1) < 0.01
        
        # chunk_id_2는 벡터 점수만 가져야 함
        chunk_2_result = next(r for r in merged_results if r.chunk_id == chunk_id_2)
        expected_score_2 = 0.8 * 0.7  # 0.56
        assert abs(chunk_2_result.score - expected_score_2) < 0.01
        
        # chunk_id_3은 키워드 점수만 가져야 함
        chunk_3_result = next(r for r in merged_results if r.chunk_id == chunk_id_3)
        expected_score_3 = 0.6 * 0.3  # 0.18
        assert abs(chunk_3_result.score - expected_score_3) < 0.01
        
        # 점수 순으로 정렬되어 있어야 함
        assert merged_results[0].score >= merged_results[1].score >= merged_results[2].score
