"""
Extract Text Use Case

문서에서 텍스트 추출 유즈케이스
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import UUID

from src.core.exceptions import ValidationError, DocumentProcessingError, UnsupportedFileTypeError
from src.core.logging import get_logger
from src.modules.process.domain.entities import (
    ProcessingJob,
    ProcessingType,
    ProcessingStatus
)
from src.modules.process.application.ports.repositories import ProcessingJobRepository
from src.modules.process.application.ports.services import (
    EventPublisher,
    TextExtractionService
)
from src.modules.process.application.ports.text_extraction_result import TextExtractionResult

logger = get_logger(__name__)


@dataclass
class ExtractTextCommand:
    """텍스트 추출 명령"""
    job_id: UUID
    file_path: str
    file_type: str
    extraction_options: Optional[Dict[str, Any]] = None


@dataclass
class ExtractTextResult:
    """텍스트 추출 결과"""
    job_id: UUID
    extracted_text: str
    metadata: Dict[str, Any]
    status: ProcessingStatus
    message: str


class ExtractTextUseCase:
    """문서 텍스트 추출 유즈케이스"""
    
    def __init__(
        self,
        job_repository: ProcessingJobRepository,
        text_extraction_service: TextExtractionService,
        event_publisher: EventPublisher
    ):
        self.job_repository = job_repository
        self.text_extraction_service = text_extraction_service
        self.event_publisher = event_publisher
    
    async def execute(self, command: ExtractTextCommand) -> ExtractTextResult:
        """
        텍스트 추출 실행
        
        Args:
            command: 텍스트 추출 명령
            
        Returns:
            ExtractTextResult: 추출 결과
            
        Raises:
            ValidationError: 입력 데이터 검증 실패
            DocumentProcessingError: 문서 처리 오류
            UnsupportedFileTypeError: 지원하지 않는 파일 형식
        """
        logger.info(f"Starting text extraction for job {command.job_id}")
        
        # 1. 입력 데이터 검증
        await self._validate_command(command)
        
        # 2. 작업 조회 및 상태 확인
        job = await self._get_and_validate_job(command.job_id)
        
        try:
            # 3. 작업 상태를 처리 중으로 변경
            job.start_processing()
            await self.job_repository.save(job)
            
            # 4. 텍스트 추출 실행
            extraction_data = await self.text_extraction_service.extract_text(
                document_id=job.document_id,
                file_path=command.file_path,
                file_type=command.file_type,
                parameters=command.extraction_options or {}
            )
            
            # 추출 결과를 TextExtractionResult 객체로 변환
            extraction_result = TextExtractionResult(
                text=extraction_data["text_content"],
                metadata=extraction_data["metadata"]
            )
            
            # 5. 추출 결과 검증
            if not extraction_result.text or len(extraction_result.text.strip()) == 0:
                raise DocumentProcessingError("No text could be extracted from the document")
            
            # 6. 작업 완료 처리
            job.complete_processing()
            await self.job_repository.save(job)
            
            # 7. 이벤트 발행
            await self.event_publisher.publish_processing_completed(
                job_id=job.id,
                document_id=job.document_id,
                user_id=job.user_id,
                processing_type=job.processing_type.value,
                result_data={
                    "text_length": len(extraction_result.text),
                    "page_count": extraction_result.page_count,
                    "metadata": extraction_result.metadata
                }
            )
            
            logger.info(
                f"Text extraction completed for job {command.job_id}. "
                f"Extracted {len(extraction_result.text)} characters"
            )
            
            return ExtractTextResult(
                job_id=job.id,
                extracted_text=extraction_result.text,
                metadata=extraction_result.metadata,
                status=job.status,
                message="Text extraction completed successfully"
            )
            
        except Exception as e:
            # 8. 오류 처리
            await self._handle_extraction_error(job, e)
            raise
    
    async def _validate_command(self, command: ExtractTextCommand) -> None:
        """명령 데이터 검증"""
        if not command.job_id:
            raise ValidationError("Job ID is required")
        
        if not command.file_path:
            raise ValidationError("File path is required")
        
        if not command.file_type:
            raise ValidationError("File type is required")
        
        # 지원하는 파일 형식 확인
        supported_types = ["pdf", "docx", "doc", "txt", "html", "md"]
        if command.file_type.lower() not in supported_types:
            raise UnsupportedFileTypeError(
                f"File type '{command.file_type}' is not supported. "
                f"Supported types: {', '.join(supported_types)}"
            )
    
    async def _get_and_validate_job(self, job_id: UUID) -> ProcessingJob:
        """작업 조회 및 상태 검증"""
        job = await self.job_repository.find_by_id(job_id)
        if not job:
            raise ValidationError(f"Job {job_id} not found")
        
        if job.processing_type != ProcessingType.TEXT_EXTRACTION:
            raise ValidationError(
                f"Job {job_id} is not a text extraction job. "
                f"Type: {job.processing_type.value}"
            )
        
        if job.status != ProcessingStatus.PENDING:
            raise ValidationError(
                f"Job {job_id} is not in pending status. "
                f"Current status: {job.status.value}"
            )
        
        return job
    
    async def _handle_extraction_error(self, job: ProcessingJob, error: Exception) -> None:
        """추출 오류 처리"""
        error_message = str(error)
        error_type = type(error).__name__
        
        logger.error(
            f"Text extraction failed for job {job.id}: {error_message}",
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
        # 파일 형식 오류나 검증 오류는 재시도하지 않음
        non_retryable_types = (
            UnsupportedFileTypeError,
            ValidationError,
        )
        
        if isinstance(error, non_retryable_types):
            return False
        
        # 파일 접근 오류나 일시적 처리 오류는 재시도 가능
        return True
