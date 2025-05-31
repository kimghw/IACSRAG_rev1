"""
Generate Embeddings Use Case

임베딩 생성 유즈케이스
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
    ProcessingMetadata
)
from src.modules.process.application.ports.repositories import ProcessingJobRepository
from src.modules.process.application.ports.services import (
    EventPublisher,
    EmbeddingService
)
from src.modules.process.application.ports.repositories import (
    TextChunkRepository as ChunkRepository
)

logger = get_logger(__name__)


@dataclass
class GenerateEmbeddingsCommand:
    """임베딩 생성 명령"""
    job_id: UUID
    chunk_ids: List[UUID]
    document_id: UUID
    embedding_options: Optional[Dict[str, Any]] = None


@dataclass
class EmbeddingResult:
    """임베딩 결과"""
    chunk_id: UUID
    embedding_id: UUID
    vector: List[float]
    model_name: str
    dimensions: int


@dataclass
class GenerateEmbeddingsResult:
    """임베딩 생성 결과"""
    job_id: UUID
    embeddings: List[EmbeddingResult]
    total_embeddings: int
    status: ProcessingStatus
    message: str
    processing_metadata: Optional[ProcessingMetadata] = None


class GenerateEmbeddingsUseCase:
    """임베딩 생성 유즈케이스"""
    
    def __init__(
        self,
        job_repository: ProcessingJobRepository,
        chunk_repository: ChunkRepository,
        embedding_service: EmbeddingService,
        event_publisher: EventPublisher
    ):
        self.job_repository = job_repository
        self.chunk_repository = chunk_repository
        self.embedding_service = embedding_service
        self.event_publisher = event_publisher
    
    async def execute(self, command: GenerateEmbeddingsCommand) -> GenerateEmbeddingsResult:
        """
        임베딩 생성 실행
        
        Args:
            command: 임베딩 생성 명령
            
        Returns:
            GenerateEmbeddingsResult: 임베딩 생성 결과
            
        Raises:
            ValidationError: 입력 데이터 검증 실패
            DocumentProcessingError: 문서 처리 오류
        """
        logger.info(f"Starting embedding generation for job {command.job_id}")
        
        # 1. 입력 데이터 검증
        await self._validate_command(command)
        
        # 2. 작업 조회 및 상태 확인
        job = await self._get_and_validate_job(command.job_id)
        
        try:
            # 3. 작업 상태를 처리 중으로 변경
            job.start_processing()
            await self.job_repository.save(job)
            
            # 4. 청크 데이터 조회
            chunks = await self._get_and_validate_chunks(command.chunk_ids)
            
            # 5. 임베딩 생성 옵션 설정
            embedding_options = self._prepare_embedding_options(command.embedding_options)
            
            # 6. 배치 임베딩 생성
            embeddings = await self._generate_embeddings_batch(
                chunks=chunks,
                options=embedding_options
            )
            
            # 7. 임베딩 결과 검증
            if not embeddings or len(embeddings) == 0:
                raise DocumentProcessingError("No embeddings could be generated")
            
            # 8. 청크에 임베딩 ID 연결
            await self._link_embeddings_to_chunks(chunks, embeddings)
            
            # 9. 처리 메타데이터 생성
            metadata = self._create_processing_metadata(embeddings, embedding_options)
            
            # 10. 작업 완료 처리
            job.complete_processing(metadata)
            await self.job_repository.save(job)
            
            # 11. 이벤트 발행
            await self.event_publisher.publish_processing_completed(
                job_id=job.id,
                document_id=job.document_id,
                user_id=job.user_id,
                processing_type=job.processing_type.value,
                result_data={
                    "total_embeddings": len(embeddings),
                    "embedding_ids": [str(emb.embedding_id) for emb in embeddings],
                    "model_name": embedding_options.get("model_name", "unknown"),
                    "dimensions": embeddings[0].dimensions if embeddings else 0
                }
            )
            
            # 12. 임베딩 생성 이벤트 발행
            await self.event_publisher.publish_embeddings_created(
                document_id=command.document_id,
                user_id=job.user_id,
                embedding_count=len(embeddings),
                embedding_ids=[emb.embedding_id for emb in embeddings]
            )
            
            logger.info(
                f"Embedding generation completed for job {command.job_id}. "
                f"Generated {len(embeddings)} embeddings"
            )
            
            return GenerateEmbeddingsResult(
                job_id=job.id,
                embeddings=embeddings,
                total_embeddings=len(embeddings),
                status=job.status,
                message="Embedding generation completed successfully",
                processing_metadata=metadata
            )
            
        except Exception as e:
            # 13. 오류 처리
            await self._handle_embedding_error(job, e)
            raise
    
    async def _validate_command(self, command: GenerateEmbeddingsCommand) -> None:
        """명령 데이터 검증"""
        if not command.job_id:
            raise ValidationError("Job ID is required")
        
        if not command.chunk_ids:
            raise ValidationError("Chunk IDs are required")
        
        if not command.document_id:
            raise ValidationError("Document ID is required")
        
        # 청크 ID 개수 제한 (배치 처리 한계)
        max_chunks_per_batch = 100
        if len(command.chunk_ids) > max_chunks_per_batch:
            raise ValidationError(
                f"Too many chunks in single batch. "
                f"Maximum {max_chunks_per_batch}, got {len(command.chunk_ids)}"
            )
        
        # 중복 청크 ID 확인
        if len(command.chunk_ids) != len(set(command.chunk_ids)):
            raise ValidationError("Duplicate chunk IDs found")
    
    async def _get_and_validate_job(self, job_id: UUID) -> ProcessingJob:
        """작업 조회 및 상태 검증"""
        job = await self.job_repository.find_by_id(job_id)
        if not job:
            raise ValidationError(f"Job {job_id} not found")
        
        if job.processing_type != ProcessingType.EMBEDDING:
            raise ValidationError(
                f"Job {job_id} is not an embedding job. "
                f"Type: {job.processing_type.value}"
            )
        
        if job.status != ProcessingStatus.PENDING:
            raise ValidationError(
                f"Job {job_id} is not in pending status. "
                f"Current status: {job.status.value}"
            )
        
        return job
    
    async def _get_and_validate_chunks(self, chunk_ids: List[UUID]) -> List[TextChunk]:
        """청크 조회 및 검증"""
        chunks = await self.chunk_repository.find_by_ids(chunk_ids)
        
        if not chunks:
            raise ValidationError("No chunks found for the given IDs")
        
        if len(chunks) != len(chunk_ids):
            found_ids = {chunk.id for chunk in chunks}
            missing_ids = set(chunk_ids) - found_ids
            raise ValidationError(f"Chunks not found: {missing_ids}")
        
        # 이미 임베딩이 생성된 청크 확인
        chunks_with_embeddings = [chunk for chunk in chunks if chunk.embedding_id]
        if chunks_with_embeddings:
            chunk_ids_with_embeddings = [str(chunk.id) for chunk in chunks_with_embeddings]
            logger.warning(
                f"Some chunks already have embeddings: {chunk_ids_with_embeddings}"
            )
        
        return chunks
    
    def _prepare_embedding_options(self, options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """임베딩 옵션 준비"""
        default_options = {
            "model_name": "text-embedding-ada-002",
            "batch_size": 50,
            "max_retries": 3,
            "timeout": 30.0
        }
        
        if options:
            default_options.update(options)
        
        return default_options
    
    async def _generate_embeddings_batch(
        self,
        chunks: List[TextChunk],
        options: Dict[str, Any]
    ) -> List[EmbeddingResult]:
        """배치 임베딩 생성"""
        batch_size = options.get("batch_size", 50)
        embeddings = []
        
        # 청크를 배치 단위로 분할
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            
            logger.info(f"Processing embedding batch {i//batch_size + 1}, chunks: {len(batch_chunks)}")
            
            # 배치 텍스트 추출
            texts = [chunk.content for chunk in batch_chunks]
            
            # 임베딩 서비스 호출
            batch_embeddings = await self.embedding_service.generate_embeddings(
                texts=texts,
                model_name=options.get("model_name"),
                timeout=options.get("timeout")
            )
            
            # 결과 매핑
            for chunk, embedding_data in zip(batch_chunks, batch_embeddings):
                embedding_result = EmbeddingResult(
                    chunk_id=chunk.id,
                    embedding_id=embedding_data["embedding_id"],
                    vector=embedding_data["vector"],
                    model_name=embedding_data["model_name"],
                    dimensions=len(embedding_data["vector"])
                )
                embeddings.append(embedding_result)
        
        return embeddings
    
    async def _link_embeddings_to_chunks(
        self,
        chunks: List[TextChunk],
        embeddings: List[EmbeddingResult]
    ) -> None:
        """청크에 임베딩 ID 연결"""
        embedding_map = {emb.chunk_id: emb.embedding_id for emb in embeddings}
        
        for chunk in chunks:
            if chunk.id in embedding_map:
                chunk.set_embedding_id(embedding_map[chunk.id])
                await self.chunk_repository.save(chunk)
    
    def _create_processing_metadata(
        self,
        embeddings: List[EmbeddingResult],
        options: Dict[str, Any]
    ) -> ProcessingMetadata:
        """처리 메타데이터 생성"""
        return ProcessingMetadata(
            model_name=options.get("model_name"),
            model_version="1.0",  # 실제 모델 버전으로 교체
            parameters={
                "batch_size": options.get("batch_size"),
                "total_embeddings": len(embeddings),
                "dimensions": embeddings[0].dimensions if embeddings else 0,
                "embedding_model": options.get("model_name")
            }
        )
    
    async def _handle_embedding_error(self, job: ProcessingJob, error: Exception) -> None:
        """임베딩 오류 처리"""
        error_message = str(error)
        error_type = type(error).__name__
        
        logger.error(
            f"Embedding generation failed for job {job.id}: {error_message}",
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
        
        # API 호출 실패, 네트워크 오류 등은 재시도 가능
        return True
