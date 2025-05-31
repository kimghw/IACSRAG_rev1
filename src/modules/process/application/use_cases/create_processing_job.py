"""
Create Processing Job Use Case

문서 처리 작업 생성 유즈케이스
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import UUID

from src.core.exceptions import ValidationError, BusinessRuleViolationError
from src.core.logging import get_logger
from src.modules.process.domain.entities import (
    ProcessingJob,
    ProcessingType,
    ProcessingStatus
)
from src.modules.process.application.ports.repositories import ProcessingJobRepository
from src.modules.process.application.ports.services import EventPublisher

logger = get_logger(__name__)


@dataclass
class CreateProcessingJobCommand:
    """처리 작업 생성 명령"""
    document_id: UUID
    user_id: UUID
    processing_type: ProcessingType
    priority: int = 0
    parameters: Optional[Dict[str, Any]] = None
    max_retries: int = 3


@dataclass
class CreateProcessingJobResult:
    """처리 작업 생성 결과"""
    job_id: UUID
    status: ProcessingStatus
    created_at: str
    message: str


class CreateProcessingJobUseCase:
    """문서 처리 작업 생성 유즈케이스"""
    
    def __init__(
        self,
        job_repository: ProcessingJobRepository,
        event_publisher: EventPublisher
    ):
        self.job_repository = job_repository
        self.event_publisher = event_publisher
    
    async def execute(self, command: CreateProcessingJobCommand) -> CreateProcessingJobResult:
        """
        처리 작업 생성 실행
        
        Args:
            command: 처리 작업 생성 명령
            
        Returns:
            CreateProcessingJobResult: 생성 결과
            
        Raises:
            ValidationError: 입력 데이터 검증 실패
            BusinessLogicError: 비즈니스 로직 오류
        """
        processing_type_str = command.processing_type.value if command.processing_type else 'None'
        logger.info(
            f"Creating processing job for document {command.document_id}, "
            f"user {command.user_id}, type {processing_type_str}"
        )
        
        # 1. 입력 데이터 검증
        await self._validate_command(command)
        
        # 2. 중복 작업 확인
        await self._check_duplicate_job(command)
        
        # 3. 처리 작업 생성
        job = ProcessingJob.create(
            document_id=command.document_id,
            user_id=command.user_id,
            processing_type=command.processing_type,
            priority=command.priority,
            parameters=command.parameters or {},
            max_retries=command.max_retries
        )
        
        # 4. 작업 저장
        await self.job_repository.save(job)
        
        # 5. 이벤트 발행
        await self.event_publisher.publish_processing_started(
            job_id=job.id,
            document_id=job.document_id,
            user_id=job.user_id,
            processing_type=job.processing_type.value
        )
        
        logger.info(f"Processing job created successfully: {job.id}")
        
        return CreateProcessingJobResult(
            job_id=job.id,
            status=job.status,
            created_at=job.created_at.isoformat(),
            message="Processing job created successfully"
        )
    
    async def _validate_command(self, command: CreateProcessingJobCommand) -> None:
        """명령 데이터 검증"""
        if not command.document_id:
            raise ValidationError("Document ID is required")
        
        if not command.user_id:
            raise ValidationError("User ID is required")
        
        if not command.processing_type:
            raise ValidationError("Processing type is required")
        
        if command.priority < 0:
            raise ValidationError("Priority must be non-negative")
        
        if command.max_retries < 0:
            raise ValidationError("Max retries must be non-negative")
        
        # 처리 유형별 파라미터 검증
        await self._validate_processing_parameters(command)
    
    async def _validate_processing_parameters(self, command: CreateProcessingJobCommand) -> None:
        """처리 유형별 파라미터 검증"""
        parameters = command.parameters or {}
        
        if command.processing_type == ProcessingType.TEXT_EXTRACTION:
            # 텍스트 추출 파라미터 검증
            if "file_path" not in parameters:
                raise ValidationError("file_path is required for text extraction")
            if "file_type" not in parameters:
                raise ValidationError("file_type is required for text extraction")
        
        elif command.processing_type == ProcessingType.CHUNKING:
            # 청킹 파라미터 검증
            if "chunk_type" not in parameters:
                raise ValidationError("chunk_type is required for chunking")
            if "chunk_size" in parameters and parameters["chunk_size"] <= 0:
                raise ValidationError("chunk_size must be positive")
        
        elif command.processing_type == ProcessingType.EMBEDDING:
            # 임베딩 파라미터 검증
            if "model_name" not in parameters:
                raise ValidationError("model_name is required for embedding")
        
        elif command.processing_type == ProcessingType.INDEXING:
            # 인덱싱 파라미터 검증
            if "collection_name" not in parameters:
                raise ValidationError("collection_name is required for indexing")
    
    async def _check_duplicate_job(self, command: CreateProcessingJobCommand) -> None:
        """중복 작업 확인"""
        # 같은 문서에 대해 동일한 처리 유형의 진행 중인 작업이 있는지 확인
        existing_jobs = await self.job_repository.find_by_document_id(command.document_id)
        
        for job in existing_jobs:
            if (job.processing_type == command.processing_type and 
                job.status in [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]):
                raise BusinessRuleViolationError(
                    f"A {command.processing_type.value} job is already in progress "
                    f"for document {command.document_id}"
                )
