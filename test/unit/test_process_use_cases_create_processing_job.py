"""
Create Processing Job Use Case 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.core.exceptions import ValidationError, BusinessRuleViolationError
from src.modules.process.domain.entities import (
    ProcessingJob,
    ProcessingType,
    ProcessingStatus
)
from src.modules.process.application.use_cases.create_processing_job import (
    CreateProcessingJobUseCase,
    CreateProcessingJobCommand,
    CreateProcessingJobResult
)


class TestCreateProcessingJobUseCase:
    """Create Processing Job Use Case 테스트"""
    
    @pytest.fixture
    def mock_job_repository(self):
        """Mock 작업 리포지토리"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_event_publisher(self):
        """Mock 이벤트 발행자"""
        return AsyncMock()
    
    @pytest.fixture
    def use_case(self, mock_job_repository, mock_event_publisher):
        """Use Case 인스턴스"""
        return CreateProcessingJobUseCase(
            job_repository=mock_job_repository,
            event_publisher=mock_event_publisher
        )
    
    @pytest.fixture
    def valid_command(self):
        """유효한 명령"""
        return CreateProcessingJobCommand(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION,
            priority=5,
            parameters={
                "file_path": "/path/to/file.pdf",
                "file_type": "pdf"
            },
            max_retries=3
        )
    
    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, mock_job_repository, mock_event_publisher, valid_command):
        """성공적인 처리 작업 생성 테스트"""
        # Given
        mock_job_repository.find_by_document_id.return_value = []
        
        # When
        result = await use_case.execute(valid_command)
        
        # Then
        assert isinstance(result, CreateProcessingJobResult)
        assert result.status == ProcessingStatus.PENDING
        assert result.message == "Processing job created successfully"
        
        # 리포지토리 호출 확인
        mock_job_repository.save.assert_called_once()
        saved_job = mock_job_repository.save.call_args[0][0]
        assert isinstance(saved_job, ProcessingJob)
        assert saved_job.document_id == valid_command.document_id
        assert saved_job.user_id == valid_command.user_id
        assert saved_job.processing_type == valid_command.processing_type
        assert saved_job.priority == valid_command.priority
        assert saved_job.parameters == valid_command.parameters
        assert saved_job.max_retries == valid_command.max_retries
        
        # 이벤트 발행 확인
        mock_event_publisher.publish_processing_started.assert_called_once_with(
            job_id=saved_job.id,
            document_id=saved_job.document_id,
            user_id=saved_job.user_id,
            processing_type=saved_job.processing_type.value
        )
    
    @pytest.mark.asyncio
    async def test_execute_missing_document_id(self, use_case, valid_command):
        """문서 ID 누락 테스트"""
        # Given
        valid_command.document_id = None
        
        # When & Then
        with pytest.raises(ValidationError, match="Document ID is required"):
            await use_case.execute(valid_command)
    
    @pytest.mark.asyncio
    async def test_execute_missing_user_id(self, use_case, valid_command):
        """사용자 ID 누락 테스트"""
        # Given
        valid_command.user_id = None
        
        # When & Then
        with pytest.raises(ValidationError, match="User ID is required"):
            await use_case.execute(valid_command)
    
    @pytest.mark.asyncio
    async def test_execute_missing_processing_type(self, use_case, valid_command):
        """처리 유형 누락 테스트"""
        # Given
        valid_command.processing_type = None
        
        # When & Then
        with pytest.raises(ValidationError, match="Processing type is required"):
            await use_case.execute(valid_command)
    
    @pytest.mark.asyncio
    async def test_execute_negative_priority(self, use_case, valid_command):
        """음수 우선순위 테스트"""
        # Given
        valid_command.priority = -1
        
        # When & Then
        with pytest.raises(ValidationError, match="Priority must be non-negative"):
            await use_case.execute(valid_command)
    
    @pytest.mark.asyncio
    async def test_execute_negative_max_retries(self, use_case, valid_command):
        """음수 최대 재시도 횟수 테스트"""
        # Given
        valid_command.max_retries = -1
        
        # When & Then
        with pytest.raises(ValidationError, match="Max retries must be non-negative"):
            await use_case.execute(valid_command)
    
    @pytest.mark.asyncio
    async def test_execute_text_extraction_missing_file_path(self, use_case, valid_command):
        """텍스트 추출 시 파일 경로 누락 테스트"""
        # Given
        valid_command.processing_type = ProcessingType.TEXT_EXTRACTION
        valid_command.parameters = {"file_type": "pdf"}
        
        # When & Then
        with pytest.raises(ValidationError, match="file_path is required for text extraction"):
            await use_case.execute(valid_command)
    
    @pytest.mark.asyncio
    async def test_execute_text_extraction_missing_file_type(self, use_case, valid_command):
        """텍스트 추출 시 파일 유형 누락 테스트"""
        # Given
        valid_command.processing_type = ProcessingType.TEXT_EXTRACTION
        valid_command.parameters = {"file_path": "/path/to/file.pdf"}
        
        # When & Then
        with pytest.raises(ValidationError, match="file_type is required for text extraction"):
            await use_case.execute(valid_command)
    
    @pytest.mark.asyncio
    async def test_execute_chunking_missing_chunk_type(self, use_case, valid_command):
        """청킹 시 청크 유형 누락 테스트"""
        # Given
        valid_command.processing_type = ProcessingType.CHUNKING
        valid_command.parameters = {"chunk_size": 1000}
        
        # When & Then
        with pytest.raises(ValidationError, match="chunk_type is required for chunking"):
            await use_case.execute(valid_command)
    
    @pytest.mark.asyncio
    async def test_execute_chunking_invalid_chunk_size(self, use_case, valid_command):
        """청킹 시 잘못된 청크 크기 테스트"""
        # Given
        valid_command.processing_type = ProcessingType.CHUNKING
        valid_command.parameters = {
            "chunk_type": "paragraph",
            "chunk_size": 0
        }
        
        # When & Then
        with pytest.raises(ValidationError, match="chunk_size must be positive"):
            await use_case.execute(valid_command)
    
    @pytest.mark.asyncio
    async def test_execute_embedding_missing_model_name(self, use_case, valid_command):
        """임베딩 시 모델명 누락 테스트"""
        # Given
        valid_command.processing_type = ProcessingType.EMBEDDING
        valid_command.parameters = {}
        
        # When & Then
        with pytest.raises(ValidationError, match="model_name is required for embedding"):
            await use_case.execute(valid_command)
    
    @pytest.mark.asyncio
    async def test_execute_indexing_missing_collection_name(self, use_case, valid_command):
        """인덱싱 시 컬렉션명 누락 테스트"""
        # Given
        valid_command.processing_type = ProcessingType.INDEXING
        valid_command.parameters = {}
        
        # When & Then
        with pytest.raises(ValidationError, match="collection_name is required for indexing"):
            await use_case.execute(valid_command)
    
    @pytest.mark.asyncio
    async def test_execute_duplicate_job_pending(self, use_case, mock_job_repository, valid_command):
        """중복 작업 (대기 중) 테스트"""
        # Given
        existing_job = ProcessingJob.create(
            document_id=valid_command.document_id,
            user_id=valid_command.user_id,
            processing_type=valid_command.processing_type
        )
        existing_job.status = ProcessingStatus.PENDING
        mock_job_repository.find_by_document_id.return_value = [existing_job]
        
        # When & Then
        with pytest.raises(BusinessRuleViolationError, match="job is already in progress"):
            await use_case.execute(valid_command)
    
    @pytest.mark.asyncio
    async def test_execute_duplicate_job_processing(self, use_case, mock_job_repository, valid_command):
        """중복 작업 (처리 중) 테스트"""
        # Given
        existing_job = ProcessingJob.create(
            document_id=valid_command.document_id,
            user_id=valid_command.user_id,
            processing_type=valid_command.processing_type
        )
        existing_job.status = ProcessingStatus.PROCESSING
        mock_job_repository.find_by_document_id.return_value = [existing_job]
        
        # When & Then
        with pytest.raises(BusinessRuleViolationError, match="job is already in progress"):
            await use_case.execute(valid_command)
    
    @pytest.mark.asyncio
    async def test_execute_duplicate_job_completed_allowed(self, use_case, mock_job_repository, mock_event_publisher, valid_command):
        """중복 작업 (완료됨) - 허용 테스트"""
        # Given
        existing_job = ProcessingJob.create(
            document_id=valid_command.document_id,
            user_id=valid_command.user_id,
            processing_type=valid_command.processing_type
        )
        existing_job.status = ProcessingStatus.COMPLETED
        mock_job_repository.find_by_document_id.return_value = [existing_job]
        
        # When
        result = await use_case.execute(valid_command)
        
        # Then
        assert isinstance(result, CreateProcessingJobResult)
        assert result.status == ProcessingStatus.PENDING
        mock_job_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_different_processing_type_allowed(self, use_case, mock_job_repository, mock_event_publisher, valid_command):
        """다른 처리 유형 - 허용 테스트"""
        # Given
        existing_job = ProcessingJob.create(
            document_id=valid_command.document_id,
            user_id=valid_command.user_id,
            processing_type=ProcessingType.CHUNKING  # 다른 처리 유형
        )
        existing_job.status = ProcessingStatus.PROCESSING
        mock_job_repository.find_by_document_id.return_value = [existing_job]
        
        # When
        result = await use_case.execute(valid_command)
        
        # Then
        assert isinstance(result, CreateProcessingJobResult)
        assert result.status == ProcessingStatus.PENDING
        mock_job_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_with_default_parameters(self, use_case, mock_job_repository, mock_event_publisher):
        """기본 파라미터로 실행 테스트"""
        # Given
        command = CreateProcessingJobCommand(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION,
            parameters={
                "file_path": "/path/to/file.pdf",
                "file_type": "pdf"
            }
        )
        mock_job_repository.find_by_document_id.return_value = []
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert isinstance(result, CreateProcessingJobResult)
        assert result.status == ProcessingStatus.PENDING
        
        saved_job = mock_job_repository.save.call_args[0][0]
        assert saved_job.priority == 0  # 기본값
        assert saved_job.max_retries == 3  # 기본값
