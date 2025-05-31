"""
로깅 모듈 단위 테스트
"""

import pytest
from unittest.mock import patch, MagicMock
import structlog

from src.core.logging import (
    setup_logging,
    get_logger,
    LoggerMixin,
    log_function_call,
    log_error,
    log_performance
)


class TestLoggingSetup:
    """로깅 설정 테스트"""
    
    @patch('src.core.logging.settings')
    @patch('structlog.configure')
    def test_setup_logging_debug_mode(self, mock_configure, mock_settings):
        """디버그 모드 로깅 설정 테스트"""
        mock_settings.debug = True
        mock_settings.log_level = "DEBUG"
        
        setup_logging()
        
        # structlog.configure가 호출되었는지 확인
        mock_configure.assert_called_once()
        
        # 호출된 인자 확인
        call_args = mock_configure.call_args
        processors = call_args[1]['processors']
        
        # 마지막 프로세서가 ConsoleRenderer인지 확인 (디버그 모드)
        assert any('ConsoleRenderer' in str(processor) for processor in processors)
    
    @patch('src.core.logging.settings')
    @patch('structlog.configure')
    def test_setup_logging_production_mode(self, mock_configure, mock_settings):
        """프로덕션 모드 로깅 설정 테스트"""
        mock_settings.debug = False
        mock_settings.log_level = "INFO"
        
        setup_logging()
        
        # structlog.configure가 호출되었는지 확인
        mock_configure.assert_called_once()
        
        # 호출된 인자 확인
        call_args = mock_configure.call_args
        processors = call_args[1]['processors']
        
        # 마지막 프로세서가 JSONRenderer인지 확인 (프로덕션 모드)
        assert any('JSONRenderer' in str(processor) for processor in processors)


class TestGetLogger:
    """로거 인스턴스 테스트"""
    
    @patch('structlog.get_logger')
    def test_get_logger(self, mock_get_logger):
        """로거 인스턴스 반환 테스트"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        logger = get_logger("test_module")
        
        mock_get_logger.assert_called_once_with("test_module")
        assert logger == mock_logger


class TestLoggerMixin:
    """로거 믹스인 테스트"""
    
    def test_logger_mixin(self):
        """로거 믹스인 속성 테스트"""
        class TestClass(LoggerMixin):
            pass
        
        test_instance = TestClass()
        
        # logger 속성이 존재하는지 확인
        assert hasattr(test_instance, 'logger')
        
        # logger가 structlog 로거인지 확인 (BoundLoggerLazyProxy일 수 있음)
        logger = test_instance.logger
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')


class TestLogHelpers:
    """로그 헬퍼 함수 테스트"""
    
    def test_log_function_call(self):
        """함수 호출 로그 컨텍스트 테스트"""
        result = log_function_call("test_function", param1="value1", param2=123)
        
        expected = {
            "function": "test_function",
            "parameters": {"param1": "value1", "param2": 123},
            "log_event": "function_call"
        }
        
        assert result == expected
    
    def test_log_function_call_no_params(self):
        """파라미터 없는 함수 호출 로그 테스트"""
        result = log_function_call("simple_function")
        
        expected = {
            "function": "simple_function",
            "parameters": {},
            "log_event": "function_call"
        }
        
        assert result == expected
    
    def test_log_error_basic(self):
        """기본 에러 로그 컨텍스트 테스트"""
        error = ValueError("Test error message")
        result = log_error(error)
        
        expected = {
            "error_type": "ValueError",
            "error_message": "Test error message",
            "log_event": "error"
        }
        
        assert result == expected
    
    def test_log_error_with_context(self):
        """컨텍스트가 있는 에러 로그 테스트"""
        error = RuntimeError("Runtime error")
        context = {"user_id": "123", "operation": "file_upload"}
        
        result = log_error(error, context)
        
        expected = {
            "error_type": "RuntimeError",
            "error_message": "Runtime error",
            "log_event": "error",
            "user_id": "123",
            "operation": "file_upload"
        }
        
        assert result == expected
    
    def test_log_performance(self):
        """성능 로그 컨텍스트 테스트"""
        result = log_performance("database_query", 0.1234, query_type="SELECT")
        
        expected = {
            "operation": "database_query",
            "duration_ms": 123.4,
            "log_event": "performance",
            "query_type": "SELECT"
        }
        
        assert result == expected
    
    def test_log_performance_rounding(self):
        """성능 로그 시간 반올림 테스트"""
        result = log_performance("api_call", 0.123456789)
        
        # 소수점 둘째 자리까지 반올림되는지 확인
        assert result["duration_ms"] == 123.46
    
    def test_log_performance_with_additional_data(self):
        """추가 데이터가 있는 성능 로그 테스트"""
        result = log_performance(
            "file_processing", 
            2.5, 
            file_size=1024, 
            file_type="pdf"
        )
        
        expected = {
            "operation": "file_processing",
            "duration_ms": 2500.0,
            "log_event": "performance",
            "file_size": 1024,
            "file_type": "pdf"
        }
        
        assert result == expected


class TestIntegration:
    """통합 테스트"""
    
    def test_logger_mixin_integration(self):
        """로거 믹스인 통합 테스트"""
        class TestService(LoggerMixin):
            def process_data(self, data):
                # event 키워드 충돌을 피하기 위해 별도로 처리
                log_context = log_function_call("process_data", data=data)
                self.logger.info("Processing data", **log_context)
                return f"processed_{data}"
        
        service = TestService()
        
        # 로거가 정상적으로 작동하는지 확인
        assert hasattr(service, 'logger')
        
        # 메서드 실행이 정상적으로 되는지 확인
        result = service.process_data("test_data")
        assert result == "processed_test_data"
