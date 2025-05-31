"""
API v1 스키마 테스트
"""

import pytest
from uuid import uuid4
from datetime import datetime
from pydantic import ValidationError
from src.api.v1.schemas import (
    SearchRequest,
    SearchResultItem,
    SearchResponse,
    AnswerRequest,
    AnswerResponse,
    ChunkDetailRequest,
    DocumentChunksRequest,
    DocumentChunksResponse,
    HealthCheckResponse,
    ErrorResponse
)


class TestSearchRequest:
    """검색 요청 스키마 테스트"""

    def test_valid_search_request(self):
        """유효한 검색 요청 테스트"""
        request = SearchRequest(
            query="Python 프로그래밍",
            limit=10,
            threshold=0.8,
            filters={"source": "guide.pdf"},
            search_type="hybrid"
        )
        assert request.query == "Python 프로그래밍"
        assert request.limit == 10
        assert request.threshold == 0.8
        assert request.search_type == "hybrid"

    def test_default_values(self):
        """기본값 테스트"""
        request = SearchRequest(query="test")
        assert request.limit == 10
        assert request.threshold == 0.7
        assert request.search_type == "hybrid"
        assert request.filters is None

    def test_invalid_query_length(self):
        """잘못된 쿼리 길이 테스트"""
        with pytest.raises(ValidationError):
            SearchRequest(query="")  # 너무 짧음
        
        with pytest.raises(ValidationError):
            SearchRequest(query="x" * 1001)  # 너무 김

    def test_invalid_limit_range(self):
        """잘못된 limit 범위 테스트"""
        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=0)  # 너무 작음
        
        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=101)  # 너무 큼

    def test_invalid_threshold_range(self):
        """잘못된 threshold 범위 테스트"""
        with pytest.raises(ValidationError):
            SearchRequest(query="test", threshold=-0.1)  # 너무 작음
        
        with pytest.raises(ValidationError):
            SearchRequest(query="test", threshold=1.1)  # 너무 큼


class TestSearchResultItem:
    """검색 결과 항목 스키마 테스트"""

    def test_valid_search_result_item(self):
        """유효한 검색 결과 항목 테스트"""
        chunk_id = uuid4()
        document_id = uuid4()
        item = SearchResultItem(
            chunk_id=chunk_id,
            document_id=document_id,
            content="테스트 내용",
            score=0.95,
            metadata={"source": "test.pdf", "page": 1}
        )
        assert item.chunk_id == chunk_id
        assert item.document_id == document_id
        assert item.content == "테스트 내용"
        assert item.score == 0.95

    def test_invalid_score_range(self):
        """잘못된 점수 범위 테스트"""
        with pytest.raises(ValidationError):
            SearchResultItem(
                chunk_id=uuid4(),
                document_id=uuid4(),
                content="test",
                score=-0.1,  # 너무 작음
                metadata={}
            )
        
        with pytest.raises(ValidationError):
            SearchResultItem(
                chunk_id=uuid4(),
                document_id=uuid4(),
                content="test",
                score=1.1,  # 너무 큼
                metadata={}
            )


class TestAnswerRequest:
    """답변 생성 요청 스키마 테스트"""

    def test_valid_answer_request(self):
        """유효한 답변 요청 테스트"""
        request = AnswerRequest(
            question="Python이란 무엇인가요?",
            context_limit=5,
            temperature=0.7,
            max_tokens=500
        )
        assert request.question == "Python이란 무엇인가요?"
        assert request.context_limit == 5
        assert request.temperature == 0.7
        assert request.max_tokens == 500

    def test_default_values(self):
        """기본값 테스트"""
        request = AnswerRequest(question="test question")
        assert request.context_limit == 5
        assert request.temperature == 0.7
        assert request.max_tokens == 500
        assert request.search_filters is None

    def test_invalid_question_length(self):
        """잘못된 질문 길이 테스트"""
        with pytest.raises(ValidationError):
            AnswerRequest(question="")  # 너무 짧음
        
        with pytest.raises(ValidationError):
            AnswerRequest(question="x" * 1001)  # 너무 김

    def test_invalid_context_limit_range(self):
        """잘못된 컨텍스트 제한 범위 테스트"""
        with pytest.raises(ValidationError):
            AnswerRequest(question="test", context_limit=0)  # 너무 작음
        
        with pytest.raises(ValidationError):
            AnswerRequest(question="test", context_limit=21)  # 너무 큼

    def test_invalid_temperature_range(self):
        """잘못된 온도 범위 테스트"""
        with pytest.raises(ValidationError):
            AnswerRequest(question="test", temperature=-0.1)  # 너무 작음
        
        with pytest.raises(ValidationError):
            AnswerRequest(question="test", temperature=2.1)  # 너무 큼

    def test_invalid_max_tokens_range(self):
        """잘못된 최대 토큰 범위 테스트"""
        with pytest.raises(ValidationError):
            AnswerRequest(question="test", max_tokens=49)  # 너무 작음
        
        with pytest.raises(ValidationError):
            AnswerRequest(question="test", max_tokens=2001)  # 너무 큼


