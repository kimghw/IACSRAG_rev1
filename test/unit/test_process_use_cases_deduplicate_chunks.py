"""
Deduplicate Chunks Use Case 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
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
from src.modules.process.application.use_cases.deduplicate_chunks import (
    DeduplicateChunksUseCase,
    DeduplicateChunksCommand,
    DeduplicateChunksResult,
    DuplicateGroup
)


class TestDeduplicateChunksUseCase:
    """중복 청크 제거 유즈케이스 테스트"""
    
    @pytest.fixture
    def mock_job_repository(self):
        """Mock 작업 리포지토리"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_chunk_repository(self):
        """Mock 청크 리포지토리"""
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
        mock_event_publisher
    ):
        """중복 청크 제거 유즈케이스 인스턴스"""
        return DeduplicateChunksUseCase(
            job_repository=mock_job_repository,
            chunk_repository=mock_chunk_repository,
            event_publisher=mock_event_publisher
        )
    
    @pytest.fixture
    def sample_job(self):
        """샘플 처리 작업"""
        return ProcessingJob.create(
            document_id=uuid4(),
            user_id=uuid4(),
            processing_type=ProcessingType.DEDUPLICATION,
            priority=1,
            parameters={"similarity_threshold": 0.95}
        )
    
    @pytest.fixture
    def sample_chunks_with_duplicates(self):
        """중복이 포함된 샘플 텍스트 청크 목록"""
        document_id = uuid4()
        user_id = uuid4()
        
        chunks = []
        
        # 원본 청크들
        chunk1 = TextChunk.create(
            document_id=document_id,
            user_id=user_id,
            content="This is a unique content.",
            chunk_type=ChunkType.PARAGRAPH,
            sequence_number=1,
            start_position=0,
            end_position=25
        )
        chunks.append(chunk1)
        
        # 중복 청크 1 (동일한 내용)
        chunk2 = TextChunk.create(
            document_id=document_id,
            user_id=user_id,
            content="This is a duplicate content.",
            chunk_type=ChunkType.PARAGRAPH,
            sequence_number=2,
            start_position=26,
            end_position=53
        )
        chunks.append(chunk2)
        
        # 중복 청크 2 (chunk2와 동일한 내용)
        chunk3 = TextChunk.create(
            document_id=document_id,
            user_id=user_id,
            content="This is a duplicate content.",
            chunk_type=ChunkType.PARAGRAPH,
            sequence_number=3,
            start_position=54,
            end_position=81
        )
        chunks.append(chunk3)
        
        # 또 다른 원본 청크
        chunk4 = TextChunk.create(
            document_id=document_id,
            user_id=user_id,
            content="Another unique content here.",
            chunk_type=ChunkType.PARAGRAPH,
            sequence_number=4,
            start_position=82,
            end_position=109
        )
        chunks.append(chunk4)
        
        return chunks
    
    @pytest.fixture
    def sample_command(self, sample_job):
        """샘플 중복 제거 명령"""
        return DeduplicateChunksCommand(
            job_id=sample_job.id,
            document_id=sample_job.document_id,
            similarity_threshold=0.95
        )
    
    async def test_execute_success_with_duplicates(
        self,
        use_case,
        sample_command,
        sample_job,
        sample_chunks_with_duplicates,
        mock_job_repository,
        mock_chunk_repository,
        mock_event_publisher
    ):
        """중복 청크가 있는 경우 정상 처리 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunk_repository.find_by_document_id.return_value = sample_chunks_with_duplicates
        
        with patch('src.utils.hash.calculate_content_hash') as mock_hash:
            # 동일한 내용에 대해 같은 해시 반환
            def hash_side_effect(content):
                if content == "This is a duplicate content.":
                    return "duplicate_hash"
                elif content == "This is a unique content.":
                    return "unique_hash_1"
                elif content == "Another unique content here.":
                    return "unique_hash_2"
                return f"hash_{content}"
            
            mock_hash.side_effect = hash_side_effect
            
            # When
            result = await use_case.execute(sample_command)
            
            # Then
            assert isinstance(result, DeduplicateChunksResult)
            assert result.job_id == sample_job.id
            assert result.document_id == sample_command.document_id
            assert result.total_chunks_before == 4
            assert result.total_chunks_after == 3  # 1개 중복 제거
            assert result.removed_chunks_count == 1
            assert len(result.duplicate_groups) == 1
            assert result.status == ProcessingStatus.COMPLETED
            
            # 중복 그룹 검증
            duplicate_group = result.duplicate_groups[0]
            assert duplicate_group.group_size == 2
            assert len(duplicate_group.duplicate_chunk_ids) == 1
            
            # 리포지토리 호출 검증
            mock_job_repository.find_by_id.assert_called_once_with(sample_command.job_id)
            mock_chunk_repository.find_by_document_id.assert_called_once_with(sample_command.document_id)
            mock_job_repository.save.assert_called()
            
            # 이벤트 발행 검증
            mock_event_publisher.publish_processing_completed.assert_called_once()
            mock_event_publisher.publish_chunks_deduplicated.assert_called_once()
    
    async def test_execute_success_no_duplicates(
        self,
        use_case,
        sample_command,
        sample_job,
        mock_job_repository,
        mock_chunk_repository,
        mock_event_publisher
    ):
        """중복 청크가 없는 경우 테스트"""
        # Given
        unique_chunks = []
        for i in range(3):
            chunk = TextChunk.create(
                document_id=sample_job.document_id,
                user_id=sample_job.user_id,
                content=f"Unique content {i}",
                chunk_type=ChunkType.PARAGRAPH,
                sequence_number=i + 1,
                start_position=i * 100,
                end_position=(i + 1) * 100 - 1
            )
            unique_chunks.append(chunk)
        
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunk_repository.find_by_document_id.return_value = unique_chunks
        
        with patch('src.utils.hash.calculate_content_hash') as mock_hash:
            # 각 청크마다 다른 해시 반환
            mock_hash.side_effect = lambda content: f"hash_{content}"
            
            # When
            result = await use_case.execute(sample_command)
            
            # Then
            assert result.total_chunks_before == 3
            assert result.total_chunks_after == 3
            assert result.removed_chunks_count == 0
            assert len(result.duplicate_groups) == 0
            assert result.status == ProcessingStatus.COMPLETED
    
    async def test_execute_with_empty_chunks(
        self,
        use_case,
        sample_command,
        sample_job,
        mock_job_repository,
        mock_chunk_repository,
        mock_event_publisher
    ):
        """청크가 없는 경우 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunk_repository.find_by_document_id.return_value = []
        
        # When
        result = await use_case.execute(sample_command)
        
        # Then
        assert result.total_chunks_before == 0
        assert result.total_chunks_after == 0
        assert result.removed_chunks_count == 0
        assert len(result.duplicate_groups) == 0
        assert result.status == ProcessingStatus.COMPLETED
        assert result.message == "No chunks found for deduplication"
    
    async def test_execute_with_invalid_job_id(
        self,
        use_case
    ):
        """잘못된 작업 ID로 실행 시 오류 테스트"""
        # Given
        command = DeduplicateChunksCommand(
            job_id=None,  # 잘못된 ID
            document_id=uuid4()
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Job ID is required"):
            await use_case.execute(command)
    
    async def test_execute_with_invalid_document_id(
        self,
        use_case
    ):
        """잘못된 문서 ID로 실행 시 오류 테스트"""
        # Given
        command = DeduplicateChunksCommand(
            job_id=uuid4(),
            document_id=None  # 잘못된 ID
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Document ID is required"):
            await use_case.execute(command)
    
    async def test_execute_with_invalid_similarity_threshold(
        self,
        use_case
    ):
        """잘못된 유사도 임계값으로 실행 시 오류 테스트"""
        # Given
        command = DeduplicateChunksCommand(
            job_id=uuid4(),
            document_id=uuid4(),
            similarity_threshold=1.5  # 잘못된 값 (0.0-1.0 범위 초과)
        )
        
        # When & Then
        with pytest.raises(ValidationError, match="Similarity threshold must be between 0.0 and 1.0"):
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
        with pytest.raises(ValidationError, match="is not a deduplication job"):
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
    
    async def test_prepare_deduplication_options(self, use_case):
        """중복 제거 옵션 준비 테스트"""
        # Given
        command = DeduplicateChunksCommand(
            job_id=uuid4(),
            document_id=uuid4(),
            similarity_threshold=0.8,
            deduplication_options={"min_chunk_length": 100}
        )
        
        # When
        options = use_case._prepare_deduplication_options(command)
        
        # Then
        assert options["similarity_threshold"] == 0.8
        assert options["min_chunk_length"] == 100
        assert options["use_content_hash"] is True
        assert options["use_semantic_similarity"] is False
        assert options["preserve_metadata"] is True
    
    async def test_prepare_deduplication_options_defaults(self, use_case):
        """기본 중복 제거 옵션 테스트"""
        # Given
        command = DeduplicateChunksCommand(
            job_id=uuid4(),
            document_id=uuid4()
        )
        
        # When
        options = use_case._prepare_deduplication_options(command)
        
        # Then
        assert options["similarity_threshold"] == 0.95
        assert options["min_chunk_length"] == 50
        assert options["use_content_hash"] is True
        assert options["use_semantic_similarity"] is False
        assert options["preserve_metadata"] is True
    
    async def test_group_by_content_hash(self, use_case):
        """콘텐츠 해시로 그룹화 테스트"""
        # Given
        chunks = []
        for i in range(4):
            chunk = TextChunk.create(
                document_id=uuid4(),
                user_id=uuid4(),
                content="Same content" if i < 2 else f"Different content {i}",
                chunk_type=ChunkType.PARAGRAPH,
                sequence_number=i + 1,
                start_position=i * 100,
                end_position=(i + 1) * 100 - 1
            )
            chunks.append(chunk)
        
        with patch('src.utils.hash.calculate_content_hash') as mock_hash:
            def hash_side_effect(content):
                if content == "Same content":
                    return "same_hash"
                return f"hash_{content}"
            
            mock_hash.side_effect = hash_side_effect
            
            # When
            hash_groups = await use_case._group_by_content_hash(chunks)
            
            # Then
            assert len(hash_groups) == 1  # 중복 그룹만 반환
            assert "same_hash" in hash_groups
            assert len(hash_groups["same_hash"]) == 2
    
    async def test_detect_duplicate_chunks(
        self,
        use_case,
        sample_chunks_with_duplicates
    ):
        """중복 청크 탐지 테스트"""
        # Given
        options = {
            "use_content_hash": True,
            "use_semantic_similarity": False,
            "similarity_threshold": 0.95
        }
        
        with patch('src.utils.hash.calculate_content_hash') as mock_hash:
            def hash_side_effect(content):
                if content == "This is a duplicate content.":
                    return "duplicate_hash"
                return f"hash_{content}"
            
            mock_hash.side_effect = hash_side_effect
            
            # When
            duplicate_groups = await use_case._detect_duplicate_chunks(
                chunks=sample_chunks_with_duplicates,
                options=options
            )
            
            # Then
            assert len(duplicate_groups) == 1
            group = duplicate_groups[0]
            assert group.group_size == 2
            assert len(group.duplicate_chunk_ids) == 1
            assert all(score == 1.0 for score in group.similarity_scores)
    
    async def test_remove_duplicate_chunks(self, use_case):
        """중복 청크 제거 테스트"""
        # Given
        duplicate_groups = [
            DuplicateGroup(
                representative_chunk_id=uuid4(),
                duplicate_chunk_ids=[uuid4(), uuid4()],
                similarity_scores=[1.0, 1.0],
                group_size=3
            )
        ]
        
        # When
        removed_chunks = await use_case._remove_duplicate_chunks(duplicate_groups)
        
        # Then
        assert len(removed_chunks) == 2
        assert all(chunk_id in duplicate_groups[0].duplicate_chunk_ids for chunk_id in removed_chunks)
    
    def test_create_processing_metadata(self, use_case):
        """처리 메타데이터 생성 테스트"""
        # Given
        duplicate_groups = [
            DuplicateGroup(
                representative_chunk_id=uuid4(),
                duplicate_chunk_ids=[uuid4()],
                similarity_scores=[1.0],
                group_size=2
            )
        ]
        
        options = {
            "similarity_threshold": 0.95,
            "use_content_hash": True,
            "use_semantic_similarity": False
        }
        
        # When
        metadata = use_case._create_processing_metadata(
            chunks_before=10,
            chunks_after=9,
            duplicate_groups=duplicate_groups,
            options=options
        )
        
        # Then
        assert isinstance(metadata, ProcessingMetadata)
        assert metadata.model_name == "content-hash-deduplication"
        assert metadata.parameters["chunks_before"] == 10
        assert metadata.parameters["chunks_after"] == 9
        assert metadata.parameters["removed_count"] == 1
        assert metadata.parameters["duplicate_groups_count"] == 1
        assert metadata.parameters["similarity_threshold"] == 0.95
    
    def test_is_retryable_error(self, use_case):
        """재시도 가능한 오류 판단 테스트"""
        # Given & When & Then
        assert not use_case._is_retryable_error(ValidationError("Invalid input"))
        assert use_case._is_retryable_error(Exception("Database error"))
        assert use_case._is_retryable_error(RuntimeError("Network timeout"))
    
    async def test_execute_with_processing_error(
        self,
        use_case,
        sample_command,
        sample_job,
        sample_chunks_with_duplicates,
        mock_job_repository,
        mock_chunk_repository,
        mock_event_publisher
    ):
        """처리 중 오류 발생 시 처리 테스트"""
        # Given
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunk_repository.find_by_document_id.return_value = sample_chunks_with_duplicates
        
        with patch('src.utils.hash.calculate_content_hash') as mock_hash:
            mock_hash.side_effect = Exception("Hash calculation failed")
            
            # When & Then
            with pytest.raises(Exception, match="Hash calculation failed"):
                await use_case.execute(sample_command)
            
            # 실패 이벤트 발행 검증
            mock_event_publisher.publish_processing_failed.assert_called_once()
    
    async def test_execute_with_multiple_duplicate_groups(
        self,
        use_case,
        sample_command,
        sample_job,
        mock_job_repository,
        mock_chunk_repository,
        mock_event_publisher
    ):
        """여러 중복 그룹이 있는 경우 테스트"""
        # Given
        chunks = []
        document_id = sample_job.document_id
        user_id = sample_job.user_id
        
        # 첫 번째 중복 그룹
        for i in range(2):
            chunk = TextChunk.create(
                document_id=document_id,
                user_id=user_id,
                content="First duplicate content",
                chunk_type=ChunkType.PARAGRAPH,
                sequence_number=i + 1,
                start_position=i * 100,
                end_position=(i + 1) * 100 - 1
            )
            chunks.append(chunk)
        
        # 두 번째 중복 그룹
        for i in range(3):
            chunk = TextChunk.create(
                document_id=document_id,
                user_id=user_id,
                content="Second duplicate content",
                chunk_type=ChunkType.PARAGRAPH,
                sequence_number=i + 3,
                start_position=(i + 2) * 100,
                end_position=(i + 3) * 100 - 1
            )
            chunks.append(chunk)
        
        mock_job_repository.find_by_id.return_value = sample_job
        mock_chunk_repository.find_by_document_id.return_value = chunks
        
        with patch('src.utils.hash.calculate_content_hash') as mock_hash:
            def hash_side_effect(content):
                if content == "First duplicate content":
                    return "first_hash"
                elif content == "Second duplicate content":
                    return "second_hash"
                return f"hash_{content}"
            
            mock_hash.side_effect = hash_side_effect
            
            # When
            result = await use_case.execute(sample_command)
            
            # Then
            assert result.total_chunks_before == 5
            assert result.total_chunks_after == 2  # 2개 그룹에서 각각 1개, 2개 제거하여 2개만 남음
            assert result.removed_chunks_count == 3
            assert len(result.duplicate_groups) == 2
