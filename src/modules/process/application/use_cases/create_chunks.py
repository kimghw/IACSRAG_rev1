"""
Create Chunks Use Case

문서 청킹 유즈케이스
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from uuid import UUID

from src.core.exceptions import ValidationError, DocumentProcessingError
from src.core.logging import get_logger
from src.modules.process.domain.entities import (
    ProcessingJob,
    ProcessingType,
    ProcessingStatus,
    TextChunk,
    ChunkType
)
from src.modules.process.application.ports.repositories import ProcessingJobRepository
from src.modules.process.application.ports.services import (
    EventPublisher,
    ChunkingService
)

logger = get_logger(__name__)


@dataclass
class CreateChunksCommand:
    """청킹 생성 명령"""
    job_id: UUID
    text_content: str
    document_id: UUID
    chunking_options: Optional[Dict[str, Any]] = None


@dataclass
class CreateChunksResult:
    """청킹 생성 결과"""
    job_id: UUID
    chunks: List[TextChunk]
    total_chunks: int
    status: ProcessingStatus
    message: str


class CreateChunksUseCase:
    """문서 청킹 생성 유즈케이스"""
    
    def __init__(
        self,
        job_repository: ProcessingJobRepository,
        chunking_service: ChunkingService,
        event_publisher: EventPublisher
    ):
        self.job_repository = job_repository
        self.chunking_service = chunking_service
        self.event_publisher = event_publisher
    
    async def execute(self, command: CreateChunksCommand) -> CreateChunksResult:
        """
        청킹 생성 실행
        
        Args:
            command: 청킹 생성 명령
            
        Returns:
            CreateChunksResult: 청킹 생성 결과
            
        Raises:
            ValidationError: 입력 데이터 검증 실패
            DocumentProcessingError: 문서 처리 오류
        """
        logger.info(f"Starting chunk creation for job {command.job_id}")
        
        # 1. 입력 데이터 검증
        await self._validate_command(command)
        
        # 2. 작업 조회 및 상태 확인
        job = await self._get_and_validate_job(command.job_id)
        
        try:
            # 3. 작업 상태를 처리 중으로 변경
            job.start_processing()
            await self.job_repository.save(job)
            
            # 4. 텍스트 청킹 실행
            chunk_type = self._get_chunk_type(command.chunking_options)
            chunk_data = await self.chunking_service.chunk_text(
                text_content=command.text_content,
                chunk_type=chunk_type,
                parameters=command.chunking_options or {}
            )
            
            # 5. 청크 엔티티 생성
            chunks = []
            for i, chunk_info in enumerate(chunk_data):
                chunk = TextChunk.create(
                    document_id=command.document_id,
                    user_id=job.user_id,
                    content=chunk_info['content'],
                    chunk_type=chunk_type,
                    sequence_number=i,
                    start_position=chunk_info.get('start_position', 0),
                    end_position=chunk_info.get('end_position', len(chunk_info['content'])),
                    metadata=chunk_info.get('metadata', {})
                )
                chunks.append(chunk)
            
            # 6. 청킹 결과 검증
            if not chunks or len(chunks) == 0:
                raise DocumentProcessingError("No chunks could be created from the text content")
            
            # 7. 작업 완료 처리
            job.complete_processing()
            await self.job_repository.save(job)
            
            # 8. 이벤트 발행
            await self.event_publisher.publish_processing_completed(
                job_id=job.id,
                document_id=job.document_id,
                user_id=job.user_id,
                processing_type=job.processing_type.value,
                result_data={
                    "total_chunks": len(chunks),
                    "chunk_ids": [str(chunk.id) for chunk in chunks],
                    "average_chunk_size": sum(len(chunk.content) for chunk in chunks) // len(chunks)
                }
            )
            
            # 9. 청크 생성 이벤트 발행
            await self.event_publisher.publish_chunks_created(
                document_id=command.document_id,
                user_id=job.user_id,
                chunk_count=len(chunks),
                chunk_ids=[chunk.id for chunk in chunks]
            )
            
            logger.info(
                f"Chunk creation completed for job {command.job_id}. "
                f"Created {len(chunks)} chunks"
            )
            
            return CreateChunksResult(
                job_id=job.id,
                chunks=chunks,
                total_chunks=len(chunks),
                status=job.status,
                message="Chunk creation completed successfully"
            )
            
        except Exception as e:
            # 10. 오류 처리
            await self._handle_chunking_error(job, e)
            raise
    
    async def _validate_command(self, command: CreateChunksCommand) -> None:
        """명령 데이터 검증"""
        if not command.job_id:
            raise ValidationError("Job ID is required")
        
        if not command.text_content:
            raise ValidationError("Text content is required")
        
        if not command.document_id:
            raise ValidationError("Document ID is required")
        
        # 텍스트 길이 검증
        if len(command.text_content.strip()) < 10:
            raise ValidationError("Text content is too short for chunking")
        
        # 최대 텍스트 길이 검증 (예: 10MB)
        max_text_size = 10 * 1024 * 1024  # 10MB
        if len(command.text_content.encode('utf-8')) > max_text_size:
            raise ValidationError(f"Text content exceeds maximum size of {max_text_size} bytes")
    
    async def _get_and_validate_job(self, job_id: UUID) -> ProcessingJob:
        """작업 조회 및 상태 검증"""
        job = await self.job_repository.find_by_id(job_id)
        if not job:
            raise ValidationError(f"Job {job_id} not found")
        
        if job.processing_type != ProcessingType.CHUNKING:
            raise ValidationError(
                f"Job {job_id} is not a chunking job. "
                f"Type: {job.processing_type.value}"
            )
        
        if job.status != ProcessingStatus.PENDING:
            raise ValidationError(
                f"Job {job_id} is not in pending status. "
                f"Current status: {job.status.value}"
            )
        
        return job
    
    def _get_chunk_type(self, chunking_options: Optional[Dict[str, Any]]) -> ChunkType:
        """청킹 옵션에서 청크 타입 추출"""
        if not chunking_options:
            return ChunkType.FIXED_SIZE
        
        chunk_type_str = chunking_options.get('chunk_type', 'fixed_size')
        
        # 문자열을 ChunkType enum으로 변환
        chunk_type_mapping = {
            'fixed_size': ChunkType.FIXED_SIZE,
            'semantic': ChunkType.SEMANTIC,
            'paragraph': ChunkType.PARAGRAPH,
            'sentence': ChunkType.SENTENCE
        }
        
        return chunk_type_mapping.get(chunk_type_str, ChunkType.FIXED_SIZE)
    
    async def _handle_chunking_error(self, job: ProcessingJob, error: Exception) -> None:
        """청킹 오류 처리"""
        error_message = str(error)
        error_type = type(error).__name__
        
        logger.error(
            f"Chunk creation failed for job {job.id}: {error_message}",
            extra={"error_type": error_type, "job_id": str(job.id)}
        )
        
        # 재시도 가능한 오류인지 확인
        if job.can_retry() and self._is_retryable_error(error):
            job.fail_with_retry(error_message)
            await self.job_repository.save(job)
            
            logger.info(f"Job {job.id} will be retried. Retry count: {job.retry_count}")
        else:
            job.fail_permanently(error_message)
            await self.job_repository.save(job)
            
            # 실패 이벤트 발행
            await self.event_publisher.publish_processing_failed(
                job_id=job.id,
                document_id=job.document_id,
                user_id=job.user_id,
                processing_type=job.processing_type.value,
                error_message=error_message
            )
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """재시도 가능한 오류인지 확인"""
        # 검증 오류는 재시도하지 않음
        non_retryable_types = (
            ValidationError,
        )
        
        if isinstance(error, non_retryable_types):
            return False
        
        # 일시적 처리 오류는 재시도 가능
        return True
