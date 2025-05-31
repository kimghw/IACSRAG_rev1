"""
예외 처리 모듈 단위 테스트
"""

import pytest
from fastapi import HTTPException, status

from src.core.exceptions import (
    BaseApplicationError,
    ValidationError,
    NotFoundError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
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
    VectorSearchError,
    DatabaseError,
    DatabaseConnectionError,
    MessageQueueError,
    MessageQueueConnectionError,
    MessagePublishError,
    MessageConsumeError,
    SearchError,
    SearchQueryError,
    SearchResultError,
    to_http_exception,
    handle_external_service_error,
    handle_validation_error
)


class TestBaseApplicationError:
    """기본 애플리케이션 예외 테스트"""
    
    def test_basic_initialization(self):
        """기본 초기화 테스트"""
        error = BaseApplicationError("Test error message")
        
        assert error.message == "Test error message"
        assert error.error_code == "BaseApplicationError"
        assert error.details == {}
        assert str(error) == "Test error message"
    
    def test_initialization_with_all_params(self):
        """모든 파라미터를 포함한 초기화 테스트"""
        details = {"field": "value", "count": 42}
        error = BaseApplicationError(
            message="Custom error",
            error_code="CUSTOM_ERROR",
            details=details
        )
        
        assert error.message == "Custom error"
        assert error.error_code == "CUSTOM_ERROR"
        assert error.details == details
    
    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        details = {"user_id": "123", "action": "upload"}
        error = BaseApplicationError(
            message="Operation failed",
            error_code="OP_FAILED",
            details=details
        )
        
        result = error.to_dict()
        expected = {
            "error_code": "OP_FAILED",
            "message": "Operation failed",
            "details": details
        }
        
        assert result == expected


class TestSpecificExceptions:
    """특정 예외 클래스들 테스트"""
    
    def test_validation_error(self):
        """검증 오류 테스트"""
        error = ValidationError("Invalid input")
        
        assert isinstance(error, BaseApplicationError)
        assert error.error_code == "ValidationError"
        assert error.message == "Invalid input"
    
    def test_not_found_error(self):
        """리소스 없음 오류 테스트"""
        error = NotFoundError("Resource not found")
        
        assert isinstance(error, BaseApplicationError)
        assert error.error_code == "NotFoundError"
    
    def test_document_not_found_error_inheritance(self):
        """문서 없음 오류 상속 테스트"""
        error = DocumentNotFoundError("Document not found")
        
        # 다중 상속 확인
        assert isinstance(error, DocumentError)
        assert isinstance(error, NotFoundError)
        assert isinstance(error, BaseApplicationError)
    
    def test_unsupported_file_type_error_inheritance(self):
        """지원하지 않는 파일 형식 오류 상속 테스트"""
        error = UnsupportedFileTypeError("Unsupported file type")
        
        assert isinstance(error, DocumentError)
        assert isinstance(error, ValidationError)
        assert isinstance(error, BaseApplicationError)
    
    def test_vector_store_connection_error_inheritance(self):
        """벡터 저장소 연결 오류 상속 테스트"""
        error = VectorStoreConnectionError("Connection failed")
        
        assert isinstance(error, VectorStoreError)
        assert isinstance(error, ExternalServiceError)
        assert isinstance(error, BaseApplicationError)


