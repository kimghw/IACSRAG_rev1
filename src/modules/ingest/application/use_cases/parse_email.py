"""
UC-01: 이메일 파싱 유즈케이스

이메일 메시지를 파싱하여 본문과 첨부파일을 추출하고,
문서로 저장하는 비즈니스 로직을 담당합니다.
"""

import email
import email.policy
from email.message import EmailMessage
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass
import base64
import mimetypes

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
from src.modules.ingest.application.ports.event_publisher import EventPublisherPort


logger = get_logger(__name__)


@dataclass
class EmailParseCommand:
    """이메일 파싱 명령"""
    user_id: UUID
    email_content: bytes  # 원본 이메일 내용 (RFC 822 형식)
    source: str = "email"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class EmailParseResult:
    """이메일 파싱 결과"""
    main_document: Document  # 이메일 본문 문서
    attachment_documents: List[Document]  # 첨부파일 문서들
    email_metadata: Dict[str, Any]  # 이메일 메타데이터


@dataclass
class ParsedEmail:
    """파싱된 이메일 정보"""
    subject: str
    sender: str
    recipients: List[str]
    date: Optional[datetime]
    body_text: str
    body_html: Optional[str]
    attachments: List['EmailAttachment']
    message_id: str
    headers: Dict[str, str]


@dataclass
class EmailAttachment:
    """이메일 첨부파일"""
    filename: str
    content: bytes
    content_type: str
    size: int


