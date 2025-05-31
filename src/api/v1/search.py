"""
Search API 엔드포인트
"""

import time
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from src.api.v1.schemas import (
    SearchRequest, SearchResponse, SearchResultItem,
    AnswerRequest, AnswerResponse,
    ChunkDetailRequest, DocumentChunksRequest, DocumentChunksResponse,
    HealthCheckResponse, ErrorResponse
)
from src.modules.search.application.use_cases.search_documents import SearchDocumentsUseCase
from src.modules.search.application.use_cases.generate_answer import GenerateAnswerUseCase
from src.modules.search.infrastructure.vector_db import VectorDatabase
from src.modules.search.domain.entities import SearchResult
from src.core.exceptions import SearchError, ValidationError
from src.core.logging import get_logger
from src.core.dependencies import get_vector_database, get_search_use_case, get_answer_use_case
from datetime import datetime
import math

logger = get_logger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


def convert_search_result_to_item(result: SearchResult) -> SearchResultItem:
    """SearchResult를 SearchResultItem으로 변환"""
    return SearchResultItem(
        chunk_id=result.chunk_id,
        document_id=result.document_id,
        content=result.content,
        score=result.score,
        metadata=result.metadata
    )


@router.post("/", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    search_use_case: SearchDocumentsUseCase = Depends(get_search_use_case)
) -> SearchResponse:
    """
    문서 검색 API
    
    - **query**: 검색 질의 (필수)
    - **limit**: 검색 결과 수 (기본값: 10, 최대: 100)
    - **threshold**: 유사도 임계값 (기본값: 0.7)
    - **filters**: 검색 필터 (선택사항)
    - **search_type**: 검색 타입 (vector, keyword, hybrid)
    """
    try:
        start_time = time.time()
        logger.info(f"Search request: query='{request.query}', type={request.search_type}")
        
        # 검색 실행
        search_results = await search_use_case.execute(
            query=request.query,
            limit=request.limit,
            threshold=request.threshold,
            filters=request.filters,
            search_type=request.search_type
        )
        
        # 응답 변환
        result_items = [convert_search_result_to_item(result) for result in search_results]
        search_time_ms = (time.time() - start_time) * 1000
        
        response = SearchResponse(
            query=request.query,
            results=result_items,
            total_count=len(result_items),
            search_time_ms=search_time_ms,
            search_type=request.search_type
        )
        
        logger.info(f"Search completed: {len(result_items)} results in {search_time_ms:.2f}ms")
        return response
        
    except ValidationError as e:
        logger.error(f"Validation error in search: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except SearchError as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in search: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/answer", response_model=AnswerResponse)
