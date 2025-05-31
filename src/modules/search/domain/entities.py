"""
Search Domain Entities

검색 도메인의 핵심 엔티티들을 정의
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from src.utils.datetime import utc_now


class SearchType(Enum):
    """검색 유형"""
    SEMANTIC = "semantic"  # 의미 기반 검색
    KEYWORD = "keyword"    # 키워드 검색
    HYBRID = "hybrid"      # 하이브리드 검색


class SearchStatus(Enum):
    """검색 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SearchQuery:
    """검색 쿼리 엔티티"""
    
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default=None)
    query_text: str = field(default="")
    search_type: SearchType = field(default=SearchType.SEMANTIC)
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = field(default=10)
    threshold: float = field(default=0.7)
    created_at: datetime = field(default_factory=utc_now)
    
    @classmethod
    def create(
        cls,
        user_id: UUID,
        query_text: str,
        search_type: SearchType = SearchType.SEMANTIC,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        threshold: float = 0.7
    ) -> "SearchQuery":
        """검색 쿼리 생성"""
        return cls(
            user_id=user_id,
            query_text=query_text,
            search_type=search_type,
            filters=filters or {},
            limit=limit,
            threshold=threshold
        )
    
    def add_filter(self, key: str, value: Any) -> None:
        """필터 추가"""
        self.filters[key] = value
    
    def remove_filter(self, key: str) -> None:
        """필터 제거"""
        self.filters.pop(key, None)
    
    def is_valid(self) -> bool:
        """쿼리 유효성 검증"""
        return (
            self.user_id is not None and
            self.query_text.strip() != "" and
            0 < self.limit <= 100 and
            0.0 <= self.threshold <= 1.0
        )


@dataclass
class SearchResult:
    """검색 결과 항목"""
    
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """초기화 후 처리"""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("Score must be between 0.0 and 1.0")


@dataclass
class SearchResponse:
    """검색 응답 엔티티"""
    
    id: UUID = field(default_factory=uuid4)
    query_id: UUID = field(default=None)
    user_id: UUID = field(default=None)
    query_text: str = field(default="")
    results: List[SearchResult] = field(default_factory=list)
    total_results: int = field(default=0)
    search_time_ms: float = field(default=0.0)
    status: SearchStatus = field(default=SearchStatus.PENDING)
    error_message: Optional[str] = field(default=None)
    created_at: datetime = field(default_factory=utc_now)
    completed_at: Optional[datetime] = field(default=None)
    
    @classmethod
    def create(
        cls,
        query: SearchQuery,
        results: List[SearchResult],
        search_time_ms: float
    ) -> "SearchResponse":
        """검색 응답 생성"""
        return cls(
            query_id=query.id,
            user_id=query.user_id,
            query_text=query.query_text,
            results=results,
            total_results=len(results),
            search_time_ms=search_time_ms,
            status=SearchStatus.COMPLETED,
            completed_at=utc_now()
        )
    
    def mark_as_failed(self, error_message: str) -> None:
        """실패로 표시"""
        self.status = SearchStatus.FAILED
        self.error_message = error_message
        self.completed_at = utc_now()
    
    def add_result(self, result: SearchResult) -> None:
        """검색 결과 추가"""
        self.results.append(result)
        self.total_results = len(self.results)
    
    def get_top_results(self, limit: int) -> List[SearchResult]:
        """상위 결과 반환"""
        return sorted(self.results, key=lambda x: x.score, reverse=True)[:limit]


