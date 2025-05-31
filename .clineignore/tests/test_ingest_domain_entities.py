"""
Ingest 모듈 도메인 엔티티 단위 테스트
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.modules.ingest.domain.entities import (
    Document,
    DocumentMetadata,
    DocumentStatus,
    DocumentType,
    User
)


class TestDocumentMetadata:
    """DocumentMetadata 테스트"""

    def test_create_document_metadata(self):
        """문서 메타데이터 생성 테스트"""
        metadata = DocumentMetadata(
            file_size=1024,
            mime_type="application/pdf",
            encoding="utf-8",
            page_count=10,
            word_count=500,
            language="ko",
            author="Test Author",
            title="Test Document",
            subject="Test Subject",
            keywords=["test", "document"],
            creation_date=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            modification_date=datetime(2024, 1, 16, 12, 0, 0, tzinfo=timezone.utc),
            custom_fields={"department": "IT"}
        )

        assert metadata.file_size == 1024
        assert metadata.mime_type == "application/pdf"
        assert metadata.encoding == "utf-8"
        assert metadata.page_count == 10
        assert metadata.word_count == 500
        assert metadata.language == "ko"
        assert metadata.author == "Test Author"
        assert metadata.title == "Test Document"
        assert metadata.subject == "Test Subject"
        assert metadata.keywords == ["test", "document"]
        assert metadata.custom_fields == {"department": "IT"}

    def test_metadata_to_dict(self):
        """메타데이터 딕셔너리 변환 테스트"""
        creation_date = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        metadata = DocumentMetadata(
            file_size=1024,
            mime_type="application/pdf",
            creation_date=creation_date,
            keywords=["test"]
        )

        result = metadata.to_dict()

        assert result["file_size"] == 1024
        assert result["mime_type"] == "application/pdf"
        assert result["creation_date"] == creation_date.isoformat()
        assert result["keywords"] == ["test"]
        assert "encoding" not in result  # None 값은 제외

    def test_metadata_from_dict(self):
        """딕셔너리에서 메타데이터 생성 테스트"""
        data = {
            "file_size": 1024,
            "mime_type": "application/pdf",
            "creation_date": "2024-01-15T12:00:00+00:00",
            "keywords": ["test"]
        }

        metadata = DocumentMetadata.from_dict(data)

        assert metadata.file_size == 1024
        assert metadata.mime_type == "application/pdf"
        assert metadata.creation_date == datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        assert metadata.keywords == ["test"]

    def test_metadata_minimal_fields(self):
        """최소 필드만으로 메타데이터 생성 테스트"""
        metadata = DocumentMetadata(
            file_size=1024,
            mime_type="application/pdf"
        )

        assert metadata.file_size == 1024
        assert metadata.mime_type == "application/pdf"
        assert metadata.encoding is None
        assert metadata.page_count is None
        assert metadata.custom_fields == {}


class TestDocument:
    """Document 엔티티 테스트"""

    def test_create_document(self):
        """문서 생성 테스트"""
        user_id = uuid4()
        metadata = DocumentMetadata(file_size=1024, mime_type="application/pdf")

        document = Document.create(
            user_id=user_id,
            filename="test.pdf",
            original_filename="original_test.pdf",
            file_path="/uploads/test.pdf",
            document_type=DocumentType.PDF,
            metadata=metadata,
            source="upload",
            tags=["important", "work"]
        )

        assert isinstance(document.id, UUID)
        assert document.user_id == user_id
        assert document.filename == "test.pdf"
        assert document.original_filename == "original_test.pdf"
        assert document.file_path == "/uploads/test.pdf"
        assert document.document_type == DocumentType.PDF
        assert document.status == DocumentStatus.UPLOADED
        assert document.metadata == metadata
        assert document.source == "upload"
        assert document.tags == ["important", "work"]
        assert isinstance(document.created_at, datetime)
        assert isinstance(document.updated_at, datetime)
        assert document.processed_at is None
        assert document.error_message is None
        assert document.parent_id is None

    def test_update_status(self):
        """문서 상태 업데이트 테스트"""
        user_id = uuid4()
        metadata = DocumentMetadata(file_size=1024, mime_type="application/pdf")
        document = Document.create(
            user_id=user_id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_path="/uploads/test.pdf",
            document_type=DocumentType.PDF,
            metadata=metadata
        )

        original_updated_at = document.updated_at

        # 처리 중 상태로 변경
        document.update_status(DocumentStatus.PROCESSING)
        assert document.status == DocumentStatus.PROCESSING
        assert document.updated_at > original_updated_at
        assert document.processed_at is None
        assert document.error_message is None

        # 처리 완료 상태로 변경
        document.update_status(DocumentStatus.PROCESSED)
        assert document.status == DocumentStatus.PROCESSED
        assert document.processed_at is not None
        assert document.error_message is None

        # 실패 상태로 변경
        document.update_status(DocumentStatus.FAILED, "Processing error")
        assert document.status == DocumentStatus.FAILED
        assert document.error_message == "Processing error"

    def test_add_remove_tag(self):
        """태그 추가/제거 테스트"""
        user_id = uuid4()
        metadata = DocumentMetadata(file_size=1024, mime_type="application/pdf")
        document = Document.create(
            user_id=user_id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_path="/uploads/test.pdf",
            document_type=DocumentType.PDF,
            metadata=metadata,
            tags=["initial"]
        )

        # 태그 추가
        document.add_tag("new_tag")
        assert "new_tag" in document.tags
        assert "initial" in document.tags

        # 중복 태그 추가 (무시됨)
        original_length = len(document.tags)
        document.add_tag("new_tag")
        assert len(document.tags) == original_length

        # 태그 제거
        document.remove_tag("initial")
        assert "initial" not in document.tags
        assert "new_tag" in document.tags

        # 존재하지 않는 태그 제거 (무시됨)
        document.remove_tag("nonexistent")
        assert "new_tag" in document.tags

    def test_update_metadata(self):
        """메타데이터 업데이트 테스트"""
        user_id = uuid4()
        original_metadata = DocumentMetadata(file_size=1024, mime_type="application/pdf")
        document = Document.create(
            user_id=user_id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_path="/uploads/test.pdf",
            document_type=DocumentType.PDF,
            metadata=original_metadata
        )

        new_metadata = DocumentMetadata(
            file_size=2048,
            mime_type="application/pdf",
            page_count=10
        )

        original_updated_at = document.updated_at
        document.update_metadata(new_metadata)

        assert document.metadata == new_metadata
        assert document.metadata.file_size == 2048
        assert document.metadata.page_count == 10
        assert document.updated_at > original_updated_at

    def test_status_check_methods(self):
        """상태 확인 메서드 테스트"""
        user_id = uuid4()
        metadata = DocumentMetadata(file_size=1024, mime_type="application/pdf")
        document = Document.create(
            user_id=user_id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_path="/uploads/test.pdf",
            document_type=DocumentType.PDF,
            metadata=metadata
        )

        # 초기 상태 (UPLOADED)
        assert not document.is_processed()
        assert not document.is_failed()
        assert document.can_be_processed()

        # 처리 완료 상태
        document.update_status(DocumentStatus.PROCESSED)
        assert document.is_processed()
        assert not document.is_failed()
        assert not document.can_be_processed()

        # 실패 상태
        document.update_status(DocumentStatus.FAILED)
        assert not document.is_processed()
        assert document.is_failed()
        assert document.can_be_processed()

    def test_document_to_dict(self):
        """문서 딕셔너리 변환 테스트"""
        user_id = uuid4()
        parent_id = uuid4()
        metadata = DocumentMetadata(file_size=1024, mime_type="application/pdf")
        document = Document.create(
            user_id=user_id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_path="/uploads/test.pdf",
            document_type=DocumentType.PDF,
            metadata=metadata,
            parent_id=parent_id,
            tags=["test"]
        )

        result = document.to_dict()

        assert result["id"] == str(document.id)
        assert result["user_id"] == str(user_id)
        assert result["filename"] == "test.pdf"
        assert result["document_type"] == "pdf"
        assert result["status"] == "uploaded"
        assert result["parent_id"] == str(parent_id)
        assert result["tags"] == ["test"]
        assert "metadata" in result
        assert result["processed_at"] is None

    def test_document_from_dict(self):
        """딕셔너리에서 문서 생성 테스트"""
        user_id = uuid4()
        document_id = uuid4()
        data = {
            "id": str(document_id),
            "user_id": str(user_id),
            "filename": "test.pdf",
            "original_filename": "test.pdf",
            "file_path": "/uploads/test.pdf",
            "document_type": "pdf",
            "status": "uploaded",
            "metadata": {
                "file_size": 1024,
                "mime_type": "application/pdf"
            },
            "created_at": "2024-01-15T12:00:00+00:00",
            "updated_at": "2024-01-15T12:00:00+00:00",
            "processed_at": None,
            "error_message": None,
            "tags": ["test"],
            "source": "upload",
            "parent_id": None
        }

        document = Document.from_dict(data)

        assert document.id == document_id
        assert document.user_id == user_id
        assert document.filename == "test.pdf"
        assert document.document_type == DocumentType.PDF
        assert document.status == DocumentStatus.UPLOADED
        assert document.metadata.file_size == 1024
        assert document.tags == ["test"]
        assert document.source == "upload"

    def test_document_with_parent(self):
        """부모 문서가 있는 문서 테스트 (이메일 첨부파일 등)"""
        user_id = uuid4()
        parent_id = uuid4()
        metadata = DocumentMetadata(file_size=1024, mime_type="application/pdf")

        document = Document.create(
            user_id=user_id,
            filename="attachment.pdf",
            original_filename="attachment.pdf",
            file_path="/uploads/attachment.pdf",
            document_type=DocumentType.PDF,
            metadata=metadata,
            source="email",
            parent_id=parent_id
        )

        assert document.parent_id == parent_id
        assert document.source == "email"


class TestUser:
    """User 엔티티 테스트"""

    def test_create_user(self):
        """사용자 생성 테스트"""
        user = User.create(
            email="test@example.com",
            name="Test User"
        )

        assert isinstance(user.id, UUID)
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.is_active is True
        assert user.settings == {}
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    def test_update_settings(self):
        """사용자 설정 업데이트 테스트"""
        user = User.create(
            email="test@example.com",
            name="Test User"
        )

        original_updated_at = user.updated_at
        settings = {"language": "ko", "theme": "dark"}
        user.update_settings(settings)

        assert user.settings["language"] == "ko"
        assert user.settings["theme"] == "dark"
        assert user.updated_at > original_updated_at

        # 추가 설정 업데이트
        additional_settings = {"notifications": True}
        user.update_settings(additional_settings)

        assert user.settings["language"] == "ko"  # 기존 설정 유지
        assert user.settings["notifications"] is True  # 새 설정 추가

    def test_activate_deactivate_user(self):
        """사용자 활성화/비활성화 테스트"""
        user = User.create(
            email="test@example.com",
            name="Test User"
        )

        assert user.is_active is True

        # 비활성화
        original_updated_at = user.updated_at
        user.deactivate()
        assert user.is_active is False
        assert user.updated_at > original_updated_at

        # 활성화
        user.activate()
        assert user.is_active is True

    def test_user_to_dict(self):
        """사용자 딕셔너리 변환 테스트"""
        user = User.create(
            email="test@example.com",
            name="Test User"
        )
        user.update_settings({"language": "ko"})

        result = user.to_dict()

        assert result["id"] == str(user.id)
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"
        assert result["is_active"] is True
        assert result["settings"] == {"language": "ko"}
        assert "created_at" in result
        assert "updated_at" in result

    def test_user_from_dict(self):
        """딕셔너리에서 사용자 생성 테스트"""
        user_id = uuid4()
        data = {
            "id": str(user_id),
            "email": "test@example.com",
            "name": "Test User",
            "created_at": "2024-01-15T12:00:00+00:00",
            "updated_at": "2024-01-15T12:00:00+00:00",
            "is_active": True,
            "settings": {"language": "ko"}
        }

        user = User.from_dict(data)

        assert user.id == user_id
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.is_active is True
        assert user.settings == {"language": "ko"}


class TestDocumentEnums:
    """문서 관련 Enum 테스트"""

    def test_document_status_enum(self):
        """DocumentStatus Enum 테스트"""
        assert DocumentStatus.UPLOADED.value == "uploaded"
        assert DocumentStatus.PARSING.value == "parsing"
        assert DocumentStatus.PARSED.value == "parsed"
        assert DocumentStatus.PROCESSING.value == "processing"
        assert DocumentStatus.PROCESSED.value == "processed"
        assert DocumentStatus.FAILED.value == "failed"
        assert DocumentStatus.DELETED.value == "deleted"

    def test_document_type_enum(self):
        """DocumentType Enum 테스트"""
        assert DocumentType.PDF.value == "pdf"
        assert DocumentType.DOCX.value == "docx"
        assert DocumentType.TXT.value == "txt"
        assert DocumentType.EMAIL.value == "email"
        assert DocumentType.HTML.value == "html"
        assert DocumentType.MARKDOWN.value == "md"
        assert DocumentType.UNKNOWN.value == "unknown"


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_document_with_empty_tags(self):
        """빈 태그 리스트로 문서 생성 테스트"""
        user_id = uuid4()
        metadata = DocumentMetadata(file_size=1024, mime_type="application/pdf")
        document = Document.create(
            user_id=user_id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_path="/uploads/test.pdf",
            document_type=DocumentType.PDF,
            metadata=metadata,
            tags=[]
        )

        assert document.tags == []

    def test_document_without_optional_fields(self):
        """선택적 필드 없이 문서 생성 테스트"""
        user_id = uuid4()
        metadata = DocumentMetadata(file_size=1024, mime_type="application/pdf")
        document = Document.create(
            user_id=user_id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_path="/uploads/test.pdf",
            document_type=DocumentType.PDF,
            metadata=metadata
        )

        assert document.source is None
        assert document.parent_id is None
        assert document.tags == []

    def test_metadata_with_none_values(self):
        """None 값이 포함된 메타데이터 테스트"""
        metadata = DocumentMetadata(
            file_size=1024,
            mime_type="application/pdf",
            encoding=None,
            page_count=None
        )

        dict_result = metadata.to_dict()
        assert "encoding" not in dict_result
        assert "page_count" not in dict_result
        assert dict_result["file_size"] == 1024

    def test_user_with_empty_settings(self):
        """빈 설정으로 사용자 생성 테스트"""
        user = User.create(
            email="test@example.com",
            name="Test User"
        )

        assert user.settings == {}
        user.update_settings({})
        assert user.settings == {}
