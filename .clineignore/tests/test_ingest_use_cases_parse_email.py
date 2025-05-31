"""
이메일 파싱 유즈케이스 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.modules.ingest.application.use_cases.parse_email import (
    ParseEmailUseCase,
    EmailParseCommand,
    EmailParseResult,
    ParsedEmail,
    EmailAttachment
)
from src.modules.ingest.domain.entities import Document, DocumentMetadata, DocumentType
from src.core.exceptions import ValidationError, DocumentProcessingError


@pytest.fixture
def mock_document_service():
    """Mock Document Service"""
    return AsyncMock()


@pytest.fixture
def mock_event_publisher():
    """Mock Event Publisher"""
    return AsyncMock()


@pytest.fixture
def parse_email_use_case(mock_document_service, mock_event_publisher):
    """Parse Email Use Case 인스턴스"""
    return ParseEmailUseCase(
        document_service=mock_document_service,
        event_publisher=mock_event_publisher,
        max_attachment_size=10 * 1024 * 1024,  # 10MB for testing
        allowed_attachment_types=['.pdf', '.docx', '.txt']
    )


@pytest.fixture
def sample_email_content():
    """테스트용 이메일 내용 (RFC 822 형식)"""
    return b"""From: sender@example.com
To: recipient@example.com
Subject: Test Email Subject
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-ID: <test@example.com>
Content-Type: multipart/mixed; boundary="boundary123"

--boundary123
Content-Type: text/plain; charset=utf-8

This is the email body content.
It contains multiple lines.

Best regards,
Sender

--boundary123
Content-Type: application/pdf; name="test.pdf"
Content-Disposition: attachment; filename="test.pdf"
Content-Transfer-Encoding: base64

JVBERi0xLjQKJcOkw7zDtsO4CjIgMCBvYmoKPDwKL0xlbmd0aCAzIDAgUgo+PgpzdHJlYW0K

--boundary123--
"""


@pytest.fixture
def sample_document():
    """테스트용 문서 엔티티"""
    user_id = uuid4()
    metadata = DocumentMetadata(file_size=1024, mime_type="text/plain")
    
    return Document.create(
        user_id=user_id,
        filename="email_Test_Email_Subject_20240101.txt",
        original_filename="email_Test_Email_Subject_20240101.txt",
        file_path="/uploads/email.txt",
        document_type=DocumentType.TXT,
        metadata=metadata,
        tags=["email", "main"]
    )


class TestParseEmailUseCase:
    """이메일 파싱 유즈케이스 테스트"""

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        parse_email_use_case,
        mock_document_service,
        mock_event_publisher,
        sample_email_content,
        sample_document
    ):
        """이메일 파싱 성공 테스트"""
        # Given
        user_id = uuid4()
        command = EmailParseCommand(
            user_id=user_id,
            email_content=sample_email_content,
            tags=["test"]
        )
        
        # Mock 설정
        mock_document_service.upload_document.return_value = sample_document
        
        # When
        result = await parse_email_use_case.execute(command)
        
        # Then
        assert isinstance(result, EmailParseResult)
        assert result.main_document == sample_document
        assert isinstance(result.attachment_documents, list)
        assert isinstance(result.email_metadata, dict)
        
        # 문서 서비스 호출 확인
        mock_document_service.upload_document.assert_called()
        
        # 이벤트 발행 확인
        mock_event_publisher.publish_email_parsed.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_invalid_email_format(
        self,
        parse_email_use_case,
        mock_document_service
    ):
        """잘못된 이메일 형식 테스트"""
        # Given
        user_id = uuid4()
        # 완전히 잘못된 이메일 형식 (헤더가 없음)
        invalid_email_content = b"\x00\x01\x02\x03"  # 바이너리 데이터
        command = EmailParseCommand(
            user_id=user_id,
            email_content=invalid_email_content
        )
        
        # When & Then
        with pytest.raises(DocumentProcessingError):
            await parse_email_use_case.execute(command)

    @pytest.mark.asyncio
    async def test_execute_document_service_failure(
        self,
        parse_email_use_case,
        mock_document_service,
        sample_email_content
    ):
        """문서 서비스 실패 테스트"""
        # Given
        user_id = uuid4()
        command = EmailParseCommand(
            user_id=user_id,
            email_content=sample_email_content
        )
        
        mock_document_service.upload_document.side_effect = Exception("Upload failed")
        
        # When & Then
        with pytest.raises(DocumentProcessingError):
            await parse_email_use_case.execute(command)


class TestEmailParsing:
    """이메일 파싱 로직 테스트"""

    def test_parse_email_content_success(
        self,
        parse_email_use_case,
        sample_email_content
    ):
        """이메일 내용 파싱 성공 테스트"""
        # When
        parsed_email = parse_email_use_case._parse_email_content(sample_email_content)
        
        # Then
        assert isinstance(parsed_email, ParsedEmail)
        assert parsed_email.subject == "Test Email Subject"
        assert parsed_email.sender == "sender@example.com"
        assert "recipient@example.com" in parsed_email.recipients
        assert "This is the email body content" in parsed_email.body_text
        assert len(parsed_email.attachments) > 0

    def test_parse_email_content_simple_text(
        self,
        parse_email_use_case
    ):
        """단순 텍스트 이메일 파싱 테스트"""
        # Given
        simple_email = b"""From: sender@example.com