class TestHttpExceptionConversion:
    """HTTP 예외 변환 테스트"""
    
    def test_validation_error_to_http(self):
        """검증 오류 HTTP 변환 테스트"""
        error = ValidationError("Invalid data")
        http_exc = to_http_exception(error)
        
        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == status.HTTP_400_BAD_REQUEST
        assert http_exc.detail == error.to_dict()
    
    def test_not_found_error_to_http(self):
        """리소스 없음 오류 HTTP 변환 테스트"""
        error = NotFoundError("Resource not found")
        http_exc = to_http_exception(error)
        
        assert http_exc.status_code == status.HTTP_404_NOT_FOUND
        assert http_exc.detail == error.to_dict()
    
    def test_unauthorized_error_to_http(self):
        """인증 오류 HTTP 변환 테스트"""
        error = UnauthorizedError("Authentication required")
        http_exc = to_http_exception(error)
        
        assert http_exc.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_forbidden_error_to_http(self):
        """권한 오류 HTTP 변환 테스트"""
        error = ForbiddenError("Access denied")
        http_exc = to_http_exception(error)
        
        assert http_exc.status_code == status.HTTP_403_FORBIDDEN
    
    def test_conflict_error_to_http(self):
        """충돌 오류 HTTP 변환 테스트"""
        error = ConflictError("Resource conflict")
        http_exc = to_http_exception(error)
        
        assert http_exc.status_code == status.HTTP_409_CONFLICT
    
    def test_file_size_exceeded_error_to_http(self):
        """파일 크기 초과 오류 HTTP 변환 테스트"""
        error = FileSizeExceededError("File too large")
        http_exc = to_http_exception(error)
        
        assert http_exc.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    
    def test_external_service_error_to_http(self):
        """외부 서비스 오류 HTTP 변환 테스트"""
        error = ExternalServiceError("Service unavailable")
        http_exc = to_http_exception(error)
        
        assert http_exc.status_code == status.HTTP_502_BAD_GATEWAY
    
    def test_database_connection_error_to_http(self):
        """데이터베이스 연결 오류 HTTP 변환 테스트"""
        error = DatabaseConnectionError("DB connection failed")
        http_exc = to_http_exception(error)
        
        assert http_exc.status_code == status.HTTP_502_BAD_GATEWAY
    
    def test_document_not_found_error_to_http(self):
        """문서 없음 오류 HTTP 변환 테스트 (다중 상속)"""
        error = DocumentNotFoundError("Document not found")
        http_exc = to_http_exception(error)
        
        # NotFoundError가 더 구체적이므로 404가 되어야 함
        assert http_exc.status_code == status.HTTP_404_NOT_FOUND
    
    def test_unsupported_file_type_error_to_http(self):
        """지원하지 않는 파일 형식 오류 HTTP 변환 테스트"""
        error = UnsupportedFileTypeError("Unsupported file")
        http_exc = to_http_exception(error)
        
        # ValidationError가 더 구체적이므로 400이 되어야 함
        assert http_exc.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_base_application_error_to_http(self):
        """기본 애플리케이션 오류 HTTP 변환 테스트"""
        error = BaseApplicationError("Unknown error")
        http_exc = to_http_exception(error)
        
        assert http_exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestHelperFunctions:
    """헬퍼 함수 테스트"""
    
    def test_handle_external_service_error_basic(self):
        """외부 서비스 오류 처리 기본 테스트"""
        original_error = ConnectionError("Connection timeout")
        
        result = handle_external_service_error("OpenAI", original_error)
        
        assert isinstance(result, ExternalServiceError)
        assert result.message == "OpenAI 서비스 오류"
        assert result.error_code == "OPENAI_SERVICE_ERROR"
        assert result.details["service"] == "OpenAI"
        assert result.details["original_error"] == "Connection timeout"
        assert result.details["error_type"] == "ConnectionError"
    
    def test_handle_external_service_error_with_operation(self):
        """작업 정보가 포함된 외부 서비스 오류 처리 테스트"""
        original_error = ValueError("Invalid API key")
        
        result = handle_external_service_error(
            "Qdrant", 
            original_error, 
            operation="vector_search"
        )
        
        assert result.message == "Qdrant 서비스 오류 (작업: vector_search)"
        assert result.error_code == "QDRANT_SERVICE_ERROR"
        assert result.details["operation"] == "vector_search"
    
    def test_handle_validation_error_basic(self):
        """검증 오류 처리 기본 테스트"""
        result = handle_validation_error(
            field="email",
            value="invalid-email",
            constraint="must be valid email format"
        )
        
        assert isinstance(result, ValidationError)
        assert result.message == "필드 'email' 검증 실패: must be valid email format"
        assert result.error_code == "VALIDATION_ERROR"
        assert result.details["field"] == "email"
        assert result.details["value"] == "invalid-email"
        assert result.details["constraint"] == "must be valid email format"
    
    def test_handle_validation_error_with_expected(self):
        """예상값이 포함된 검증 오류 처리 테스트"""
        result = handle_validation_error(
            field="age",
            value=-5,
            constraint="must be positive",
            expected="positive integer"
        )
        
        assert result.details["expected"] == "positive integer"
        assert result.details["value"] == "-5"


class TestExceptionHierarchy:
    """예외 계층 구조 테스트"""
    
    def test_all_exceptions_inherit_from_base(self):
        """모든 예외가 기본 클래스를 상속하는지 테스트"""
        exceptions_to_test = [
            ValidationError,
            NotFoundError,
            ConflictError,
            UnauthorizedError,
            ForbiddenError,
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
            VectorSearchError,
            DatabaseError,
            DatabaseConnectionError,
            MessageQueueError,
            MessageQueueConnectionError,
            MessagePublishError,
            MessageConsumeError,
            SearchError,
            SearchQueryError,
            SearchResultError
        ]
        
        for exception_class in exceptions_to_test:
            error = exception_class("Test message")
            assert isinstance(error, BaseApplicationError)
            assert isinstance(error, Exception)
    
    def test_domain_specific_inheritance(self):
        """도메인별 예외 상속 구조 테스트"""
        # Document 관련 예외들
        doc_exceptions = [
            DocumentNotFoundError,
            DocumentProcessingError,
            UnsupportedFileTypeError,
            FileSizeExceededError,
            TextExtractionError,
            ChunkingError
        ]
        
        for exception_class in doc_exceptions:
            error = exception_class("Test message")
            assert isinstance(error, DocumentError)
        
        # Embedding 관련 예외들
        embedding_exceptions = [EmbeddingGenerationError]
        
        for exception_class in embedding_exceptions:
            error = exception_class("Test message")
            assert isinstance(error, EmbeddingError)
        
        # VectorStore 관련 예외들
        vector_exceptions = [VectorStoreConnectionError, VectorSearchError]
        
        for exception_class in vector_exceptions:
            error = exception_class("Test message")
            assert isinstance(error, VectorStoreError)
