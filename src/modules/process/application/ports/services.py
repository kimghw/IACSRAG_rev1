"""
Process Service Ports

문서 처리 관련 외부 서비스 포트를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from uuid import UUID

from src.modules.process.domain.entities import (
    TextChunk,
    ChunkType,
    ProcessingMetadata
)


class TextExtractionService(ABC):
    """텍스트 추출 서비스 포트"""
    
    @abstractmethod
    async def extract_text(
        self,
        document_id: UUID,
        file_path: str,
        file_type: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        문서에서 텍스트 추출
        
        Args:
            document_id: 문서 ID
            file_path: 파일 경로
            file_type: 파일 유형
            parameters: 추출 파라미터
            
        Returns:
            Dict[str, Any]: 추출된 텍스트와 메타데이터
            {
                "text_content": str,
                "metadata": Dict[str, Any],
                "page_count": int,
                "word_count": int
            }
        """
        pass
    
    @abstractmethod
    async def extract_text_with_structure(
        self,
        document_id: UUID,
        file_path: str,
        file_type: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        구조 정보와 함께 텍스트 추출
        
        Args:
            document_id: 문서 ID
            file_path: 파일 경로
            file_type: 파일 유형
            parameters: 추출 파라미터
            
        Returns:
            Dict[str, Any]: 구조화된 텍스트 정보
            {
                "sections": List[Dict],
                "tables": List[Dict],
                "images": List[Dict],
                "metadata": Dict[str, Any]
            }
        """
        pass


class ChunkingService(ABC):
    """청킹 서비스 포트"""
    
    @abstractmethod
    async def chunk_text(
        self,
        text_content: str,
        chunk_type: ChunkType,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        텍스트 청킹
        
        Args:
            text_content: 청킹할 텍스트
            chunk_type: 청킹 유형
            parameters: 청킹 파라미터
            
        Returns:
            List[Dict[str, Any]]: 청크 정보 목록
            [
                {
                    "content": str,
                    "start_position": int,
                    "end_position": int,
                    "metadata": Dict[str, Any]
                }
            ]
        """
        pass
    
    @abstractmethod
    async def chunk_with_overlap(
        self,
        text_content: str,
        chunk_size: int,
        overlap_size: int,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        오버랩을 고려한 텍스트 청킹
        
        Args:
            text_content: 청킹할 텍스트
            chunk_size: 청크 크기
            overlap_size: 오버랩 크기
            parameters: 청킹 파라미터
            
        Returns:
            List[Dict[str, Any]]: 청크 정보 목록
        """
        pass
    
    @abstractmethod
    async def semantic_chunking(
        self,
        text_content: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        의미 기반 청킹
        
        Args:
            text_content: 청킹할 텍스트
            parameters: 청킹 파라미터
            
        Returns:
            List[Dict[str, Any]]: 의미 단위 청크 목록
        """
        pass


class EmbeddingService(ABC):
    """임베딩 서비스 포트"""
    
    @abstractmethod
    async def generate_embedding(
        self,
        text: str,
        model_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        단일 텍스트 임베딩 생성
        
        Args:
            text: 임베딩할 텍스트
            model_name: 사용할 모델명
            parameters: 임베딩 파라미터
            
        Returns:
            Dict[str, Any]: 임베딩 정보
            {
                "embedding": List[float],
                "model_name": str,
                "model_version": str,
                "dimension": int,
                "metadata": Dict[str, Any]
            }
        """
        pass
    
    @abstractmethod
    async def generate_batch_embeddings(
        self,
        texts: List[str],
        model_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        배치 텍스트 임베딩 생성
        
        Args:
            texts: 임베딩할 텍스트 목록
            model_name: 사용할 모델명
            parameters: 임베딩 파라미터
            
        Returns:
            List[Dict[str, Any]]: 임베딩 정보 목록
        """
        pass
    
    @abstractmethod
    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        모델 정보 조회
        
        Args:
            model_name: 모델명
            
        Returns:
            Dict[str, Any]: 모델 정보
            {
                "name": str,
                "version": str,
                "dimension": int,
                "max_tokens": int,
                "description": str
            }
        """
        pass


class VectorStoreService(ABC):
    """벡터 스토어 서비스 포트"""
    
    @abstractmethod
    async def store_embedding(
        self,
        embedding_id: UUID,
        vector: List[float],
        metadata: Dict[str, Any],
        collection_name: Optional[str] = None
    ) -> None:
        """
        임베딩 벡터 저장
        
        Args:
            embedding_id: 임베딩 ID
            vector: 벡터 데이터
            metadata: 메타데이터
            collection_name: 컬렉션명
        """
        pass
    
    @abstractmethod
    async def store_batch_embeddings(
        self,
        embeddings: List[Dict[str, Any]],
        collection_name: Optional[str] = None
    ) -> None:
        """
        배치 임베딩 벡터 저장
        
        Args:
            embeddings: 임베딩 데이터 목록
            [
                {
                    "id": UUID,
                    "vector": List[float],
                    "metadata": Dict[str, Any]
                }
            ]
            collection_name: 컬렉션명
        """
        pass
    
    @abstractmethod
    async def delete_embedding(
        self,
        embedding_id: UUID,
        collection_name: Optional[str] = None
    ) -> None:
        """
        임베딩 벡터 삭제
        
        Args:
            embedding_id: 임베딩 ID
            collection_name: 컬렉션명
        """
        pass
    
    @abstractmethod
    async def delete_by_document_id(
        self,
        document_id: UUID,
        collection_name: Optional[str] = None
    ) -> None:
        """
        문서 ID로 임베딩 벡터 삭제
        
        Args:
            document_id: 문서 ID
            collection_name: 컬렉션명
        """
        pass
    
    @abstractmethod
    async def search_similar(
        self,
        query_vector: List[float],
        limit: int = 10,
        threshold: Optional[float] = None,
        collection_name: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        유사 벡터 검색
        
        Args:
            query_vector: 쿼리 벡터
            limit: 결과 수 제한
            threshold: 유사도 임계값
            collection_name: 컬렉션명
            filters: 필터 조건
            
        Returns:
            List[Dict[str, Any]]: 검색 결과
            [
                {
                    "id": UUID,
                    "score": float,
                    "metadata": Dict[str, Any]
                }
            ]
        """
        pass


class EventPublisher(ABC):
    """이벤트 발행 서비스 포트"""
    
    @abstractmethod
    async def publish_processing_started(
        self,
        job_id: UUID,
        document_id: UUID,
        user_id: UUID,
        processing_type: str
    ) -> None:
        """처리 시작 이벤트 발행"""
        pass
    
    @abstractmethod
    async def publish_processing_completed(
        self,
        job_id: UUID,
        document_id: UUID,
        user_id: UUID,
        processing_type: str,
        result_data: Dict[str, Any]
    ) -> None:
        """처리 완료 이벤트 발행"""
        pass
    
    @abstractmethod
    async def publish_processing_failed(
        self,
        job_id: UUID,
        document_id: UUID,
        user_id: UUID,
        processing_type: str,
        error_message: str
    ) -> None:
        """처리 실패 이벤트 발행"""
        pass
    
    @abstractmethod
    async def publish_chunks_created(
        self,
        document_id: UUID,
        user_id: UUID,
        chunk_count: int,
        chunk_ids: List[UUID]
    ) -> None:
        """청크 생성 이벤트 발행"""
        pass
    
    @abstractmethod
    async def publish_embeddings_created(
        self,
        document_id: UUID,
        user_id: UUID,
        embedding_count: int,
        embedding_ids: List[UUID]
    ) -> None:
        """임베딩 생성 이벤트 발행"""
        pass
    
    @abstractmethod
    async def publish_chunks_deduplicated(
        self,
        document_id: UUID,
        user_id: UUID,
        removed_chunk_count: int,
        duplicate_groups_count: int
    ) -> None:
        """청크 중복 제거 완료 이벤트 발행"""
        pass


class NotificationService(ABC):
    """알림 서비스 포트"""
    
    @abstractmethod
    async def send_processing_notification(
        self,
        user_id: UUID,
        document_id: UUID,
        status: str,
        message: str,
        notification_type: str = "processing"
    ) -> None:
        """
        처리 상태 알림 발송
        
        Args:
            user_id: 사용자 ID
            document_id: 문서 ID
            status: 처리 상태
            message: 알림 메시지
            notification_type: 알림 유형
        """
        pass
    
    @abstractmethod
    async def send_error_notification(
        self,
        user_id: UUID,
        document_id: UUID,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        오류 알림 발송
        
        Args:
            user_id: 사용자 ID
            document_id: 문서 ID
            error_message: 오류 메시지
            error_details: 오류 상세 정보
        """
        pass