@dataclass
class AnswerRequest:
    """답변 생성 요청 엔티티"""
    
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default=None)
    query_text: str = field(default="")
    context_chunks: List[SearchResult] = field(default_factory=list)
    model_name: str = field(default="gpt-3.5-turbo")
    max_tokens: int = field(default=1000)
    temperature: float = field(default=0.7)
    system_prompt: Optional[str] = field(default=None)
    created_at: datetime = field(default_factory=utc_now)
    
    @classmethod
    def create(
        cls,
        user_id: UUID,
        query_text: str,
        context_chunks: List[SearchResult],
        model_name: str = "gpt-3.5-turbo",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> "AnswerRequest":
        """답변 요청 생성"""
        return cls(
            user_id=user_id,
            query_text=query_text,
            context_chunks=context_chunks,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt
        )
    
    def is_valid(self) -> bool:
        """요청 유효성 검증"""
        return (
            self.user_id is not None and
            self.query_text.strip() != "" and
            len(self.context_chunks) > 0 and
            self.max_tokens > 0 and
            0.0 <= self.temperature <= 2.0
        )
    
    def get_context_text(self) -> str:
        """컨텍스트 텍스트 생성"""
        return "\n\n".join([chunk.content for chunk in self.context_chunks])


@dataclass
class Answer:
    """답변 엔티티"""
    
    id: UUID = field(default_factory=uuid4)
    request_id: UUID = field(default=None)
    user_id: UUID = field(default=None)
    query_text: str = field(default="")
    answer_text: str = field(default="")
    confidence_score: float = field(default=0.0)
    source_chunks: List[UUID] = field(default_factory=list)
    model_name: str = field(default="")
    tokens_used: int = field(default=0)
    generation_time_ms: float = field(default=0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    
    @classmethod
    def create(
        cls,
        request: AnswerRequest,
        answer_text: str,
        confidence_score: float,
        tokens_used: int,
        generation_time_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "Answer":
        """답변 생성"""
        return cls(
            request_id=request.id,
            user_id=request.user_id,
            query_text=request.query_text,
            answer_text=answer_text,
            confidence_score=confidence_score,
            source_chunks=[chunk.chunk_id for chunk in request.context_chunks],
            model_name=request.model_name,
            tokens_used=tokens_used,
            generation_time_ms=generation_time_ms,
            metadata=metadata or {}
        )
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """높은 신뢰도 여부"""
        return self.confidence_score >= threshold
    
    def add_metadata(self, key: str, value: Any) -> None:
        """메타데이터 추가"""
        self.metadata[key] = value


@dataclass
class AnswerResult:
    """답변 결과 엔티티 (Use Case 반환용)"""
    
    answer: str
    sources: List[SearchResult]
    confidence: float
    generation_time_ms: float = field(default=0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        answer: str,
        sources: List[SearchResult],
        confidence: float,
        generation_time_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "AnswerResult":
        """답변 결과 생성"""
        return cls(
            answer=answer,
            sources=sources,
            confidence=confidence,
            generation_time_ms=generation_time_ms,
            metadata=metadata or {}
        )


@dataclass
class SearchSession:
    """검색 세션 엔티티"""
    
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default=None)
    queries: List[SearchQuery] = field(default_factory=list)
    answers: List[Answer] = field(default_factory=list)
    session_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    last_activity_at: datetime = field(default_factory=utc_now)
    
    @classmethod
    def create(cls, user_id: UUID) -> "SearchSession":
        """검색 세션 생성"""
        return cls(user_id=user_id)
    
    def add_query(self, query: SearchQuery) -> None:
        """쿼리 추가"""
        self.queries.append(query)
        self.last_activity_at = utc_now()
    
    def add_answer(self, answer: Answer) -> None:
        """답변 추가"""
        self.answers.append(answer)
        self.last_activity_at = utc_now()
    
    def get_query_count(self) -> int:
        """쿼리 수 반환"""
        return len(self.queries)
    
    def get_latest_query(self) -> Optional[SearchQuery]:
        """최신 쿼리 반환"""
        return self.queries[-1] if self.queries else None
    
    def is_active(self, timeout_minutes: int = 30) -> bool:
        """세션 활성 상태 확인"""
        from datetime import timedelta
        timeout = timedelta(minutes=timeout_minutes)
        return (utc_now() - self.last_activity_at) < timeout
