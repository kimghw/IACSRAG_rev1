"""
Process Domain Entities

문서 처리 관련 도메인 엔티티를 정의합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from src.utils.datetime import utc_now


class ProcessingStatus(Enum):
    """처리 상태"""
    PENDING = "pending"          # 대기 중
    PROCESSING = "processing"    # 처리 중
    COMPLETED = "completed"      # 완료
    FAILED = "failed"           # 실패
    CANCELLED = "cancelled"     # 취소됨


class ProcessingType(Enum):
    """처리 유형"""
    TEXT_EXTRACTION = "text_extraction"    # 텍스트 추출
    CHUNKING = "chunking"                  # 청킹
    EMBEDDING = "embedding"                # 임베딩 생성
    DEDUPLICATION = "deduplication"        # 중복 제거
    INDEXING = "indexing"                  # 인덱싱
    FULL_PIPELINE = "full_pipeline"        # 전체 파이프라인


class ChunkType(Enum):
    """청크 유형"""
    PARAGRAPH = "paragraph"      # 문단 단위
    SENTENCE = "sentence"        # 문장 단위
    FIXED_SIZE = "fixed_size"    # 고정 크기
    SEMANTIC = "semantic"        # 의미 단위


@dataclass
class ProcessingMetadata:
    """처리 메타데이터"""
    processing_time: Optional[float] = None      # 처리 시간 (초)
    memory_usage: Optional[int] = None           # 메모리 사용량 (바이트)
    cpu_usage: Optional[float] = None            # CPU 사용률 (%)
    model_name: Optional[str] = None             # 사용된 모델명
    model_version: Optional[str] = None          # 모델 버전
    parameters: Dict[str, Any] = field(default_factory=dict)  # 처리 파라미터
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "processing_time": self.processing_time,
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "parameters": self.parameters
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingMetadata":
        """딕셔너리에서 생성"""
        return cls(
            processing_time=data.get("processing_time"),
            memory_usage=data.get("memory_usage"),
            cpu_usage=data.get("cpu_usage"),
            model_name=data.get("model_name"),
            model_version=data.get("model_version"),
            parameters=data.get("parameters", {})
        )


@dataclass
class ProcessingJob:
    """처리 작업 엔티티"""
    id: UUID
    document_id: UUID
    user_id: UUID
    processing_type: ProcessingType
    status: ProcessingStatus
    priority: int = 0                           # 우선순위 (높을수록 우선)
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Optional[ProcessingMetadata] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @classmethod
    def create(
        cls,
        document_id: UUID,
        user_id: UUID,
        processing_type: ProcessingType,
        priority: int = 0,
        parameters: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> "ProcessingJob":
        """새 처리 작업 생성"""
        return cls(
            id=uuid4(),
            document_id=document_id,
            user_id=user_id,
            processing_type=processing_type,
            status=ProcessingStatus.PENDING,
            priority=priority,
            parameters=parameters or {},
            max_retries=max_retries
        )
    
    def start_processing(self) -> None:
        """처리 시작"""
        if self.status != ProcessingStatus.PENDING:
            raise ValueError(f"Cannot start processing job in status: {self.status}")
        
        self.status = ProcessingStatus.PROCESSING
        self.started_at = utc_now()
        self.updated_at = utc_now()
    
    def complete_processing(self, metadata: Optional[ProcessingMetadata] = None) -> None:
        """처리 완료"""
        if self.status != ProcessingStatus.PROCESSING:
            raise ValueError(f"Cannot complete processing job in status: {self.status}")
        
        self.status = ProcessingStatus.COMPLETED
        self.completed_at = utc_now()
        self.updated_at = utc_now()
        if metadata:
            self.metadata = metadata
    
    def fail_processing(self, error_message: str) -> None:
        """처리 실패"""
        if self.status not in [ProcessingStatus.PROCESSING, ProcessingStatus.PENDING]:
            raise ValueError(f"Cannot fail processing job in status: {self.status}")
        
        self.status = ProcessingStatus.FAILED
        self.error_message = error_message
        self.updated_at = utc_now()
    
    def retry_processing(self) -> bool:
        """처리 재시도"""
        if self.status != ProcessingStatus.FAILED:
            raise ValueError(f"Cannot retry processing job in status: {self.status}")
        
        if self.retry_count >= self.max_retries:
            return False
        
        self.retry_count += 1
        self.status = ProcessingStatus.PENDING
        self.error_message = None
        self.updated_at = utc_now()
        return True
    
    def cancel_processing(self) -> None:
        """처리 취소"""
        if self.status in [ProcessingStatus.COMPLETED, ProcessingStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel processing job in status: {self.status}")
        
        self.status = ProcessingStatus.CANCELLED
        self.updated_at = utc_now()
    
    def can_retry(self) -> bool:
        """재시도 가능 여부"""
        return (
            self.status == ProcessingStatus.FAILED and 
            self.retry_count < self.max_retries
        )
    
    def fail_with_retry(self, error_message: str) -> None:
        """재시도와 함께 실패 처리"""
        if self.status not in [ProcessingStatus.PROCESSING, ProcessingStatus.PENDING]:
            raise ValueError(f"Cannot fail processing job in status: {self.status}")
        
        self.retry_count += 1
        self.status = ProcessingStatus.FAILED
        self.error_message = error_message
        self.updated_at = utc_now()
    
    def fail_permanently(self, error_message: str) -> None:
        """영구적으로 실패 처리 (재시도 불가)"""
        if self.status not in [ProcessingStatus.PROCESSING, ProcessingStatus.PENDING, ProcessingStatus.FAILED]:
            raise ValueError(f"Cannot permanently fail processing job in status: {self.status}")
        
        self.status = ProcessingStatus.FAILED
        self.error_message = error_message
        self.retry_count = self.max_retries  # 최대 재시도 횟수로 설정하여 재시도 불가능하게 만듦
        self.updated_at = utc_now()
    
    def is_terminal_status(self) -> bool:
        """종료 상태 여부"""
        return self.status in [
            ProcessingStatus.COMPLETED,
            ProcessingStatus.CANCELLED
        ]
    
    def get_processing_duration(self) -> Optional[float]:
        """처리 시간 계산 (초)"""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or utc_now()
        return (end_time - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "user_id": str(self.user_id),
            "processing_type": self.processing_type.value,
            "status": self.status.value,
            "priority": self.priority,
            "parameters": self.parameters,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingJob":
        """딕셔너리에서 생성"""
        metadata = None
        if data.get("metadata"):
            metadata = ProcessingMetadata.from_dict(data["metadata"])
        
        return cls(
            id=UUID(data["id"]),
            document_id=UUID(data["document_id"]),
            user_id=UUID(data["user_id"]),
            processing_type=ProcessingType(data["processing_type"]),
            status=ProcessingStatus(data["status"]),
            priority=data["priority"],
            parameters=data["parameters"],
            metadata=metadata,
            error_message=data.get("error_message"),
            retry_count=data["retry_count"],
            max_retries=data["max_retries"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        )


@dataclass
class TextChunk:
    """텍스트 청크 엔티티"""
    id: UUID
    document_id: UUID
    user_id: UUID
    content: str
    chunk_type: ChunkType
    sequence_number: int                        # 문서 내 순서
    start_position: int                         # 원본 텍스트에서 시작 위치
    end_position: int                          # 원본 텍스트에서 끝 위치
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding_id: Optional[UUID] = None         # 연결된 임베딩 ID
    created_at: datetime = field(default_factory=utc_now)
    
    @classmethod
    def create(
        cls,
        document_id: UUID,
        user_id: UUID,
        content: str,
        chunk_type: ChunkType,
        sequence_number: int,
        start_position: int,
        end_position: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "TextChunk":
        """새 텍스트 청크 생성"""
        return cls(
            id=uuid4(),
            document_id=document_id,
            user_id=user_id,
            content=content,
            chunk_type=chunk_type,
            sequence_number=sequence_number,
            start_position=start_position,
            end_position=end_position,
            metadata=metadata or {}
        )
    
    def get_content_length(self) -> int:
        """콘텐츠 길이"""
        return len(self.content)
    
    def get_word_count(self) -> int:
        """단어 수"""
        return len(self.content.split())
    
    def set_embedding_id(self, embedding_id: UUID) -> None:
        """임베딩 ID 설정"""
        self.embedding_id = embedding_id
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "user_id": str(self.user_id),
            "content": self.content,
            "chunk_type": self.chunk_type.value,
            "sequence_number": self.sequence_number,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "metadata": self.metadata,
            "embedding_id": str(self.embedding_id) if self.embedding_id else None,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TextChunk":
        """딕셔너리에서 생성"""
        return cls(
            id=UUID(data["id"]),
            document_id=UUID(data["document_id"]),
            user_id=UUID(data["user_id"]),
            content=data["content"],
            chunk_type=ChunkType(data["chunk_type"]),
            sequence_number=data["sequence_number"],
            start_position=data["start_position"],
            end_position=data["end_position"],
            metadata=data["metadata"],
            embedding_id=UUID(data["embedding_id"]) if data.get("embedding_id") else None,
            created_at=datetime.fromisoformat(data["created_at"])
        )


@dataclass
class EmbeddingResult:
    """임베딩 결과 엔티티"""
    text: str                                   # 원본 텍스트
    vector: List[float]                         # 임베딩 벡터
    model: str                                  # 사용된 모델명
    dimensions: int                             # 벡터 차원 수
    metadata: Dict[str, Any] = field(default_factory=dict)  # 추가 메타데이터
    
    @classmethod
    def create(
        cls,
        text: str,
        vector: List[float],
        model: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "EmbeddingResult":
        """새 임베딩 결과 생성"""
        return cls(
            text=text,
            vector=vector,
            model=model,
            dimensions=len(vector),
            metadata=metadata or {}
        )
    
    def get_vector_norm(self) -> float:
        """벡터 노름 계산"""
        return sum(x * x for x in self.vector) ** 0.5
    
    def normalize_vector(self) -> List[float]:
        """벡터 정규화"""
        norm = self.get_vector_norm()
        if norm == 0:
            return self.vector
        return [x / norm for x in self.vector]
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "text": self.text,
            "vector": self.vector,
            "model": self.model,
            "dimensions": self.dimensions,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingResult":
        """딕셔너리에서 생성"""
        return cls(
            text=data["text"],
            vector=data["vector"],
            model=data["model"],
            dimensions=data["dimensions"],
            metadata=data.get("metadata", {})
        )


@dataclass
class ProcessingResult:
    """처리 결과 엔티티"""
    id: UUID
    job_id: UUID
    document_id: UUID
    user_id: UUID
    processing_type: ProcessingType
    result_data: Dict[str, Any]                 # 처리 결과 데이터
    metadata: Optional[ProcessingMetadata] = None
    created_at: datetime = field(default_factory=utc_now)
    
    @classmethod
    def create(
        cls,
        job_id: UUID,
        document_id: UUID,
        user_id: UUID,
        processing_type: ProcessingType,
        result_data: Dict[str, Any],
        metadata: Optional[ProcessingMetadata] = None
    ) -> "ProcessingResult":
        """새 처리 결과 생성"""
        return cls(
            id=uuid4(),
            job_id=job_id,
            document_id=document_id,
            user_id=user_id,
            processing_type=processing_type,
            result_data=result_data,
            metadata=metadata
        )
    
    def get_text_content(self) -> Optional[str]:
        """텍스트 콘텐츠 추출"""
        return self.result_data.get("text_content")
    
    def get_chunk_count(self) -> Optional[int]:
        """청크 수 조회"""
        return self.result_data.get("chunk_count")
    
    def get_embedding_count(self) -> Optional[int]:
        """임베딩 수 조회"""
        return self.result_data.get("embedding_count")
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "document_id": str(self.document_id),
            "user_id": str(self.user_id),
            "processing_type": self.processing_type.value,
            "result_data": self.result_data,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingResult":
        """딕셔너리에서 생성"""
        metadata = None
        if data.get("metadata"):
            metadata = ProcessingMetadata.from_dict(data["metadata"])
        
        return cls(
            id=UUID(data["id"]),
            job_id=UUID(data["job_id"]),
            document_id=UUID(data["document_id"]),
            user_id=UUID(data["user_id"]),
            processing_type=ProcessingType(data["processing_type"]),
            result_data=data["result_data"],
            metadata=metadata,
            created_at=datetime.fromisoformat(data["created_at"])
        )
