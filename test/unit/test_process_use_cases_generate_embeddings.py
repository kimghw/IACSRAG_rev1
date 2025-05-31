"""
Generate Embeddings Use Case 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4, UUID
from typing import List, Dict, Any

from src.core.exceptions import ValidationError, DocumentProcessingError
from src.modules.process.domain.entities import (
    ProcessingJob,
    ProcessingType,
    ProcessingStatus,
    TextChunk,
    ChunkType,
    ProcessingMetadata
)
from src.modules.process.application.use_cases.generate_embeddings import (
    GenerateEmbeddingsUseCase,
    GenerateEmbeddingsCommand,
    GenerateEmbeddingsResult,
    EmbeddingResult
)


class TestGenerateEmbeddingsUseCase:
    """임베딩 생성 유즈케이스 테스트"""
    
    @pytest.fixture
    def mock_job_repository(self):
        """Mock 작업 리포지토리"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_chunk_repository(self):
        """Mock 청크 리포지토리"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock 임베딩 서비스"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_event_publisher(self):
        """Mock 이벤트 발행자"""
        return AsyncMock()
    
    @pytest.fixture
    def use_case(
        self,
        mock_job_repository,
        mock_chunk_repository,
        mock_embedding_service,
        mock_event_publisher
    ):
        """임베딩 생성 유즈케이스 인스턴스"""
        return GenerateEmbeddingsUseCase(
            job_repository=mock_job_repository,
            chunk_repository=mock_chunk_repository,
            embedding_service=mock_embedding_service,
            event_publisher=mock_event_publisher
        )
    
    @pytest.fixture
    def sample_job(self):
        """샘플 처리 작업"""
        return ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.EMBEDDING,
            priority=1,
            parameters={"model_name": "text-embedding-ada-002"}
        )
    
    @pytest.fixture
    def sample_chunks(self):
        """샘플 텍스트 청크 목록"""
        chunks = []
        for i in range(3):
            chunk = TextChunk.create(
                document_id=uuid4(),
                user_id=uuid4(),
                content=f"Sample text content {i}",
                chunk_type=ChunkType.PARAGRAPH,
                sequence_number=i + 1,
                start_position=i * 100,
                end_position=(i + 1) * 100 - 1,
                metadata={"page": i + 1}
            )
            chunks.append(chunk)
        return chunks
    
    @pytest.fixture
    def sample_command(self, sample_job, sample_chunks):
        """샘플 임베딩 생성 명령"""
        return GenerateEmbeddingsCommand(
            job_id=sample_job.id,
            chunk_ids=[chunk.id for chunk in sample_chunks],
            document_id=sample_job.document_id,
            embedding_options={"model_name": "text-embedding-ada-002"}
        )
    
    @pytest.fixture
    def sample_embedding_results(self, sample_chunks):
        """샘플 임베딩 결과"""
        results = []
        for chunk in sample_chunks:
            results.append({
                "embedding_id": uuid4(),
                "vector": [0.1, 0.2, 0.3] * 512,  # 1536 차원
                "model_name": "text-embedding-ada-002",
                "dimensions": 1536
            })
        return results
    
    async def test_execute_success(
        self,
        use_case,
        sample_command,
        sample_job,
        sample_chunks,
        sample_embedding_results,
        mock_job_repository,
        mock_chunk_repository,
        mock_embedding_service,
        mock_event_publisher
    ):
        """정상적인 임베딩 생성 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunk_repository.find_by_ids.return_value = sample_chunks
        mock_embedding_service.generate_embeddings.return_value = sample_embedding_results
        
        # When
        result = await use_case.execute(sample_command)
        
        # Then
        assert isinstance(result, GenerateEmbeddingsResult)
        assert result.job_id == sample_job.id
        assert result.total_embeddings == len(sample_chunks)
        assert result.status == ProcessingStatus.COMPLETED
        assert len(result.embeddings) == len(sample_chunks)
        
        # 리포지토리 호출 검증
        mock_job_repository.find_by_id.assert_called_once_with(sample_command.job_id)
        mock_chunk_repository.find_by_ids.assert_called_once_with(sample_command.chunk_ids)
        mock_job_repository.save.assert_called()
        
        # 임베딩 서비스 호출 검증
        mock_embedding_service.generate_embeddings.assert_called_once()
        
        # 이벤트 발행 검증
        mock_event_publisher.publish_processing_completed.assert_called_once()
        mock_event_publisher.publish_embeddings_created.assert_called_once()
    
    async def test_execute_with_invalid_job_id(
        self,
        use_case,
        sample_command
    ):
        """잘못된 작업 ID로 실행 시 오류 테스트"""
        # Given
        command = GenerateEmbeddingsCommand(
            job_id=None,  # 잘못된 ID
            chunk_ids=[uuid4()],
            document_id=uuid4()
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Job ID is required"):
            await use_case.execute(command)
    
    async def test_execute_with_empty_chunk_ids(
        self,
        use_case,
        sample_command
    ):
        """빈 청크 ID 목록으로 실행 시 오류 테스트"""
        # Given
        command = GenerateEmbeddingsCommand(
            job_id=uuid4(),
            chunk_ids=[],  # 빈 목록
            document_id=uuid4()
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Chunk IDs are required"):
            await use_case.execute(command)
    
    async def test_execute_with_too_many_chunks(
        self,
        use_case
    ):
        """너무 많은 청크로 실행 시 오류 테스트"""
        # Given
        command = GenerateEmbeddingsCommand(
            job_id=uuid4(),
            chunk_ids=[uuid4() for _ in range(101)],  # 100개 초과
            document_id=uuid4()
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Too many chunks in single batch"):
            await use_case.execute(command)
    
    async def test_execute_with_duplicate_chunk_ids(
        self,
        use_case
    ):
        """중복 청크 ID로 실행 시 오류 테스트"""
        # Given
        chunk_id = uuid4()
        command = GenerateEmbeddingsCommand(
            job_id=uuid4(),
            chunk_ids=[chunk_id, chunk_id],  # 중복 ID
            document_id=uuid4()
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Duplicate chunk IDs found"):
            await use_case.execute(command)
    
    async def test_execute_with_job_not_found(
        self,
        use_case,
        sample_command,
        mock_job_repository
    ):
        """존재하지 않는 작업으로 실행 시 오류 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = None
        
        # When & Then
        with pytest.raises(ValidationError, match="Job .* not found"):
            await use_case.execute(sample_command)
    
    async def test_execute_with_wrong_job_type(
        self,
        use_case,
        sample_command,
        mock_job_repository
    ):
        """잘못된 작업 유형으로 실행 시 오류 테스트"""
        # Given
        wrong_job = ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.TEXT_EXTRACTION,  # 잘못된 유형
            priority=1
        )
        mock_job_repository.find_by_id.return_value = wrong_job
        
        # When & Then
        with pytest.raises(ValidationError, match="is not an embedding job"):
            await use_case.execute(sample_command)
    
    async def test_execute_with_wrong_job_status(
        self,
        use_case,
        sample_command,
        sample_job,
        mock_job_repository
    ):
        """잘못된 작업 상태로 실행 시 오류 테스트"""
        # Given
        sample_job.start_processing()  # 상태를 PROCESSING으로 변경
        mock_job_repository.find_by_id.return_value = sample_job
        
        # When & Then
        with pytest.raises(ValidationError, match="is not in pending status"):
            await use_case.execute(sample_command)
    
    async def test_execute_with_chunks_not_found(
        self,
        use_case,
        sample_command,
        sample_job,
        mock_job_repository,
        mock_chunk_repository
    ):
        """청크를 찾을 수 없을 때 오류 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunk_repository.find_by_ids.return_value = []  # 빈 결과
        
        # When & Then
        with pytest.raises(ValidationError, match="No chunks found"):
            await use_case.execute(sample_command)
    
    async def test_execute_with_missing_chunks(
        self,
        use_case,
        sample_command,
        sample_job,
        sample_chunks,
        mock_job_repository,
        mock_chunk_repository
    ):
        """일부 청크가 누락된 경우 오류 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunk_repository.find_by_ids.return_value = sample_chunks[:2]  # 일부만 반환
        
        # When & Then
        with pytest.raises(ValidationError, match="Chunks not found"):
            await use_case.execute(sample_command)
    
    async def test_execute_with_no_embeddings_generated(
        self,
        use_case,
        sample_command,
        sample_job,
        sample_chunks,
        mock_job_repository,
        mock_chunk_repository,
        mock_embedding_service
    ):
        """임베딩 생성 실패 시 오류 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunk_repository.find_by_ids.return_value = sample_chunks
        mock_embedding_service.generate_embeddings.return_value = []  # 빈 결과
        
        # When & Then
        with pytest.raises(DocumentProcessingError, match="No embeddings could be generated"):
            await use_case.execute(sample_command)
    
    async def test_execute_with_embedding_service_error(
        self,
        use_case,
        sample_command,
        sample_job,
        sample_chunks,
        mock_job_repository,
        mock_chunk_repository,
        mock_embedding_service,
        mock_event_publisher
    ):
        """임베딩 서비스 오류 시 처리 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunk_repository.find_by_ids.return_value = sample_chunks
        mock_embedding_service.generate_embeddings.side_effect = Exception("API Error")
        
        # When & Then
        with pytest.raises(Exception, match="API Error"):
            await use_case.execute(sample_command)
        
        # 실패 이벤트 발행 검증
        mock_event_publisher.publish_processing_failed.assert_called_once()
    
    async def test_execute_with_batch_processing(
        self,
        use_case,
        sample_job,
        mock_job_repository,
        mock_chunk_repository,
        mock_embedding_service,
        mock_event_publisher
    ):
        """배치 처리 테스트"""
        # Given
        # 60개 청크 생성 (배치 크기 50보다 큰 수)
        chunks = []
        for i in range(60):
            chunk = TextChunk.create(
                document_id=sample_job.document_id,
                user_id=sample_job.user_id,
                content=f"Content {i}",
                chunk_type=ChunkType.PARAGRAPH,
                sequence_number=i + 1,
                start_position=i * 100,
                end_position=(i + 1) * 100 - 1
            )
            chunks.append(chunk)
        
        command = GenerateEmbeddingsCommand(
            job_id=sample_job.id,
            chunk_ids=[chunk.id for chunk in chunks],
            document_id=sample_job.document_id,
            embedding_options={"batch_size": 50}
        )
        
        # 배치별 임베딩 결과 설정
        batch1_results = []
        batch2_results = []
        
        for i in range(50):
            batch1_results.append({
                "embedding_id": uuid4(),
                "vector": [0.1] * 1536,
                "model_name": "text-embedding-ada-002",
                "dimensions": 1536
            })
        
        for i in range(10):
            batch2_results.append({
                "embedding_id": uuid4(),
                "vector": [0.2] * 1536,
                "model_name": "text-embedding-ada-002",
                "dimensions": 1536
            })
        
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunk_repository.find_by_ids.return_value = chunks
        mock_embedding_service.generate_embeddings.side_effect = [batch1_results, batch2_results]
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.total_embeddings == 60
        assert len(result.embeddings) == 60
        
        # 임베딩 서비스가 2번 호출되었는지 확인 (배치 처리)
        assert mock_embedding_service.generate_embeddings.call_count == 2
    
    async def test_prepare_embedding_options(self, use_case):
        """임베딩 옵션 준비 테스트"""
        # Given
        custom_options = {
            "model_name": "custom-model",
            "batch_size": 25
        }
        
        # When
        options = use_case._prepare_embedding_options(custom_options)
        
        # Then
        assert options["model_name"] == "custom-model"
        assert options["batch_size"] == 25
        assert options["max_retries"] == 3  # 기본값
        assert options["timeout"] == 30.0  # 기본값
    
    async def test_prepare_embedding_options_with_none(self, use_case):
        """None 옵션으로 임베딩 옵션 준비 테스트"""
        # When
        options = use_case._prepare_embedding_options(None)
        
        # Then
        assert options["model_name"] == "text-embedding-ada-002"
        assert options["batch_size"] == 50
        assert options["max_retries"] == 3
        assert options["timeout"] == 30.0
    
    def test_create_processing_metadata(self, use_case, sample_chunks):
        """처리 메타데이터 생성 테스트"""
        # Given
        embeddings = []
        for chunk in sample_chunks:
            embeddings.append(EmbeddingResult(
                chunk_id=chunk.id,
                embedding_id=uuid4(),
                vector=[0.1] * 1536,
                model_name="text-embedding-ada-002",
                dimensions=1536
            ))
        
        options = {
            "model_name": "text-embedding-ada-002",
            "batch_size": 50
        }
        
        # When
        metadata = use_case._create_processing_metadata(embeddings, options)
        
        # Then
        assert isinstance(metadata, ProcessingMetadata)
        assert metadata.model_name == "text-embedding-ada-002"
        assert metadata.parameters["total_embeddings"] == len(embeddings)
        assert metadata.parameters["dimensions"] == 1536
        assert metadata.parameters["batch_size"] == 50
    
    def test_is_retryable_error(self, use_case):
        """재시도 가능한 오류 판단 테스트"""
        # Given & When & Then
        assert not use_case._is_retryable_error(ValidationError("Invalid input"))
        assert use_case._is_retryable_error(Exception("Network error"))
        assert use_case._is_retryable_error(RuntimeError("API timeout"))
    
    async def test_execute_with_chunks_already_having_embeddings(
        self,
        use_case,
        sample_command,
        sample_job,
        sample_chunks,
        sample_embedding_results,
        mock_job_repository,
        mock_chunk_repository,
        mock_embedding_service,
        mock_event_publisher
    ):
        """이미 임베딩이 있는 청크 처리 테스트"""
        # Given
        # 첫 번째 청크에 이미 임베딩 ID 설정
        sample_chunks[0].set_embedding_id(uuid4())
        
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunk_repository.find_by_ids.return_value = sample_chunks
        mock_embedding_service.generate_embeddings.return_value = sample_embedding_results
        
        # When
        result = await use_case.execute(sample_command)
        
        # Then
        # 경고 로그가 출력되지만 처리는 계속됨
        assert result.total_embeddings == len(sample_chunks)
        assert result.status == ProcessingStatus.COMPLETED
