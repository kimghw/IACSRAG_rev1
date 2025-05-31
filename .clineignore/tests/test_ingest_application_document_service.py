"""
Document Service 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.modules.ingest.application.services.document_service import DocumentService
from src.modules.ingest.domain.entities import Document, DocumentMetadata, DocumentStatus, DocumentType
from src.core.exceptions import ValidationError, BusinessRuleViolationError


@pytest.fixture
def mock_document_repository():
    """Mock Document Repository"""
    return AsyncMock()


@pytest.fixture
def mock_event_publisher():
    """Mock Event Publisher"""
    return AsyncMock()


@pytest.fixture
def mock_file_storage():
    """Mock File Storage"""
    return AsyncMock()


@pytest.fixture
def document_service(mock_document_repository, mock_event_publisher, mock_file_storage):
    """Document Service 인스턴스"""
    return DocumentService(
        document_repository=mock_document_repository,
        event_publisher=mock_event_publisher,
        file_storage=mock_file_storage,
        max_file_size=10 * 1024 * 1024,  # 10MB for testing
        allowed_extensions=['.pdf', '.docx', '.txt']
    )


@pytest.fixture
def sample_file_content():
    """테스트용 파일 내용"""
    return b"This is a test file content for unit testing."


@pytest.fixture
def sample_document():
    """테스트용 문서 엔티티"""
    user_id = uuid4()
    metadata = DocumentMetadata(file_size=1024, mime_type="application/pdf")
    
    return Document.create(
        user_id=user_id,
        filename="test.pdf",
        original_filename="test.pdf",
        file_path="/uploads/test.pdf",
        document_type=DocumentType.PDF,
        metadata=metadata,
        tags=["test"]
    )


class TestDocumentServiceUpload:
    """문서 업로드 관련 테스트"""

    @pytest.mark.asyncio
    async def test_upload_document_success(
        self, 
        document_service, 
        mock_document_repository,
        mock_event_publisher,
        mock_file_storage,
        sample_file_content,
        sample_document
    ):
        """문서 업로드 성공 테스트"""
        # Given
        user_id = uuid4()
        filename = "test.pdf"
        content_type = "application/pdf"
        file_path = "/uploads/test.pdf"
        
        mock_file_storage.save_file.return_value = file_path
        mock_document_repository.save.return_value = sample_document
        
        # When
        result = await document_service.upload_document(
            user_id=user_id,
            filename=filename,
            file_content=sample_file_content,
            content_type=content_type,
            tags=["test"],
            source="upload"
        )
        
        # Then
        assert result == sample_document
        mock_file_storage.save_file.assert_called_once()
        mock_document_repository.save.assert_called_once()
        mock_event_publisher.publish_document_uploaded.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_document_file_too_large(
        self, 
        document_service,
        sample_file_content
    ):
        """파일 크기 초과 테스트"""
        # Given
        user_id = uuid4()
        filename = "large_file.pdf"
        large_content = b"x" * (20 * 1024 * 1024)  # 20MB (limit is 10MB)
        
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            await document_service.upload_document(
                user_id=user_id,
                filename=filename,
                file_content=large_content
            )
        
        assert "File size exceeds maximum allowed size" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_document_invalid_file_type(
        self, 
        document_service,
        sample_file_content
    ):
        """허용되지 않는 파일 타입 테스트"""
        # Given
        user_id = uuid4()
        filename = "test.exe"  # Not allowed extension
        
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            await document_service.upload_document(
                user_id=user_id,
                filename=filename,
                file_content=sample_file_content
            )
        
        assert "File type not allowed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_document_empty_file(
        self, 
        document_service
    ):
        """빈 파일 업로드 테스트"""
        # Given
        user_id = uuid4()
        filename = "empty.pdf"
        empty_content = b""
        
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            await document_service.upload_document(
                user_id=user_id,
                filename=filename,
                file_content=empty_content
            )
        
        assert "Empty file is not allowed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_document_storage_failure(
        self, 
        document_service,
        mock_file_storage,
        sample_file_content
    ):
        """파일 저장 실패 테스트"""
        # Given
        user_id = uuid4()
        filename = "test.pdf"
        mock_file_storage.save_file.side_effect = Exception("Storage failed")
        
        # When & Then
        with pytest.raises(Exception) as exc_info:
            await document_service.upload_document(
                user_id=user_id,
                filename=filename,
                file_content=sample_file_content
            )
        
        assert "Storage failed" in str(exc_info.value)


class TestDocumentServiceRetrieval:
    """문서 조회 관련 테스트"""

    @pytest.mark.asyncio
    async def test_get_document_success(
        self, 
        document_service,
        mock_document_repository,
        sample_document
    ):
        """문서 조회 성공 테스트"""
        # Given
        document_id = sample_document.id
        mock_document_repository.find_by_id.return_value = sample_document
        
        # When
        result = await document_service.get_document(document_id)
        
        # Then
        assert result == sample_document
        mock_document_repository.find_by_id.assert_called_once_with(document_id)

    @pytest.mark.asyncio
    async def test_get_document_not_found(
        self, 
        document_service,
        mock_document_repository
    ):
        """문서 조회 실패 테스트"""
        # Given
        document_id = uuid4()
        mock_document_repository.find_by_id.return_value = None
        
        # When
        result = await document_service.get_document(document_id)
        
        # Then
        assert result is None
        mock_document_repository.find_by_id.assert_called_once_with(document_id)

    @pytest.mark.asyncio
    async def test_get_user_documents(
        self, 
        document_service,
        mock_document_repository,
        sample_document
    ):
        """사용자 문서 목록 조회 테스트"""
        # Given
        user_id = uuid4()
        documents = [sample_document]
        mock_document_repository.find_by_user_id.return_value = documents
        
        # When
        result = await document_service.get_user_documents(
            user_id=user_id,
            limit=10,
            offset=0,
            status=DocumentStatus.UPLOADED
        )
        
        # Then
        assert result == documents
        mock_document_repository.find_by_user_id.assert_called_once_with(
            user_id, 10, 0, DocumentStatus.UPLOADED, None
        )

    @pytest.mark.asyncio
    async def test_search_documents(
        self, 
        document_service,
        mock_document_repository,
        sample_document
    ):
        """문서 검색 테스트"""
        # Given
        user_id = uuid4()
        filename_pattern = "test"
        documents = [sample_document]
        mock_document_repository.search_by_filename.return_value = documents
        
        # When
        result = await document_service.search_documents(
            user_id=user_id,
            filename_pattern=filename_pattern,
            limit=50
        )
        
        # Then
        assert result == documents
        mock_document_repository.search_by_filename.assert_called_once_with(
            user_id, filename_pattern, 50
        )


class TestDocumentServiceUpdate:
    """문서 업데이트 관련 테스트"""

    @pytest.mark.asyncio
    async def test_update_document_status_success(
        self, 
        document_service,
        mock_document_repository
    ):
        """문서 상태 업데이트 성공 테스트"""
        # Given
        document_id = uuid4()
        status = DocumentStatus.PROCESSING
        mock_document_repository.update_status.return_value = True
        
        # When
        result = await document_service.update_document_status(
            document_id=document_id,
            status=status
        )
        
        # Then
        assert result is True
        mock_document_repository.update_status.assert_called_once_with(
            document_id, status, None
        )

    @pytest.mark.asyncio
    async def test_update_document_status_with_error(
        self, 
        document_service,
        mock_document_repository
    ):
        """에러와 함께 문서 상태 업데이트 테스트"""
        # Given
        document_id = uuid4()
        status = DocumentStatus.FAILED
        error_message = "Processing failed"
        mock_document_repository.update_status.return_value = True
        
        # When
        result = await document_service.update_document_status(
            document_id=document_id,
            status=status,
            error_message=error_message
        )
        
        # Then
        assert result is True
        mock_document_repository.update_status.assert_called_once_with(
            document_id, status, error_message
        )

    @pytest.mark.asyncio
    async def test_update_document_status_not_found(
        self, 
        document_service,
        mock_document_repository
    ):
        """존재하지 않는 문서 상태 업데이트 테스트"""
        # Given
        document_id = uuid4()
        status = DocumentStatus.PROCESSING
        mock_document_repository.update_status.return_value = False
        
        # When
        result = await document_service.update_document_status(
            document_id=document_id,
            status=status
        )
        
        # Then
        assert result is False


class TestDocumentServiceDeletion:
    """문서 삭제 관련 테스트"""

    @pytest.mark.asyncio
    async def test_delete_document_success(
        self, 
        document_service,
        mock_document_repository,
        mock_file_storage,
        sample_document
    ):
        """문서 삭제 성공 테스트"""
        # Given
        document_id = sample_document.id
        mock_document_repository.find_by_id.return_value = sample_document
        mock_file_storage.delete_file.return_value = True
        mock_document_repository.delete_by_id.return_value = True
        
        # When
        result = await document_service.delete_document(document_id)
        
        # Then
        assert result is True
        mock_document_repository.find_by_id.assert_called_once_with(document_id)
        mock_file_storage.delete_file.assert_called_once_with(sample_document.file_path)
        mock_document_repository.delete_by_id.assert_called_once_with(document_id)

    @pytest.mark.asyncio
    async def test_delete_document_not_found(
        self, 
        document_service,
        mock_document_repository
    ):
        """존재하지 않는 문서 삭제 테스트"""
        # Given
        document_id = uuid4()
        mock_document_repository.find_by_id.return_value = None
        
        # When
        result = await document_service.delete_document(document_id)
        
        # Then
        assert result is False
        mock_document_repository.find_by_id.assert_called_once_with(document_id)

    @pytest.mark.asyncio
    async def test_delete_document_file_deletion_failure(
        self, 
        document_service,
        mock_document_repository,
        mock_file_storage,
        sample_document
    ):
        """파일 삭제 실패 테스트"""
        # Given
        document_id = sample_document.id
        mock_document_repository.find_by_id.return_value = sample_document
        mock_file_storage.delete_file.side_effect = Exception("File deletion failed")
        
        # When
        result = await document_service.delete_document(document_id)
        
        # Then
        assert result is False


class TestDocumentServiceStatistics:
    """통계 관련 테스트"""

    @pytest.mark.asyncio
    async def test_get_processing_statistics_all_users(
        self, 
        document_service,
        mock_document_repository
    ):
        """전체 사용자 처리 통계 조회 테스트"""
        # Given
        expected_stats = {
            "uploaded": 10,
            "processing": 5,
            "processed": 20,
            "failed": 2
        }
        mock_document_repository.get_processing_statistics.return_value = expected_stats
        
        # When
        result = await document_service.get_processing_statistics()
        
        # Then
        assert result == expected_stats
        mock_document_repository.get_processing_statistics.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_get_processing_statistics_specific_user(
        self, 
        document_service,
        mock_document_repository
    ):
        """특정 사용자 처리 통계 조회 테스트"""
        # Given
        user_id = uuid4()
        expected_stats = {
            "uploaded": 3,
            "processing": 1,
            "processed": 5,
            "failed": 0
        }
        mock_document_repository.get_processing_statistics.return_value = expected_stats
        
        # When
        result = await document_service.get_processing_statistics(user_id)
        
        # Then
        assert result == expected_stats
        mock_document_repository.get_processing_statistics.assert_called_once_with(user_id)


class TestDocumentServiceHelperMethods:
    """헬퍼 메서드 테스트"""

    def test_determine_document_type_pdf(self, document_service):
        """PDF 문서 유형 결정 테스트"""
        # Given
        filename = "test.pdf"
        content_type = "application/pdf"
        
        # When
        result = document_service._determine_document_type(filename, content_type)
        
        # Then
        assert result == DocumentType.PDF

    def test_determine_document_type_docx(self, document_service):
        """DOCX 문서 유형 결정 테스트"""
        # Given
        filename = "test.docx"
        
        # When
        result = document_service._determine_document_type(filename)
        
        # Then
        assert result == DocumentType.DOCX

    def test_determine_document_type_unknown(self, document_service):
        """알 수 없는 문서 유형 테스트"""
        # Given
        filename = "test.xyz"
        
        # When
        result = document_service._determine_document_type(filename)
        
        # Then
        assert result == DocumentType.HTML

    def test_get_mime_type_pdf(self, document_service):
        """PDF MIME 타입 테스트"""
        # Given
        filename = "test.pdf"
        
        # When
        result = document_service._get_mime_type(filename)
        
        # Then
        assert result == "application/pdf"

    def test_get_mime_type_unknown(self, document_service):
        """알 수 없는 MIME 타입 테스트"""
        # Given
        filename = "test.xyz"
        
        # When
        result = document_service._get_mime_type(filename)
        
        # Then
        assert result == "application/octet-stream"


class TestDocumentServiceValidation:
    """파일 검증 관련 테스트"""

    @pytest.mark.asyncio
    async def test_validate_file_success(
        self, 
        document_service,
        sample_file_content
    ):
        """파일 검증 성공 테스트"""
        # Given
        filename = "test.pdf"
        content_type = "application/pdf"
        
        # When & Then (예외가 발생하지 않아야 함)
        await document_service._validate_file(filename, sample_file_content, content_type)

    @pytest.mark.asyncio
    async def test_validate_file_size_exceeded(
        self, 
        document_service
    ):
        """파일 크기 초과 검증 테스트"""
        # Given
        filename = "test.pdf"
        large_content = b"x" * (20 * 1024 * 1024)  # 20MB
        
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            await document_service._validate_file(filename, large_content)
        
        assert "File size exceeds maximum allowed size" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_file_type_not_allowed(
        self, 
        document_service,
        sample_file_content
    ):
        """허용되지 않는 파일 타입 검증 테스트"""
        # Given
        filename = "test.exe"
        
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            await document_service._validate_file(filename, sample_file_content)
        
        assert "File type not allowed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_empty_file(
        self, 
        document_service
    ):
        """빈 파일 검증 테스트"""
        # Given
        filename = "test.pdf"
        empty_content = b""
        
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            await document_service._validate_file(filename, empty_content)
        
        assert "Empty file is not allowed" in str(exc_info.value)
