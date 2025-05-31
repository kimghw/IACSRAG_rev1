"""
Ingest 모듈 도메인 엔티티

문서 수집 관련 핵심 비즈니스 객체들을 정의합니다.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from uuid import UUID

from src.utils.id_generator import generate_uuid_object
from src.utils.datetime import get_current_utc_datetime


class DocumentStatus(Enum):
    """문서 처리 상태"""
    UPLOADED = "uploaded"           # 업로드 완료
    PARSING = "parsing"            # 파싱 중
    PARSED = "parsed"              # 파싱 완료
    PROCESSING = "processing"      # 처리 중
    PROCESSED = "processed"        # 처리 완료
    FAILED = "failed"              # 처리 실패
    DELETED = "deleted"            # 삭제됨


class DocumentType(Enum):
    """문서 유형"""
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    TXT = "txt"
    EMAIL = "email"
    HTML = "html"
    MARKDOWN = "md"
    PPTX = "pptx"
    PPT = "ppt"
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"
    UNKNOWN = "unknown"


@dataclass
class DocumentMetadata:
    """문서 메타데이터"""
    file_size: int
    mime_type: str
    encoding: Optional[str] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    language: Optional[str] = None
    author: Optional[str] = None
    title: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[List[str]] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, list):
                    result[key] = value
                elif isinstance(value, dict):
                    result[key] = value
                else:
                    result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentMetadata':
        """딕셔너리에서 생성"""
        # datetime 필드 변환
        if 'creation_date' in data and data['creation_date']:
            data['creation_date'] = datetime.fromisoformat(data['creation_date'])
        if 'modification_date' in data and data['modification_date']:
            data['modification_date'] = datetime.fromisoformat(data['modification_date'])
        
        return cls(**data)


@dataclass
class Document:
    """문서 엔티티"""
    id: UUID
    user_id: UUID
    filename: str
    original_filename: str
    file_path: str
    document_type: DocumentType
    status: DocumentStatus
    metadata: DocumentMetadata
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    source: Optional[str] = None  # 문서 출처 (email, upload, etc.)
    parent_id: Optional[UUID] = None  # 이메일 첨부파일 등의 경우 부모 문서 ID

    @classmethod
    def create(
        cls,
        user_id: UUID,
        filename: str,
        original_filename: str,
        file_path: str,
        document_type: DocumentType,
        metadata: DocumentMetadata,
        source: Optional[str] = None,
        parent_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None
    ) -> 'Document':
        """새 문서 생성"""
        now = get_current_utc_datetime()
        
        return cls(
            id=generate_uuid_object(),
            user_id=user_id,
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            document_type=document_type,
            status=DocumentStatus.UPLOADED,
            metadata=metadata,
            created_at=now,
            updated_at=now,
            tags=tags or [],
            source=source,
            parent_id=parent_id
        )

    def update_status(self, status: DocumentStatus, error_message: Optional[str] = None) -> None:
        """상태 업데이트"""
        self.status = status
        self.updated_at = get_current_utc_datetime()
        
        if status == DocumentStatus.PROCESSED:
            self.processed_at = self.updated_at
        
        if error_message:
            self.error_message = error_message
        elif status != DocumentStatus.FAILED:
            # 실패 상태가 아니면 에러 메시지 초기화
            self.error_message = None

    def add_tag(self, tag: str) -> None:
        """태그 추가"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = get_current_utc_datetime()

    def remove_tag(self, tag: str) -> None:
        """태그 제거"""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = get_current_utc_datetime()

    def update_metadata(self, metadata: DocumentMetadata) -> None:
        """메타데이터 업데이트"""
        self.metadata = metadata
        self.updated_at = get_current_utc_datetime()

    def is_processed(self) -> bool:
        """처리 완료 여부 확인"""
        return self.status == DocumentStatus.PROCESSED

    def is_failed(self) -> bool:
        """처리 실패 여부 확인"""
        return self.status == DocumentStatus.FAILED

    def can_be_processed(self) -> bool:
        """처리 가능 여부 확인"""
        return self.status in [
            DocumentStatus.UPLOADED,
            DocumentStatus.PARSED,
            DocumentStatus.FAILED
        ]

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_path': self.file_path,
            'document_type': self.document_type.value,
            'status': self.status.value,
            'metadata': self.metadata.to_dict(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'error_message': self.error_message,
            'tags': self.tags,
            'source': self.source,
            'parent_id': str(self.parent_id) if self.parent_id else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """딕셔너리에서 생성"""
        # UUID 필드 변환
        data['id'] = UUID(data['id'])
        data['user_id'] = UUID(data['user_id'])
        if data.get('parent_id'):
            data['parent_id'] = UUID(data['parent_id'])
        
        # Enum 필드 변환
        data['document_type'] = DocumentType(data['document_type'])
        data['status'] = DocumentStatus(data['status'])
        
        # datetime 필드 변환
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if data.get('processed_at'):
            data['processed_at'] = datetime.fromisoformat(data['processed_at'])
        
        # 메타데이터 변환
        data['metadata'] = DocumentMetadata.from_dict(data['metadata'])
        
        return cls(**data)


@dataclass
class User:
    """사용자 엔티티"""
    id: UUID
    email: str
    name: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, email: str, name: str) -> 'User':
        """새 사용자 생성"""
        now = get_current_utc_datetime()
        
        return cls(
            id=generate_uuid_object(),
            email=email,
            name=name,
            created_at=now,
            updated_at=now
        )

    def update_settings(self, settings: Dict[str, Any]) -> None:
        """설정 업데이트"""
        self.settings.update(settings)
        self.updated_at = get_current_utc_datetime()

    def deactivate(self) -> None:
        """사용자 비활성화"""
        self.is_active = False
        self.updated_at = get_current_utc_datetime()

    def activate(self) -> None:
        """사용자 활성화"""
        self.is_active = True
        self.updated_at = get_current_utc_datetime()

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'id': str(self.id),
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active,
            'settings': self.settings
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """딕셔너리에서 생성"""
        data['id'] = UUID(data['id'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        return cls(**data)
