"""
UC-02: 파일 업로드 유즈케이스

사용자가 업로드한 파일을 검증하고 저장하는 비즈니스 로직을 담당합니다.
"""

import os
import mimetypes
from typing import List, Optional, Dict, Any
from uuid import UUID
from dataclasses import dataclass
from pathlib import Path

from src.core.logging import get_logger
from src.core.exceptions import (
    ValidationError,
    BusinessRuleViolationError,
    DocumentProcessingError
)
from src.modules.ingest.domain.entities import (
    Document,
    DocumentMetadata,
    DocumentType,
    DocumentStatus
)
from src.modules.ingest.application.services.document_service import DocumentService
from src.modules.ingest.application.ports.event_publisher import (
    EventPublisherPort,
    FileStoragePort
)


logger = get_logger(__name__)


@dataclass
class FileUploadCommand:
    """파일 업로드 명령"""
    user_id: UUID
    filename: str
    file_content: bytes
    content_type: Optional[str] = None
    source: str = "upload"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class FileUploadResult:
    """파일 업로드 결과"""
    document: Document
    file_path: str
    metadata: Dict[str, Any]


class UploadFileUseCase:
    """
    UC-02: 파일 업로드 유즈케이스
    
    사용자가 업로드한 파일을 검증하고 저장소에 저장한 후,
    문서 엔티티를 생성하여 데이터베이스에 저장합니다.
    """
    
    def __init__(
        self,
        document_service: DocumentService,
        file_storage: FileStoragePort,
        event_publisher: EventPublisherPort,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        allowed_file_types: List[str] = None
    ):
        self.document_service = document_service
        self.file_storage = file_storage
        self.event_publisher = event_publisher
        self.max_file_size = max_file_size
        self.allowed_file_types = allowed_file_types or [
            '.pdf', '.docx', '.doc', '.txt', '.html', '.htm', '.md',
            '.pptx', '.ppt', '.xlsx', '.xls', '.csv'
        ]
    
    async def execute(self, command: FileUploadCommand) -> FileUploadResult:
        """
        파일 업로드 실행
        
        Args:
            command: 파일 업로드 명령
            
        Returns:
            FileUploadResult: 업로드 결과
            
        Raises:
            ValidationError: 파일 검증 오류
            BusinessRuleViolationError: 비즈니스 규칙 위반
            DocumentProcessingError: 문서 처리 오류
        """
        try:
            logger.info(
                "Starting file upload",
                extra={
                    "user_id": str(command.user_id),
                    "filename": command.filename,
                    "file_size": len(command.file_content),
                    "source": command.source
                }
            )
            
            # 1. 파일 검증
            self._validate_file(command)
            
            # 2. 파일 저장
            file_path = await self._save_file(command)
            
            # 3. 문서 엔티티 생성
            document = await self._create_document(command, file_path)
            
            # 4. 이벤트 발행
            await self._publish_file_uploaded_event(command, document, file_path)
            
            result = FileUploadResult(
                document=document,
                file_path=file_path,
                metadata=self._extract_file_metadata(command, file_path)
            )
            
            logger.info(
                "File upload completed successfully",
                extra={
                    "user_id": str(command.user_id),
                    "document_id": str(document.id),
                    "filename": command.filename,
                    "file_path": file_path
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Failed to upload file: {e}",
                extra={
                    "user_id": str(command.user_id),
                    "filename": command.filename,
                    "error": str(e)
                }
            )
            
            # 실패 시 정리 작업
            await self._cleanup_on_failure(command)
            
            if isinstance(e, (ValidationError, BusinessRuleViolationError)):
                raise
            else:
                raise DocumentProcessingError(
                    f"File upload failed: {e}",
                    details={
                        "user_id": str(command.user_id),
                        "filename": command.filename
                    }
                )
    
    def _validate_file(self, command: FileUploadCommand) -> None:
        """
        파일 검증
        
        Args:
            command: 파일 업로드 명령
            
        Raises:
            ValidationError: 검증 실패
            BusinessRuleViolationError: 비즈니스 규칙 위반
        """
        # 파일명 검증
        if not command.filename or not command.filename.strip():
            raise ValidationError(
                "Filename is required",
                details={"filename": command.filename}
            )
        
        # 파일 크기 검증
        file_size = len(command.file_content)
        if file_size == 0:
            raise ValidationError(
                "File is empty",
                details={"filename": command.filename}
            )
        
        if file_size > self.max_file_size:
            raise BusinessRuleViolationError(
                f"File size exceeds maximum allowed size ({self.max_file_size} bytes)",
                details={
                    "filename": command.filename,
                    "file_size": file_size,
                    "max_size": self.max_file_size
                }
            )
        
        # 파일 확장자 검증
        file_extension = self._get_file_extension(command.filename)
        if file_extension not in self.allowed_file_types:
            raise BusinessRuleViolationError(
                f"File type '{file_extension}' is not allowed",
                details={
                    "filename": command.filename,
                    "file_extension": file_extension,
                    "allowed_types": self.allowed_file_types
                }
            )
        
        # 파일 내용 기본 검증
        self._validate_file_content(command)
    
    def _validate_file_content(self, command: FileUploadCommand) -> None:
        """
        파일 내용 검증
        
        Args:
            command: 파일 업로드 명령
            
        Raises:
            ValidationError: 내용 검증 실패
        """
        file_extension = self._get_file_extension(command.filename)
        
        # PDF 파일 검증
        if file_extension == '.pdf':
            if not command.file_content.startswith(b'%PDF-'):
                raise ValidationError(
                    "Invalid PDF file format",
                    details={"filename": command.filename}
                )
        
        # ZIP 기반 파일 검증 (DOCX, PPTX, XLSX)
        elif file_extension in ['.docx', '.pptx', '.xlsx']:
            # ZIP 파일 시그니처 확인
            if not (command.file_content.startswith(b'PK\x03\x04') or 
                    command.file_content.startswith(b'PK\x05\x06') or
                    command.file_content.startswith(b'PK\x07\x08')):
                raise ValidationError(
                    f"Invalid {file_extension} file format",
                    details={"filename": command.filename}
                )
        
        # 텍스트 파일 검증
        elif file_extension in ['.txt', '.md', '.html', '.htm', '.csv']:
            try:
                # UTF-8 디코딩 시도
                command.file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    # CP949 디코딩 시도 (한국어 환경)
                    command.file_content.decode('cp949')
                except UnicodeDecodeError:
                    raise ValidationError(
                        "Text file encoding is not supported (UTF-8 or CP949 required)",
                        details={"filename": command.filename}
                    )
    
    def _get_file_extension(self, filename: str) -> str:
        """파일 확장자 추출"""
        return Path(filename).suffix.lower()
    
    def _detect_content_type(self, filename: str, file_content: bytes) -> str:
        """파일 MIME 타입 감지"""
        # 파일명 기반 MIME 타입 추측
        mime_type, _ = mimetypes.guess_type(filename)
        
        if mime_type:
            return mime_type
        
        # 파일 내용 기반 MIME 타입 감지
        if file_content.startswith(b'%PDF-'):
            return 'application/pdf'
        elif file_content.startswith(b'PK'):
            # ZIP 기반 파일들
            if filename.lower().endswith('.docx'):
                return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            elif filename.lower().endswith('.xlsx'):
                return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            elif filename.lower().endswith('.pptx'):
                return 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        
        # 기본값
        return 'application/octet-stream'
    
    async def _save_file(self, command: FileUploadCommand) -> str:
        """
        파일 저장
        
        Args:
            command: 파일 업로드 명령
            
        Returns:
            str: 저장된 파일 경로
        """
        content_type = command.content_type or self._detect_content_type(
            command.filename, command.file_content
        )
        
        file_path = await self.file_storage.save_file(
            file_content=command.file_content,
            filename=command.filename,
            user_id=command.user_id,
            content_type=content_type
        )
        
        return file_path
    
    async def _create_document(
        self,
        command: FileUploadCommand,
        file_path: str
    ) -> Document:
        """
        문서 엔티티 생성
        
        Args:
            command: 파일 업로드 명령
            file_path: 저장된 파일 경로
            
        Returns:
            Document: 생성된 문서 엔티티
        """
        # 문서 타입 결정
        document_type = self._determine_document_type(command.filename)
        
        # 콘텐츠 타입 결정
        content_type = command.content_type or self._detect_content_type(
            command.filename, command.file_content
        )
        
        return await self.document_service.upload_document(
            user_id=command.user_id,
            filename=command.filename,
            file_content=command.file_content,
            content_type=content_type,
            tags=command.tags,
            source=command.source
        )
    
    def _determine_document_type(self, filename: str) -> DocumentType:
        """파일명으로부터 문서 타입 결정"""
        extension = self._get_file_extension(filename)
        
        type_mapping = {
            '.pdf': DocumentType.PDF,
            '.docx': DocumentType.DOCX,
            '.doc': DocumentType.DOC,
            '.txt': DocumentType.TXT,
            '.md': DocumentType.TXT,
            '.html': DocumentType.HTML,
            '.htm': DocumentType.HTML,
            '.pptx': DocumentType.PPTX,
            '.ppt': DocumentType.PPT,
            '.xlsx': DocumentType.XLSX,
            '.xls': DocumentType.XLS,
            '.csv': DocumentType.CSV
        }
        
        return type_mapping.get(extension, DocumentType.TXT)
    
    def _extract_file_metadata(
        self,
        command: FileUploadCommand,
        file_path: str
    ) -> Dict[str, Any]:
        """파일 메타데이터 추출"""
        return {
            "original_filename": command.filename,
            "file_size": len(command.file_content),
            "content_type": command.content_type or self._detect_content_type(
                command.filename, command.file_content
            ),
            "file_extension": self._get_file_extension(command.filename),
            "source": command.source,
            "tags": command.tags,
            "file_path": file_path
        }
    
    async def _publish_file_uploaded_event(
        self,
        command: FileUploadCommand,
        document: Document,
        file_path: str
    ) -> None:
        """파일 업로드 완료 이벤트 발행"""
        try:
            await self.event_publisher.publish_document_uploaded(
                document_id=document.id,
                user_id=command.user_id,
                filename=command.filename,
                document_type=document.document_type.value,
                file_path=file_path,
                metadata=self._extract_file_metadata(command, file_path)
            )
        except Exception as e:
            logger.error(
                f"Failed to publish file uploaded event: {e}",
                extra={
                    "user_id": str(command.user_id),
                    "document_id": str(document.id),
                    "filename": command.filename,
                    "error": str(e)
                }
            )
            # 이벤트 발행 실패는 전체 프로세스를 중단하지 않음
    
    async def _cleanup_on_failure(self, command: FileUploadCommand) -> None:
        """실패 시 정리 작업"""
        try:
            # 저장된 파일이 있다면 삭제 시도
            # 실제 구현에서는 file_path를 추적해야 함
            logger.info(
                "Cleaning up after upload failure",
                extra={
                    "user_id": str(command.user_id),
                    "filename": command.filename
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to cleanup after upload failure: {e}",
                extra={
                    "user_id": str(command.user_id),
                    "filename": command.filename,
                    "cleanup_error": str(e)
                }
            )


class FileValidationService:
    """파일 검증 서비스"""
    
    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """안전한 파일명인지 검증"""
        if not filename:
            return False
        
        # 위험한 문자 체크
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            if char in filename:
                return False
        
        # 예약된 파일명 체크 (Windows)
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            return False
        
        return True
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """파일명 정리"""
        if not filename:
            return "unnamed_file"
        
        # 위험한 문자 제거
        safe_chars = []
        for char in filename:
            if char.isalnum() or char in ['.', '-', '_', ' ']:
                safe_chars.append(char)
            else:
                safe_chars.append('_')
        
        sanitized = ''.join(safe_chars)
        
        # 연속된 언더스코어 정리
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        
        # 앞뒤 공백 및 점 제거
        sanitized = sanitized.strip('. ')
        
        if not sanitized:
            return "unnamed_file"
        
        return sanitized
