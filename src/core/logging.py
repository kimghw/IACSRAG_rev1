"""
구조화된 로깅 설정
"""

import sys
import structlog
from typing import Any, Dict
from structlog.types import Processor

from .config import settings


def setup_logging() -> None:
    """로깅 설정 초기화"""
    
    # 로그 레벨 설정
    log_level = settings.log_level.upper()
    
    # 프로세서 체인 구성
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # 개발 환경에서는 컬러 출력, 프로덕션에서는 JSON
    if settings.debug:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    # structlog 설정
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """구조화된 로거 인스턴스 반환"""
    return structlog.get_logger(name)


class LoggerMixin:
    """로거 믹스인 클래스"""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """클래스별 로거 반환"""
        return get_logger(self.__class__.__name__)


def log_function_call(func_name: str, **kwargs: Any) -> Dict[str, Any]:
    """함수 호출 로그용 컨텍스트 생성"""
    return {
        "function": func_name,
        "parameters": kwargs,
        "log_event": "function_call"
    }


def log_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """에러 로그용 컨텍스트 생성"""
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "log_event": "error"
    }
    
    if context:
        error_context.update(context)
    
    return error_context


def log_performance(operation: str, duration: float, **kwargs: Any) -> Dict[str, Any]:
    """성능 로그용 컨텍스트 생성"""
    return {
        "operation": operation,
        "duration_ms": round(duration * 1000, 2),
        "log_event": "performance",
        **kwargs
    }
