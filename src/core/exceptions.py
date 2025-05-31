"""
애플리케이션 예외 클래스 정의
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class BaseApplicationError(Exception):
    """애플리케이션 기본 예외 클래스"""
    
    def __init__(
        self,
        message: str,
        error_code: str = None,
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """예외를 딕셔너리로 변환"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ValidationError(BaseApplicationError):
    """검증 오류"""
    pass


class NotFoundError(BaseApplicationError):
    """리소스를 찾을 수 없음"""
    pass


class ConflictError(BaseApplicationError):
    """리소스 충돌"""
    pass


class UnauthorizedError(BaseApplicationError):
    """인증 오류"""
    pass


class ForbiddenError(BaseApplicationError):
    """권한 오류"""
    pass


class BusinessRuleViolationError(BaseApplicationError):
    """비즈니스 규칙 위반 오류"""
    pass


class BusinessLogicError(BaseApplicationError):
    """비즈니스 로직 오류"""
    pass


class ExternalServiceError(BaseApplicationError):
    """외부 서비스 오류"""
    pass


class ConfigurationError(BaseApplicationError):
    """설정 오류"""
    pass


# 도메인별 예외 클래스들

class DocumentError(BaseApplicationError):
    """문서 관련 오류"""
    pass


class DocumentNotFoundError(DocumentError, NotFoundError):
    """문서를 찾을 수 없음"""
    pass


class DocumentProcessingError(DocumentError):
    """문서 처리 오류"""
    pass


class UnsupportedFileTypeError(DocumentError, ValidationError):
    """지원하지 않는 파일 형식"""
    pass


class FileSizeExceededError(DocumentError, ValidationError):
    """파일 크기 초과"""
    pass


class TextExtractionError(DocumentError):
    """텍스트 추출 오류"""
    pass


class ChunkingError(DocumentError):
    """청킹 오류"""
    pass


class EmbeddingError(BaseApplicationError):
    """임베딩 관련 오류"""
    pass


class EmbeddingGenerationError(EmbeddingError):
    """임베딩 생성 오류"""
    pass


class VectorStoreError(BaseApplicationError):
    """벡터 저장소 오류"""
    pass


class VectorStoreConnectionError(VectorStoreError, ExternalServiceError):
    """벡터 저장소 연결 오류"""
    pass


class VectorStoreOperationError(VectorStoreError):
    """벡터 저장소 작업 오류"""
    pass


class VectorSearchError(VectorStoreError):
    """벡터 검색 오류"""
    pass


class DatabaseError(BaseApplicationError):
    """데이터베이스 오류"""
    pass


class RepositoryError(BaseApplicationError):
    """리포지토리 계층 오류"""
    pass


class DatabaseConnectionError(DatabaseError, ExternalServiceError):
    """데이터베이스 연결 오류"""
    pass


class EntityNotFoundError(DatabaseError, NotFoundError):
    """엔티티를 찾을 수 없음"""
    pass


class DuplicateEntityError(DatabaseError, ConflictError):
    """중복된 엔티티"""
    pass


class MessageQueueError(BaseApplicationError):
    """메시지 큐 오류"""
    pass


class MessageQueueConnectionError(MessageQueueError, ExternalServiceError):
    """메시지 큐 연결 오류"""
    pass


class MessagePublishError(MessageQueueError):
    """메시지 발행 오류"""
    pass


class MessageConsumeError(MessageQueueError):
    """메시지 소비 오류"""
    pass


class MessagingError(BaseApplicationError):
    """메시징 관련 오류"""
    pass


class MessagingConnectionError(MessagingError, ExternalServiceError):
    """메시징 연결 오류"""
    pass


class SearchError(BaseApplicationError):
    """검색 관련 오류"""
    pass


class SearchQueryError(SearchError, ValidationError):
    """검색 쿼리 오류"""
    pass


class SearchResultError(SearchError):
    """검색 결과 오류"""
    pass


# HTTP 예외 변환 함수들

def to_http_exception(error: BaseApplicationError) -> HTTPException:
    """애플리케이션 예외를 HTTP 예외로 변환"""
    
    # 가장 구체적인 예외부터 순서대로 확인 (상속 관계 고려)
    status_code_mapping = [
        # 가장 구체적인 예외들 먼저
        (FileSizeExceededError, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE),
        (UnsupportedFileTypeError, status.HTTP_400_BAD_REQUEST),
        (DocumentNotFoundError, status.HTTP_404_NOT_FOUND),
        (VectorStoreConnectionError, status.HTTP_502_BAD_GATEWAY),
        (DatabaseConnectionError, status.HTTP_502_BAD_GATEWAY),
        (MessageQueueConnectionError, status.HTTP_502_BAD_GATEWAY),
        (SearchQueryError, status.HTTP_400_BAD_REQUEST),
        
        # 일반적인 예외들
        (ValidationError, status.HTTP_400_BAD_REQUEST),
        (UnauthorizedError, status.HTTP_401_UNAUTHORIZED),
        (ForbiddenError, status.HTTP_403_FORBIDDEN),
        (NotFoundError, status.HTTP_404_NOT_FOUND),
        (ConflictError, status.HTTP_409_CONFLICT),
        (ExternalServiceError, status.HTTP_502_BAD_GATEWAY),
        
        # 기본 예외
        (BaseApplicationError, status.HTTP_500_INTERNAL_SERVER_ERROR),
    ]
    
    # 가장 구체적인 예외 타입부터 확인
    for exception_type, status_code in status_code_mapping:
        if isinstance(error, exception_type):
            return HTTPException(
                status_code=status_code,
                detail=error.to_dict()
            )
    
    # 기본값 (여기에 도달하면 안 됨)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=error.to_dict()
    )


def handle_external_service_error(
    service_name: str,
    original_error: Exception,
    operation: str = None
) -> ExternalServiceError:
    """외부 서비스 오류를 애플리케이션 예외로 변환"""
    
    details = {
        "service": service_name,
        "original_error": str(original_error),
        "error_type": type(original_error).__name__
    }
    
    if operation:
        details["operation"] = operation
    
    message = f"{service_name} 서비스 오류"
    if operation:
        message += f" (작업: {operation})"
    
    return ExternalServiceError(
        message=message,
        error_code=f"{service_name.upper()}_SERVICE_ERROR",
        details=details
    )


def handle_validation_error(
    field: str,
    value: Any,
    constraint: str,
    expected: str = None
) -> ValidationError:
    """검증 오류를 생성하는 헬퍼 함수"""
    
    details = {
        "field": field,
        "value": str(value),
        "constraint": constraint
    }
    
    if expected:
        details["expected"] = expected
    
    message = f"필드 '{field}' 검증 실패: {constraint}"
    
    return ValidationError(
        message=message,
        error_code="VALIDATION_ERROR",
        details=details
    )



class NotificationError(BaseApplicationError):
    """알림 관련 오류"""
    pass


class NotificationSendError(NotificationError):
    """알림 전송 오류"""
    pass


class NotificationConfigError(NotificationError, ConfigurationError):
    """알림 설정 오류"""
    pass



class HealthCheckError(BaseApplicationError):
    """헬스체크 관련 오류"""
    pass


class HealthCheckFailedError(HealthCheckError):
    """헬스체크 실패 오류"""
    pass


class HealthCheckTimeoutError(HealthCheckError):
    """헬스체크 타임아웃 오류"""
    pass



class EmbeddingServiceError(EmbeddingError):
    """임베딩 서비스 오류"""
    pass
