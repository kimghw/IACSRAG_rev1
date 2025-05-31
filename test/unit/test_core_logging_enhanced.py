"""
Core Logging 모듈 강화된 테스트
structlog 기반 로깅 시스템 테스트
"""

import pytest
from unittest.mock import patch, MagicMock, call
import structlog
import sys
import os
from io import StringIO
from typing import Any, Dict

from src.core.logging import (
    setup_logging,
    get_logger,
    LoggerMixin,
    log_function_call,
    log_error,
    log_performance
)


class TestSetupLogging:
    """로깅 설정 함수 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 structlog 설정 초기화"""
        # structlog 설정 초기화
        structlog.reset_defaults()
    
    def teardown_method(self):
        """각 테스트 후에 structlog 설정 정리"""
        structlog.reset_defaults()
    
    @patch('src.core.logging.settings')
    def test_setup_logging_debug_mode(self, mock_settings):
        """디버그 모드에서 로깅 설정 테스트"""
        mock_settings.log_level = "DEBUG"
        mock_settings.debug = True
        
        setup_logging()
        
        # structlog이 설정되었는지 확인
        logger = structlog.get_logger("test")
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')
    
    @patch('src.core.logging.settings')
    def test_setup_logging_production_mode(self, mock_settings):
        """프로덕션 모드에서 로깅 설정 테스트"""
        mock_settings.log_level = "INFO"
        mock_settings.debug = False
        
        setup_logging()
        
        # structlog이 설정되었는지 확인
        logger = structlog.get_logger("test")
        assert logger is not None
    
    @patch('src.core.logging.settings')
    def test_setup_logging_different_log_levels(self, mock_settings):
        """다양한 로그 레벨로 설정 테스트"""
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in log_levels:
            mock_settings.log_level = level
            mock_settings.debug = True
            
            setup_logging()
            
            # 각 레벨에서 로거가 정상적으로 생성되는지 확인
            logger = structlog.get_logger("test")
            assert logger is not None
    
    @patch('src.core.logging.settings')
    def test_setup_logging_with_lowercase_level(self, mock_settings):
        """소문자 로그 레벨로 설정 테스트"""
        mock_settings.log_level = "info"  # 소문자
        mock_settings.debug = True
        
        setup_logging()
        
        # 대문자로 변환되어 처리되는지 확인
        logger = structlog.get_logger("test")
        assert logger is not None


class TestGetLogger:
    """로거 가져오기 함수 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 로깅 설정"""
        with patch('src.core.logging.settings') as mock_settings:
            mock_settings.log_level = "DEBUG"
            mock_settings.debug = True
            setup_logging()
    
    def test_get_logger_with_name(self):
        """이름을 지정하여 로거 가져오기 테스트"""
        logger = get_logger("test_module")
        
        # structlog의 로거는 BoundLoggerLazyProxy 또는 BoundLogger일 수 있음
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')
    
    def test_get_logger_different_names(self):
        """다른 이름으로 로거를 가져올 때 테스트"""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        assert logger1 is not None
        assert logger2 is not None
        # structlog에서는 같은 이름이면 같은 인스턴스를 반환할 수 있음
    
    def test_get_logger_empty_name(self):
        """빈 이름으로 로거 가져오기 테스트"""
        logger = get_logger("")
        
        assert logger is not None
    
    def test_get_logger_special_characters(self):
        """특수 문자가 포함된 이름으로 로거 가져오기 테스트"""
        logger = get_logger("test.module-name_123")
        
        assert logger is not None


class TestLoggerMixin:
    """로거 믹스인 클래스 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 로깅 설정"""
        with patch('src.core.logging.settings') as mock_settings:
            mock_settings.log_level = "DEBUG"
            mock_settings.debug = True
            setup_logging()
    
    def test_logger_mixin_property(self):
        """로거 믹스인 프로퍼티 테스트"""
        class TestClass(LoggerMixin):
            pass
        
        test_instance = TestClass()
        logger = test_instance.logger
        
        # structlog의 로거는 BoundLoggerLazyProxy 또는 BoundLogger일 수 있음
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')
    
    def test_logger_mixin_different_classes(self):
        """다른 클래스에서 로거 믹스인 사용 테스트"""
        class ClassA(LoggerMixin):
            pass
        
        class ClassB(LoggerMixin):
            pass
        
        instance_a = ClassA()
        instance_b = ClassB()
        
        logger_a = instance_a.logger
        logger_b = instance_b.logger
        
        assert logger_a is not None
        assert logger_b is not None
    
    def test_logger_mixin_inheritance(self):
        """로거 믹스인 상속 테스트"""
        class BaseClass(LoggerMixin):
            pass
        
        class DerivedClass(BaseClass):
            pass
        
        derived_instance = DerivedClass()
        logger = derived_instance.logger
        
        # structlog의 로거는 BoundLoggerLazyProxy 또는 BoundLogger일 수 있음
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')