class ParseEmailUseCase:
    """
    UC-01: 이메일 파싱 유즈케이스
    
    이메일 메시지를 파싱하여 본문과 첨부파일을 추출하고,
    각각을 별도의 문서로 저장합니다.
    """
    
    def __init__(
        self,
        document_service: DocumentService,
        event_publisher: EventPublisherPort,
        max_attachment_size: int = 50 * 1024 * 1024,  # 50MB
        allowed_attachment_types: List[str] = None
    ):
        self.document_service = document_service
        self.event_publisher = event_publisher
        self.max_attachment_size = max_attachment_size
        self.allowed_attachment_types = allowed_attachment_types or [
            '.pdf', '.docx', '.doc', '.txt', '.html', '.htm'
        ]
    
    async def execute(self, command: EmailParseCommand) -> EmailParseResult:
        """
        이메일 파싱 실행
        
        Args:
            command: 이메일 파싱 명령
            
        Returns:
            EmailParseResult: 파싱 결과
            
        Raises:
            ValidationError: 이메일 형식 오류
            DocumentProcessingError: 문서 처리 오류
        """
        try:
            logger.info(
                "Starting email parsing",
                extra={
                    "user_id": str(command.user_id),
                    "source": command.source,
                    "email_size": len(command.email_content)
                }
            )
            
            # 1. 이메일 파싱
            parsed_email = self._parse_email_content(command.email_content)
            
            # 2. 이메일 본문 문서 생성
            main_document = await self._create_main_document(
                command, parsed_email
            )
            
            # 3. 첨부파일 문서들 생성
            attachment_documents = await self._create_attachment_documents(
                command, parsed_email, main_document.id
            )
            
            # 4. 이벤트 발행
            await self._publish_email_parsed_event(
                command.user_id,
                main_document,
                attachment_documents,
                parsed_email
            )
            
            result = EmailParseResult(
                main_document=main_document,
                attachment_documents=attachment_documents,
                email_metadata=self._extract_email_metadata(parsed_email)
            )
            
            logger.info(
                "Email parsing completed successfully",
                extra={
                    "user_id": str(command.user_id),
                    "main_document_id": str(main_document.id),
                    "attachment_count": len(attachment_documents),
                    "subject": parsed_email.subject
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Failed to parse email: {e}",
                extra={
                    "user_id": str(command.user_id),
                    "error": str(e)
                }
            )
            raise DocumentProcessingError(
                f"Email parsing failed: {e}",
                details={"user_id": str(command.user_id)}
            )
    
    def _parse_email_content(self, email_content: bytes) -> ParsedEmail:
        """
        이메일 내용 파싱
        
        Args:
            email_content: 원본 이메일 내용
            
        Returns:
            ParsedEmail: 파싱된 이메일 정보
        """
        try:
            # 기본적인 이메일 형식 검증
            if not self._is_valid_email_format(email_content):
                raise ValidationError(
                    "Invalid email format: Missing required headers",
                    details={"content_length": len(email_content)}
                )
            
            # RFC 822 형식의 이메일 파싱
            msg = email.message_from_bytes(
                email_content, 
                policy=email.policy.default
            )
            
            # 기본 헤더 정보 추출
            subject = self._decode_header(msg.get('Subject', ''))
            sender = self._decode_header(msg.get('From', ''))
            recipients = self._parse_recipients(msg)
            date = self._parse_date(msg.get('Date'))
            message_id = msg.get('Message-ID', '')
            
            # 본문 추출
            body_text, body_html = self._extract_body(msg)
            
            # 첨부파일 추출
            attachments = self._extract_attachments(msg)
            
            # 헤더 정보 수집
            headers = dict(msg.items())
            
            return ParsedEmail(
                subject=subject,
                sender=sender,
                recipients=recipients,
                date=date,
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                message_id=message_id,
                headers=headers
            )
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                f"Invalid email format: {e}",
                details={"parsing_error": str(e)}
            )
    
    def _decode_header(self, header_value: str) -> str:
        """헤더 값 디코딩"""
        if not header_value:
            return ""
        
        try:
            decoded_parts = email.header.decode_header(header_value)
            decoded_string = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding)
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += part
            
            return decoded_string.strip()
        except Exception:
            return header_value
    
    def _parse_recipients(self, msg: EmailMessage) -> List[str]:
        """수신자 목록 파싱"""
        recipients = []
        
        for header in ['To', 'Cc', 'Bcc']:
            value = msg.get(header)
            if value:
                recipients.extend([
                    addr.strip() for addr in value.split(',')
                ])
        
        return recipients
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """날짜 파싱"""
        if not date_str:
            return None
        
        try:
            return email.utils.parsedate_to_datetime(date_str)
        except Exception:
            return None
    
    def _extract_body(self, msg: EmailMessage) -> Tuple[str, Optional[str]]:
        """이메일 본문 추출"""
        body_text = ""
        body_html = None
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                
                if content_type == 'text/plain':
                    charset = part.get_content_charset() or 'utf-8'
                    content = part.get_payload(decode=True)
                    if content:
                        body_text += content.decode(charset, errors='ignore')
                
                elif content_type == 'text/html':
                    charset = part.get_content_charset() or 'utf-8'
                    content = part.get_payload(decode=True)
                    if content:
                        body_html = content.decode(charset, errors='ignore')
        else:
            content_type = msg.get_content_type()
            charset = msg.get_content_charset() or 'utf-8'
            content = msg.get_payload(decode=True)
            
            if content:
                if content_type == 'text/plain':
                    body_text = content.decode(charset, errors='ignore')
                elif content_type == 'text/html':
                    body_html = content.decode(charset, errors='ignore')
        
        return body_text.strip(), body_html
    
    def _extract_attachments(self, msg: EmailMessage) -> List[EmailAttachment]:
        """첨부파일 추출"""
        attachments = []
        
        for part in msg.walk():
            # 첨부파일인지 확인
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if not filename:
                    continue
                
                # 파일명 디코딩
                filename = self._decode_header(filename)
                
                # 내용 추출
                content = part.get_payload(decode=True)
                if not content:
                    continue
                
                content_type = part.get_content_type()
                size = len(content)
                
                # 크기 제한 확인
                if size > self.max_attachment_size:
                    logger.warning(
                        f"Attachment too large: {filename} ({size} bytes)",
                        extra={"filename": filename, "size": size}
                    )
                    continue
                
                attachments.append(EmailAttachment(
                    filename=filename,
                    content=content,
                    content_type=content_type,
                    size=size
                ))
        
        return attachments
    
    async def _create_main_document(
        self,
        command: EmailParseCommand,
        parsed_email: ParsedEmail
    ) -> Document:
        """이메일 본문 문서 생성"""
        
        # 이메일 본문을 텍스트로 구성
        email_body = self._format_email_body(parsed_email)
        
        # 파일명 생성 (제목 기반)
        filename = self._generate_email_filename(parsed_email)
        
        # 태그에 이메일 관련 정보 추가
        tags = command.tags.copy()
        tags.extend(['email', 'main'])
        if parsed_email.sender:
            tags.append(f"from:{parsed_email.sender}")
        
        return await self.document_service.upload_document(
            user_id=command.user_id,
            filename=filename,
            file_content=email_body.encode('utf-8'),
            content_type='text/plain',
            tags=tags,
            source=command.source
        )
    
    async def _create_attachment_documents(
        self,
        command: EmailParseCommand,
        parsed_email: ParsedEmail,
        parent_document_id: UUID
    ) -> List[Document]:
        """첨부파일 문서들 생성"""
        
        attachment_documents = []
        
        for attachment in parsed_email.attachments:
            # 허용된 파일 타입인지 확인
            if not self._is_allowed_attachment(attachment.filename):
                logger.info(
                    f"Skipping unsupported attachment: {attachment.filename}",
                    extra={"filename": attachment.filename}
                )
                continue
            
            try:
                # 태그에 첨부파일 정보 추가
                tags = command.tags.copy()
                tags.extend(['email', 'attachment'])
                tags.append(f"parent:{parent_document_id}")
                
                document = await self.document_service.upload_document(
                    user_id=command.user_id,
                    filename=attachment.filename,
                    file_content=attachment.content,
                    content_type=attachment.content_type,
                    tags=tags,
                    source=command.source
                )
                
                attachment_documents.append(document)
                
            except Exception as e:
                logger.error(
                    f"Failed to create document for attachment: {attachment.filename}",
                    extra={
                        "filename": attachment.filename,
                        "error": str(e)
                    }
                )
                # 첨부파일 처리 실패는 전체 프로세스를 중단하지 않음
                continue
        
        return attachment_documents
    
    def _format_email_body(self, parsed_email: ParsedEmail) -> str:
        """이메일 본문 포맷팅"""
        lines = []
        
        # 헤더 정보
        lines.append(f"Subject: {parsed_email.subject}")
        lines.append(f"From: {parsed_email.sender}")
        lines.append(f"To: {', '.join(parsed_email.recipients)}")
        
        if parsed_email.date:
            lines.append(f"Date: {parsed_email.date.isoformat()}")
        
        if parsed_email.message_id:
            lines.append(f"Message-ID: {parsed_email.message_id}")
        
        lines.append("")  # 빈 줄
        lines.append("--- Email Body ---")
        lines.append("")
        
        # 본문 내용
        if parsed_email.body_text:
            lines.append(parsed_email.body_text)
        elif parsed_email.body_html:
            # HTML이 있고 텍스트가 없는 경우 HTML을 포함
            lines.append("--- HTML Content ---")
            lines.append(parsed_email.body_html)
        
        # 첨부파일 목록
        if parsed_email.attachments:
            lines.append("")
            lines.append("--- Attachments ---")
            for attachment in parsed_email.attachments:
                lines.append(f"- {attachment.filename} ({attachment.size} bytes)")
        
        return "\n".join(lines)
    
    def _generate_email_filename(self, parsed_email: ParsedEmail) -> str:
        """이메일 파일명 생성"""
        subject = parsed_email.subject or "No Subject"
        
        # 파일명에 사용할 수 없는 문자 제거
        safe_subject = "".join(
            c for c in subject if c.isalnum() or c in (' ', '-', '_')
        ).strip()
        
        # 길이 제한
        if len(safe_subject) > 50:
            safe_subject = safe_subject[:50]
        
        # 날짜 추가
        date_str = ""
        if parsed_email.date:
            date_str = f"_{parsed_email.date.strftime('%Y%m%d')}"
        
        return f"email_{safe_subject}{date_str}.txt"
    
    def _is_allowed_attachment(self, filename: str) -> bool:
        """첨부파일 허용 여부 확인"""
        if not filename:
            return False
        
        # 확장자 추출
        _, ext = filename.rsplit('.', 1) if '.' in filename else ('', '')
        ext = f".{ext.lower()}"
        
        return ext in self.allowed_attachment_types
    
    def _extract_email_metadata(self, parsed_email: ParsedEmail) -> Dict[str, Any]:
        """이메일 메타데이터 추출"""
        return {
            "subject": parsed_email.subject,
            "sender": parsed_email.sender,
            "recipients": parsed_email.recipients,
            "date": parsed_email.date.isoformat() if parsed_email.date else None,
            "message_id": parsed_email.message_id,
            "attachment_count": len(parsed_email.attachments),
            "has_html": parsed_email.body_html is not None,
            "body_length": len(parsed_email.body_text)
        }
    
    async def _publish_email_parsed_event(
        self,
        user_id: UUID,
        main_document: Document,
        attachment_documents: List[Document],
        parsed_email: ParsedEmail
    ) -> None:
        """이메일 파싱 완료 이벤트 발행"""
        
        try:
            await self.event_publisher.publish_email_parsed(
                user_id=user_id,
                main_document_id=main_document.id,
                attachment_document_ids=[doc.id for doc in attachment_documents],
                email_metadata=self._extract_email_metadata(parsed_email)
            )
        except Exception as e:
            logger.error(
                f"Failed to publish email parsed event: {e}",
                extra={
                    "user_id": str(user_id),
                    "main_document_id": str(main_document.id),
                    "error": str(e)
                }
            )
            # 이벤트 발행 실패는 전체 프로세스를 중단하지 않음
    
    def _is_valid_email_format(self, email_content: bytes) -> bool:
        """
        기본적인 이메일 형식 검증
        
        Args:
            email_content: 이메일 내용
            
        Returns:
            bool: 유효한 이메일 형식 여부
        """
        try:
            # 바이너리 데이터나 너무 짧은 내용 체크
            if len(email_content) < 10:
                return False
            
            # UTF-8로 디코딩 가능한지 확인
            try:
                content_str = email_content.decode('utf-8', errors='strict')
            except UnicodeDecodeError:
                # 바이너리 데이터인 경우
                return False
            
            # 기본적인 이메일 헤더가 있는지 확인
            lines = content_str.split('\n')
            has_header = False
            
            for line in lines[:10]:  # 처음 10줄만 확인
                if ':' in line and not line.startswith(' ') and not line.startswith('\t'):
                    # 헤더 형식인지 확인 (key: value)
                    key = line.split(':', 1)[0].strip()
                    if key and key.replace('-', '').replace('_', '').isalnum():
                        has_header = True
                        break
            
            return has_header
            
        except Exception:
            return False
