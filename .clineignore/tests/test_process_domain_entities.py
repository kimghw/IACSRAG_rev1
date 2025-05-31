"""
Process Domain Entities 단위 테스트
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID

from src.modules.process.domain.entities import (
    ProcessingJob,
    ProcessingStatus,
    ProcessingType,
    ProcessingMetadata,
    TextChunk,
    ChunkType,
    ProcessingResult
)
from src.utils.datetime import utc_now


class TestProcessingMetadata:
    """ProcessingMetadata 테스트"""
    
    def test_create_empty_metadata(self):
        """빈 메타데이터 생성 테스트"""
        metadata = ProcessingMetadata()
        
        assert metadata.processing_time is None
        assert metadata.memory_usage is None
        assert metadata.cpu_usage is None
        assert metadata.model_name is None
        assert metadata.model_version is None
        assert metadata.parameters == {}
    
    def test_create_metadata_with_values(self):
        """값이 있는 메타데이터 생성 테스트"""
        metadata = ProcessingMetadata(
            processing_time=10.5,
            memory_usage=1024,
            cpu_usage=75.5,
            model_name="test-model",
            model_version="1.0",
            parameters={"param1": "value1"}
        )
        
        assert metadata.processing_time == 10.5
        assert metadata.memory_usage == 1024
        assert metadata.cpu_usage == 75.5
        assert metadata.model_name == "test-model"
        assert metadata.model_version == "1.0"
        assert metadata.parameters == {"param1": "value1"}
    
    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        metadata = ProcessingMetadata(
            processing_time=10.5,
            memory_usage=1024,
            parameters={"param1": "value1"}
        )
        
        result = metadata.to_dict()
        
        assert result["processing_time"] == 10.5
        assert result["memory_usage"] == 1024
        assert result["cpu_usage"] is None
        assert result["parameters"] == {"param1": "value1"}
    
    def test_from_dict(self):
        """딕셔너리에서 생성 테스트"""
        data = {
            "processing_time": 10.5,
            "memory_usage": 1024,
            "cpu_usage": 75.5,
            "model_name": "test-model",
            "model_version": "1.0",
            "parameters": {"param1": "value1"}
        }
        
        metadata = ProcessingMetadata.from_dict(data)
        
        assert metadata.processing_time == 10.5
        assert metadata.memory_usage == 1024
        assert metadata.cpu_usage == 75.5
        assert metadata.model_name == "test-model"
        assert metadata.model_version == "1.0"
        assert metadata.parameters == {"param1": "value1"}


class TestProcessingJob:
    """ProcessingJob 테스트"""
    
    def test_create_processing_job(self):
        """처리 작업 생성 테스트"""
        document_id = uuid4()
        user_id = uuid4()
        
        job = ProcessingJob.create(
            document_id=document_id,
            user_id=user_id,
            processing_type=ProcessingType.TEXT_EXTRACTION,
            priority=5,
            parameters={"param1": "value1"},
            max_retries=5
        )
        
        assert isinstance(job.id, UUID)
        assert job.document_id == document_id
        assert job.user_id == user_id
        assert job.processing_type == ProcessingType.TEXT_EXTRACTION
        assert job.status == ProcessingStatus.PENDING
        assert job.priority == 5
        assert job.parameters == {"param1": "value1"}
        assert job.max_retries == 5
        assert job.retry_count == 0
        assert job.error_message is None
        assert job.metadata is None
        assert job.started_at is None
        assert job.completed_at is None
        assert isinstance(job.created_at, datetime)
        assert isinstance(job.updated_at, datetime)
    
    def test_start_processing(self):
        """처리 시작 테스트"""
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION
        )
        
        job.start_processing()
        
        assert job.status == ProcessingStatus.PROCESSING
        assert job.started_at is not None
        assert isinstance(job.started_at, datetime)
    
    def test_start_processing_invalid_status(self):
        """잘못된 상태에서 처리 시작 테스트"""
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION
        )
        job.status = ProcessingStatus.COMPLETED
        
        with pytest.raises(ValueError, match="Cannot start processing job in status"):
            job.start_processing()
    
    def test_complete_processing(self):
        """처리 완료 테스트"""
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION
        )
        job.start_processing()
        
        metadata = ProcessingMetadata(processing_time=10.5)
        job.complete_processing(metadata)
        
        assert job.status == ProcessingStatus.COMPLETED
        assert job.completed_at is not None
        assert job.metadata == metadata
        assert isinstance(job.completed_at, datetime)
    
    def test_complete_processing_invalid_status(self):
        """잘못된 상태에서 처리 완료 테스트"""
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION
        )
        
        with pytest.raises(ValueError, match="Cannot complete processing job in status"):
            job.complete_processing()
    
    def test_fail_processing(self):
        """처리 실패 테스트"""
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION
        )
        job.start_processing()
        
        error_message = "Processing failed"
        job.fail_processing(error_message)
        
        assert job.status == ProcessingStatus.FAILED
        assert job.error_message == error_message
    
    def test_retry_processing(self):
        """처리 재시도 테스트"""
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION,
            max_retries=3
        )
        job.start_processing()
        job.fail_processing("Error")
        
        result = job.retry_processing()
        
        assert result is True
        assert job.status == ProcessingStatus.PENDING
        assert job.retry_count == 1
        assert job.error_message is None
    
    def test_retry_processing_max_retries_exceeded(self):
        """최대 재시도 횟수 초과 테스트"""
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION,
            max_retries=1
        )
        job.start_processing()
        job.fail_processing("Error")
        job.retry_processing()  # 첫 번째 재시도
        job.start_processing()
        job.fail_processing("Error again")
        
        result = job.retry_processing()  # 두 번째 재시도 시도
        
        assert result is False
        assert job.status == ProcessingStatus.FAILED
        assert job.retry_count == 1
    
    def test_cancel_processing(self):
        """처리 취소 테스트"""
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION
        )
        
        job.cancel_processing()
        
        assert job.status == ProcessingStatus.CANCELLED
    
    def test_cancel_processing_invalid_status(self):
        """잘못된 상태에서 처리 취소 테스트"""
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION
        )
        job.start_processing()
        job.complete_processing()
        
        with pytest.raises(ValueError, match="Cannot cancel processing job in status"):
            job.cancel_processing()
    
    def test_can_retry(self):
        """재시도 가능 여부 테스트"""
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION,
            max_retries=3
        )
        
        # 초기 상태
        assert job.can_retry() is False
        
        # 실패 상태
        job.start_processing()
        job.fail_processing("Error")
        assert job.can_retry() is True
        
        # 최대 재시도 횟수 도달
        job.retry_count = 3
        assert job.can_retry() is False
    
    def test_is_terminal_status(self):
        """종료 상태 여부 테스트"""
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION
        )
        
        # 초기 상태
        assert job.is_terminal_status() is False
        
        # 처리 중
        job.start_processing()
        assert job.is_terminal_status() is False
        
        # 완료
        job.complete_processing()
        assert job.is_terminal_status() is True
        
        # 취소
        job.status = ProcessingStatus.CANCELLED
        assert job.is_terminal_status() is True
        
        # 실패
        job.status = ProcessingStatus.FAILED
        assert job.is_terminal_status() is False
    
    def test_get_processing_duration(self):
        """처리 시간 계산 테스트"""
        job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION
        )
        
        # 시작 전
        assert job.get_processing_duration() is None
        
        # 시작 후
        start_time = utc_now()
        job.started_at = start_time
        job.completed_at = start_time + timedelta(seconds=10)
        
        duration = job.get_processing_duration()
        assert duration == 10.0
    
    def test_to_dict_and_from_dict(self):
        """딕셔너리 변환 테스트"""
        document_id = uuid4()
        user_id = uuid4()
        
        original_job = ProcessingJob.create(
            document_id=document_id,
            user_id=user_id,
            processing_type=ProcessingType.TEXT_EXTRACTION,
            priority=5,
            parameters={"param1": "value1"}
        )
        original_job.start_processing()
        
        # 딕셔너리로 변환
        job_dict = original_job.to_dict()
        
        # 딕셔너리에서 복원
        restored_job = ProcessingJob.from_dict(job_dict)
        
        assert restored_job.id == original_job.id
        assert restored_job.document_id == original_job.document_id
        assert restored_job.user_id == original_job.user_id
        assert restored_job.processing_type == original_job.processing_type
        assert restored_job.status == original_job.status
        assert restored_job.priority == original_job.priority
        assert restored_job.parameters == original_job.parameters


class TestTextChunk:
    """TextChunk 테스트"""
    
    def test_create_text_chunk(self):
        """텍스트 청크 생성 테스트"""
        document_id = uuid4()
        user_id = uuid4()
        content = "This is a test chunk content."
        
        chunk = TextChunk.create(
            document_id=document_id,
            user_id=user_id,
            content=content,
            chunk_type=ChunkType.PARAGRAPH,
            sequence_number=1,
            start_position=0,
            end_position=len(content),
            metadata={"source": "test"}
        )
        
        assert isinstance(chunk.id, UUID)
        assert chunk.document_id == document_id
        assert chunk.user_id == user_id
        assert chunk.content == content
        assert chunk.chunk_type == ChunkType.PARAGRAPH
        assert chunk.sequence_number == 1
        assert chunk.start_position == 0
        assert chunk.end_position == len(content)
        assert chunk.metadata == {"source": "test"}
        assert chunk.embedding_id is None
        assert isinstance(chunk.created_at, datetime)
    
    def test_get_content_length(self):
        """콘텐츠 길이 테스트"""
        chunk = TextChunk.create(
            document_id=uuid4(),
            user_id=uuid4(),
            content="Hello World",
            chunk_type=ChunkType.SENTENCE,
            sequence_number=1,
            start_position=0,
            end_position=11
        )
        
        assert chunk.get_content_length() == 11
    
    def test_get_word_count(self):
        """단어 수 테스트"""
        chunk = TextChunk.create(
            document_id=uuid4(),
            user_id=uuid4(),
            content="Hello World Test",
            chunk_type=ChunkType.SENTENCE,
            sequence_number=1,
            start_position=0,
            end_position=16
        )
        
        assert chunk.get_word_count() == 3
    
    def test_set_embedding_id(self):
        """임베딩 ID 설정 테스트"""
        chunk = TextChunk.create(
            document_id=uuid4(),
            user_id=uuid4(),
            content="Test content",
            chunk_type=ChunkType.PARAGRAPH,
            sequence_number=1,
            start_position=0,
            end_position=12
        )
        
        embedding_id = uuid4()
        chunk.set_embedding_id(embedding_id)
        
        assert chunk.embedding_id == embedding_id
    
    def test_to_dict_and_from_dict(self):
        """딕셔너리 변환 테스트"""
        document_id = uuid4()
        user_id = uuid4()
        embedding_id = uuid4()
        
        original_chunk = TextChunk.create(
            document_id=document_id,
            user_id=user_id,
            content="Test content",
            chunk_type=ChunkType.PARAGRAPH,
            sequence_number=1,
            start_position=0,
            end_position=12,
            metadata={"source": "test"}
        )
        original_chunk.set_embedding_id(embedding_id)
        
        # 딕셔너리로 변환
        chunk_dict = original_chunk.to_dict()
        
        # 딕셔너리에서 복원
        restored_chunk = TextChunk.from_dict(chunk_dict)
        
        assert restored_chunk.id == original_chunk.id
        assert restored_chunk.document_id == original_chunk.document_id
        assert restored_chunk.user_id == original_chunk.user_id
        assert restored_chunk.content == original_chunk.content
        assert restored_chunk.chunk_type == original_chunk.chunk_type
        assert restored_chunk.sequence_number == original_chunk.sequence_number
        assert restored_chunk.start_position == original_chunk.start_position
        assert restored_chunk.end_position == original_chunk.end_position
        assert restored_chunk.metadata == original_chunk.metadata
        assert restored_chunk.embedding_id == original_chunk.embedding_id


class TestProcessingResult:
    """ProcessingResult 테스트"""
    
    def test_create_processing_result(self):
        """처리 결과 생성 테스트"""
        job_id = uuid4()
        document_id = uuid4()
        user_id = uuid4()
        result_data = {
            "text_content": "Extracted text",
            "chunk_count": 5,
            "embedding_count": 5
        }
        metadata = ProcessingMetadata(processing_time=10.5)
        
        result = ProcessingResult.create(
            job_id=job_id,
            document_id=document_id,
            user_id=user_id,
            processing_type=ProcessingType.TEXT_EXTRACTION,
            result_data=result_data,
            metadata=metadata
        )
        
        assert isinstance(result.id, UUID)
        assert result.job_id == job_id
        assert result.document_id == document_id
        assert result.user_id == user_id
        assert result.processing_type == ProcessingType.TEXT_EXTRACTION
        assert result.result_data == result_data
        assert result.metadata == metadata
        assert isinstance(result.created_at, datetime)
    
    def test_get_text_content(self):
        """텍스트 콘텐츠 추출 테스트"""
        result = ProcessingResult.create(
            job_id=uuid4(),
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION,
            result_data={"text_content": "Extracted text"}
        )
        
        assert result.get_text_content() == "Extracted text"
    
    def test_get_chunk_count(self):
        """청크 수 조회 테스트"""
        result = ProcessingResult.create(
            job_id=uuid4(),
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.CHUNKING,
            result_data={"chunk_count": 10}
        )
        
        assert result.get_chunk_count() == 10
    
    def test_get_embedding_count(self):
        """임베딩 수 조회 테스트"""
        result = ProcessingResult.create(
            job_id=uuid4(),
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.EMBEDDING,
            result_data={"embedding_count": 15}
        )
        
        assert result.get_embedding_count() == 15
    
    def test_to_dict_and_from_dict(self):
        """딕셔너리 변환 테스트"""
        job_id = uuid4()
        document_id = uuid4()
        user_id = uuid4()
        result_data = {"text_content": "Test"}
        metadata = ProcessingMetadata(processing_time=5.0)
        
        original_result = ProcessingResult.create(
            job_id=job_id,
            document_id=document_id,
            user_id=user_id,
            processing_type=ProcessingType.TEXT_EXTRACTION,
            result_data=result_data,
            metadata=metadata
        )
        
        # 딕셔너리로 변환
        result_dict = original_result.to_dict()
        
        # 딕셔너리에서 복원
        restored_result = ProcessingResult.from_dict(result_dict)
        
        assert restored_result.id == original_result.id
        assert restored_result.job_id == original_result.job_id
        assert restored_result.document_id == original_result.document_id
        assert restored_result.user_id == original_result.user_id
        assert restored_result.processing_type == original_result.processing_type
        assert restored_result.result_data == original_result.result_data
        assert restored_result.metadata.processing_time == original_result.metadata.processing_time