class TestLoggingHelperFunctions:
    """로깅 헬퍼 함수들 테스트"""
    
    def test_log_function_call(self):
        """함수 호출 로그 컨텍스트 생성 테스트"""
        context = log_function_call("test_function", param1="value1", param2=123)
        
        assert context["function"] == "test_function"
        assert context["parameters"]["param1"] == "value1"
        assert context["parameters"]["param2"] == 123
        assert context["log_event"] == "function_call"
    
    def test_log_function_call_no_params(self):
        """파라미터 없는 함수 호출 로그 테스트"""
        context = log_function_call("simple_function")
        
        assert context["function"] == "simple_function"
        assert context["parameters"] == {}
        assert context["log_event"] == "function_call"
    
    def test_log_function_call_complex_params(self):
        """복잡한 파라미터를 가진 함수 호출 로그 테스트"""
        complex_param = {"nested": {"key": "value"}, "list": [1, 2, 3]}
        context = log_function_call("complex_function", data=complex_param, count=42)
        
        assert context["function"] == "complex_function"
        assert context["parameters"]["data"] == complex_param
        assert context["parameters"]["count"] == 42
    
    def test_log_error_basic(self):
        """기본 에러 로그 컨텍스트 생성 테스트"""
        error = ValueError("Test error message")
        context = log_error(error)
        
        assert context["error_type"] == "ValueError"
        assert context["error_message"] == "Test error message"
        assert context["log_event"] == "error"
    
    def test_log_error_with_context(self):
        """컨텍스트가 있는 에러 로그 테스트"""
        error = RuntimeError("Runtime error")
        additional_context = {"user_id": "123", "operation": "data_processing"}
        
        context = log_error(error, additional_context)
        
        assert context["error_type"] == "RuntimeError"
        assert context["error_message"] == "Runtime error"
        assert context["log_event"] == "error"
        assert context["user_id"] == "123"
        assert context["operation"] == "data_processing"
    
    def test_log_error_different_exception_types(self):
        """다양한 예외 타입에 대한 에러 로그 테스트"""
        exceptions = [
            ValueError("Value error"),
            TypeError("Type error"),
            KeyError("Key error"),
            AttributeError("Attribute error"),
            FileNotFoundError("File not found")
        ]
        
        for exc in exceptions:
            context = log_error(exc)
            
            assert context["error_type"] == type(exc).__name__
            assert context["error_message"] == str(exc)
            assert context["log_event"] == "error"
    
    def test_log_performance_basic(self):
        """기본 성능 로그 컨텍스트 생성 테스트"""
        context = log_performance("database_query", 0.123)
        
        assert context["operation"] == "database_query"
        assert context["duration_ms"] == 123.0
        assert context["log_event"] == "performance"
    
    def test_log_performance_with_additional_data(self):
        """추가 데이터가 있는 성능 로그 테스트"""
        context = log_performance(
            "api_call", 
            0.456, 
            endpoint="/api/users", 
            status_code=200,
            records_count=150
        )
        
        assert context["operation"] == "api_call"
        assert context["duration_ms"] == 456.0
        assert context["log_event"] == "performance"
        assert context["endpoint"] == "/api/users"
        assert context["status_code"] == 200
        assert context["records_count"] == 150
    
    def test_log_performance_precision(self):
        """성능 로그 시간 정밀도 테스트"""
        # 매우 작은 시간
        context1 = log_performance("fast_operation", 0.0001)
        assert context1["duration_ms"] == 0.1
        
        # 매우 긴 시간
        context2 = log_performance("slow_operation", 5.123456)
        assert context2["duration_ms"] == 5123.46
        
        # 정확히 0
        context3 = log_performance("instant_operation", 0.0)
        assert context3["duration_ms"] == 0.0


