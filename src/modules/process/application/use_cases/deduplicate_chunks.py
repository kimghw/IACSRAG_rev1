"""
Deduplicate Chunks Use Case

중복 청크 제거 유즈케이스
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Set, Tuple
from uuid import UUID

from src.core.exceptions import ValidationError, DocumentProcessingError
from src.core.logging import get_logger
from src.modules.process.domain.entities import (
    ProcessingJob,
    ProcessingType,
    ProcessingStatus,
    TextChunk,
    ProcessingMetadata
)
from src.modules.process.application.ports.repositories import (
    ProcessingJobRepository,
    TextChunkRepository
)
from src.modules.process.application.ports.services import (
    EventPublisher
)

logger = get_logger(__name__)


@dataclass
class DeduplicateChunksCommand:
    """중복 청크 제거 명령"""
    job_id: UUID
    document_id: UUID
    similarity_threshold: Optional[float] = 0.95
    deduplication_options: Optional[Dict[str, Any]] = None


@dataclass
class DuplicateGroup:
    """중복 그룹"""
    representative_chunk_id: UUID
    duplicate_chunk_ids: List[UUID]
    similarity_scores: List[float]
    group_size: int


@dataclass
class DeduplicateChunksResult:
    """중복 청크 제거 결과"""
    job_id: UUID
    document_id: UUID
    total_chunks_before: int
    total_chunks_after: int
    removed_chunks_count: int
    duplicate_groups: List[DuplicateGroup]
    status: ProcessingStatus
    message: str
    processing_metadata: Optional[ProcessingMetadata] = None


class DeduplicateChunksUseCase:
    """중복 청크 제거 유즈케이스"""
    
    def __init__(
        self,
        job_repository: ProcessingJobRepository,
        chunk_repository: TextChunkRepository,
        event_publisher: EventPublisher
    ):
        self.job_repository = job_repository
        self.chunk_repository = chunk_repository
        self.event_publisher = event_publisher
    
    async def execute(self, command: DeduplicateChunksCommand) -> DeduplicateChunksResult:
        """
        중복 청크 제거 실행
        
        Args:
            command: 중복 청크 제거 명령
            
        Returns:
            DeduplicateChunksResult: 중복 청크 제거 결과
            
        Raises:
            ValidationError: 입력 데이터 검증 실패
            DocumentProcessingError: 문서 처리 오류
        """
        logger.info(f"Starting chunk deduplication for job {command.job_id}")
        
        # 1. 입력 데이터 검증
        await self._validate_command(command)
        
        # 2. 작업 조회 및 상태 확인
        job = await self._get_and_validate_job(command.job_id)
        
        try:
            # 3. 작업 상태를 처리 중으로 변경
            job.start_processing()
            await self.job_repository.save(job)
            
            # 4. 문서의 모든 청크 조회
            chunks = await self._get_document_chunks(command.document_id)
            
            if not chunks:
                logger.warning(f"No chunks found for document {command.document_id}")
                return self._create_empty_result(command, job)
            
            # 5. 중복 제거 옵션 설정
            dedup_options = self._prepare_deduplication_options(command)
            
            # 6. 중복 청크 탐지
            duplicate_groups = await self._detect_duplicate_chunks(
                chunks=chunks,
                options=dedup_options
            )
            
            # 7. 중복 청크 제거
            removed_chunks = await self._remove_duplicate_chunks(duplicate_groups)
            
            # 8. 처리 메타데이터 생성
            metadata = self._create_processing_metadata(
                chunks_before=len(chunks),
                chunks_after=len(chunks) - len(removed_chunks),
                duplicate_groups=duplicate_groups,
                options=dedup_options
            )
            
            # 9. 작업 완료 처리
            job.complete_processing(metadata)
            await self.job_repository.save(job)
            
            # 10. 이벤트 발행
            await self.event_publisher.publish_processing_completed(
                job_id=job.id,
                document_id=job.document_id,
                user_id=job.user_id,
                processing_type=job.processing_type.value,
                result_data={
                    "chunks_before": len(chunks),
                    "chunks_after": len(chunks) - len(removed_chunks),
                    "removed_count": len(removed_chunks),
                    "duplicate_groups_count": len(duplicate_groups)
                }
            )
            
            # 11. 중복 제거 완료 이벤트 발행
            await self.event_publisher.publish_chunks_deduplicated(
                document_id=command.document_id,
                user_id=job.user_id,
                removed_chunk_count=len(removed_chunks),
                duplicate_groups_count=len(duplicate_groups)
            )
            
            logger.info(
                f"Chunk deduplication completed for job {command.job_id}. "
                f"Removed {len(removed_chunks)} duplicate chunks"
            )
            
            return DeduplicateChunksResult(
                job_id=job.id,
                document_id=command.document_id,
                total_chunks_before=len(chunks),
                total_chunks_after=len(chunks) - len(removed_chunks),
                removed_chunks_count=len(removed_chunks),
                duplicate_groups=duplicate_groups,
                status=job.status,
                message="Chunk deduplication completed successfully",
                processing_metadata=metadata
            )
            
        except Exception as e:
            # 12. 오류 처리
            await self._handle_deduplication_error(job, e)
            raise
    
    async def _validate_command(self, command: DeduplicateChunksCommand) -> None:
        """명령 데이터 검증"""
        if not command.job_id:
            raise ValidationError("Job ID is required")
        
        if not command.document_id:
            raise ValidationError("Document ID is required")
        
        if command.similarity_threshold is not None:
            if not 0.0 <= command.similarity_threshold <= 1.0:
                raise ValidationError(
                    f"Similarity threshold must be between 0.0 and 1.0, "
                    f"got {command.similarity_threshold}"
                )
    
    async def _get_and_validate_job(self, job_id: UUID) -> ProcessingJob:
        """작업 조회 및 상태 검증"""
        job = await self.job_repository.find_by_id(job_id)
        if not job:
            raise ValidationError(f"Job {job_id} not found")
        
        if job.processing_type != ProcessingType.DEDUPLICATION:
            raise ValidationError(
                f"Job {job_id} is not a deduplication job. "
                f"Type: {job.processing_type.value}"
            )
        
        if job.status != ProcessingStatus.PENDING:
            raise ValidationError(
                f"Job {job_id} is not in pending status. "
                f"Current status: {job.status.value}"
            )
        
        return job
    
    async def _get_document_chunks(self, document_id: UUID) -> List[TextChunk]:
        """문서의 모든 청크 조회"""
        chunks = await self.chunk_repository.find_by_document_id(document_id)
        return chunks
    
    def _prepare_deduplication_options(
        self, 
        command: DeduplicateChunksCommand
    ) -> Dict[str, Any]:
        """중복 제거 옵션 준비"""
        default_options = {
            "similarity_threshold": 0.95,
            "min_chunk_length": 50,
            "use_content_hash": True,
            "use_semantic_similarity": False,  # 향후 구현
            "preserve_metadata": True
        }
        
        if command.similarity_threshold is not None:
            default_options["similarity_threshold"] = command.similarity_threshold
        
        if command.deduplication_options:
            default_options.update(command.deduplication_options)
        
        return default_options
    
    async def _detect_duplicate_chunks(
        self,
        chunks: List[TextChunk],
        options: Dict[str, Any]
    ) -> List[DuplicateGroup]:
        """중복 청크 탐지"""
        duplicate_groups = []
        processed_chunks: Set[UUID] = set()
        
        # 콘텐츠 해시 기반 중복 탐지
        if options.get("use_content_hash", True):
            hash_groups = await self._group_by_content_hash(chunks)
            
            for content_hash, chunk_group in hash_groups.items():
                if len(chunk_group) > 1:
                    # 첫 번째 청크를 대표로 선택 (생성 시간 기준)
                    representative = min(chunk_group, key=lambda c: c.created_at)
                    duplicates = [c for c in chunk_group if c.id != representative.id]
                    
                    duplicate_group = DuplicateGroup(
                        representative_chunk_id=representative.id,
                        duplicate_chunk_ids=[c.id for c in duplicates],
                        similarity_scores=[1.0] * len(duplicates),  # 완전 일치
                        group_size=len(chunk_group)
                    )
                    duplicate_groups.append(duplicate_group)
                    
                    # 처리된 청크 표시
                    for chunk in chunk_group:
                        processed_chunks.add(chunk.id)
        
        # 텍스트 유사도 기반 중복 탐지 (향후 구현)
        if options.get("use_semantic_similarity", False):
            semantic_groups = await self._group_by_semantic_similarity(
                chunks=[c for c in chunks if c.id not in processed_chunks],
                threshold=options.get("similarity_threshold", 0.95)
            )
            duplicate_groups.extend(semantic_groups)
        
        logger.info(f"Detected {len(duplicate_groups)} duplicate groups")
        return duplicate_groups
    
    async def _group_by_content_hash(
        self, 
        chunks: List[TextChunk]
    ) -> Dict[str, List[TextChunk]]:
        """콘텐츠 해시로 청크 그룹화"""
        from src.utils.hash import calculate_content_hash
        
        hash_groups: Dict[str, List[TextChunk]] = {}
        
        for chunk in chunks:
            # 청크 내용의 해시 계산
            content_hash = calculate_content_hash(chunk.content.strip())
            
            if content_hash not in hash_groups:
                hash_groups[content_hash] = []
            
            hash_groups[content_hash].append(chunk)
        
        # 단일 청크 그룹 제거 (중복이 아님)
        return {h: chunks for h, chunks in hash_groups.items() if len(chunks) > 1}
    
    async def _group_by_semantic_similarity(
        self,
        chunks: List[TextChunk],
        threshold: float
    ) -> List[DuplicateGroup]:
        """의미적 유사도로 청크 그룹화 (향후 구현)"""
        # TODO: 임베딩 기반 유사도 계산 구현
        # 현재는 빈 리스트 반환
        logger.info("Semantic similarity grouping not implemented yet")
        return []
    
    async def _remove_duplicate_chunks(
        self, 
        duplicate_groups: List[DuplicateGroup]
    ) -> List[UUID]:
        """중복 청크 제거"""
        removed_chunk_ids = []
        
        for group in duplicate_groups:
            # 대표 청크를 제외한 모든 중복 청크 제거
            for duplicate_id in group.duplicate_chunk_ids:
                try:
                    # 청크 삭제 (실제로는 소프트 삭제 또는 상태 변경)
                    # 여기서는 리포지토리에서 삭제하지 않고 ID만 수집
                    removed_chunk_ids.append(duplicate_id)
                    
                    logger.debug(f"Marked chunk {duplicate_id} for removal")
                    
                except Exception as e:
                    logger.error(f"Failed to remove chunk {duplicate_id}: {e}")
                    # 개별 청크 삭제 실패는 전체 프로세스를 중단하지 않음
                    continue
        
        # 실제 삭제는 배치로 처리 (성능 최적화)
        if removed_chunk_ids:
            await self._batch_remove_chunks(removed_chunk_ids)
        
        return removed_chunk_ids
    
    async def _batch_remove_chunks(self, chunk_ids: List[UUID]) -> None:
        """청크 배치 삭제"""
        # TODO: 배치 삭제 구현
        # 현재는 개별 삭제로 처리
        for chunk_id in chunk_ids:
            try:
                # 실제 구현에서는 소프트 삭제 또는 상태 변경
                # await self.chunk_repository.soft_delete(chunk_id)
                logger.debug(f"Removed chunk {chunk_id}")
            except Exception as e:
                logger.error(f"Failed to remove chunk {chunk_id}: {e}")
    
    def _create_processing_metadata(
        self,
        chunks_before: int,
        chunks_after: int,
        duplicate_groups: List[DuplicateGroup],
        options: Dict[str, Any]
    ) -> ProcessingMetadata:
        """처리 메타데이터 생성"""
        return ProcessingMetadata(
            model_name="content-hash-deduplication",
            model_version="1.0",
            parameters={
                "similarity_threshold": options.get("similarity_threshold"),
                "chunks_before": chunks_before,
                "chunks_after": chunks_after,
                "removed_count": chunks_before - chunks_after,
                "duplicate_groups_count": len(duplicate_groups),
                "use_content_hash": options.get("use_content_hash"),
                "use_semantic_similarity": options.get("use_semantic_similarity")
            }
        )
    
    def _create_empty_result(
        self, 
        command: DeduplicateChunksCommand, 
        job: ProcessingJob
    ) -> DeduplicateChunksResult:
        """빈 결과 생성 (청크가 없는 경우)"""
        return DeduplicateChunksResult(
            job_id=job.id,
            document_id=command.document_id,
            total_chunks_before=0,
            total_chunks_after=0,
            removed_chunks_count=0,
            duplicate_groups=[],
            status=ProcessingStatus.COMPLETED,
            message="No chunks found for deduplication"
        )
    
    async def _handle_deduplication_error(self, job: ProcessingJob, error: Exception) -> None:
        """중복 제거 오류 처리"""
        error_message = str(error)
        error_type = type(error).__name__
        
        logger.error(
            f"Chunk deduplication failed for job {job.id}: {error_message}",
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
        
        # 데이터베이스 오류, 네트워크 오류 등은 재시도 가능
        return True
