"""
LLM Port

대화형 언어 모델 서비스 인터페이스 정의
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from uuid import UUID

from src.modules.search.domain.entities import AnswerRequest, Answer


class LLMPort(ABC):
    """LLM 서비스 포트 인터페이스"""
    
    @abstractmethod
    async def generate_answer(
        self,
        request: AnswerRequest
    ) -> Answer:
        """
        컨텍스트 기반 답변 생성
        
        Args:
            request: 답변 생성 요청
            
        Returns:
            생성된 답변
        """
        pass
    
    @abstractmethod
    async def generate_query_embedding(
        self,
        query_text: str,
        model_name: str = "text-embedding-ada-002"
    ) -> List[float]:
        """
        쿼리 텍스트의 임베딩 벡터 생성
        
        Args:
            query_text: 쿼리 텍스트
            model_name: 임베딩 모델 이름
            
        Returns:
            임베딩 벡터
        """
        pass
    
    @abstractmethod
    async def extract_keywords(
        self,
        query_text: str,
        max_keywords: int = 10
    ) -> List[str]:
        """
        쿼리에서 키워드 추출
        
        Args:
            query_text: 쿼리 텍스트
            max_keywords: 최대 키워드 수
            
        Returns:
            추출된 키워드 리스트
        """
        pass
    
    @abstractmethod
    async def calculate_confidence_score(
        self,
        query_text: str,
        answer_text: str,
        context_chunks: List[str]
    ) -> float:
        """
        답변의 신뢰도 점수 계산
        
        Args:
            query_text: 원본 쿼리
            answer_text: 생성된 답변
            context_chunks: 컨텍스트 청크들
            
        Returns:
            신뢰도 점수 (0.0 ~ 1.0)
        """
        pass
    
    @abstractmethod
    async def improve_query(
        self,
        original_query: str,
        search_results: List[Dict[str, Any]]
    ) -> str:
        """
        검색 결과를 바탕으로 쿼리 개선
        
        Args:
            original_query: 원본 쿼리
            search_results: 검색 결과
            
        Returns:
            개선된 쿼리
        """
        pass
    
    @abstractmethod
    async def summarize_context(
        self,
        context_chunks: List[str],
        max_length: int = 1000
    ) -> str:
        """
        컨텍스트 청크들을 요약
        
        Args:
            context_chunks: 컨텍스트 청크들
            max_length: 최대 요약 길이
            
        Returns:
            요약된 텍스트
        """
        pass
    
    @abstractmethod
    async def check_model_availability(
        self,
        model_name: str
    ) -> bool:
        """
        모델 사용 가능 여부 확인
        
        Args:
            model_name: 모델 이름
            
        Returns:
            사용 가능 여부
        """
        pass
    
    @abstractmethod
    async def get_model_info(
        self,
        model_name: str
    ) -> Dict[str, Any]:
        """
        모델 정보 조회
        
        Args:
            model_name: 모델 이름
            
        Returns:
            모델 정보 딕셔너리
        """
        pass


class EmbeddingPort(ABC):
    """임베딩 서비스 포트 인터페이스"""
    
    @abstractmethod
    async def create_embedding(
        self,
        text: str,
        model_name: str = "text-embedding-ada-002"
    ) -> List[float]:
        """
        텍스트 임베딩 생성
        
        Args:
            text: 입력 텍스트
            model_name: 임베딩 모델 이름
            
        Returns:
            임베딩 벡터
        """
        pass
    
    @abstractmethod
    async def create_embeddings_batch(
        self,
        texts: List[str],
        model_name: str = "text-embedding-ada-002",
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        배치 임베딩 생성
        
        Args:
            texts: 입력 텍스트 리스트
            model_name: 임베딩 모델 이름
            batch_size: 배치 크기
            
        Returns:
            임베딩 벡터 리스트
        """
        pass
    
    @abstractmethod
    async def calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        두 임베딩 간 유사도 계산
        
        Args:
            embedding1: 첫 번째 임베딩
            embedding2: 두 번째 임베딩
            
        Returns:
            유사도 점수 (0.0 ~ 1.0)
        """
        pass
    
    @abstractmethod
    async def get_embedding_dimension(
        self,
        model_name: str = "text-embedding-ada-002"
    ) -> int:
        """
        임베딩 차원 수 조회
        
        Args:
            model_name: 임베딩 모델 이름
            
        Returns:
            임베딩 차원 수
        """
        pass