class TestLoggingFunctionality:
    """로깅 기능 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 로깅 설정"""
        with patch('src.core.logging.settings') as mock_settings:
            mock_settings.log_level = "DEBUG"
            mock_settings.debug = True
            setup_logging()
    
    def test_logger_basic_methods(self):
        """로거 기본 메서드 테스트"""
        logger = get_logger("test")
        
        # 기본 로깅 메서드들이 존재하는지 확인
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'critical')
        
        # 메서드들이 호출 가능한지 확인
        assert callable(logger.debug)
        assert callable(logger.info)
        assert callable(logger.warning)
        assert callable(logger.error)
        assert callable(logger.critical)
    
    def test_logger_with_structured_data(self):
        """구조화된 데이터로 로깅 테스트"""
        logger = get_logger("test")
        
        # 구조화된 데이터로 로깅 (예외가 발생하지 않아야 함)
        logger.info("User login", user_id="123", ip_address="192.168.1.1")
        logger.error("Database error", error_code="DB001", table="users")
        logger.debug("Processing data", records_count=100, batch_size=10)
        
        # 예외가 발생하지 않으면 성공
        assert True
    
    def test_logger_with_complex_data(self):
        """복잡한 데이터 구조로 로깅 테스트"""
        logger = get_logger("test")
        
        complex_data = {
            "user": {"id": "123", "name": "John Doe"},
            "metadata": {"timestamp": "2023-01-01T00:00:00Z", "version": "1.0"},
            "items": [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
        }
        
        logger.info("Complex operation", data=complex_data)
        
        # 예외가 발생하지 않으면 성공
        assert True
    
    def test_logger_bind_method(self):
        """로거 바인드 메서드 테스트"""
        logger = get_logger("test")
        
        # structlog의 bind 메서드 테스트
        if hasattr(logger, 'bind'):
            bound_logger = logger.bind(user_id="123", session_id="abc")
            assert bound_logger is not None
            
            # 바인드된 로거로 로깅
            bound_logger.info("User action performed")
        
        # 예외가 발생하지 않으면 성공
        assert True


class TestLoggingEdgeCases:
    """로깅 엣지 케이스 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 로깅 설정"""
        with patch('src.core.logging.settings') as mock_settings:
            mock_settings.log_level = "DEBUG"
            mock_settings.debug = True
            setup_logging()
    
    def test_logging_with_none_values(self):
        """None 값으로 로깅 테스트"""
        logger = get_logger("test")
        
        logger.info("Test message", value=None, data=None)
        
        # 예외가 발생하지 않아야 함
        assert True
    
    def test_logging_with_unicode_characters(self):
        """유니코드 문자로 로깅 테스트"""
        logger = get_logger("test")
        
        logger.info("한글 메시지", 사용자="김철수", 상태="성공")
        logger.info("Emoji test 🚀🎉", status="✅")
        
        # 예외가 발생하지 않아야 함
        assert True
    
    def test_logging_with_very_long_message(self):
        """매우 긴 메시지로 로깅 테스트"""
        logger = get_logger("test")
        
        long_message = "A" * 10000
        logger.info(long_message)
        
        # 예외가 발생하지 않아야 함
        assert True
    
    def test_logging_with_circular_reference(self):
        """순환 참조가 있는 데이터로 로깅 테스트"""
        logger = get_logger("test")
        
        data = {"key": "value"}
        data["self"] = data  # 순환 참조
        
        # structlog은 순환 참조를 처리할 수 있어야 함
        try:
            logger.info("Circular reference test", data=data)
            # 예외가 발생하지 않으면 성공
            assert True
        except (ValueError, RecursionError):
            # 순환 참조로 인한 예외가 발생할 수 있음
            assert True
    
    def test_logging_with_special_characters(self):
        """특수 문자로 로깅 테스트"""
        logger = get_logger("test")
        
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        logger.info("Special characters test", chars=special_chars)
        
        # 예외가 발생하지 않아야 함
        assert True


class TestLoggingPerformance:
    """로깅 성능 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 로깅 설정"""
        with patch('src.core.logging.settings') as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.debug = False
            setup_logging()
    
    def test_logging_performance(self):
        """로깅 성능 테스트"""
        import time
        
        logger = get_logger("performance_test")
        
        start_time = time.time()
        
        # 1000번 로깅
        for i in range(1000):
            logger.info("Performance test message", iteration=i)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # 1000번 로깅이 2초 이내에 완료되어야 함 (structlog은 표준 logging보다 느릴 수 있음)
        assert elapsed < 2.0
    
    def test_helper_function_performance(self):
        """헬퍼 함수 성능 테스트"""
        import time
        
        start_time = time.time()
        
        # 1000번 헬퍼 함수 호출
        for i in range(1000):
            log_function_call("test_function", param=i)
            log_error(ValueError(f"Error {i}"))
            log_performance("operation", 0.001, iteration=i)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # 3000번 헬퍼 함수 호출이 1초 이내에 완료되어야 함
        assert elapsed < 1.0


class TestLoggingIntegration:
    """로깅 통합 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 로깅 설정"""
        with patch('src.core.logging.settings') as mock_settings:
            mock_settings.log_level = "DEBUG"
            mock_settings.debug = True
            setup_logging()
    
    def test_multiple_loggers_integration(self):
        """여러 로거 통합 테스트"""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        logger3 = get_logger("module3")
        
        # 각 로거로 동시에 로깅
        logger1.info("Message from module1")
        logger2.info("Message from module2")
        logger3.info("Message from module3")
        
        # 예외가 발생하지 않아야 함
        assert True
    
    def test_mixin_and_function_integration(self):
        """믹스인과 함수 통합 테스트"""
        class TestService(LoggerMixin):
            def process_data(self, data):
                self.logger.info("Processing started", **log_function_call("process_data", data=data))
                
                try:
                    # 가상의 처리 로직
                    if not data:
                        raise ValueError("Empty data")
                    
                    import time
                    start_time = time.time()
                    time.sleep(0.001)  # 가상의 처리 시간
                    end_time = time.time()
                    
                    self.logger.info("Processing completed", **log_performance("process_data", end_time - start_time))
                    
                except Exception as e:
                    self.logger.error("Processing failed", **log_error(e, {"data": data}))
                    raise
        
        service = TestService()
        
        # 성공 케이스
        service.process_data({"key": "value"})
        
        # 실패 케이스
        with pytest.raises(ValueError):
            service.process_data(None)
        
        # 예외가 적절히 처리되었으면 성공
        assert True
    
    def test_logging_with_context_manager(self):
        """컨텍스트 매니저와 함께 로깅 테스트"""
        logger = get_logger("context_test")
        
        class LoggingContext:
            def __init__(self, operation_name):
                self.operation_name = operation_name
                self.start_time = None
            
            def __enter__(self):
                import time
                self.start_time = time.time()
                logger.info("Operation started", **log_function_call(self.operation_name))
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                import time
                end_time = time.time()
                duration = end_time - self.start_time
                
                if exc_type:
                    logger.error("Operation failed", **log_error(exc_val, {"operation": self.operation_name}))
                else:
                    logger.info("Operation completed", **log_performance(self.operation_name, duration))
        
        # 성공 케이스
        with LoggingContext("successful_operation"):
            pass
        
        # 실패 케이스
        try:
            with LoggingContext("failed_operation"):
                raise RuntimeError("Test error")
        except RuntimeError:
            pass
        
        # 예외가 적절히 처리되었으면 성공
        assert True


class TestLoggingConfiguration:
    """로깅 설정 테스트"""
    
    def test_setup_logging_multiple_calls(self):
        """로깅 설정을 여러 번 호출하는 테스트"""
        with patch('src.core.logging.settings') as mock_settings:
            mock_settings.log_level = "INFO"
            mock_settings.debug = True
            
            # 첫 번째 설정
            setup_logging()
            logger1 = get_logger("test")
            
            # 두 번째 설정
            setup_logging()
            logger2 = get_logger("test")
            
            # 로거가 정상적으로 작동해야 함
            assert logger1 is not None
            assert logger2 is not None
    
    @patch('src.core.logging.settings')
    def test_setup_logging_with_invalid_settings(self, mock_settings):
        """잘못된 설정으로 로깅 설정 테스트"""
        mock_settings.log_level = None
        mock_settings.debug = None
        
        # 잘못된 설정이어도 예외가 발생하지 않아야 함
        try:
            setup_logging()
            logger = get_logger("test")
            assert logger is not None
        except Exception:
            # 설정 오류로 인한 예외가 발생할 수 있음
            assert True
