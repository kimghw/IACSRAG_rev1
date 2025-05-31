"""
Create Chunks Use Case 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from datetime import datetime

from src.core.exceptions import ValidationError, DocumentProcessingError
from src.modules.process.domain.entities import (
    ProcessingJob,
    ProcessingType,
    ProcessingStatus,
    TextChunk,
    ChunkType
)
from src.modules.process.application.use_cases.create_chunks import (
    CreateChunksUseCase,
    CreateChunksCommand,
    CreateChunksResult
)


class TestCreateChunksUseCase:
    """Create Chunks Use Case 테스트"""
    
    @pytest.fixture
    def mock_job_repository(self):
        """Mock ProcessingJobRepository"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_chunking_service(self):
        """Mock ChunkingService"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_event_publisher(self):
        """Mock EventPublisher"""
        return AsyncMock()
    
    @pytest.fixture
    def use_case(self, mock_job_repository, mock_chunking_service, mock_event_publisher):
        """CreateChunksUseCase 인스턴스"""
        return CreateChunksUseCase(
            job_repository=mock_job_repository,
            chunking_service=mock_chunking_service,
            event_publisher=mock_event_publisher
        )
    
    @pytest.fixture
    def sample_job(self):
        """샘플 ProcessingJob"""
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.CHUNKING,
            priority=0,
            parameters={"chunk_size": 1000, "overlap": 100},
            max_retries=3
        )
        return job
    
    @pytest.fixture
    def sample_command(self, sample_job):
        """샘플 CreateChunksCommand"""
        return CreateChunksCommand(
            job_id=sample_job.id,
            text_content="This is a long text content that needs to be chunked into smaller pieces. " * 20,
            document_id=sample_job.document_id,
            chunking_options={"chunk_type": "fixed_size", "chunk_size": 500, "overlap": 50}
        )
    
    @pytest.fixture
    def sample_chunk_data(self):
        """샘플 청크 데이터"""
        return [
            {
                "content": "This is the first chunk of text content.",
                "start_position": 0,
                "end_position": 40,
                "metadata": {"chunk_index": 0, "word_count": 8}
            },
            {
                "content": "This is the second chunk of text content.",
                "start_position": 35,
                "end_position": 76,
                "metadata": {"chunk_index": 1, "word_count": 8}
            },
            {
                "content": "This is the third chunk of text content.",
                "start_position": 71,
                "end_position": 111,
                "metadata": {"chunk_index": 2, "word_count": 8}
            }
        ]
    
    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        use_case,
        mock_job_repository,
        mock_chunking_service,
        mock_event_publisher,
        sample_job,
        sample_command,
        sample_chunk_data
    ):
        """정상적인 청킹 생성 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunking_service.chunk_text.return_value = sample_chunk_data
        
        # When
        result = await use_case.execute(sample_command)
        
        # Then
        assert isinstance(result, CreateChunksResult)
        assert result.job_id == sample_job.id
        assert result.total_chunks == 3
        assert len(result.chunks) == 3
        assert result.status == ProcessingStatus.COMPLETED
        assert "successfully" in result.message
        
        # 청킹 서비스 호출 확인
        mock_chunking_service.chunk_text.assert_called_once_with(
            text_content=sample_command.text_content,
            chunk_type=ChunkType.FIXED_SIZE,
            parameters=sample_command.chunking_options
        )
        
        # 작업 저장 확인 (시작 시와 완료 시 2번)
        assert mock_job_repository.save.call_count == 2
        
        # 이벤트 발행 확인
        mock_event_publisher.publish_processing_completed.assert_called_once()
        mock_event_publisher.publish_chunks_created.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_missing_job_id(self, use_case):
        """Job ID 누락 테스트"""
        # Given
        command = CreateChunksCommand(
            job_id=None,
            text_content="Sample text content",
            document_id=uuid4()
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Job ID is required"):
            await use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_execute_missing_text_content(self, use_case, sample_job):
        """텍스트 내용 누락 테스트"""
        # Given
        command = CreateChunksCommand(
            job_id=sample_job.id,
            text_content="",
            document_id=sample_job.document_id
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Text content is required"):
            await use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_execute_missing_document_id(self, use_case, sample_job):
        """문서 ID 누락 테스트"""
        # Given
        command = CreateChunksCommand(
            job_id=sample_job.id,
            text_content="Sample text content",
            document_id=None
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Document ID is required"):
            await use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_execute_text_too_short(self, use_case, sample_job):
        """텍스트가 너무 짧은 경우 테스트"""
        # Given
        command = CreateChunksCommand(
            job_id=sample_job.id,
            text_content="short",
            document_id=sample_job.document_id
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="too short for chunking"):
            await use_case.execute(command)
    
    @pytest.mark.asyncio
    async def test_execute_text_too_large(self, use_case, sample_job):
        """텍스트가 너무 큰 경우 테스트"""
        # Given
        large_text = "x" * (11 * 1024 * 1024)  # 11MB
        command = CreateChunksCommand(
            job_id=sample_job.id,
            text_content=large_text,
            document_id=sample_job.document_id
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="exceeds maximum size"):
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
            processing_type=ProcessingType.TEXT_EXTRACTION,  # 다른 타입
            priority=0,
            parameters={},
            max_retries=3
        )
        mock_job_repository.find_by_id.return_value = job
        
        # When & Then
        with pytest.raises(ValidationError, match="not a chunking job"):
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
    async def test_execute_no_chunks_created(
        self,
        use_case,
        mock_job_repository,
        mock_chunking_service,
        sample_job,
        sample_command
    ):
        """청크가 생성되지 않은 경우 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunking_service.chunk_text.return_value = []  # 빈 청크 목록
        
        # When & Then
        with pytest.raises(DocumentProcessingError, match="No chunks could be created"):
            await use_case.execute(sample_command)
    
    @pytest.mark.asyncio
    async def test_execute_chunking_service_error_retryable(
        self,
        use_case,
        mock_job_repository,
        mock_chunking_service,
        mock_event_publisher,
        sample_job,
        sample_command
    ):
        """재시도 가능한 청킹 서비스 오류 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunking_service.chunk_text.side_effect = Exception("Temporary chunking error")
        
        # When & Then
        with pytest.raises(Exception, match="Temporary chunking error"):
            await use_case.execute(sample_command)
        
        # 작업이 실패 상태로 변경되었는지 확인
        assert sample_job.status == ProcessingStatus.FAILED
        assert sample_job.retry_count > 0
        
        # 실패 이벤트 발행 확인
        mock_event_publisher.publish_processing_failed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_chunking_service_error_non_retryable(
        self,
        use_case,
        mock_job_repository,
        mock_chunking_service,
        mock_event_publisher,
        sample_job,
        sample_command
    ):
        """재시도 불가능한 청킹 서비스 오류 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunking_service.chunk_text.side_effect = ValidationError("Invalid chunking parameters")
        
        # When & Then
        with pytest.raises(ValidationError):
            await use_case.execute(sample_command)
        
        # 작업이 영구 실패 상태로 변경되었는지 확인
        assert sample_job.status == ProcessingStatus.FAILED
        assert sample_job.retry_count == sample_job.max_retries
        
        # 실패 이벤트 발행 확인
        mock_event_publisher.publish_processing_failed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_with_default_chunking_options(
        self,
        use_case,
        mock_job_repository,
        mock_chunking_service,
        sample_job,
        sample_chunk_data
    ):
        """기본 청킹 옵션으로 실행 테스트"""
        # Given
        command = CreateChunksCommand(
            job_id=sample_job.id,
            text_content="This is a sample text content for chunking.",
            document_id=sample_job.document_id
            # chunking_options 없음
        )
        
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunking_service.chunk_text.return_value = sample_chunk_data
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.status == ProcessingStatus.COMPLETED
        
        # 기본 청크 타입과 빈 파라미터가 전달되었는지 확인
        mock_chunking_service.chunk_text.assert_called_once_with(
            text_content=command.text_content,
            chunk_type=ChunkType.FIXED_SIZE,
            parameters={}
        )
    
    @pytest.mark.asyncio
    async def test_execute_with_semantic_chunking(
        self,
        use_case,
        mock_job_repository,
        mock_chunking_service,
        sample_job,
        sample_chunk_data
    ):
        """의미 기반 청킹 테스트"""
        # Given
        command = CreateChunksCommand(
            job_id=sample_job.id,
            text_content="This is a sample text content for semantic chunking.",
            document_id=sample_job.document_id,
            chunking_options={"chunk_type": "semantic", "min_chunk_size": 100}
        )
        
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunking_service.chunk_text.return_value = sample_chunk_data
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.status == ProcessingStatus.COMPLETED
        
        # 의미 기반 청크 타입이 전달되었는지 확인
        mock_chunking_service.chunk_text.assert_called_once_with(
            text_content=command.text_content,
            chunk_type=ChunkType.SEMANTIC,
            parameters=command.chunking_options
        )
    
    def test_get_chunk_type_fixed_size(self, use_case):
        """고정 크기 청크 타입 테스트"""
        options = {"chunk_type": "fixed_size"}
        chunk_type = use_case._get_chunk_type(options)
        assert chunk_type == ChunkType.FIXED_SIZE
    
    def test_get_chunk_type_semantic(self, use_case):
        """의미 기반 청크 타입 테스트"""
        options = {"chunk_type": "semantic"}
        chunk_type = use_case._get_chunk_type(options)
        assert chunk_type == ChunkType.SEMANTIC
    
    def test_get_chunk_type_paragraph(self, use_case):
        """문단 기반 청크 타입 테스트"""
        options = {"chunk_type": "paragraph"}
        chunk_type = use_case._get_chunk_type(options)
        assert chunk_type == ChunkType.PARAGRAPH
    
    def test_get_chunk_type_sentence(self, use_case):
        """문장 기반 청크 타입 테스트"""
        options = {"chunk_type": "sentence"}
        chunk_type = use_case._get_chunk_type(options)
        assert chunk_type == ChunkType.SENTENCE
    
    def test_get_chunk_type_default(self, use_case):
        """기본 청크 타입 테스트"""
        # None 옵션
        chunk_type = use_case._get_chunk_type(None)
        assert chunk_type == ChunkType.FIXED_SIZE
        
        # 빈 딕셔너리
        chunk_type = use_case._get_chunk_type({})
        assert chunk_type == ChunkType.FIXED_SIZE
        
        # 알 수 없는 타입
        chunk_type = use_case._get_chunk_type({"chunk_type": "unknown"})
        assert chunk_type == ChunkType.FIXED_SIZE
    
    def test_is_retryable_error_validation_error(self, use_case):
        """ValidationError는 재시도 불가능"""
        error = ValidationError("Invalid input")
        assert not use_case._is_retryable_error(error)
    
    def test_is_retryable_error_generic_exception(self, use_case):
        """일반 예외는 재시도 가능"""
        error = Exception("Temporary failure")
        assert use_case._is_retryable_error(error)
    
    def test_is_retryable_error_document_processing_error(self, use_case):
        """DocumentProcessingError는 재시도 가능"""
        error = DocumentProcessingError("Processing failed")
        assert use_case._is_retryable_error(error)
