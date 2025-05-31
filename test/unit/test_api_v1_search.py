"""
Search API 테스트
"""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import UUID, uuid4
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.search import router, convert_search_result_to_item
from src.api.v1.schemas import SearchResultItem
from src.modules.search.domain.entities import SearchResult, AnswerResult
from src.modules.search.application.use_cases.search_documents import SearchDocumentsUseCase
from src.modules.search.application.use_cases.generate_answer import GenerateAnswerUseCase
from src.modules.search.infrastructure.vector_db import VectorDatabase
from src.core.exceptions import SearchError, ValidationError
from src.core.dependencies import get_search_use_case, get_answer_use_case, get_vector_database


class TestSearchAPI:
    """Search API 테스트"""
    
    @pytest.fixture
    def app(self):
        """FastAPI 앱 인스턴스"""
        app = FastAPI()
        app.include_router(router)
        return app
    
    @pytest.fixture
    def client(self, app):
        """테스트 클라이언트"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_search_use_case(self):
        """Mock Search Use Case"""
        return Mock(spec=SearchDocumentsUseCase)
    
    @pytest.fixture
    def mock_answer_use_case(self):
        """Mock Answer Use Case"""
        return Mock(spec=GenerateAnswerUseCase)
    
    @pytest.fixture
    def mock_vector_db(self):
        """Mock Vector Database"""
        return Mock(spec=VectorDatabase)
    
    @pytest.fixture
    def sample_search_result(self):
        """샘플 검색 결과"""
        return SearchResult(
            chunk_id=uuid4(),
            document_id=uuid4(),
            content="Python은 프로그래밍 언어입니다.",
            score=0.95,
            metadata={
                "source": "python_guide.pdf",
                "page": 1,
                "chunk_index": 0,
                "created_at": "2024-01-01T00:00:00Z"
            }
        )
    
    @pytest.fixture
    def sample_answer_result(self, sample_search_result):
        """샘플 답변 결과"""
        return AnswerResult(
            answer="Python은 간단하고 읽기 쉬운 프로그래밍 언어입니다.",
            sources=[sample_search_result],
            confidence=0.85
        )
    
    def test_convert_search_result_to_item(self, sample_search_result):
        """SearchResult를 SearchResultItem으로 변환 테스트"""
        # When
        item = convert_search_result_to_item(sample_search_result)
        
        # Then
        assert isinstance(item, SearchResultItem)
        assert item.chunk_id == sample_search_result.chunk_id
        assert item.document_id == sample_search_result.document_id
        assert item.content == sample_search_result.content
        assert item.score == sample_search_result.score
        assert item.metadata == sample_search_result.metadata
    
    @pytest.mark.asyncio
    async def test_search_documents_success(self, client, mock_search_use_case, sample_search_result):
        """문서 검색 성공 테스트"""
        # Given
        mock_search_use_case.execute = AsyncMock(return_value=[sample_search_result])
        
        # Mock dependency injection
        def get_mock_search_use_case():
            return mock_search_use_case
        
        client.app.dependency_overrides[get_search_use_case] = get_mock_search_use_case
        
        request_data = {
            "query": "Python 프로그래밍",
            "limit": 10,
            "threshold": 0.7,
            "search_type": "hybrid"
        }
        
        # When
        response = client.post("/search/", json=request_data)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == "Python 프로그래밍"
        assert data["search_type"] == "hybrid"
        assert data["total_count"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["content"] == "Python은 프로그래밍 언어입니다."
        assert "search_time_ms" in data
        
        # Use case가 올바른 파라미터로 호출되었는지 확인
        mock_search_use_case.execute.assert_called_once_with(
            query="Python 프로그래밍",
            limit=10,
            threshold=0.7,
            filters=None,
            search_type="hybrid"
        )
    
    @pytest.mark.asyncio
    async def test_search_documents_with_filters(self, client, mock_search_use_case, sample_search_result):
        """필터가 있는 문서 검색 테스트"""
        # Given
        mock_search_use_case.execute = AsyncMock(return_value=[sample_search_result])
        
        def get_mock_search_use_case():
            return mock_search_use_case
        
        client.app.dependency_overrides[get_search_use_case] = get_mock_search_use_case
        
        request_data = {
            "query": "Python",
            "limit": 5,
            "filters": {
                "source": "python_guide.pdf",
                "page": {"gte": 1, "lte": 10}
            }
        }
        
        # When
        response = client.post("/search/", json=request_data)
        
        # Then
        assert response.status_code == 200
        
        # Use case가 필터와 함께 호출되었는지 확인
        mock_search_use_case.execute.assert_called_once_with(
            query="Python",
            limit=5,
            threshold=0.7,  # 기본값
            filters={
                "source": "python_guide.pdf",
                "page": {"gte": 1, "lte": 10}
            },
            search_type="hybrid"  # 기본값
        )
    
    @pytest.mark.asyncio
    async def test_search_documents_validation_error(self, client, mock_search_use_case):
        """검색 요청 검증 오류 테스트"""
        # Given
        def get_mock_search_use_case():
            return mock_search_use_case
        
        client.app.dependency_overrides[get_search_use_case] = get_mock_search_use_case
        
        request_data = {
            "query": "",  # 빈 쿼리
            "limit": 10
        }
        
        # When
        response = client.post("/search/", json=request_data)
        
        # Then
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_search_documents_search_error(self, client, mock_search_use_case):
        """검색 오류 테스트"""
        # Given
        mock_search_use_case.execute = AsyncMock(side_effect=SearchError("Vector search failed"))
        
        def get_mock_search_use_case():
            return mock_search_use_case
        
        client.app.dependency_overrides[get_search_use_case] = get_mock_search_use_case
        
        request_data = {
            "query": "Python",
            "limit": 10
        }
        
        # When
        response = client.post("/search/", json=request_data)
        
        # Then
        assert response.status_code == 500
        assert "Vector search failed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_generate_answer_success(self, client, mock_answer_use_case, sample_answer_result):
        """답변 생성 성공 테스트"""
        # Given
        mock_answer_use_case.execute = AsyncMock(return_value=sample_answer_result)
        
        def get_mock_answer_use_case():
            return mock_answer_use_case
        
        client.app.dependency_overrides[get_answer_use_case] = get_mock_answer_use_case
        
        request_data = {
            "question": "Python이란 무엇인가요?",
            "context_limit": 5,
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        # When
        response = client.post("/search/answer", json=request_data)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        
        assert data["question"] == "Python이란 무엇인가요?"
        assert data["answer"] == "Python은 간단하고 읽기 쉬운 프로그래밍 언어입니다."
        assert data["confidence"] == 0.85
        assert len(data["sources"]) == 1
        assert "generation_time_ms" in data
        
        # Use case가 올바른 파라미터로 호출되었는지 확인
        mock_answer_use_case.execute.assert_called_once_with(
            question="Python이란 무엇인가요?",
            context_limit=5,
            search_filters=None,
            temperature=0.7,
            max_tokens=500
        )
    
    @pytest.mark.asyncio
    async def test_generate_answer_with_filters(self, client, mock_answer_use_case, sample_answer_result):
        """필터가 있는 답변 생성 테스트"""
        # Given
        mock_answer_use_case.execute = AsyncMock(return_value=sample_answer_result)
        
        def get_mock_answer_use_case():
            return mock_answer_use_case
        
        client.app.dependency_overrides[get_answer_use_case] = get_mock_answer_use_case
        
        request_data = {
            "question": "Python의 특징은?",
            "search_filters": {
                "source": "python_guide.pdf"
            }
        }
        
        # When
        response = client.post("/search/answer", json=request_data)
        
        # Then
        assert response.status_code == 200
        
        # Use case가 필터와 함께 호출되었는지 확인
        mock_answer_use_case.execute.assert_called_once_with(
            question="Python의 특징은?",
            context_limit=5,  # 기본값
            search_filters={"source": "python_guide.pdf"},
            temperature=0.7,  # 기본값
            max_tokens=500  # 기본값
        )
    
    @pytest.mark.asyncio
    async def test_get_chunk_detail_success(self, client, mock_vector_db, sample_search_result):
        """청크 상세 조회 성공 테스트"""
        # Given
        chunk_id = sample_search_result.chunk_id
        mock_vector_db.get_chunk_by_id = AsyncMock(return_value=sample_search_result)
        
        def get_mock_vector_db():
            return mock_vector_db
        
        client.app.dependency_overrides[get_vector_database] = get_mock_vector_db
        
        # When
        response = client.get(f"/search/chunks/{chunk_id}")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        
        assert data["chunk_id"] == str(chunk_id)
        assert data["content"] == "Python은 프로그래밍 언어입니다."
        assert data["score"] == 0.95
        
        mock_vector_db.get_chunk_by_id.assert_called_once_with(chunk_id)
    
    @pytest.mark.asyncio
    async def test_get_chunk_detail_not_found(self, client, mock_vector_db):
        """청크 상세 조회 실패 테스트"""
        # Given
        chunk_id = uuid4()
        mock_vector_db.get_chunk_by_id = AsyncMock(return_value=None)
        
        def get_mock_vector_db():
            return mock_vector_db
        
        client.app.dependency_overrides[get_vector_database] = get_mock_vector_db
        
        # When
        response = client.get(f"/search/chunks/{chunk_id}")
        
        # Then
        assert response.status_code == 404
        assert "Chunk not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_document_chunks_success(self, client, mock_vector_db, sample_search_result):
        """문서별 청크 조회 성공 테스트"""
        # Given
        document_id = sample_search_result.document_id
        
        # 여러 청크 생성 (페이지네이션 테스트용)
        chunks = []
        for i in range(25):  # 25개 청크
            chunk = SearchResult(
                chunk_id=uuid4(),
                document_id=document_id,
                content=f"청크 내용 {i}",
                score=1.0,
                metadata={"chunk_index": i}
            )
            chunks.append(chunk)
        
        mock_vector_db.get_chunks_by_document = AsyncMock(return_value=chunks)
        
        def get_mock_vector_db():
            return mock_vector_db
        
        client.app.dependency_overrides[get_vector_database] = get_mock_vector_db
        
        # When
        response = client.get(f"/search/documents/{document_id}/chunks?page=1&size=20")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        
        assert data["document_id"] == str(document_id)
        assert data["total_count"] == 25
        assert data["page"] == 1
        assert data["size"] == 20
        assert data["total_pages"] == 2
        assert len(data["chunks"]) == 20  # 첫 페이지는 20개
        
        mock_vector_db.get_chunks_by_document.assert_called_once_with(document_id)
    
    @pytest.mark.asyncio
    async def test_get_document_chunks_second_page(self, client, mock_vector_db):
        """문서별 청크 조회 두 번째 페이지 테스트"""
        # Given
        document_id = uuid4()
        
        chunks = []
        for i in range(25):
            chunk = SearchResult(
                chunk_id=uuid4(),
                document_id=document_id,
                content=f"청크 내용 {i}",
                score=1.0,
                metadata={"chunk_index": i}
            )
            chunks.append(chunk)
        
        mock_vector_db.get_chunks_by_document = AsyncMock(return_value=chunks)
        
        def get_mock_vector_db():
            return mock_vector_db
        
        client.app.dependency_overrides[get_vector_database] = get_mock_vector_db
        
        # When
        response = client.get(f"/search/documents/{document_id}/chunks?page=2&size=20")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 2
        assert len(data["chunks"]) == 5  # 두 번째 페이지는 5개
    
    @pytest.mark.asyncio
    async def test_get_document_chunks_not_found(self, client, mock_vector_db):
        """문서별 청크 조회 실패 테스트"""
        # Given
        document_id = uuid4()
        mock_vector_db.get_chunks_by_document = AsyncMock(return_value=[])
        
        def get_mock_vector_db():
            return mock_vector_db
        
        client.app.dependency_overrides[get_vector_database] = get_mock_vector_db
        
        # When
        response = client.get(f"/search/documents/{document_id}/chunks")
        
        # Then
        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client, mock_vector_db):
        """헬스체크 성공 테스트"""
        # Given
        mock_vector_db.check_collection_health = AsyncMock(return_value={
            "health": "healthy",
            "name": "document_chunks",
            "points_count": 1000
        })
        
        def get_mock_vector_db():
            return mock_vector_db
        
        client.app.dependency_overrides[get_vector_database] = get_mock_vector_db
        
        # When
        response = client.get("/search/health")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data
        assert "components" in data
        assert data["components"]["vector_db"]["status"] == "healthy"
        assert "response_time_ms" in data["components"]["vector_db"]
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, client, mock_vector_db):
        """헬스체크 실패 테스트"""
        # Given
        mock_vector_db.check_collection_health = AsyncMock(return_value={
            "health": "unhealthy",
            "error": "Connection failed"
        })
        
        def get_mock_vector_db():
            return mock_vector_db
        
        client.app.dependency_overrides[get_vector_database] = get_mock_vector_db
        
        # When
        response = client.get("/search/health")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert data["components"]["vector_db"]["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_health_check_exception(self, client, mock_vector_db):
        """헬스체크 예외 테스트"""
        # Given
        mock_vector_db.check_collection_health = AsyncMock(side_effect=Exception("Connection error"))
        
        def get_mock_vector_db():
            return mock_vector_db
        
        client.app.dependency_overrides[get_vector_database] = get_mock_vector_db
        
        # When
        response = client.get("/search/health")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert data["components"]["vector_db"]["status"] == "unhealthy"
        assert "error" in data["components"]["vector_db"]
