"""
Core Exceptions 모듈 강화된 테스트
실제 예외 클래스들에 맞춘 테스트 케이스
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, status
from typing import Dict, Any, Optional

from src.core.exceptions import (
    BaseApplicationError,
    ValidationError,
    NotFoundError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    BusinessRuleViolationError,
    BusinessLogicError,
    ExternalServiceError,
    ConfigurationError,
    DocumentError,
    DocumentNotFoundError,
    DocumentProcessingError,
    UnsupportedFileTypeError,
    FileSizeExceededError,
    TextExtractionError,
    ChunkingError,
    EmbeddingError,
    EmbeddingGenerationError,
    VectorStoreError,
    VectorStoreConnectionError,
    VectorStoreOperationError,
    VectorSearchError,
    DatabaseError,
    RepositoryError,
    DatabaseConnectionError,
    EntityNotFoundError,
    DuplicateEntityError,
    MessageQueueError,
    MessageQueueConnectionError,
    MessagePublishError,
    MessageConsumeError,
    MessagingError,
    MessagingConnectionError,
    SearchError,
    SearchQueryError,
    SearchResultError,
    NotificationError,
    NotificationSendError,
    NotificationConfigError,
    HealthCheckError,
    HealthCheckFailedError,
    HealthCheckTimeoutError,
    to_http_exception,
    handle_external_service_error,
    handle_validation_error
)


class TestBaseApplicationError:
    """기본 애플리케이션 예외 클래스 테스트"""
    
    def test_basic_exception_creation(self):
        """기본 예외 생성 테스트"""
        exc = BaseApplicationError("Test error")
        
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.error_code == "BaseApplicationError"
        assert exc.details == {}
    
    def test_exception_with_all_parameters(self):
        """모든 파라미터를 포함한 예외 생성 테스트"""
        details = {"field": "value", "code": "E001"}
        exc = BaseApplicationError(
            message="Test error",
            error_code="CUSTOM_ERROR",
            details=details
        )
        
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.error_code == "CUSTOM_ERROR"
        assert exc.details == details
    
    def test_exception_to_dict(self):
        """예외를 딕셔너리로 변환 테스트"""
        details = {"field": "value"}
        exc = BaseApplicationError(
            message="Test error",
            error_code="TEST_001",
            details=details
        )
        
        exc_dict = exc.to_dict()
        
        assert exc_dict["message"] == "Test error"
        assert exc_dict["error_code"] == "TEST_001"
        assert exc_dict["details"] == details
    
    def test_exception_with_none_details(self):
        """None 세부사항을 가진 예외 테스트"""
        exc = BaseApplicationError("Test error", details=None)
        
        assert exc.details == {}
        assert exc.to_dict()["details"] == {}
    
    def test_exception_with_empty_message(self):
        """빈 메시지를 가진 예외 테스트"""
        exc = BaseApplicationError("")
        
        assert str(exc) == ""
        assert exc.message == ""


class TestValidationError:
    """검증 오류 테스트"""
    
    def test_validation_error_creation(self):
        """검증 오류 생성 테스트"""
        exc = ValidationError("Invalid input")
        
        assert str(exc) == "Invalid input"
        assert exc.error_code == "ValidationError"
        assert isinstance(exc, BaseApplicationError)
    
    def test_validation_error_with_details(self):
        """세부사항이 있는 검증 오류 테스트"""
        details = {"field": "email", "value": "invalid-email"}
        exc = ValidationError("Invalid email", details=details)
        
        assert exc.details == details
        assert exc.to_dict()["details"] == details


class TestDocumentErrors:
    """문서 관련 오류 테스트"""
    
    def test_document_error(self):
        """문서 오류 테스트"""
        exc = DocumentError("Document error")
        
        assert str(exc) == "Document error"
        assert isinstance(exc, BaseApplicationError)
    
    def test_document_not_found_error(self):
        """문서를 찾을 수 없음 오류 테스트"""
        exc = DocumentNotFoundError("Document not found")
        
        assert str(exc) == "Document not found"
        assert isinstance(exc, DocumentError)
        assert isinstance(exc, NotFoundError)
        assert isinstance(exc, BaseApplicationError)
    
    def test_unsupported_file_type_error(self):
        """지원하지 않는 파일 형식 오류 테스트"""
        exc = UnsupportedFileTypeError("Unsupported file type")
        
        assert str(exc) == "Unsupported file type"
        assert isinstance(exc, DocumentError)
        assert isinstance(exc, ValidationError)
    
    def test_file_size_exceeded_error(self):
        """파일 크기 초과 오류 테스트"""
        exc = FileSizeExceededError("File too large")
        
        assert str(exc) == "File too large"
        assert isinstance(exc, DocumentError)
        assert isinstance(exc, ValidationError)
    
    def test_text_extraction_error(self):
        """텍스트 추출 오류 테스트"""
        exc = TextExtractionError("Text extraction failed")
        
        assert str(exc) == "Text extraction failed"
        assert isinstance(exc, DocumentError)
    
    def test_chunking_error(self):
        """청킹 오류 테스트"""
        exc = ChunkingError("Chunking failed")
        
        assert str(exc) == "Chunking failed"
        assert isinstance(exc, DocumentError)


class TestEmbeddingErrors:
    """임베딩 관련 오류 테스트"""
    
    def test_embedding_error(self):
        """임베딩 오류 테스트"""
        exc = EmbeddingError("Embedding error")
        
        assert str(exc) == "Embedding error"
        assert isinstance(exc, BaseApplicationError)
    
    def test_embedding_generation_error(self):
        """임베딩 생성 오류 테스트"""
        exc = EmbeddingGenerationError("Embedding generation failed")
        
        assert str(exc) == "Embedding generation failed"
        assert isinstance(exc, EmbeddingError)


class TestVectorStoreErrors:
    """벡터 저장소 오류 테스트"""
    
    def test_vector_store_error(self):
        """벡터 저장소 오류 테스트"""
        exc = VectorStoreError("Vector store error")
        
        assert str(exc) == "Vector store error"
        assert isinstance(exc, BaseApplicationError)
    
    def test_vector_store_connection_error(self):
        """벡터 저장소 연결 오류 테스트"""
        exc = VectorStoreConnectionError("Connection failed")
        
        assert str(exc) == "Connection failed"
        assert isinstance(exc, VectorStoreError)
        assert isinstance(exc, ExternalServiceError)
    
    def test_vector_store_operation_error(self):
        """벡터 저장소 작업 오류 테스트"""
        exc = VectorStoreOperationError("Operation failed")
        
        assert str(exc) == "Operation failed"
        assert isinstance(exc, VectorStoreError)
    
    def test_vector_search_error(self):
        """벡터 검색 오류 테스트"""
        exc = VectorSearchError("Search failed")
        
        assert str(exc) == "Search failed"
        assert isinstance(exc, VectorStoreError)


class TestDatabaseErrors:
    """데이터베이스 오류 테스트"""
    
    def test_database_error(self):
        """데이터베이스 오류 테스트"""
        exc = DatabaseError("Database error")
        
        assert str(exc) == "Database error"
        assert isinstance(exc, BaseApplicationError)
    
    def test_repository_error(self):
        """리포지토리 오류 테스트"""
        exc = RepositoryError("Repository error")
        
        assert str(exc) == "Repository error"
        assert isinstance(exc, BaseApplicationError)
    
    def test_database_connection_error(self):
        """데이터베이스 연결 오류 테스트"""
        exc = DatabaseConnectionError("Connection failed")
        
        assert str(exc) == "Connection failed"
        assert isinstance(exc, DatabaseError)
        assert isinstance(exc, ExternalServiceError)
    
    def test_entity_not_found_error(self):
        """엔티티를 찾을 수 없음 오류 테스트"""
        exc = EntityNotFoundError("Entity not found")
        
        assert str(exc) == "Entity not found"
        assert isinstance(exc, DatabaseError)
        assert isinstance(exc, NotFoundError)
    
    def test_duplicate_entity_error(self):
        """중복된 엔티티 오류 테스트"""
        exc = DuplicateEntityError("Duplicate entity")
        
        assert str(exc) == "Duplicate entity"
        assert isinstance(exc, DatabaseError)
        assert isinstance(exc, ConflictError)


class TestMessageQueueErrors:
    """메시지 큐 오류 테스트"""
    
    def test_message_queue_error(self):
        """메시지 큐 오류 테스트"""
        exc = MessageQueueError("Message queue error")
        
        assert str(exc) == "Message queue error"
        assert isinstance(exc, BaseApplicationError)
    
    def test_message_queue_connection_error(self):
        """메시지 큐 연결 오류 테스트"""
        exc = MessageQueueConnectionError("Connection failed")
        
        assert str(exc) == "Connection failed"
        assert isinstance(exc, MessageQueueError)
        assert isinstance(exc, ExternalServiceError)
    
    def test_message_publish_error(self):
        """메시지 발행 오류 테스트"""
        exc = MessagePublishError("Publish failed")
        
        assert str(exc) == "Publish failed"
        assert isinstance(exc, MessageQueueError)
    
    def test_message_consume_error(self):
        """메시지 소비 오류 테스트"""
        exc = MessageConsumeError("Consume failed")
        
        assert str(exc) == "Consume failed"
        assert isinstance(exc, MessageQueueError)


class TestSearchErrors:
    """검색 오류 테스트"""
    
    def test_search_error(self):
        """검색 오류 테스트"""
        exc = SearchError("Search error")
        
        assert str(exc) == "Search error"
        assert isinstance(exc, BaseApplicationError)
    
    def test_search_query_error(self):
        """검색 쿼리 오류 테스트"""
        exc = SearchQueryError("Invalid query")
        
        assert str(exc) == "Invalid query"
        assert isinstance(exc, SearchError)
        assert isinstance(exc, ValidationError)
    
    def test_search_result_error(self):
        """검색 결과 오류 테스트"""
        exc = SearchResultError("Result error")
        
        assert str(exc) == "Result error"
        assert isinstance(exc, SearchError)


class TestNotificationErrors:
    """알림 오류 테스트"""
    
    def test_notification_error(self):
        """알림 오류 테스트"""
        exc = NotificationError("Notification error")
        
        assert str(exc) == "Notification error"
        assert isinstance(exc, BaseApplicationError)
    
    def test_notification_send_error(self):
        """알림 전송 오류 테스트"""
        exc = NotificationSendError("Send failed")
        
        assert str(exc) == "Send failed"
        assert isinstance(exc, NotificationError)
    
    def test_notification_config_error(self):
        """알림 설정 오류 테스트"""
        exc = NotificationConfigError("Config error")
        
        assert str(exc) == "Config error"
        assert isinstance(exc, NotificationError)
        assert isinstance(exc, ConfigurationError)


class TestHealthCheckErrors:
    """헬스체크 오류 테스트"""
    
    def test_health_check_error(self):
        """헬스체크 오류 테스트"""
        exc = HealthCheckError("Health check error")
        
        assert str(exc) == "Health check error"
        assert isinstance(exc, BaseApplicationError)
    
    def test_health_check_failed_error(self):
        """헬스체크 실패 오류 테스트"""
        exc = HealthCheckFailedError("Health check failed")
        
        assert str(exc) == "Health check failed"
        assert isinstance(exc, HealthCheckError)
    
    def test_health_check_timeout_error(self):
        """헬스체크 타임아웃 오류 테스트"""
        exc = HealthCheckTimeoutError("Health check timeout")
        
        assert str(exc) == "Health check timeout"
        assert isinstance(exc, HealthCheckError)


class TestHTTPExceptionConversion:
    """HTTP 예외 변환 테스트"""
    
    def test_validation_error_to_http(self):
        """검증 오류를 HTTP 예외로 변환 테스트"""
        exc = ValidationError("Invalid input")
        http_exc = to_http_exception(exc)
        
        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == status.HTTP_400_BAD_REQUEST
        assert http_exc.detail == exc.to_dict()
    
    def test_not_found_error_to_http(self):
        """찾을 수 없음 오류를 HTTP 예외로 변환 테스트"""
        exc = NotFoundError("Resource not found")
        http_exc = to_http_exception(exc)
        
        assert http_exc.status_code == status.HTTP_404_NOT_FOUND
    
    def test_unauthorized_error_to_http(self):
        """인증 오류를 HTTP 예외로 변환 테스트"""
        exc = UnauthorizedError("Unauthorized")
        http_exc = to_http_exception(exc)
        
        assert http_exc.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_forbidden_error_to_http(self):
        """권한 오류를 HTTP 예외로 변환 테스트"""
        exc = ForbiddenError("Forbidden")
        http_exc = to_http_exception(exc)
        
        assert http_exc.status_code == status.HTTP_403_FORBIDDEN
    
    def test_conflict_error_to_http(self):
        """충돌 오류를 HTTP 예외로 변환 테스트"""
        exc = ConflictError("Conflict")
        http_exc = to_http_exception(exc)
        
        assert http_exc.status_code == status.HTTP_409_CONFLICT
    
    def test_external_service_error_to_http(self):
        """외부 서비스 오류를 HTTP 예외로 변환 테스트"""
        exc = ExternalServiceError("Service unavailable")
        http_exc = to_http_exception(exc)
        
        assert http_exc.status_code == status.HTTP_502_BAD_GATEWAY
    
    def test_file_size_exceeded_error_to_http(self):
        """파일 크기 초과 오류를 HTTP 예외로 변환 테스트"""
        exc = FileSizeExceededError("File too large")
        http_exc = to_http_exception(exc)
        
        assert http_exc.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    
    def test_document_not_found_error_to_http(self):
        """문서를 찾을 수 없음 오류를 HTTP 예외로 변환 테스트"""
        exc = DocumentNotFoundError("Document not found")
        http_exc = to_http_exception(exc)
        
        assert http_exc.status_code == status.HTTP_404_NOT_FOUND
    
    def test_vector_store_connection_error_to_http(self):
        """벡터 저장소 연결 오류를 HTTP 예외로 변환 테스트"""
        exc = VectorStoreConnectionError("Connection failed")
        http_exc = to_http_exception(exc)
        
        assert http_exc.status_code == status.HTTP_502_BAD_GATEWAY
    
    def test_base_application_error_to_http(self):
        """기본 애플리케이션 오류를 HTTP 예외로 변환 테스트"""
        exc = BaseApplicationError("Generic error")
        http_exc = to_http_exception(exc)
        
        assert http_exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestExceptionHelperFunctions:
    """예외 헬퍼 함수들 테스트"""
    
    def test_handle_external_service_error(self):
        """외부 서비스 오류 처리 테스트"""
        original_error = ConnectionError("Connection refused")
        
        exc = handle_external_service_error(
            service_name="test_service",
            original_error=original_error,
            operation="connect"
        )
        
        assert isinstance(exc, ExternalServiceError)
        assert "test_service 서비스 오류" in str(exc)
        assert exc.error_code == "TEST_SERVICE_SERVICE_ERROR"
        assert exc.details["service"] == "test_service"
        assert exc.details["operation"] == "connect"
        assert exc.details["original_error"] == "Connection refused"
        assert exc.details["error_type"] == "ConnectionError"
    
    def test_handle_external_service_error_without_operation(self):
        """작업 없이 외부 서비스 오류 처리 테스트"""
        original_error = TimeoutError("Timeout")
        
        exc = handle_external_service_error(
            service_name="api_service",
            original_error=original_error
        )
        
        assert isinstance(exc, ExternalServiceError)
        assert "api_service 서비스 오류" in str(exc)
        assert "operation" not in exc.details
    
    def test_handle_validation_error(self):
        """검증 오류 처리 테스트"""
        exc = handle_validation_error(
            field="email",
            value="invalid-email",
            constraint="valid email format",
            expected="user@example.com"
        )
        
        assert isinstance(exc, ValidationError)
        assert "필드 'email' 검증 실패" in str(exc)
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.details["field"] == "email"
        assert exc.details["value"] == "invalid-email"
        assert exc.details["constraint"] == "valid email format"
        assert exc.details["expected"] == "user@example.com"
    
    def test_handle_validation_error_without_expected(self):
        """예상값 없이 검증 오류 처리 테스트"""
        exc = handle_validation_error(
            field="age",
            value=-1,
            constraint="positive integer"
        )
        
        assert isinstance(exc, ValidationError)
        assert exc.details["field"] == "age"
        assert exc.details["value"] == "-1"
        assert "expected" not in exc.details


class TestExceptionInheritance:
    """예외 상속 관계 테스트"""
    
    def test_all_exceptions_inherit_from_base(self):
        """모든 예외가 기본 예외를 상속하는지 테스트"""
        exception_classes = [
            ValidationError, NotFoundError, ConflictError,
            UnauthorizedError, ForbiddenError, BusinessRuleViolationError,
            BusinessLogicError, ExternalServiceError, ConfigurationError,
            DocumentError, DocumentNotFoundError, DocumentProcessingError,
            UnsupportedFileTypeError, FileSizeExceededError, TextExtractionError,
            ChunkingError, EmbeddingError, EmbeddingGenerationError,
            VectorStoreError, VectorStoreConnectionError, VectorStoreOperationError,
            VectorSearchError, DatabaseError, RepositoryError,
            DatabaseConnectionError, EntityNotFoundError, DuplicateEntityError,
            MessageQueueError, MessageQueueConnectionError, MessagePublishError,
            MessageConsumeError, MessagingError, MessagingConnectionError,
            SearchError, SearchQueryError, SearchResultError,
            NotificationError, NotificationSendError, NotificationConfigError,
            HealthCheckError, HealthCheckFailedError, HealthCheckTimeoutError
        ]
        
        for exc_class in exception_classes:
            assert issubclass(exc_class, BaseApplicationError)
    
    def test_multiple_inheritance_exceptions(self):
        """다중 상속 예외들 테스트"""
        # DocumentNotFoundError는 DocumentError와 NotFoundError를 모두 상속
        exc = DocumentNotFoundError("Document not found")
        assert isinstance(exc, DocumentError)
        assert isinstance(exc, NotFoundError)
        assert isinstance(exc, BaseApplicationError)
        
        # UnsupportedFileTypeError는 DocumentError와 ValidationError를 모두 상속
        exc = UnsupportedFileTypeError("Unsupported file")
        assert isinstance(exc, DocumentError)
        assert isinstance(exc, ValidationError)
        assert isinstance(exc, BaseApplicationError)


class TestExceptionEdgeCases:
    """예외 엣지 케이스 테스트"""
    
    def test_exception_with_none_message(self):
        """None 메시지를 가진 예외 테스트"""
        exc = BaseApplicationError(None)
        assert str(exc) == "None"
        assert exc.message is None
    
    def test_exception_with_unicode_message(self):
        """유니코드 메시지를 가진 예외 테스트"""
        exc = BaseApplicationError("한글 오류 메시지")
        assert str(exc) == "한글 오류 메시지"
        assert exc.message == "한글 오류 메시지"
    
    def test_exception_with_very_long_message(self):
        """매우 긴 메시지를 가진 예외 테스트"""
        long_message = "A" * 10000
        exc = BaseApplicationError(long_message)
        assert str(exc) == long_message
        assert exc.message == long_message
    
    def test_exception_with_complex_details(self):
        """복잡한 세부사항을 가진 예외 테스트"""
        complex_details = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "none_value": None,
            "boolean": True,
            "number": 42
        }
        
        exc = BaseApplicationError("Complex error", details=complex_details)
        assert exc.details == complex_details
        assert exc.to_dict()["details"] == complex_details
    
    def test_exception_with_circular_reference_in_details(self):
        """세부사항에 순환 참조가 있는 예외 테스트"""
        details = {"key": "value"}
        details["self"] = details  # 순환 참조
        
        # 순환 참조가 있어도 예외 생성은 가능해야 함
        exc = BaseApplicationError("Test error", details=details)
        assert str(exc) == "Test error"
        
        # to_dict 호출 시 순환 참조가 있어도 오류가 발생하지 않아야 함
        # (실제로는 순환 참조로 인해 문제가 될 수 있지만, 예외 생성 자체는 가능)
        exc_dict = exc.to_dict()
        assert exc_dict["message"] == "Test error"


class TestExceptionPerformance:
    """예외 성능 테스트"""
    
    def test_exception_creation_performance(self):
        """예외 생성 성능 테스트"""
        import time
        
        start_time = time.time()
        
        # 1000개의 예외 생성
        for i in range(1000):
            exc = BaseApplicationError(f"Error {i}", error_code=f"E{i:03d}")
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # 1000개 예외 생성이 1초 이내에 완료되어야 함
        assert elapsed < 1.0
    
    def test_exception_to_dict_performance(self):
        """예외 딕셔너리 변환 성능 테스트"""
        import time
        
        exc = BaseApplicationError(
            "Test error",
            error_code="TEST_001",
            details={"data": list(range(100))}
        )
        
        start_time = time.time()
        
        # 1000번 딕셔너리 변환
        for _ in range(1000):
            exc_dict = exc.to_dict()
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # 1000번 변환이 1초 이내에 완료되어야 함
        assert elapsed < 1.0
    
    def test_http_exception_conversion_performance(self):
        """HTTP 예외 변환 성능 테스트"""
        import time
        
        exc = ValidationError("Test error")
        
        start_time = time.time()
        
        # 1000번 HTTP 예외 변환
        for _ in range(1000):
            http_exc = to_http_exception(exc)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # 1000번 변환이 1초 이내에 완료되어야 함
        assert elapsed < 1.0
