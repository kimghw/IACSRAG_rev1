"""
Process Repository Ports

문서 처리 관련 리포지토리 포트를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID

from src.modules.process.domain.entities import (
    ProcessingJob,
    ProcessingStatus,
    ProcessingType,
    TextChunk,
    ProcessingResult
)


class ProcessingJobRepository(ABC):
    """처리 작업 리포지토리 포트"""
    
    @abstractmethod
    async def save(self, job: ProcessingJob) -> None:
        """처리 작업 저장"""
        pass
    
    @abstractmethod
    async def find_by_id(self, job_id: UUID) -> Optional[ProcessingJob]:
        """ID로 처리 작업 조회"""
        pass
    
    @abstractmethod
    async def find_by_document_id(self, document_id: UUID) -> List[ProcessingJob]:
        """문서 ID로 처리 작업 목록 조회"""
        pass
    
    @abstractmethod
    async def find_by_user_id(self, user_id: UUID) -> List[ProcessingJob]:
        """사용자 ID로 처리 작업 목록 조회"""
        pass
    
    @abstractmethod
    async def find_by_status(self, status: ProcessingStatus) -> List[ProcessingJob]:
        """상태별 처리 작업 목록 조회"""
        pass
    
    @abstractmethod
    async def find_pending_jobs(self, limit: Optional[int] = None) -> List[ProcessingJob]:
        """대기 중인 작업 목록 조회 (우선순위 순)"""
        pass
    
    @abstractmethod
    async def find_failed_jobs_for_retry(self) -> List[ProcessingJob]:
        """재시도 가능한 실패 작업 목록 조회"""
        pass
    
    @abstractmethod
    async def update_status(self, job_id: UUID, status: ProcessingStatus) -> None:
        """작업 상태 업데이트"""
        pass
    
    @abstractmethod
    async def delete(self, job_id: UUID) -> None:
        """처리 작업 삭제"""
        pass
    
    @abstractmethod
    async def count_by_status(self, status: ProcessingStatus) -> int:
        """상태별 작업 수 조회"""
        pass
    
    @abstractmethod
    async def find_with_filters(
        self,
        user_id: Optional[UUID] = None,
        document_id: Optional[UUID] = None,
        processing_type: Optional[ProcessingType] = None,
        status: Optional[ProcessingStatus] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[ProcessingJob]:
        """필터 조건으로 처리 작업 목록 조회"""
        pass


class TextChunkRepository(ABC):
    """텍스트 청크 리포지토리 포트"""
    
    @abstractmethod
    async def save(self, chunk: TextChunk) -> None:
        """텍스트 청크 저장"""
        pass
    
    @abstractmethod
    async def save_batch(self, chunks: List[TextChunk]) -> None:
        """텍스트 청크 배치 저장"""
        pass
    
    @abstractmethod
    async def find_by_id(self, chunk_id: UUID) -> Optional[TextChunk]:
        """ID로 텍스트 청크 조회"""
        pass
    
    @abstractmethod
    async def find_by_document_id(self, document_id: UUID) -> List[TextChunk]:
        """문서 ID로 텍스트 청크 목록 조회"""
        pass
    
    @abstractmethod
    async def find_by_user_id(self, user_id: UUID) -> List[TextChunk]:
        """사용자 ID로 텍스트 청크 목록 조회"""
        pass
    
    @abstractmethod
    async def find_by_embedding_id(self, embedding_id: UUID) -> Optional[TextChunk]:
        """임베딩 ID로 텍스트 청크 조회"""
        pass
    
    @abstractmethod
    async def update_embedding_id(self, chunk_id: UUID, embedding_id: UUID) -> None:
        """청크의 임베딩 ID 업데이트"""
        pass
    
    @abstractmethod
    async def delete_by_document_id(self, document_id: UUID) -> None:
        """문서 ID로 텍스트 청크 삭제"""
        pass
    
    @abstractmethod
    async def count_by_document_id(self, document_id: UUID) -> int:
        """문서 ID별 청크 수 조회"""
        pass
    
    @abstractmethod
    async def find_with_filters(
        self,
        user_id: Optional[UUID] = None,
        document_id: Optional[UUID] = None,
        chunk_type: Optional[str] = None,
        has_embedding: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[TextChunk]:
        """필터 조건으로 텍스트 청크 목록 조회"""
        pass


class ProcessingResultRepository(ABC):
    """처리 결과 리포지토리 포트"""
    
    @abstractmethod
    async def save(self, result: ProcessingResult) -> None:
        """처리 결과 저장"""
        pass
    
    @abstractmethod
    async def find_by_id(self, result_id: UUID) -> Optional[ProcessingResult]:
        """ID로 처리 결과 조회"""
        pass
    
    @abstractmethod
    async def find_by_job_id(self, job_id: UUID) -> Optional[ProcessingResult]:
        """작업 ID로 처리 결과 조회"""
        pass
    
    @abstractmethod
    async def find_by_document_id(self, document_id: UUID) -> List[ProcessingResult]:
        """문서 ID로 처리 결과 목록 조회"""
        pass
    
    @abstractmethod
    async def find_by_user_id(self, user_id: UUID) -> List[ProcessingResult]:
        """사용자 ID로 처리 결과 목록 조회"""
        pass
    
    @abstractmethod
    async def find_by_processing_type(self, processing_type: ProcessingType) -> List[ProcessingResult]:
        """처리 유형별 결과 목록 조회"""
        pass
    
    @abstractmethod
    async def delete(self, result_id: UUID) -> None:
        """처리 결과 삭제"""
        pass
    
    @abstractmethod
    async def delete_by_job_id(self, job_id: UUID) -> None:
        """작업 ID로 처리 결과 삭제"""
        pass
    
    @abstractmethod
    async def find_with_filters(
        self,
        user_id: Optional[UUID] = None,
        document_id: Optional[UUID] = None,
        processing_type: Optional[ProcessingType] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[ProcessingResult]:
        """필터 조건으로 처리 결과 목록 조회"""
        pass
