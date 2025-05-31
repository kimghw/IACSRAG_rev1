"""
Search Documents Use Case

문서 검색 유즈케이스 구현 (UC-09)
"""

import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from uuid import UUID

from src.core.exceptions import ValidationError, SearchError
from src.core.logging import get_logger
from src.modules.search.domain.entities import (
    SearchQuery,
    SearchResult,
    SearchResponse,
    SearchType,
    SearchStatus
)
from src.modules.search.application.ports.vector_search_port import VectorSearchPort
from src.modules.search.application.ports.llm_port import EmbeddingPort

logger = get_logger(__name__)


@dataclass
class SearchDocumentsCommand:
    """문서 검색 명령"""
    
    user_id: UUID
    query_text: str
    search_type: SearchType = SearchType.SEMANTIC
    limit: int = 10
    threshold: float = 0.7
    filters: Optional[Dict[str, Any]] = None
    include_metadata: bool = True


@dataclass
class SearchDocumentsResult:
    """문서 검색 결과"""
    
    search_response: SearchResponse
    execution_time_ms: float
    total_results: int
    filtered_results: int


class SearchDocumentsUseCase:
    """문서 검색 유즈케이스"""
    
    def __init__(
        self,
        vector_search_port: VectorSearchPort,
        embedding_port: EmbeddingPort
    ):
        self.vector_search_port = vector_search_port
        self.embedding_port = embedding_port
    
    async def execute(self, command: SearchDocumentsCommand) -> SearchDocumentsResult:
        """
        문서 검색 실행
        
        Args:
            command: 검색 명령
            
        Returns:
            검색 결과
            
        Raises:
            ValidationError: 입력 검증 실패
            SearchError: 검색 실행 실패
        """
        start_time = time.time()
        
        try:
            # 1. 입력 검증
            self._validate_command(command)
            
            # 2. 검색 쿼리 생성
            search_query = self._create_search_query(command)
            
            # 3. 검색 실행
            search_results = await self._execute_search(search_query, command)
            
            # 4. 결과 후처리
            processed_results = await self._post_process_results(
                search_results, command
            )
            
            # 5. 응답 생성
            execution_time = (time.time() - start_time) * 1000
            search_response = SearchResponse.create(
                query=search_query,
                results=processed_results,
                search_time_ms=execution_time
            )
            
            logger.info(
                "Document search completed",
                extra={
                    "user_id": str(command.user_id),
                    "query_text": command.query_text,
                    "search_type": command.search_type.value,
                    "results_count": len(processed_results),
                    "execution_time_ms": execution_time
                }
            )
            
            return SearchDocumentsResult(
                search_response=search_response,
                execution_time_ms=execution_time,
                total_results=len(search_results),
                filtered_results=len(processed_results)
            )
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                "Document search failed",
                extra={
                    "user_id": str(command.user_id),
                    "query_text": command.query_text,
                    "error": str(e)
                }
            )
            raise SearchError(f"Search execution failed: {str(e)}") from e
    
    def _validate_command(self, command: SearchDocumentsCommand) -> None:
        """명령 검증"""
        if not command.user_id:
            raise ValidationError("User ID is required")
        
        if not command.query_text or not command.query_text.strip():
            raise ValidationError("Query text is required")
        
        if command.limit <= 0 or command.limit > 100:
            raise ValidationError("Limit must be between 1 and 100")
        
        if not 0.0 <= command.threshold <= 1.0:
            raise ValidationError("Threshold must be between 0.0 and 1.0")
        
        if len(command.query_text) > 1000:
            raise ValidationError("Query text is too long (max 1000 characters)")
    
    def _create_search_query(self, command: SearchDocumentsCommand) -> SearchQuery:
        """검색 쿼리 생성"""
        return SearchQuery.create(
            user_id=command.user_id,
            query_text=command.query_text.strip(),
            search_type=command.search_type,
            filters=command.filters or {},
            limit=command.limit,
            threshold=command.threshold
        )
    
    async def _execute_search(
        self,
        search_query: SearchQuery,
        command: SearchDocumentsCommand
    ) -> List[SearchResult]:
        """검색 실행"""
        try:
            if search_query.search_type == SearchType.SEMANTIC:
                return await self._execute_semantic_search(search_query, command)
            elif search_query.search_type == SearchType.KEYWORD:
                return await self._execute_keyword_search(search_query, command)
            elif search_query.search_type == SearchType.HYBRID:
                return await self._execute_hybrid_search(search_query, command)
            else:
                raise ValidationError(f"Unsupported search type: {search_query.search_type}")
                
        except Exception as e:
            logger.error(
                "Search execution failed",
                extra={
                    "search_type": search_query.search_type.value,
                    "query_text": search_query.query_text,
                    "error": str(e)
                }
            )
            raise SearchError(f"Failed to execute {search_query.search_type.value} search") from e
    
    async def _execute_semantic_search(
        self,
        search_query: SearchQuery,
        command: SearchDocumentsCommand
    ) -> List[SearchResult]:
        """의미 기반 검색 실행"""
        # 쿼리 임베딩 생성
        query_embedding = await self.embedding_port.create_embedding(
            text=search_query.query_text
        )
        
        # 벡터 검색 실행
        return await self.vector_search_port.search_similar_chunks(
            query_embedding=query_embedding,
            limit=search_query.limit,
            threshold=search_query.threshold,
            filters=search_query.filters,
            user_id=search_query.user_id
        )
    
    async def _execute_keyword_search(
        self,
        search_query: SearchQuery,
        command: SearchDocumentsCommand
    ) -> List[SearchResult]:
        """키워드 기반 검색 실행"""
        # 키워드 추출
        keywords = self._extract_keywords(search_query.query_text)
        
        # 키워드 검색 실행
        return await self.vector_search_port.search_by_keywords(
            keywords=keywords,
            limit=search_query.limit,
            filters=search_query.filters,
            user_id=search_query.user_id
        )
    
    async def _execute_hybrid_search(
        self,
        search_query: SearchQuery,
        command: SearchDocumentsCommand
    ) -> List[SearchResult]:
        """하이브리드 검색 실행"""
        # 쿼리 임베딩 생성
        query_embedding = await self.embedding_port.create_embedding(
            text=search_query.query_text
        )
        
        # 키워드 추출
        keywords = self._extract_keywords(search_query.query_text)
        
        # 하이브리드 검색 실행
        return await self.vector_search_port.hybrid_search(
            query_embedding=query_embedding,
            keywords=keywords,
            semantic_weight=0.7,
            keyword_weight=0.3,
            limit=search_query.limit,
            threshold=search_query.threshold,
            filters=search_query.filters,
            user_id=search_query.user_id
        )
    
    def _extract_keywords(self, query_text: str) -> List[str]:
        """키워드 추출 (간단한 구현)"""
        # 실제로는 더 정교한 키워드 추출 로직이 필요
        import re
        
        # 특수문자 제거 및 소문자 변환
        cleaned_text = re.sub(r'[^\w\s]', '', query_text.lower())
        
        # 단어 분리
        words = cleaned_text.split()
        
        # 불용어 제거 (간단한 예시)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords[:10]  # 최대 10개 키워드
    
    async def _post_process_results(
        self,
        search_results: List[SearchResult],
        command: SearchDocumentsCommand
    ) -> List[SearchResult]:
        """검색 결과 후처리"""
        processed_results = []
        
        for result in search_results:
            # 점수 기반 필터링
            if result.score >= command.threshold:
                # 메타데이터 추가/제거
                if not command.include_metadata:
                    result.metadata = {}
                
                processed_results.append(result)
        
        # 점수 기준 정렬
        processed_results.sort(key=lambda x: x.score, reverse=True)
        
        # 중복 제거 (같은 문서의 청크가 여러 개인 경우)
        seen_documents = set()
        unique_results = []
        
        for result in processed_results:
            if result.document_id not in seen_documents:
                unique_results.append(result)
                seen_documents.add(result.document_id)
            elif len(unique_results) < command.limit:
                # 같은 문서라도 limit 내에서는 포함
                unique_results.append(result)
        
        return unique_results[:command.limit]
    
    async def get_search_suggestions(
        self,
        user_id: UUID,
        partial_query: str,
        limit: int = 5
    ) -> List[str]:
        """검색 제안 생성"""
        try:
            # 간단한 검색 제안 로직
            # 실제로는 검색 히스토리, 인기 검색어 등을 활용
            suggestions = []
            
            if len(partial_query) >= 2:
                # 부분 쿼리로 키워드 검색
                keywords = self._extract_keywords(partial_query)
                if keywords:
                    # 키워드 기반 제안 생성
                    for keyword in keywords[:limit]:
                        suggestions.append(f"{partial_query} {keyword}")
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.warning(
                "Failed to generate search suggestions",
                extra={
                    "user_id": str(user_id),
                    "partial_query": partial_query,
                    "error": str(e)
                }
            )
            return []
    
    async def get_search_history(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """검색 히스토리 조회"""
        # 실제로는 데이터베이스에서 검색 히스토리를 조회
        # 현재는 빈 리스트 반환
        return []
