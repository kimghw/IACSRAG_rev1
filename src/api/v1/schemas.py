"""
API v1 스키마 정의
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime


class SearchRequest(BaseModel):
    """검색 요청 스키마"""
    query: str = Field(..., description="검색 질의", min_length=1, max_length=1000)
    limit: int = Field(default=10, description="검색 결과 수", ge=1, le=100)
    threshold: float = Field(default=0.7, description="유사도 임계값", ge=0.0, le=1.0)
    filters: Optional[Dict[str, Any]] = Field(default=None, description="검색 필터")
    search_type: str = Field(default="hybrid", description="검색 타입 (vector, keyword, hybrid)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Python 프로그래밍 기초",
                "limit": 10,
                "threshold": 0.7,
                "filters": {
                    "source": "python_guide.pdf",
                    "page": {"gte": 1, "lte": 10}
                },
                "search_type": "hybrid"
            }
        }
    )


class SearchResultItem(BaseModel):
    """검색 결과 항목 스키마"""
    chunk_id: UUID = Field(..., description="청크 ID")
    document_id: UUID = Field(..., description="문서 ID")
    content: str = Field(..., description="청크 내용")
    score: float = Field(..., description="유사도 점수", ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(..., description="메타데이터")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "chunk_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_id": "550e8400-e29b-41d4-a716-446655440001",
                "content": "Python은 간단하고 읽기 쉬운 프로그래밍 언어입니다.",
                "score": 0.95,
                "metadata": {
                    "source": "python_guide.pdf",
                    "page": 1,
                    "chunk_index": 0,
                    "created_at": "2024-01-01T00:00:00Z",
                    "author": "John Doe"
                }
            }
        }
    )


class SearchResponse(BaseModel):
    """검색 응답 스키마"""
    query: str = Field(..., description="검색 질의")
    results: List[SearchResultItem] = Field(..., description="검색 결과 목록")
    total_count: int = Field(..., description="총 결과 수")
    search_time_ms: float = Field(..., description="검색 소요 시간 (밀리초)")
    search_type: str = Field(..., description="사용된 검색 타입")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Python 프로그래밍 기초",
                "results": [
                    {
                        "chunk_id": "550e8400-e29b-41d4-a716-446655440000",
                        "document_id": "550e8400-e29b-41d4-a716-446655440001",
                        "content": "Python은 간단하고 읽기 쉬운 프로그래밍 언어입니다.",
                        "score": 0.95,
                        "metadata": {
                            "source": "python_guide.pdf",
                            "page": 1,
                            "chunk_index": 0,
                            "created_at": "2024-01-01T00:00:00Z"
                        }
                    }
                ],
                "total_count": 1,
                "search_time_ms": 125.5,
                "search_type": "hybrid"
            }
        }
    )


class AnswerRequest(BaseModel):
    """답변 생성 요청 스키마"""
    question: str = Field(..., description="질문", min_length=1, max_length=1000)
    context_limit: int = Field(default=5, description="컨텍스트로 사용할 검색 결과 수", ge=1, le=20)
    search_filters: Optional[Dict[str, Any]] = Field(default=None, description="검색 필터")
    temperature: float = Field(default=0.7, description="답변 생성 온도", ge=0.0, le=2.0)
    max_tokens: int = Field(default=500, description="최대 토큰 수", ge=50, le=2000)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "Python에서 리스트와 튜플의 차이점은 무엇인가요?",
                "context_limit": 5,
                "search_filters": {
                    "source": "python_guide.pdf"
                },
                "temperature": 0.7,
                "max_tokens": 500
            }
        }
    )


class AnswerResponse(BaseModel):
    """답변 생성 응답 스키마"""
    question: str = Field(..., description="질문")
    answer: str = Field(..., description="생성된 답변")
    sources: List[SearchResultItem] = Field(..., description="참조된 소스 목록")
    confidence: float = Field(..., description="답변 신뢰도", ge=0.0, le=1.0)
    generation_time_ms: float = Field(..., description="답변 생성 소요 시간 (밀리초)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "Python에서 리스트와 튜플의 차이점은 무엇인가요?",
                "answer": "Python에서 리스트와 튜플의 주요 차이점은 다음과 같습니다:\n\n1. **가변성**: 리스트는 가변(mutable)이고 튜플은 불변(immutable)입니다.\n2. **성능**: 튜플이 리스트보다 메모리 효율적이고 빠릅니다.\n3. **사용 목적**: 리스트는 동적 데이터에, 튜플은 고정 데이터에 적합합니다.",
                "sources": [
                    {
                        "chunk_id": "550e8400-e29b-41d4-a716-446655440000",
                        "document_id": "550e8400-e29b-41d4-a716-446655440001",
                        "content": "리스트는 가변 객체이고 튜플은 불변 객체입니다.",
                        "score": 0.92,
                        "metadata": {
                            "source": "python_guide.pdf",
                            "page": 15,
                            "chunk_index": 3
                        }
                    }
                ],
                "confidence": 0.85,
                "generation_time_ms": 1250.0
            }
        }
    )


class ChunkDetailRequest(BaseModel):
    """청크 상세 조회 요청 스키마"""
    chunk_id: UUID = Field(..., description="청크 ID")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "chunk_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )


class DocumentChunksRequest(BaseModel):
    """문서별 청크 조회 요청 스키마"""
    document_id: UUID = Field(..., description="문서 ID")
    page: int = Field(default=1, description="페이지 번호", ge=1)
    size: int = Field(default=20, description="페이지 크기", ge=1, le=100)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440001",
                "page": 1,
                "size": 20
            }
        }
    )


class DocumentChunksResponse(BaseModel):
    """문서별 청크 조회 응답 스키마"""
    document_id: UUID = Field(..., description="문서 ID")
    chunks: List[SearchResultItem] = Field(..., description="청크 목록")
    total_count: int = Field(..., description="총 청크 수")
    page: int = Field(..., description="현재 페이지")
    size: int = Field(..., description="페이지 크기")
    total_pages: int = Field(..., description="총 페이지 수")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440001",
                "chunks": [
                    {
                        "chunk_id": "550e8400-e29b-41d4-a716-446655440000",
                        "document_id": "550e8400-e29b-41d4-a716-446655440001",
                        "content": "Python은 간단하고 읽기 쉬운 프로그래밍 언어입니다.",
                        "score": 1.0,
                        "metadata": {
                            "source": "python_guide.pdf",
                            "page": 1,
                            "chunk_index": 0
                        }
                    }
                ],
                "total_count": 50,
                "page": 1,
                "size": 20,
                "total_pages": 3
            }
        }
    )


class HealthCheckResponse(BaseModel):
    """헬스체크 응답 스키마"""
    status: str = Field(..., description="서비스 상태")
    timestamp: datetime = Field(..., description="체크 시간")
    version: str = Field(..., description="서비스 버전")
    components: Dict[str, Dict[str, Any]] = Field(..., description="컴포넌트 상태")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T12:00:00Z",
                "version": "1.0.0",
                "components": {
                    "vector_db": {
                        "status": "healthy",
                        "response_time_ms": 15.2
                    },
                    "llm_service": {
                        "status": "healthy",
                        "response_time_ms": 250.0
                    }
                }
            }
        }
    )


class ErrorResponse(BaseModel):
    """에러 응답 스키마"""
    error: str = Field(..., description="에러 타입")
    message: str = Field(..., description="에러 메시지")
    details: Optional[Dict[str, Any]] = Field(default=None, description="에러 상세 정보")
    timestamp: datetime = Field(..., description="에러 발생 시간")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "ValidationError",
                "message": "검색 질의는 필수입니다.",
                "details": {
                    "field": "query",
                    "value": ""
                },
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
    )
