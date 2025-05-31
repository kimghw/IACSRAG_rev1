"""
UC-03: 문서 상태 조회 유즈케이스

사용자가 업로드한 문서의 처리 상태를 조회하는 비즈니스 로직을 담당합니다.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime

from src.core.logging import get_logger
from src.core.exceptions import (
    ValidationError,
    NotFoundError,
    UnauthorizedError
)
from src.modules.ingest.domain.entities import Document, DocumentStatus
from src.modules.ingest.application.services.document_service import DocumentService


logger = get_logger(__name__)


@dataclass
class DocumentStatusQuery:
    """문서 상태 조회 쿼리"""
    user_id: UUID
    document_id: Optional[UUID] = None
    status_filter: Optional[DocumentStatus] = None
    limit: int = 50
    offset: int = 0
    include_metadata: bool = False


@dataclass
class DocumentStatusInfo:
    """문서 상태 정보"""
    id: UUID
    filename: str
    original_filename: str
    document_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    tags: List[str] = None
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class DocumentStatusResult:
    """문서 상태 조회 결과"""
    documents: List[DocumentStatusInfo]
    total_count: int
    has_more: bool


class GetDocumentStatusUseCase:
    """
    UC-03: 문서 상태 조회 유즈케이스
    
    사용자가 업로드한 문서들의 처리 상태를 조회합니다.
    단일 문서 조회와 목록 조회를 모두 지원합니다.
    """
    
    def __init__(self, document_service: DocumentService):
        self.document_service = document_service
    
    async def execute(self, query: DocumentStatusQuery) -> DocumentStatusResult:
        """
        문서 상태 조회 실행
        
        Args:
            query: 문서 상태 조회 쿼리
            
        Returns:
            DocumentStatusResult: 조회 결과
            
        Raises:
            ValidationError: 쿼리 검증 오류
            NotFoundError: 문서를 찾을 수 없음
            UnauthorizedError: 권한 없음
        """
        try:
            logger.info(
                "Starting document status query",
                extra={
                    "user_id": str(query.user_id),
                    "document_id": str(query.document_id) if query.document_id else None,
                    "status_filter": query.status_filter.value if query.status_filter else None,
                    "limit": query.limit,
                    "offset": query.offset
                }
            )
            
            # 1. 쿼리 검증
            self._validate_query(query)
            
            # 2. 문서 조회
            if query.document_id:
                # 단일 문서 조회
                result = await self._get_single_document(query)
            else:
                # 문서 목록 조회
                result = await self._get_document_list(query)
            
            logger.info(
                "Document status query completed",
                extra={
                    "user_id": str(query.user_id),
                    "document_count": len(result.documents),
                    "total_count": result.total_count
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Failed to query document status: {e}",
                extra={
                    "user_id": str(query.user_id),
                    "document_id": str(query.document_id) if query.document_id else None,
                    "error": str(e)
                }
            )
            raise
    
    def _validate_query(self, query: DocumentStatusQuery) -> None:
        """
        쿼리 검증
        
        Args:
            query: 문서 상태 조회 쿼리
            
        Raises:
            ValidationError: 검증 실패
        """
        if query.limit <= 0 or query.limit > 1000:
            raise ValidationError(
                "Limit must be between 1 and 1000",
                details={"limit": query.limit}
            )
        
        if query.offset < 0:
            raise ValidationError(
                "Offset must be non-negative",
                details={"offset": query.offset}
            )
    
    async def _get_single_document(self, query: DocumentStatusQuery) -> DocumentStatusResult:
        """
        단일 문서 상태 조회
        
        Args:
            query: 문서 상태 조회 쿼리
            
        Returns:
            DocumentStatusResult: 조회 결과
            
        Raises:
            NotFoundError: 문서를 찾을 수 없음
            UnauthorizedError: 권한 없음
        """
        document = await self.document_service.get_document_by_id(query.document_id)
        
        if not document:
            raise NotFoundError(
                f"Document not found: {query.document_id}",
                details={"document_id": str(query.document_id)}
            )
        
        # 권한 확인 - 문서 소유자만 조회 가능
        if document.user_id != query.user_id:
            raise UnauthorizedError(
                "Access denied to document",
                details={
                    "document_id": str(query.document_id),
                    "user_id": str(query.user_id)
                }
            )
        
        document_info = self._convert_to_status_info(document, query.include_metadata)
        
        return DocumentStatusResult(
            documents=[document_info],
            total_count=1,
            has_more=False
        )
    
    async def _get_document_list(self, query: DocumentStatusQuery) -> DocumentStatusResult:
        """
        문서 목록 조회
        
        Args:
            query: 문서 상태 조회 쿼리
            
        Returns:
            DocumentStatusResult: 조회 결과
        """
        # 필터 조건 구성
        filters = {"user_id": query.user_id}
        if query.status_filter:
            filters["status"] = query.status_filter
        
        # 문서 목록 조회
        documents, total_count = await self.document_service.list_documents(
            filters=filters,
            limit=query.limit,
            offset=query.offset,
            sort_by="created_at",
            sort_order="desc"
        )
        
        # 결과 변환
        document_infos = [
            self._convert_to_status_info(doc, query.include_metadata)
            for doc in documents
        ]
        
        has_more = (query.offset + len(documents)) < total_count
        
        return DocumentStatusResult(
            documents=document_infos,
            total_count=total_count,
            has_more=has_more
        )
    
    def _convert_to_status_info(
        self,
        document: Document,
        include_metadata: bool = False
    ) -> DocumentStatusInfo:
        """
        Document 엔티티를 DocumentStatusInfo로 변환
        
        Args:
            document: 문서 엔티티
            include_metadata: 메타데이터 포함 여부
            
        Returns:
            DocumentStatusInfo: 문서 상태 정보
        """
        return DocumentStatusInfo(
            id=document.id,
            filename=document.filename,
            original_filename=document.original_filename,
            document_type=document.document_type.value,
            status=document.status.value,
            created_at=document.created_at,
            updated_at=document.updated_at,
            processed_at=document.processed_at,
            error_message=document.error_message,
            tags=document.tags.copy(),
            source=document.source,
            metadata=document.metadata.to_dict() if include_metadata else None
        )


class DocumentStatusSummaryUseCase:
    """
    문서 상태 요약 조회 유즈케이스
    
    사용자의 문서 처리 상태별 통계를 제공합니다.
    """
    
    def __init__(self, document_service: DocumentService):
        self.document_service = document_service
    
    async def execute(self, user_id: UUID) -> Dict[str, Any]:
        """
        문서 상태 요약 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            Dict[str, Any]: 상태별 통계
        """
        try:
            logger.info(
                "Getting document status summary",
                extra={"user_id": str(user_id)}
            )
            
            # 상태별 문서 수 조회
            status_counts = await self.document_service.get_document_counts_by_status(user_id)
            
            # 최근 문서 조회 (최근 10개)
            recent_documents, _ = await self.document_service.list_documents(
                filters={"user_id": user_id},
                limit=10,
                offset=0,
                sort_by="created_at",
                sort_order="desc"
            )
            
            # 처리 중인 문서 조회
            processing_documents, _ = await self.document_service.list_documents(
                filters={
                    "user_id": user_id,
                    "status": {"$in": [
                        DocumentStatus.PARSING.value,
                        DocumentStatus.PROCESSING.value
                    ]}
                },
                limit=50,
                offset=0
            )
            
            # 실패한 문서 조회
            failed_documents, _ = await self.document_service.list_documents(
                filters={
                    "user_id": user_id,
                    "status": DocumentStatus.FAILED.value
                },
                limit=20,
                offset=0,
                sort_by="updated_at",
                sort_order="desc"
            )
            
            summary = {
                "total_documents": sum(status_counts.values()),
                "status_counts": status_counts,
                "recent_documents": [
                    {
                        "id": str(doc.id),
                        "filename": doc.filename,
                        "status": doc.status.value,
                        "created_at": doc.created_at.isoformat(),
                        "document_type": doc.document_type.value
                    }
                    for doc in recent_documents
                ],
                "processing_documents": [
                    {
                        "id": str(doc.id),
                        "filename": doc.filename,
                        "status": doc.status.value,
                        "updated_at": doc.updated_at.isoformat()
                    }
                    for doc in processing_documents
                ],
                "failed_documents": [
                    {
                        "id": str(doc.id),
                        "filename": doc.filename,
                        "error_message": doc.error_message,
                        "updated_at": doc.updated_at.isoformat()
                    }
                    for doc in failed_documents
                ]
            }
            
            logger.info(
                "Document status summary completed",
                extra={
                    "user_id": str(user_id),
                    "total_documents": summary["total_documents"],
                    "processing_count": len(processing_documents),
                    "failed_count": len(failed_documents)
                }
            )
            
            return summary
            
        except Exception as e:
            logger.error(
                f"Failed to get document status summary: {e}",
                extra={
                    "user_id": str(user_id),
                    "error": str(e)
                }
            )
            raise


class DocumentProgressTracker:
    """
    문서 처리 진행률 추적기
    
    실시간으로 문서 처리 진행률을 추적합니다.
    """
    
    def __init__(self, document_service: DocumentService):
        self.document_service = document_service
    
    async def get_processing_progress(self, document_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        문서 처리 진행률 조회
        
        Args:
            document_id: 문서 ID
            user_id: 사용자 ID
            
        Returns:
            Dict[str, Any]: 진행률 정보
            
        Raises:
            NotFoundError: 문서를 찾을 수 없음
            UnauthorizedError: 권한 없음
        """
        document = await self.document_service.get_document_by_id(document_id)
        
        if not document:
            raise NotFoundError(
                f"Document not found: {document_id}",
                details={"document_id": str(document_id)}
            )
        
        if document.user_id != user_id:
            raise UnauthorizedError(
                "Access denied to document",
                details={
                    "document_id": str(document_id),
                    "user_id": str(user_id)
                }
            )
        
        # 상태별 진행률 계산
        progress_map = {
            DocumentStatus.UPLOADED: 10,
            DocumentStatus.PARSING: 30,
            DocumentStatus.PARSED: 50,
            DocumentStatus.PROCESSING: 80,
            DocumentStatus.PROCESSED: 100,
            DocumentStatus.FAILED: 0
        }
        
        progress_percentage = progress_map.get(document.status, 0)
        
        # 상태별 메시지
        status_messages = {
            DocumentStatus.UPLOADED: "문서가 업로드되었습니다.",
            DocumentStatus.PARSING: "문서를 파싱하고 있습니다.",
            DocumentStatus.PARSED: "문서 파싱이 완료되었습니다.",
            DocumentStatus.PROCESSING: "문서를 처리하고 있습니다.",
            DocumentStatus.PROCESSED: "문서 처리가 완료되었습니다.",
            DocumentStatus.FAILED: f"문서 처리에 실패했습니다: {document.error_message}"
        }
        
        return {
            "document_id": str(document_id),
            "filename": document.filename,
            "status": document.status.value,
            "progress_percentage": progress_percentage,
            "status_message": status_messages.get(document.status, "알 수 없는 상태"),
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat(),
            "processed_at": document.processed_at.isoformat() if document.processed_at else None,
            "is_completed": document.status == DocumentStatus.PROCESSED,
            "is_failed": document.status == DocumentStatus.FAILED,
            "error_message": document.error_message
        }