async def generate_answer(
    request: AnswerRequest,
    answer_use_case: GenerateAnswerUseCase = Depends(get_answer_use_case)
) -> AnswerResponse:
    """
    질문 답변 생성 API
    
    - **question**: 질문 (필수)
    - **context_limit**: 컨텍스트로 사용할 검색 결과 수 (기본값: 5)
    - **search_filters**: 검색 필터 (선택사항)
    - **temperature**: 답변 생성 온도 (기본값: 0.7)
    - **max_tokens**: 최대 토큰 수 (기본값: 500)
    """
    try:
        start_time = time.time()
        logger.info(f"Answer generation request: question='{request.question[:100]}...'")
        
        # 답변 생성 실행
        answer_result = await answer_use_case.execute(
            question=request.question,
            context_limit=request.context_limit,
            search_filters=request.search_filters,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # 응답 변환
        source_items = [convert_search_result_to_item(source) for source in answer_result.sources]
        generation_time_ms = (time.time() - start_time) * 1000
        
        response = AnswerResponse(
            question=request.question,
            answer=answer_result.answer,
            sources=source_items,
            confidence=answer_result.confidence,
            generation_time_ms=generation_time_ms
        )
        
        logger.info(f"Answer generated in {generation_time_ms:.2f}ms, confidence: {answer_result.confidence}")
        return response
        
    except ValidationError as e:
        logger.error(f"Validation error in answer generation: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except SearchError as e:
        logger.error(f"Search error in answer generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in answer generation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/chunks/{chunk_id}", response_model=SearchResultItem)
async def get_chunk_detail(
    chunk_id: UUID,
    vector_db: VectorDatabase = Depends(get_vector_database)
) -> SearchResultItem:
    """
    청크 상세 조회 API
    
    - **chunk_id**: 조회할 청크 ID
    """
    try:
        logger.info(f"Chunk detail request: chunk_id={chunk_id}")
        
        # 청크 조회
        chunk_result = await vector_db.get_chunk_by_id(chunk_id)
        
        if chunk_result is None:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        # 응답 변환
        response = convert_search_result_to_item(chunk_result)
        
        logger.info(f"Chunk detail retrieved: chunk_id={chunk_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chunk detail: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/{document_id}/chunks", response_model=DocumentChunksResponse)
async def get_document_chunks(
    document_id: UUID,
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    size: int = Query(default=20, ge=1, le=100, description="페이지 크기"),
    vector_db: VectorDatabase = Depends(get_vector_database)
) -> DocumentChunksResponse:
    """
    문서별 청크 조회 API
    
    - **document_id**: 문서 ID
    - **page**: 페이지 번호 (기본값: 1)
    - **size**: 페이지 크기 (기본값: 20, 최대: 100)
    """
    try:
        logger.info(f"Document chunks request: document_id={document_id}, page={page}, size={size}")
        
        # 문서의 모든 청크 조회
        all_chunks = await vector_db.get_chunks_by_document(document_id)
        
        if not all_chunks:
            raise HTTPException(status_code=404, detail="Document not found or has no chunks")
        
        # 페이지네이션 적용
        total_count = len(all_chunks)
        total_pages = math.ceil(total_count / size)
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        page_chunks = all_chunks[start_idx:end_idx]
        
        # 응답 변환
        chunk_items = [convert_search_result_to_item(chunk) for chunk in page_chunks]
        
        response = DocumentChunksResponse(
            document_id=document_id,
            chunks=chunk_items,
            total_count=total_count,
            page=page,
            size=size,
            total_pages=total_pages
        )
        
        logger.info(f"Document chunks retrieved: {len(chunk_items)} chunks on page {page}/{total_pages}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in document chunks: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    vector_db: VectorDatabase = Depends(get_vector_database)
) -> HealthCheckResponse:
    """
    검색 서비스 헬스체크 API
    
    벡터 데이터베이스와 LLM 서비스의 상태를 확인합니다.
    """
    try:
        start_time = time.time()
        
        # 벡터 DB 상태 확인
        vector_db_start = time.time()
        vector_db_health = await vector_db.check_collection_health()
        vector_db_time = (time.time() - vector_db_start) * 1000
        
        # 전체 상태 결정
        overall_status = "healthy"
        if vector_db_health.get("health") != "healthy":
            overall_status = "unhealthy"
        
        # TODO: LLM 서비스 상태 확인 추가
        llm_status = {
            "status": "healthy",
            "response_time_ms": 0.0  # 임시값
        }
        
        response = HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version="1.0.0",  # TODO: 실제 버전 정보로 교체
            components={
                "vector_db": {
                    "status": vector_db_health.get("health", "unknown"),
                    "response_time_ms": vector_db_time,
                    "details": vector_db_health
                },
                "llm_service": llm_status
            }
        )
        
        total_time = (time.time() - start_time) * 1000
        logger.info(f"Health check completed in {total_time:.2f}ms, status: {overall_status}")
        
        return response
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            components={
                "vector_db": {
                    "status": "unhealthy",
                    "response_time_ms": 0.0,
                    "error": str(e)
                },
                "llm_service": {
                    "status": "unknown",
                    "response_time_ms": 0.0
                }
            }
        )
