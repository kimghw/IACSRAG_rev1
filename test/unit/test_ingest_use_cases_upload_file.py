"""
파일 업로드 유즈케이스 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from pathlib import Path

from src.modules.ingest.application.use_cases.upload_file import (
    UploadFileUseCase,
    FileUploadCommand,
    FileUploadResult,
    FileValidationService
)
from src.modules.ingest.domain.entities import Document, DocumentMetadata, DocumentType
from src.core.exceptions import ValidationError, BusinessRuleViolationError, DocumentProcessingError


@pytest.fixture
def mock_document_service():
    """Mock Document Service"""
    return AsyncMock()


@pytest.fixture
def mock_file_storage():
    """Mock File Storage"""
    return AsyncMock()


@pytest.fixture
def mock_event_publisher():
    """Mock Event Publisher"""
    return AsyncMock()


@pytest.fixture
def upload_file_use_case(mock_document_service, mock_file_storage, mock_event_publisher):
    """Upload File Use Case 인스턴스"""
    return UploadFileUseCase(
        document_service=mock_document_service,
        file_storage=mock_file_storage,
        event_publisher=mock_event_publisher,
        max_file_size=10 * 1024 * 1024,  # 10MB for testing
        allowed_file_types=['.pdf', '.docx', '.txt', '.html']
    )


@pytest.fixture
def sample_pdf_content():
    """테스트용 PDF 내용"""
    return b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'


@pytest.fixture
def sample_docx_content():
    """테스트용 DOCX 내용 (ZIP 시그니처)"""
    return b'PK\x03\x04\x14\x00\x00\x00\x08\x00' + b'\x00' * 100


@pytest.fixture
def sample_text_content():
    """테스트용 텍스트 내용"""
    return "This is a sample text file content.".encode('utf-8')


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


class TestUploadFileUseCase:
    """파일 업로드 유즈케이스 테스트"""

    @pytest.mark.asyncio
    async def test_execute_success_pdf(
        self,
        upload_file_use_case,
        mock_document_service,
        mock_file_storage,
        mock_event_publisher,
        sample_pdf_content,
        sample_document
    ):
        """PDF 파일 업로드 성공 테스트"""
        # Given
        user_id = uuid4()
        command = FileUploadCommand(
            user_id=user_id,
            filename="test.pdf",
            file_content=sample_pdf_content,
            content_type="application/pdf",
            tags=["test"]
        )
        
        # Mock 설정
        mock_file_storage.save_file.return_value = "/uploads/test.pdf"
        mock_document_service.upload_document.return_value = sample_document
        
        # When
        result = await upload_file_use_case.execute(command)
        
        # Then
        assert isinstance(result, FileUploadResult)
        assert result.document == sample_document
        assert result.file_path == "/uploads/test.pdf"
        assert isinstance(result.metadata, dict)
        
        # 파일 저장 확인
        mock_file_storage.save_file.assert_called_once()
        
        # 문서 서비스 호출 확인
        mock_document_service.upload_document.assert_called_once()
        
        # 이벤트 발행 확인
        mock_event_publisher.publish_document_uploaded.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_success_docx(
        self,
        upload_file_use_case,
        mock_document_service,
        mock_file_storage,
        mock_event_publisher,
        sample_docx_content,
        sample_document
    ):
        """DOCX 파일 업로드 성공 테스트"""
        # Given
        user_id = uuid4()
        command = FileUploadCommand(
            user_id=user_id,
            filename="document.docx",
            file_content=sample_docx_content,
            tags=["document"]
        )
        
        # Mock 설정
        mock_file_storage.save_file.return_value = "/uploads/document.docx"
        mock_document_service.upload_document.return_value = sample_document
        
        # When
        result = await upload_file_use_case.execute(command)
        
        # Then
        assert isinstance(result, FileUploadResult)
        mock_file_storage.save_file.assert_called_once()
        mock_document_service.upload_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_success_text(
        self,
        upload_file_use_case,
        mock_document_service,
        mock_file_storage,
        mock_event_publisher,
        sample_text_content,
        sample_document
    ):
        """텍스트 파일 업로드 성공 테스트"""
        # Given
        user_id = uuid4()
        command = FileUploadCommand(
            user_id=user_id,
            filename="notes.txt",
            file_content=sample_text_content
        )
        
        # Mock 설정
        mock_file_storage.save_file.return_value = "/uploads/notes.txt"
        mock_document_service.upload_document.return_value = sample_document
        
        # When
        result = await upload_file_use_case.execute(command)
        
        # Then
        assert isinstance(result, FileUploadResult)
        mock_file_storage.save_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_empty_filename(
        self,
        upload_file_use_case,
        sample_pdf_content
    ):
        """빈 파일명 테스트"""
        # Given
        user_id = uuid4()
        command = FileUploadCommand(
            user_id=user_id,
            filename="",
            file_content=sample_pdf_content
        )
        
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            await upload_file_use_case.execute(command)
        
        assert "Filename is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_empty_file(
        self,
        upload_file_use_case
    ):
        """빈 파일 테스트"""
        # Given
        user_id = uuid4()
        command = FileUploadCommand(
            user_id=user_id,
            filename="empty.pdf",
            file_content=b""
        )
        
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            await upload_file_use_case.execute(command)
        
        assert "File is empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_file_too_large(
        self,
        upload_file_use_case
    ):
        """파일 크기 초과 테스트"""
        # Given
        user_id = uuid4()
        large_content = b'x' * (11 * 1024 * 1024)  # 11MB (제한: 10MB)
        command = FileUploadCommand(
            user_id=user_id,
            filename="large.pdf",
            file_content=large_content
        )
        
        # When & Then
        with pytest.raises(BusinessRuleViolationError) as exc_info:
            await upload_file_use_case.execute(command)
        
        assert "File size exceeds maximum allowed size" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_unsupported_file_type(
        self,
        upload_file_use_case
    ):
        """지원되지 않는 파일 타입 테스트"""
        # Given
        user_id = uuid4()
        command = FileUploadCommand(
            user_id=user_id,
            filename="virus.exe",
            file_content=b"MZ\x90\x00"  # EXE 시그니처
        )
        
        # When & Then
        with pytest.raises(BusinessRuleViolationError) as exc_info:
            await upload_file_use_case.execute(command)
        
        assert "File type '.exe' is not allowed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_invalid_pdf_format(
        self,
        upload_file_use_case
    ):
        """잘못된 PDF 형식 테스트"""
        # Given
        user_id = uuid4()
        command = FileUploadCommand(
            user_id=user_id,
            filename="fake.pdf",
            file_content=b"This is not a PDF file"
        )
        
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            await upload_file_use_case.execute(command)
        
        assert "Invalid PDF file format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_invalid_docx_format(
        self,
        upload_file_use_case
    ):
        """잘못된 DOCX 형식 테스트"""
        # Given
        user_id = uuid4()
        command = FileUploadCommand(
            user_id=user_id,
            filename="fake.docx",
            file_content=b"This is not a DOCX file"
        )
        
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            await upload_file_use_case.execute(command)
        
        assert "Invalid .docx file format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_invalid_text_encoding(
        self,
        upload_file_use_case
    ):
        """잘못된 텍스트 인코딩 테스트"""
        # Given
        user_id = uuid4()
        invalid_content = b'\xff\xfe\x00\x00'  # 잘못된 인코딩
        command = FileUploadCommand(
            user_id=user_id,
            filename="invalid.txt",
            file_content=invalid_content
        )
        
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            await upload_file_use_case.execute(command)
        
        assert "Text file encoding is not supported" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_file_storage_failure(
        self,
        upload_file_use_case,
        mock_file_storage,
        sample_pdf_content
    ):
        """파일 저장 실패 테스트"""
        # Given
        user_id = uuid4()
        command = FileUploadCommand(
            user_id=user_id,
            filename="test.pdf",
            file_content=sample_pdf_content
        )
        
        mock_file_storage.save_file.side_effect = Exception("Storage failed")
        
        # When & Then
        with pytest.raises(DocumentProcessingError):
            await upload_file_use_case.execute(command)

    @pytest.mark.asyncio
    async def test_execute_document_service_failure(
        self,
        upload_file_use_case,
        mock_document_service,
        mock_file_storage,
        sample_pdf_content
    ):
        """문서 서비스 실패 테스트"""
        # Given
        user_id = uuid4()
        command = FileUploadCommand(
            user_id=user_id,
            filename="test.pdf",
            file_content=sample_pdf_content
        )
        
        mock_file_storage.save_file.return_value = "/uploads/test.pdf"
        mock_document_service.upload_document.side_effect = Exception("Service failed")
        
        # When & Then
        with pytest.raises(DocumentProcessingError):
            await upload_file_use_case.execute(command)


class TestFileValidation:
    """파일 검증 테스트"""

    def test_get_file_extension(self, upload_file_use_case):
        """파일 확장자 추출 테스트"""
        # Given & When & Then
        assert upload_file_use_case._get_file_extension("test.pdf") == ".pdf"
        assert upload_file_use_case._get_file_extension("document.DOCX") == ".docx"
        assert upload_file_use_case._get_file_extension("file") == ""
        assert upload_file_use_case._get_file_extension("archive.tar.gz") == ".gz"

    def test_detect_content_type_pdf(self, upload_file_use_case, sample_pdf_content):
        """PDF MIME 타입 감지 테스트"""
        # When
        content_type = upload_file_use_case._detect_content_type("test.pdf", sample_pdf_content)
        
        # Then
        assert content_type == "application/pdf"

    def test_detect_content_type_docx(self, upload_file_use_case, sample_docx_content):
        """DOCX MIME 타입 감지 테스트"""
        # When
        content_type = upload_file_use_case._detect_content_type("document.docx", sample_docx_content)
        
        # Then
        assert content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def test_detect_content_type_text(self, upload_file_use_case, sample_text_content):
        """텍스트 MIME 타입 감지 테스트"""
        # When
        content_type = upload_file_use_case._detect_content_type("notes.txt", sample_text_content)
        
        # Then
        assert content_type == "text/plain"

    def test_determine_document_type(self, upload_file_use_case):
        """문서 타입 결정 테스트"""
        # Given & When & Then
        assert upload_file_use_case._determine_document_type("test.pdf") == DocumentType.PDF
        assert upload_file_use_case._determine_document_type("doc.docx") == DocumentType.DOCX
        assert upload_file_use_case._determine_document_type("notes.txt") == DocumentType.TXT
        assert upload_file_use_case._determine_document_type("page.html") == DocumentType.HTML
        assert upload_file_use_case._determine_document_type("unknown.xyz") == DocumentType.TXT

    def test_extract_file_metadata(self, upload_file_use_case, sample_pdf_content):
        """파일 메타데이터 추출 테스트"""
        # Given
        command = FileUploadCommand(
            user_id=uuid4(),
            filename="test.pdf",
            file_content=sample_pdf_content,
            content_type="application/pdf",
            tags=["test"]
        )
        file_path = "/uploads/test.pdf"
        
        # When
        metadata = upload_file_use_case._extract_file_metadata(command, file_path)
        
        # Then
        assert metadata["original_filename"] == "test.pdf"
        assert metadata["file_size"] == len(sample_pdf_content)
        assert metadata["content_type"] == "application/pdf"
        assert metadata["file_extension"] == ".pdf"
        assert metadata["source"] == "upload"
        assert metadata["tags"] == ["test"]
        assert metadata["file_path"] == file_path


class TestFileValidationService:
    """파일 검증 서비스 테스트"""

    def test_is_safe_filename_valid(self):
        """안전한 파일명 테스트"""
        # Given
        valid_filenames = [
            "document.pdf",
            "my_file.txt",
            "report-2024.docx",
            "data file.xlsx"
        ]
        
        # When & Then
        for filename in valid_filenames:
            assert FileValidationService.is_safe_filename(filename) is True

    def test_is_safe_filename_invalid(self):
        """위험한 파일명 테스트"""
        # Given
        invalid_filenames = [
            "",
            "../../../etc/passwd",
            "file/with/slash.txt",
            "file\\with\\backslash.txt",
            "file:with:colon.txt",
            "file*with*asterisk.txt",
            "file?with?question.txt",
            'file"with"quote.txt',
            "file<with>brackets.txt",
            "file|with|pipe.txt",
            "CON.txt",
            "PRN.pdf",
            "AUX.docx",
            "NUL.html",
            "COM1.txt",
            "LPT1.pdf"
        ]
        
        # When & Then
        for filename in invalid_filenames:
            assert FileValidationService.is_safe_filename(filename) is False

    def test_sanitize_filename_valid(self):
        """파일명 정리 - 유효한 경우"""
        # Given & When & Then
        assert FileValidationService.sanitize_filename("document.pdf") == "document.pdf"
        assert FileValidationService.sanitize_filename("my_file.txt") == "my_file.txt"

    def test_sanitize_filename_invalid(self):
        """파일명 정리 - 무효한 경우"""
        # Given & When & Then
        assert FileValidationService.sanitize_filename("") == "unnamed_file"
        assert FileValidationService.sanitize_filename("file/with/slash.txt") == "file_with_slash.txt"
        assert FileValidationService.sanitize_filename("file\\with\\backslash.txt") == "file_with_backslash.txt"
        assert FileValidationService.sanitize_filename("file:with:colon.txt") == "file_with_colon.txt"
        assert FileValidationService.sanitize_filename("file***multiple.txt") == "file_multiple.txt"
        assert FileValidationService.sanitize_filename("  .file.  ") == "file"

    def test_sanitize_filename_special_cases(self):
        """파일명 정리 - 특수 경우"""
        # Given & When & Then
        # 한글은 유니코드 문자로 처리되어 그대로 유지됨
        assert FileValidationService.sanitize_filename("한글파일.txt") == "한글파일.txt"
        assert FileValidationService.sanitize_filename("file__with__double.txt") == "file_with_double.txt"
        assert FileValidationService.sanitize_filename("...") == "unnamed_file"


class TestContentValidation:
    """파일 내용 검증 테스트"""

    def test_validate_korean_text_cp949(self, upload_file_use_case):
        """한국어 텍스트 파일 (CP949) 검증 테스트"""
        # Given
        korean_text = "안녕하세요. 한글 텍스트입니다."
        cp949_content = korean_text.encode('cp949')
        command = FileUploadCommand(
            user_id=uuid4(),
            filename="korean.txt",
            file_content=cp949_content
        )
        
        # When & Then (예외가 발생하지 않아야 함)
        upload_file_use_case._validate_file_content(command)

    def test_validate_html_file(self, upload_file_use_case):
        """HTML 파일 검증 테스트"""
        # Given
        html_content = "<html><body><h1>Test</h1></body></html>".encode('utf-8')
        command = FileUploadCommand(
            user_id=uuid4(),
            filename="page.html",
            file_content=html_content
        )
        
        # When & Then (예외가 발생하지 않아야 함)
        upload_file_use_case._validate_file_content(command)

    def test_validate_csv_file(self, upload_file_use_case):
        """CSV 파일 검증 테스트"""
        # Given
        csv_content = "name,age,city\nJohn,30,Seoul\nJane,25,Busan".encode('utf-8')
        command = FileUploadCommand(
            user_id=uuid4(),
            filename="data.csv",
            file_content=csv_content
        )
        
        # When & Then (예외가 발생하지 않아야 함)
        upload_file_use_case._validate_file_content(command)
