"""
Search Documents Use Case Tests

문서 검색 유즈케이스 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from typing import List

from src.core.exceptions import ValidationError, SearchError
from src.modules.search.domain.entities import SearchType, SearchResult
from src.modules.search.application.use_cases.search_documents import (
    SearchDocumentsUseCase,
    SearchDocumentsCommand,
    SearchDocumentsResult
)
from src.modules.search.application.ports.vector_search_port import VectorSearchPort
from src.modules.search.application.ports.llm_port import EmbeddingPort


class TestSearchDocumentsUseCase:
    """문서 검색 유즈케이스 테스트"""
    
    @pytest.fixture
    def mock_vector_search_port(self):
        """벡터 검색 포트 모킹"""
        return AsyncMock(spec=VectorSearchPort)
    
    @pytest.fixture
    def mock_embedding_port(self):
        """임베딩 포트 모킹"""
        return AsyncMock(spec=EmbeddingPort)
    
    @pytest.fixture
    def use_case(self, mock_vector_search_port, mock_embedding_port):
        """유즈케이스 인스턴스"""
        return SearchDocumentsUseCase(
            vector_search_port=mock_vector_search_port,
            embedding_port=mock_embedding_port
        )
    
    @pytest.fixture
    def sample_command(self):
        """샘플 검색 명령"""
        return SearchDocumentsCommand(
            user_id=uuid4(),
            query_text="Python programming tutorial",
            search_type=SearchType.SEMANTIC,
            limit=10,
            threshold=0.7
        )
    
    @pytest.fixture
    def sample_search_results(self):
        """샘플 검색 결과"""
        return [
            SearchResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                content="Python is a programming language",
                score=0.9,
                metadata={"page": 1}
            ),
            SearchResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                content="Tutorial for Python beginners",
                score=0.8,
                metadata={"page": 2}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_execute_semantic_search_success(
        self,
        use_case,
        mock_vector_search_port,
        mock_embedding_port,
        sample_command,
        sample_search_results
    ):
        """의미 기반 검색 성공 테스트"""
        # Given
        sample_embedding = [0.1, 0.2, 0.3]
        mock_embedding_port.create_embedding.return_value = sample_embedding
        mock_vector_search_port.search_similar_chunks.return_value = sample_search_results
        
        # When
        result = await use_case.execute(sample_command)
        
        # Then
        assert isinstance(result, SearchDocumentsResult)
        assert result.search_response.total_results == 2
        assert result.search_response.status.value == "completed"
        assert result.execution_time_ms > 0
        assert result.total_results == 2
        assert result.filtered_results == 2
        
        # 임베딩 생성 호출 확인
        mock_embedding_port.create_embedding.assert_called_once_with(
            text=sample_command.query_text
        )
        
        # 벡터 검색 호출 확인
        mock_vector_search_port.search_similar_chunks.assert_called_once_with(
            query_embedding=sample_embedding,
            limit=sample_command.limit,
            threshold=sample_command.threshold,
            filters={},
            user_id=sample_command.user_id
        )
    
    @pytest.mark.asyncio
    async def test_execute_keyword_search_success(
        self,
        use_case,
        mock_vector_search_port,
        mock_embedding_port,
        sample_search_results
    ):
        """키워드 기반 검색 성공 테스트"""
        # Given
        command = SearchDocumentsCommand(
            user_id=uuid4(),
            query_text="Python programming tutorial",
            search_type=SearchType.KEYWORD,
            limit=10,
            threshold=0.7
        )
        mock_vector_search_port.search_by_keywords.return_value = sample_search_results
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert isinstance(result, SearchDocumentsResult)
        assert result.search_response.total_results == 2
        
        # 키워드 검색 호출 확인
        mock_vector_search_port.search_by_keywords.assert_called_once()
        call_args = mock_vector_search_port.search_by_keywords.call_args
        assert "python" in call_args.kwargs["keywords"]
        assert "programming" in call_args.kwargs["keywords"]
        assert "tutorial" in call_args.kwargs["keywords"]
        
        # 임베딩 생성이 호출되지 않았는지 확인
        mock_embedding_port.create_embedding.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_hybrid_search_success(
        self,
        use_case,
        mock_vector_search_port,
        mock_embedding_port,
        sample_search_results
    ):
        """하이브리드 검색 성공 테스트"""
        # Given
        command = SearchDocumentsCommand(
            user_id=uuid4(),
            query_text="Python programming tutorial",
            search_type=SearchType.HYBRID,
            limit=10,
            threshold=0.7
        )
        sample_embedding = [0.1, 0.2, 0.3]
        mock_embedding_port.create_embedding.return_value = sample_embedding
        mock_vector_search_port.hybrid_search.return_value = sample_search_results
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert isinstance(result, SearchDocumentsResult)
        assert result.search_response.total_results == 2
        
        # 하이브리드 검색 호출 확인
        mock_vector_search_port.hybrid_search.assert_called_once()
        call_args = mock_vector_search_port.hybrid_search.call_args
        assert call_args.kwargs["query_embedding"] == sample_embedding
        assert "python" in call_args.kwargs["keywords"]
        assert call_args.kwargs["semantic_weight"] == 0.7
        assert call_args.kwargs["keyword_weight"] == 0.3
    
    @pytest.mark.asyncio
    async def test_execute_with_filters(
        self,
        use_case,
        mock_vector_search_port,
        mock_embedding_port,
        sample_search_results
    ):
        """필터가 있는 검색 테스트"""
        # Given
        filters = {"document_type": "pdf", "language": "en"}
        command = SearchDocumentsCommand(
            user_id=uuid4(),
            query_text="Python programming",
            search_type=SearchType.SEMANTIC,
            filters=filters
        )
        sample_embedding = [0.1, 0.2, 0.3]
        mock_embedding_port.create_embedding.return_value = sample_embedding
        mock_vector_search_port.search_similar_chunks.return_value = sample_search_results
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert isinstance(result, SearchDocumentsResult)
        
        # 필터가 전달되었는지 확인
        call_args = mock_vector_search_port.search_similar_chunks.call_args
        assert call_args.kwargs["filters"] == filters
    
    @pytest.mark.asyncio
    async def test_execute_with_threshold_filtering(
        self,
        use_case,
        mock_vector_search_port,
        mock_embedding_port
    ):
        """임계값 필터링 테스트"""
        # Given
        command = SearchDocumentsCommand(
            user_id=uuid4(),
            query_text="Python programming",
            threshold=0.8  # 높은 임계값
        )
        
        # 임계값보다 낮은 점수의 결과 포함
        search_results = [
            SearchResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                content="High score content",
                score=0.9,  # 임계값보다 높음
                metadata={}
            ),
            SearchResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                content="Low score content",
                score=0.7,  # 임계값보다 낮음
                metadata={}
            )
        ]
        
        sample_embedding = [0.1, 0.2, 0.3]
        mock_embedding_port.create_embedding.return_value = sample_embedding
        mock_vector_search_port.search_similar_chunks.return_value = search_results
        
        # When
        result = await use_case.execute(command)
        
        # Then
        # 임계값보다 높은 점수의 결과만 포함되어야 함
        assert result.search_response.total_results == 1
        assert result.search_response.results[0].score == 0.9
        assert result.total_results == 2  # 원본 결과 수
        assert result.filtered_results == 1  # 필터링 후 결과 수
    
    @pytest.mark.asyncio
    async def test_execute_without_metadata(
        self,
        use_case,
        mock_vector_search_port,
        mock_embedding_port,
        sample_search_results
    ):
        """메타데이터 제외 검색 테스트"""
        # Given
        command = SearchDocumentsCommand(
            user_id=uuid4(),
            query_text="Python programming",
            include_metadata=False
        )
        sample_embedding = [0.1, 0.2, 0.3]
        mock_embedding_port.create_embedding.return_value = sample_embedding
        mock_vector_search_port.search_similar_chunks.return_value = sample_search_results
        
        # When
        result = await use_case.execute(command)
        
        # Then
        # 메타데이터가 제거되었는지 확인
        for search_result in result.search_response.results:
            assert search_result.metadata == {}
    
    @pytest.mark.asyncio
    async def test_execute_with_invalid_user_id(self, use_case):
        """잘못된 사용자 ID로 검색 테스트"""
        # Given
        command = SearchDocumentsCommand(
            user_id=None,  # 잘못된 사용자 ID
            query_text="Python programming"
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="User ID is required"):
            await use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_execute_with_empty_query(self, use_case):
        """빈 쿼리로 검색 테스트"""
        # Given
        command = SearchDocumentsCommand(
            user_id=uuid4(),
            query_text=""  # 빈 쿼리
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Query text is required"):
            await use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_execute_with_invalid_limit(self, use_case):
        """잘못된 제한 수로 검색 테스트"""
        # Given
        command = SearchDocumentsCommand(
            user_id=uuid4(),
            query_text="Python programming",
            limit=0  # 잘못된 제한 수
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            await use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_execute_with_invalid_threshold(self, use_case):
        """잘못된 임계값으로 검색 테스트"""
        # Given
        command = SearchDocumentsCommand(
            user_id=uuid4(),
            query_text="Python programming",
            threshold=1.5  # 잘못된 임계값
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Threshold must be between 0.0 and 1.0"):
            await use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_execute_with_too_long_query(self, use_case):
        """너무 긴 쿼리로 검색 테스트"""
        # Given
        command = SearchDocumentsCommand(
            user_id=uuid4(),
            query_text="a" * 1001  # 1000자 초과
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Query text is too long"):
            await use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_execute_with_embedding_error(
        self,
        use_case,
        mock_embedding_port,
        sample_command
    ):
        """임베딩 생성 오류 테스트"""
        # Given
        mock_embedding_port.create_embedding.side_effect = Exception("Embedding service error")
        
        # When & Then
        with pytest.raises(SearchError, match="Search execution failed"):
            await use_case.execute(sample_command)
    
    @pytest.mark.asyncio
    async def test_execute_with_vector_search_error(
        self,
        use_case,
        mock_vector_search_port,
        mock_embedding_port,
        sample_command
    ):
        """벡터 검색 오류 테스트"""
        # Given
        mock_embedding_port.create_embedding.return_value = [0.1, 0.2, 0.3]
        mock_vector_search_port.search_similar_chunks.side_effect = Exception("Vector search error")
        
        # When & Then
        with pytest.raises(SearchError, match="Search execution failed"):
            await use_case.execute(sample_command)
    
    def test_extract_keywords(self, use_case):
        """키워드 추출 테스트"""
        # Given
        query_text = "Python programming tutorial for beginners"
        
        # When
        keywords = use_case._extract_keywords(query_text)
        
        # Then
        assert "python" in keywords
        assert "programming" in keywords
        assert "tutorial" in keywords
        assert "beginners" in keywords
        assert len(keywords) <= 10
        
        # 불용어가 제거되었는지 확인
        assert "for" not in keywords
    
    def test_extract_keywords_with_special_characters(self, use_case):
        """특수문자가 포함된 키워드 추출 테스트"""
        # Given
        query_text = "Python 3.9+ programming & tutorial!"
        
        # When
        keywords = use_case._extract_keywords(query_text)
        
        # Then
        assert "python" in keywords
        assert "programming" in keywords
        assert "tutorial" in keywords
        # 특수문자가 제거되었는지 확인
        assert any("&" in keyword for keyword in keywords) is False
        assert any("!" in keyword for keyword in keywords) is False
    
    @pytest.mark.asyncio
    async def test_get_search_suggestions(self, use_case):
        """검색 제안 생성 테스트"""
        # Given
        user_id = uuid4()
        partial_query = "python"
        
        # When
        suggestions = await use_case.get_search_suggestions(user_id, partial_query)
        
        # Then
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5
        # 부분 쿼리가 포함되어야 함
        for suggestion in suggestions:
            assert partial_query in suggestion.lower()
    
    @pytest.mark.asyncio
    async def test_get_search_suggestions_with_short_query(self, use_case):
        """짧은 쿼리로 검색 제안 테스트"""
        # Given
        user_id = uuid4()
        partial_query = "p"  # 2자 미만
        
        # When
        suggestions = await use_case.get_search_suggestions(user_id, partial_query)
        
        # Then
        assert suggestions == []
    
    @pytest.mark.asyncio
    async def test_get_search_history(self, use_case):
        """검색 히스토리 조회 테스트"""
        # Given
        user_id = uuid4()
        
        # When
        history = await use_case.get_search_history(user_id)
        
        # Then
        assert isinstance(history, list)
        # 현재는 빈 리스트 반환
        assert history == []
    
    @pytest.mark.asyncio
    async def test_post_process_results_deduplication(
        self,
        use_case,
        mock_vector_search_port,
        mock_embedding_port
    ):
        """결과 후처리 중복 제거 테스트"""
        # Given
        document_id = uuid4()
        command = SearchDocumentsCommand(
            user_id=uuid4(),
            query_text="Python programming",
            limit=5
        )
        
        # 같은 문서의 여러 청크
        search_results = [
            SearchResult(
                chunk_id=uuid4(),
                document_id=document_id,  # 같은 문서
                content="First chunk",
                score=0.9,
                metadata={}
            ),
            SearchResult(
                chunk_id=uuid4(),
                document_id=document_id,  # 같은 문서
                content="Second chunk",
                score=0.8,
                metadata={}
            ),
            SearchResult(
                chunk_id=uuid4(),
                document_id=uuid4(),  # 다른 문서
                content="Different document",
                score=0.7,
                metadata={}
            )
        ]
        
        sample_embedding = [0.1, 0.2, 0.3]
        mock_embedding_port.create_embedding.return_value = sample_embedding
        mock_vector_search_port.search_similar_chunks.return_value = search_results
        
        # When
        result = await use_case.execute(command)
        
        # Then
        # 중복 제거 로직에 따라 결과 확인
        assert result.search_response.total_results >= 2
        # 같은 문서의 청크도 limit 내에서는 포함될 수 있음
        document_ids = [r.document_id for r in result.search_response.results]
        assert len(set(document_ids)) >= 1  # 최소 1개 이상의 고유 문서