class TestDocumentChunksRequest:
    """문서별 청크 조회 요청 스키마 테스트"""

    def test_valid_document_chunks_request(self):
        """유효한 문서 청크 요청 테스트"""
        document_id = uuid4()
        request = DocumentChunksRequest(
            document_id=document_id,
            page=2,
            size=50
        )
        assert request.document_id == document_id
        assert request.page == 2
        assert request.size == 50

    def test_default_values(self):
        """기본값 테스트"""
        document_id = uuid4()
        request = DocumentChunksRequest(document_id=document_id)
        assert request.page == 1
        assert request.size == 20

    def test_invalid_page_range(self):
        """잘못된 페이지 범위 테스트"""
        with pytest.raises(ValidationError):
            DocumentChunksRequest(
                document_id=uuid4(),
                page=0  # 너무 작음
            )

    def test_invalid_size_range(self):
        """잘못된 크기 범위 테스트"""
        with pytest.raises(ValidationError):
            DocumentChunksRequest(
                document_id=uuid4(),
                size=0  # 너무 작음
            )
        
        with pytest.raises(ValidationError):
            DocumentChunksRequest(
                document_id=uuid4(),
                size=101  # 너무 큼
            )


class TestHealthCheckResponse:
    """헬스체크 응답 스키마 테스트"""

    def test_valid_health_check_response(self):
        """유효한 헬스체크 응답 테스트"""
        timestamp = datetime.now()
        response = HealthCheckResponse(
            status="healthy",
            timestamp=timestamp,
            version="1.0.0",
            components={
                "database": {"status": "healthy", "response_time_ms": 15.2},
                "vector_db": {"status": "healthy", "response_time_ms": 25.1}
            }
        )
        assert response.status == "healthy"
        assert response.timestamp == timestamp
        assert response.version == "1.0.0"
        assert len(response.components) == 2


class TestErrorResponse:
    """에러 응답 스키마 테스트"""

    def test_valid_error_response(self):
        """유효한 에러 응답 테스트"""
        timestamp = datetime.now()
        response = ErrorResponse(
            error="ValidationError",
            message="잘못된 입력입니다",
            details={"field": "query", "value": ""},
            timestamp=timestamp
        )
        assert response.error == "ValidationError"
        assert response.message == "잘못된 입력입니다"
        assert response.details["field"] == "query"
        assert response.timestamp == timestamp

    def test_error_response_without_details(self):
        """상세 정보 없는 에러 응답 테스트"""
        timestamp = datetime.now()
        response = ErrorResponse(
            error="InternalError",
            message="내부 서버 오류",
            timestamp=timestamp
        )
        assert response.error == "InternalError"
        assert response.message == "내부 서버 오류"
        assert response.details is None
        assert response.timestamp == timestamp


class TestSchemaIntegration:
    """스키마 통합 테스트"""

    def test_search_response_with_multiple_results(self):
        """여러 결과가 있는 검색 응답 테스트"""
        results = [
            SearchResultItem(
                chunk_id=uuid4(),
                document_id=uuid4(),
                content=f"테스트 내용 {i}",
                score=0.9 - i * 0.1,
                metadata={"source": f"test{i}.pdf", "page": i}
            )
            for i in range(3)
        ]
        
        response = SearchResponse(
            query="테스트 쿼리",
            results=results,
            total_count=3,
            search_time_ms=125.5,
            search_type="hybrid"
        )
        
        assert response.query == "테스트 쿼리"
        assert len(response.results) == 3
        assert response.total_count == 3
        assert response.search_time_ms == 125.5
        assert response.search_type == "hybrid"

    def test_answer_response_with_sources(self):
        """소스가 있는 답변 응답 테스트"""
        sources = [
            SearchResultItem(
                chunk_id=uuid4(),
                document_id=uuid4(),
                content="참조 내용",
                score=0.95,
                metadata={"source": "reference.pdf", "page": 1}
            )
        ]
        
        response = AnswerResponse(
            question="테스트 질문",
            answer="테스트 답변",
            sources=sources,
            confidence=0.85,
            generation_time_ms=1250.0
        )
        
        assert response.question == "테스트 질문"
        assert response.answer == "테스트 답변"
        assert len(response.sources) == 1
        assert response.confidence == 0.85
        assert response.generation_time_ms == 1250.0
