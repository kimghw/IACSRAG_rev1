"""
Vector Search Port

벡터 검색 서비스 인터페이스 정의
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from uuid import UUID

from src.modules.search.domain.entities import SearchQuery, SearchResult


class VectorSearchPort(ABC):
    """벡터 검색 포트 인터페이스"""
    
    @abstractmethod
    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None
    ) -> List[SearchResult]:
        """
        벡터 유사도 기반 청크 검색
        
        Args:
            query_embedding: 쿼리 임베딩 벡터
            limit: 반환할 최대 결과 수
            threshold: 유사도 임계값
            filters: 추가 필터 조건
            user_id: 사용자 ID (권한 필터링용)
            
        Returns:
            검색 결과 리스트
        """
        pass
    
    @abstractmethod
    async def search_by_keywords(
        self,
        keywords: List[str],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None
    ) -> List[SearchResult]:
        """
        키워드 기반 청크 검색
        
        Args:
            keywords: 검색 키워드 리스트
            limit: 반환할 최대 결과 수
            filters: 추가 필터 조건
            user_id: 사용자 ID (권한 필터링용)
            
        Returns:
            검색 결과 리스트
        """
        pass
    
    @abstractmethod
    async def hybrid_search(
        self,
        query_embedding: List[float],
        keywords: List[str],
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        limit: int = 10,
        threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None
    ) -> List[SearchResult]:
        """
        하이브리드 검색 (의미 + 키워드)
        
        Args:
            query_embedding: 쿼리 임베딩 벡터
            keywords: 검색 키워드 리스트
            semantic_weight: 의미 검색 가중치
            keyword_weight: 키워드 검색 가중치
            limit: 반환할 최대 결과 수
            threshold: 유사도 임계값
            filters: 추가 필터 조건
            user_id: 사용자 ID (권한 필터링용)
            
        Returns:
            검색 결과 리스트
        """
        pass
    
    @abstractmethod
    async def get_chunk_by_id(
        self,
        chunk_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[SearchResult]:
        """
        ID로 청크 조회
        
        Args:
            chunk_id: 청크 ID
            user_id: 사용자 ID (권한 확인용)
            
        Returns:
            검색 결과 또는 None
        """
        pass
    
    @abstractmethod
    async def get_chunks_by_document(
        self,
        document_id: UUID,
        user_id: Optional[UUID] = None
    ) -> List[SearchResult]:
        """
        문서별 청크 조회
        
        Args:
            document_id: 문서 ID
            user_id: 사용자 ID (권한 확인용)
            
        Returns:
            해당 문서의 청크 리스트
        """
        pass
    
    @abstractmethod
    async def check_collection_health(self) -> Dict[str, Any]:
        """
        벡터 컬렉션 상태 확인
        
        Returns:
            상태 정보 딕셔너리
        """
        pass
