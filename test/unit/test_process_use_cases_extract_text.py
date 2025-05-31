"""
Extract Text Use Case 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from datetime import datetime

from src.core.exceptions import ValidationError, DocumentProcessingError, UnsupportedFileTypeError
from src.modules.process.domain.entities import (
    ProcessingJob,
    ProcessingType,
    ProcessingStatus
)
from src.modules.process.application.use_cases.extract_text import (
    ExtractTextUseCase,
    ExtractTextCommand,
    ExtractTextResult
)


class TestExtractTextUseCase:
    """Extract Text Use Case 테스트"""
    
    @pytest.fixture
    def mock_job_repository(self):
        """Mock ProcessingJobRepository"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_text_extraction_service(self):
        """Mock TextExtractionService"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_event_publisher(self):
        """Mock EventPublisher"""
        return AsyncMock()
    
    @pytest.fixture
    def use_case(self, mock_job_repository, mock_text_extraction_service, mock_event_publisher):
        """ExtractTextUseCase 인스턴스"""
        return ExtractTextUseCase(
            job_repository=mock_job_repository,
            text_extraction_service=mock_text_extraction_service,
            event_publisher=mock_event_publisher
        )
    
    @pytest.fixture
    def sample_job(self):
        """샘플 ProcessingJob"""
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION,
            priority=0,
            parameters={"file_path": "/test/file.pdf", "file_type": "pdf"},
            max_retries=3
        )
        return job
    
    @pytest.fixture
    def sample_command(self, sample_job):
        """샘플 ExtractTextCommand"""
        return ExtractTextCommand(
            job_id=sample_job.id,
            file_path="/test/file.pdf",
            file_type="pdf",
            extraction_options={"extract_images": True}
        )
    
    @pytest.fixture
    def sample_extraction_data(self):
        """샘플 텍스트 추출 데이터"""
        return {
            "text_content": "This is extracted text content from the document.",
            "metadata": {
                "page_count": 5,
                "word_count": 150,
                "file_size": 1024000,
                "extraction_time": 2.5
            }
        }
    
    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        use_case,
        mock_job_repository,
        mock_text_extraction_service,
        mock_event_publisher,
        sample_job,
        sample_command,
        sample_extraction_data
    ):
        """정상적인 텍스트 추출 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_text_extraction_service.extract_text.return_value = sample_extraction_data
        
        # When
        result = await use_case.execute(sample_command)
        
        # Then
        assert isinstance(result, ExtractTextResult)
        assert result.job_id == sample_job.id
        assert result.extracted_text == sample_extraction_data["text_content"]
        assert result.metadata == sample_extraction_data["metadata"]
        assert result.status == ProcessingStatus.COMPLETED
        assert "successfully" in result.message
        
        # 서비스 호출 확인
        mock_text_extraction_service.extract_text.assert_called_once_with(
            document_id=sample_job.document_id,
            file_path=sample_command.file_path,
            file_type=sample_command.file_type,
            parameters=sample_command.extraction_options
        )
        
        # 작업 저장 확인 (시작 시와 완료 시 2번)
        assert mock_job_repository.save.call_count == 2
        
        # 이벤트 발행 확인
        mock_event_publisher.publish_processing_completed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_missing_job_id(self, use_case):
        """Job ID 누락 테스트"""
        # Given
        command = ExtractTextCommand(
            job_id=None,
            file_path="/test/file.pdf",
            file_type="pdf"
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Job ID is required"):
            await use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_execute_missing_file_path(self, use_case, sample_job):
        """파일 경로 누락 테스트"""
        # Given
        command = ExtractTextCommand(
            job_id=sample_job.id,
            file_path="",
            file_type="pdf"
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="File path is required"):
            await use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_execute_missing_file_type(self, use_case, sample_job):
        """파일 타입 누락 테스트"""
        # Given
        command = ExtractTextCommand(
            job_id=sample_job.id,
            file_path="/test/file.pdf",
            file_type=""
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="File type is required"):
            await use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_execute_unsupported_file_type(self, use_case, sample_job):
        """지원하지 않는 파일 타입 테스트"""
        # Given
        command = ExtractTextCommand(
            job_id=sample_job.id,
            file_path="/test/file.xyz",
            file_type="xyz"
        )
        
        # When & Then
        with pytest.raises(UnsupportedFileTypeError, match="not supported"):
            await use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_execute_job_not_found(
        self,
        use_case,
        mock_job_repository,
        sample_command
    ):
        """작업을 찾을 수 없는 경우 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = None
        
        # When & Then
        with pytest.raises(ValidationError, match="not found"):
            await use_case.execute(sample_command)
    
    @pytest.mark.asyncio
    async def test_execute_wrong_processing_type(
        self,
        use_case,
        mock_job_repository,
        sample_command
    ):
        """잘못된 처리 타입 테스트"""
        # Given
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.CHUNKING,  # 다른 타입
            priority=0,
            parameters={},
            max_retries=3
        )
        mock_job_repository.find_by_id.return_value = job
        
        # When & Then
        with pytest.raises(ValidationError, match="not a text extraction job"):
            await use_case.execute(sample_command)
    
    @pytest.mark.asyncio
    async def test_execute_job_not_pending(
        self,
        use_case,
        mock_job_repository,
        sample_job,
        sample_command
    ):
        """대기 상태가 아닌 작업 테스트"""
        # Given
        sample_job.start_processing()  # 상태를 PROCESSING으로 변경
        mock_job_repository.find_by_id.return_value = sample_job
        
        # When & Then
        with pytest.raises(ValidationError, match="not in pending status"):
            await use_case.execute(sample_command)
    
    @pytest.mark.asyncio
    async def test_execute_empty_text_extracted(
        self,
        use_case,
        mock_job_repository,
        mock_text_extraction_service,
        sample_job,
        sample_command
    ):
        """빈 텍스트 추출 결과 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_text_extraction_service.extract_text.return_value = {
            "text_content": "",  # 빈 텍스트
            "metadata": {"page_count": 1}
        }
        
        # When & Then
        with pytest.raises(DocumentProcessingError, match="No text could be extracted"):
            await use_case.execute(sample_command)
    
    @pytest.mark.asyncio
    async def test_execute_extraction_service_error_retryable(
        self,
        use_case,
        mock_job_repository,
        mock_text_extraction_service,
        mock_event_publisher,
        sample_job,
        sample_command
    ):
        """재시도 가능한 추출 서비스 오류 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_text_extraction_service.extract_text.side_effect = Exception("Temporary error")
        
        # When & Then
        with pytest.raises(Exception, match="Temporary error"):
            await use_case.execute(sample_command)
        
        # 작업이 재시도 상태로 변경되었는지 확인
        assert sample_job.status == ProcessingStatus.FAILED
        # 재시도 가능한 경우 retry_count가 증가함
        assert sample_job.retry_count > 0
        
        # 실패 이벤트 발행 확인 (최대 재시도 횟수 도달로 영구 실패)
        mock_event_publisher.publish_processing_failed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_extraction_service_error_non_retryable(
        self,
        use_case,
        mock_job_repository,
        mock_text_extraction_service,
        mock_event_publisher,
        sample_job,
        sample_command
    ):
        """재시도 불가능한 추출 서비스 오류 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_text_extraction_service.extract_text.side_effect = UnsupportedFileTypeError("Unsupported format")
        
        # When & Then
        with pytest.raises(UnsupportedFileTypeError):
            await use_case.execute(sample_command)
        
        # 작업이 영구 실패 상태로 변경되었는지 확인
        assert sample_job.status == ProcessingStatus.FAILED
        assert sample_job.retry_count == sample_job.max_retries  # 최대 재시도 횟수로 설정됨
        
        # 실패 이벤트 발행 확인
        mock_event_publisher.publish_processing_failed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_max_retries_exceeded(
        self,
        use_case,
        mock_job_repository,
        mock_text_extraction_service,
        mock_event_publisher,
        sample_command
    ):
        """최대 재시도 횟수 초과 테스트"""
        # Given
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION,
            priority=0,
            parameters={},
            max_retries=1
        )
        # 이미 최대 재시도 횟수에 도달
        job.retry_count = 1
        
        mock_job_repository.find_by_id.return_value = job
        mock_text_extraction_service.extract_text.side_effect = Exception("Persistent error")
        
        # When & Then
        with pytest.raises(Exception, match="Persistent error"):
            await use_case.execute(sample_command)
        
        # 영구 실패로 처리되었는지 확인
        assert job.status == ProcessingStatus.FAILED
        
        # 실패 이벤트 발행 확인
        mock_event_publisher.publish_processing_failed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_with_default_extraction_options(
        self,
        use_case,
        mock_job_repository,
        mock_text_extraction_service,
        sample_job,
        sample_extraction_data
    ):
        """기본 추출 옵션으로 실행 테스트"""
        # Given
        command = ExtractTextCommand(
            job_id=sample_job.id,
            file_path="/test/file.pdf",
            file_type="pdf"
            # extraction_options 없음
        )
        
        mock_job_repository.find_by_id.return_value = sample_job
        mock_text_extraction_service.extract_text.return_value = sample_extraction_data
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.status == ProcessingStatus.COMPLETED
        
        # 빈 딕셔너리가 파라미터로 전달되었는지 확인
        mock_text_extraction_service.extract_text.assert_called_once_with(
            document_id=sample_job.document_id,
            file_path=command.file_path,
            file_type=command.file_type,
            parameters={}
        )
    
    def test_is_retryable_error_validation_error(self, use_case):
        """ValidationError는 재시도 불가능"""
        error = ValidationError("Invalid input")
        assert not use_case._is_retryable_error(error)
    
    def test_is_retryable_error_unsupported_file_type(self, use_case):
        """UnsupportedFileTypeError는 재시도 불가능"""
        error = UnsupportedFileTypeError("Unsupported format")
        assert not use_case._is_retryable_error(error)
    
    def test_is_retryable_error_generic_exception(self, use_case):
        """일반 예외는 재시도 가능"""
        error = Exception("Temporary failure")
        assert use_case._is_retryable_error(error)
    
    def test_is_retryable_error_document_processing_error(self, use_case):
        """DocumentProcessingError는 재시도 가능"""
        error = DocumentProcessingError("Processing failed")
        assert use_case._is_retryable_error(error)
