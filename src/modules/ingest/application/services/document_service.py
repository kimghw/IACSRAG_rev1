"""
문서 관리 서비스

문서 업로드, 저장, 조회 등의 비즈니스 로직을 담당하는 서비스
"""

import os
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from src.core.logging import get_logger
from src.core.exceptions import (
    ValidationError, 
    BusinessRuleViolationError,
    EntityNotFoundError
)
from src.modules.ingest.domain.entities import (
    Document, 
    DocumentMetadata, 
    DocumentStatus, 
    DocumentType
)
from src.modules.ingest.infrastructure.repositories.document_repository import DocumentRepository
from src.modules.ingest.application.ports.event_publisher import (
    EventPublisherPort, 
    FileStoragePort
)


logger = get_logger(__name__)


class DocumentService:
    """
    문서 관리 서비스
    
    문서의 생명주기 관리와 비즈니스 규칙을 담당합니다.
    """
    
    def __init__(
        self,
        document_repository: DocumentRepository,
        event_publisher: EventPublisherPort,
        file_storage: FileStoragePort,
        max_file_size: int = 50 * 1024 * 1024,  # 50MB
        allowed_extensions: List[str] = None
    ):
        self.document_repository = document_repository
        self.event_publisher = event_publisher
        self.file_storage = file_storage
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions or [
            '.pdf', '.docx', '.doc', '.txt', '.eml', '.msg'
        ]
    
    async def upload_document(
        self,
        user_id: UUID,
        filename: str,
        file_content: bytes,
        content_type: str = None,
        tags: List[str] = None,
        source: str = None
    ) -> Document:
        """
        문서 업로드 처리
        
        Args:
            user_id: 사용자 ID
            filename: 파일명
            file_content: 파일 내용
            content_type: 콘텐츠 타입
            tags: 태그 목록
            source: 문서 출처
            
        Returns:
            Document: 생성된 문서 엔티티
            
        Raises:
            ValidationError: 파일 검증 실패
            BusinessRuleViolationError: 비즈니스 규칙 위반
        """
        try:
            # 1. 파일 검증
            await self._validate_file(filename, file_content, content_type)
            
            # 2. 문서 유형 결정
            document_type = self._determine_document_type(filename, content_type)
            
            # 3. 파일 저장
            file_path = await self.file_storage.save_file(
                file_content, filename, user_id, content_type
            )
            
            # 4. 메타데이터 생성
            metadata = DocumentMetadata(
                file_size=len(file_content),
                mime_type=content_type or self._get_mime_type(filename),
                encoding='utf-8',  # 기본값, 실제로는 감지 로직 필요
                language='ko',     # 기본값, 실제로는 감지 로직 필요
                page_count=None,   # 처리 단계에서 설정
                word_count=None    # 처리 단계에서 설정
            )
            
            # 5. 문서 엔티티 생성
            document = Document.create(
                user_id=user_id,
                filename=filename,
                original_filename=filename,
                file_path=file_path,
                document_type=document_type,
                metadata=metadata,
                tags=tags or [],
                source=source
            )
            
            # 6. 데이터베이스 저장
            saved_document = await self.document_repository.save(document)
            
            # 7. 이벤트 발행
            await self.event_publisher.publish_document_uploaded(
                document_id=saved_document.id,
                user_id=user_id,
                filename=filename,
                document_type=document_type.value,
                file_path=file_path,
                metadata=metadata.to_dict()
            )
            
            logger.info(
                f"Document uploaded successfully",
                extra={
                    "document_id": str(saved_document.id),
                    "user_id": str(user_id),
                    "filename": filename,
                    "file_size": len(file_content)
                }
            )
            
            return saved_document
            
        except Exception as e:
            logger.error(
                f"Failed to upload document: {e}",
                extra={
                    "user_id": str(user_id),
                    "filename": filename,
                    "error": str(e)
                }
            )
            raise
    
    async def get_document(self, document_id: UUID) -> Optional[Document]:
        """
        문서 조회
        
        Args:
            document_id: 문서 ID
            
        Returns:
            Optional[Document]: 문서 엔티티 또는 None
        """
        return await self.document_repository.find_by_id(document_id)
    
    async def get_document_by_id(self, document_id: UUID) -> Optional[Document]:
        """
        문서 ID로 조회 (get_document와 동일한 기능)
        
        Args:
            document_id: 문서 ID
            
        Returns:
            Optional[Document]: 문서 엔티티 또는 None
        """
        return await self.get_document(document_id)
    
    async def get_user_documents(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
        status: Optional[DocumentStatus] = None,
        document_type: Optional[DocumentType] = None
    ) -> List[Document]:
        """
        사용자 문서 목록 조회
        
        Args:
            user_id: 사용자 ID
            limit: 조회 제한 수
            offset: 조회 시작 위치
            status: 문서 상태 필터
            document_type: 문서 유형 필터
            
        Returns:
            List[Document]: 문서 목록
        """
        return await self.document_repository.find_by_user_id(
            user_id, limit, offset, status, document_type
        )
    
    async def update_document_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_message: str = None
    ) -> bool:
        """
        문서 상태 업데이트
        
        Args:
            document_id: 문서 ID
            status: 새로운 상태
            error_message: 에러 메시지 (실패 시)
            
        Returns:
            bool: 업데이트 성공 여부
        """
        success = await self.document_repository.update_status(
            document_id, status, error_message
        )
        
        if success:
            logger.info(
                f"Document status updated",
                extra={
                    "document_id": str(document_id),
                    "status": status.value,
                    "error_message": error_message
                }
            )
        
        return success
    
    async def delete_document(self, document_id: UUID) -> bool:
        """
        문서 삭제
        
        Args:
            document_id: 문서 ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        # 1. 문서 조회
        document = await self.document_repository.find_by_id(document_id)
        if not document:
            return False
        
        try:
            # 2. 파일 삭제
            await self.file_storage.delete_file(document.file_path)
            
            # 3. 데이터베이스에서 삭제
            success = await self.document_repository.delete_by_id(document_id)
            
            if success:
                logger.info(
                    f"Document deleted successfully",
                    extra={
                        "document_id": str(document_id),
                        "filename": document.filename
                    }
                )
            
            return success
            
        except Exception as e:
            logger.error(
                f"Failed to delete document: {e}",
                extra={
                    "document_id": str(document_id),
                    "error": str(e)
                }
            )
            return False
    
    async def search_documents(
        self,
        user_id: UUID,
        filename_pattern: str,
        limit: int = 50
    ) -> List[Document]:
        """
        파일명으로 문서 검색
        
        Args:
            user_id: 사용자 ID
            filename_pattern: 파일명 패턴
            limit: 조회 제한 수
            
        Returns:
            List[Document]: 검색된 문서 목록
        """
        return await self.document_repository.search_by_filename(
            user_id, filename_pattern, limit
        )
    
    async def get_processing_statistics(
        self,
        user_id: Optional[UUID] = None
    ) -> Dict[str, int]:
        """
        문서 처리 통계 조회
        
        Args:
            user_id: 사용자 ID (전체 통계 시 None)
            
        Returns:
            Dict[str, int]: 상태별 문서 수
        """
        return await self.document_repository.get_processing_statistics(user_id)
    
    async def list_documents(
        self,
        filters: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> tuple[List[Document], int]:
        """
        문서 목록 조회 (필터링 및 정렬 지원)
        
        Args:
            filters: 필터 조건
            limit: 조회 제한 수
            offset: 조회 시작 위치
            sort_by: 정렬 기준 필드
            sort_order: 정렬 순서 (asc/desc)
            
        Returns:
            tuple[List[Document], int]: (문서 목록, 전체 개수)
        """
        return await self.document_repository.find_with_filters(
            filters=filters,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
    
    async def get_document_counts_by_status(self, user_id: UUID) -> Dict[str, int]:
        """
        사용자의 문서 상태별 개수 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            Dict[str, int]: 상태별 문서 개수
        """
        return await self.document_repository.count_by_status(user_id)
    
    async def _validate_file(
        self,
        filename: str,
        file_content: bytes,
        content_type: str = None
    ) -> None:
        """
        파일 검증
        
        Args:
            filename: 파일명
            file_content: 파일 내용
            content_type: 콘텐츠 타입
            
        Raises:
            ValidationError: 검증 실패
        """
        # 파일 크기 검증 (바이트 단위로 직접 검증)
        if len(file_content) > self.max_file_size:
            raise ValidationError(
                f"File size exceeds maximum allowed size: {self.max_file_size} bytes"
            )
        
        # 파일 확장자 검증
        extension = os.path.splitext(filename)[1].lower()
        if extension not in self.allowed_extensions:
            raise ValidationError(
                f"File type not allowed. Allowed types: {self.allowed_extensions}"
            )
        
        # 파일 내용 검증 (빈 파일 체크)
        if len(file_content) == 0:
            raise ValidationError("Empty file is not allowed")
    
    def _determine_document_type(
        self,
        filename: str,
        content_type: str = None
    ) -> DocumentType:
        """
        파일명과 콘텐츠 타입으로 문서 유형 결정
        
        Args:
            filename: 파일명
            content_type: 콘텐츠 타입
            
        Returns:
            DocumentType: 문서 유형
        """
        extension = os.path.splitext(filename)[1].lower()
        
        type_mapping = {
            '.pdf': DocumentType.PDF,
            '.docx': DocumentType.DOCX,
            '.doc': DocumentType.DOCX,  # DOC도 DOCX로 처리
            '.txt': DocumentType.TXT,
            '.eml': DocumentType.EMAIL,
            '.msg': DocumentType.EMAIL
        }
        
        return type_mapping.get(extension, DocumentType.HTML)  # OTHER 대신 HTML 사용
    
    def _get_mime_type(self, filename: str) -> str:
        """
        파일명으로 MIME 타입 추정
        
        Args:
            filename: 파일명
            
        Returns:
            str: MIME 타입
        """
        extension = os.path.splitext(filename)[1].lower()
        
        mime_mapping = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.txt': 'text/plain',
            '.eml': 'message/rfc822',
            '.msg': 'application/vnd.ms-outlook'
        }
        
        return mime_mapping.get(extension, 'application/octet-stream')