To: recipient@example.com
Subject: Simple Email
Content-Type: text/plain

This is a simple email body.
"""
        
        # When
        parsed_email = parse_email_use_case._parse_email_content(simple_email)
        
        # Then
        assert parsed_email.subject == "Simple Email"
        assert parsed_email.sender == "sender@example.com"
        assert parsed_email.body_text == "This is a simple email body."
        assert len(parsed_email.attachments) == 0

    def test_decode_header_with_encoding(
        self,
        parse_email_use_case
    ):
        """인코딩된 헤더 디코딩 테스트"""
        # Given
        encoded_header = "=?UTF-8?B?7ZWc6riA7Ja0IOygnOuqqQ==?="  # "한글어 제목" in base64
        
        # When
        decoded = parse_email_use_case._decode_header(encoded_header)
        
        # Then
        assert decoded == "한글어 제목"

    def test_parse_recipients_multiple(
        self,
        parse_email_use_case
    ):
        """다중 수신자 파싱 테스트"""
        # Given
        email_content = b"""From: sender@example.com
To: user1@example.com, user2@example.com
Cc: user3@example.com
Subject: Test

Body content
"""
        
        # When
        parsed_email = parse_email_use_case._parse_email_content(email_content)
        
        # Then
        assert len(parsed_email.recipients) == 3
        assert "user1@example.com" in parsed_email.recipients
        assert "user2@example.com" in parsed_email.recipients
        assert "user3@example.com" in parsed_email.recipients


class TestAttachmentHandling:
    """첨부파일 처리 테스트"""

    def test_extract_attachments_success(
        self,
        parse_email_use_case,
        sample_email_content
    ):
        """첨부파일 추출 성공 테스트"""
        # When
        parsed_email = parse_email_use_case._parse_email_content(sample_email_content)
        
        # Then
        assert len(parsed_email.attachments) > 0
        attachment = parsed_email.attachments[0]
        assert attachment.filename == "test.pdf"
        assert attachment.content_type == "application/pdf"
        assert len(attachment.content) > 0

    def test_is_allowed_attachment_valid(
        self,
        parse_email_use_case
    ):
        """허용된 첨부파일 타입 테스트"""
        # Given
        valid_filenames = ["document.pdf", "report.docx", "notes.txt"]
        
        # When & Then
        for filename in valid_filenames:
            assert parse_email_use_case._is_allowed_attachment(filename) is True

    def test_is_allowed_attachment_invalid(
        self,
        parse_email_use_case
    ):
        """허용되지 않은 첨부파일 타입 테스트"""
        # Given
        invalid_filenames = ["virus.exe", "script.js", "image.jpg"]
        
        # When & Then
        for filename in invalid_filenames:
            assert parse_email_use_case._is_allowed_attachment(filename) is False

    @pytest.mark.asyncio
    async def test_create_attachment_documents_success(
        self,
        parse_email_use_case,
        mock_document_service
    ):
        """첨부파일 문서 생성 성공 테스트"""
        # Given
        user_id = uuid4()
        parent_document_id = uuid4()
        command = EmailParseCommand(user_id=user_id, email_content=b"", tags=["test"])
        
        parsed_email = ParsedEmail(
            subject="Test",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            date=None,
            body_text="Body",
            body_html=None,
            attachments=[
                EmailAttachment(
                    filename="test.pdf",
                    content=b"PDF content",
                    content_type="application/pdf",
                    size=100
                )
            ],
            message_id="test@example.com",
            headers={}
        )
        
        mock_document = MagicMock()
        mock_document_service.upload_document.return_value = mock_document
        
        # When
        result = await parse_email_use_case._create_attachment_documents(
            command, parsed_email, parent_document_id
        )
        
        # Then
        assert len(result) == 1
        assert result[0] == mock_document
        mock_document_service.upload_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_attachment_documents_skip_unsupported(
        self,
        parse_email_use_case,
        mock_document_service
    ):
        """지원되지 않는 첨부파일 건너뛰기 테스트"""
        # Given
        user_id = uuid4()
        parent_document_id = uuid4()
        command = EmailParseCommand(user_id=user_id, email_content=b"", tags=["test"])
        
        parsed_email = ParsedEmail(
            subject="Test",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            date=None,
            body_text="Body",
            body_html=None,
            attachments=[
                EmailAttachment(
                    filename="virus.exe",  # 지원되지 않는 타입
                    content=b"EXE content",
                    content_type="application/octet-stream",
                    size=100
                )
            ],
            message_id="test@example.com",
            headers={}
        )
        
        # When
        result = await parse_email_use_case._create_attachment_documents(
            command, parsed_email, parent_document_id
        )
        
        # Then
        assert len(result) == 0
        mock_document_service.upload_document.assert_not_called()


class TestEmailFormatting:
    """이메일 포맷팅 테스트"""

    def test_format_email_body(
        self,
        parse_email_use_case
    ):
        """이메일 본문 포맷팅 테스트"""
        # Given
        parsed_email = ParsedEmail(
            subject="Test Subject",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            date=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            body_text="This is the email body.",
            body_html=None,
            attachments=[
                EmailAttachment(
                    filename="test.pdf",
                    content=b"content",
                    content_type="application/pdf",
                    size=100
                )
            ],
            message_id="test@example.com",
            headers={}
        )
        
        # When
        formatted_body = parse_email_use_case._format_email_body(parsed_email)
        
        # Then
        assert "Subject: Test Subject" in formatted_body
        assert "From: sender@example.com" in formatted_body
        assert "To: recipient@example.com" in formatted_body
        assert "This is the email body." in formatted_body
        assert "test.pdf (100 bytes)" in formatted_body

    def test_generate_email_filename(
        self,
        parse_email_use_case
    ):
        """이메일 파일명 생성 테스트"""
        # Given
        parsed_email = ParsedEmail(
            subject="Important Meeting Notes",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            date=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            body_text="Body",
            body_html=None,
            attachments=[],
            message_id="test@example.com",
            headers={}
        )
        
        # When
        filename = parse_email_use_case._generate_email_filename(parsed_email)
        
        # Then
        assert filename == "email_Important Meeting Notes_20240115.txt"

    def test_generate_email_filename_long_subject(
        self,
        parse_email_use_case
    ):
        """긴 제목의 이메일 파일명 생성 테스트"""
        # Given
        long_subject = "This is a very long email subject that exceeds the maximum length limit"
        parsed_email = ParsedEmail(
            subject=long_subject,
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            date=None,
            body_text="Body",
            body_html=None,
            attachments=[],
            message_id="test@example.com",
            headers={}
        )
        
        # When
        filename = parse_email_use_case._generate_email_filename(parsed_email)
        
        # Then
        assert len(filename) <= 60  # 50자 제한 + "email_" + ".txt"
        assert filename.startswith("email_")
        assert filename.endswith(".txt")


class TestMetadataExtraction:
    """메타데이터 추출 테스트"""

    def test_extract_email_metadata(
        self,
        parse_email_use_case
    ):
        """이메일 메타데이터 추출 테스트"""
        # Given
        parsed_email = ParsedEmail(
            subject="Test Subject",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            date=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            body_text="This is the email body.",
            body_html="<p>This is the email body.</p>",
            attachments=[
                EmailAttachment(
                    filename="test.pdf",
                    content=b"content",
                    content_type="application/pdf",
                    size=100
                )
            ],
            message_id="test@example.com",
            headers={}
        )
        
        # When
        metadata = parse_email_use_case._extract_email_metadata(parsed_email)
        
        # Then
        assert metadata["subject"] == "Test Subject"
        assert metadata["sender"] == "sender@example.com"
        assert metadata["recipients"] == ["recipient@example.com"]
        assert metadata["date"] == "2024-01-01T12:00:00+00:00"
        assert metadata["message_id"] == "test@example.com"
        assert metadata["attachment_count"] == 1
        assert metadata["has_html"] is True
        assert metadata["body_length"] == len("This is the email body.")
