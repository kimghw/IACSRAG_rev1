"""
IACSRAG - 문서 검색 플랫폼 메인 애플리케이션

FastAPI 기반의 RAG(Retrieval-Augmented Generation) 시스템
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from src.api.v1 import search, monitor
from src.core.config import get_settings
from src.core.dependencies import get_database, get_vector_db, get_kafka_client
from src.core.exceptions import (
    BusinessLogicError,
    ValidationError,
    NotFoundError,
    ExternalServiceError
)
from src.core.logging import setup_logging
from src.core.dependencies import get_container


# 설정 로드
settings = get_settings()

# 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)


def setup_dependencies():
    """의존성 주입 설정"""
    container = get_container()
    
    # Infrastructure 레이어 등록
    from src.infrastructure.database.mongodb import MongoDBClient
    from src.infrastructure.vectordb.qdrant_client import QdrantClient
    from src.infrastructure.messaging.kafka_client import KafkaManager
    
    container.register_singleton(MongoDBClient, MongoDBClient)
    container.register_singleton(QdrantClient, QdrantClient)
    container.register_singleton(KafkaManager, KafkaManager)
    
    # Search 모듈 등록
    from src.modules.search.application.use_cases.search_documents import SearchDocumentsUseCase
    from src.modules.search.application.use_cases.generate_answer import GenerateAnswerUseCase
    from src.modules.search.infrastructure.vector_db import VectorDatabase
    from src.modules.search.application.ports.vector_search_port import VectorSearchPort
    from src.modules.search.application.ports.llm_port import EmbeddingPort, LLMPort
    
    # Port 구현체 등록 (VectorDatabase가 VectorSearchPort를 구현)
    container.register_transient(VectorSearchPort, VectorDatabase)
    container.register_transient(VectorDatabase, VectorDatabase)
    
    # Mock 구현체 등록 (실제 구현체가 없는 경우)
    from unittest.mock import Mock
    container.register_transient(EmbeddingPort, lambda: Mock(spec=EmbeddingPort))
    container.register_transient(LLMPort, lambda: Mock(spec=LLMPort))
    
    container.register_transient(SearchDocumentsUseCase, SearchDocumentsUseCase)
    container.register_transient(GenerateAnswerUseCase, GenerateAnswerUseCase)
    
    # Monitor 모듈 등록
    from src.modules.monitor.application.services.monitor_service import MonitorService
    from src.modules.monitor.application.use_cases.collect_metrics import CollectMetricsUseCase, CollectSystemMetricsUseCase
    from src.modules.monitor.application.use_cases.manage_alerts import CreateAlertRuleUseCase, ProcessMetricAlertUseCase
    from src.modules.monitor.application.use_cases.check_health import CheckComponentHealthUseCase, PerformHealthCheckUseCase
    from src.modules.monitor.application.ports.metric_repository import MetricRepositoryPort
    from src.modules.monitor.application.ports.alert_repository import AlertRepositoryPort
    from src.modules.monitor.application.ports.health_check_port import HealthCheckPort
    from src.modules.monitor.application.ports.notification_port import NotificationPort
    from src.modules.monitor.infrastructure.repositories.mongodb_metric_repository import MongoDBMetricRepository
    from src.modules.monitor.infrastructure.repositories.mongodb_alert_repository import MongoDBAlertRepository
    
    # Monitor Port 구현체 등록
    from src.modules.monitor.infrastructure.adapters.email_notification_adapter import EmailNotificationAdapter
    from src.modules.monitor.infrastructure.adapters.system_health_check_adapter import SystemHealthCheckAdapter
    
    container.register_transient(MetricRepositoryPort, MongoDBMetricRepository)
    container.register_transient(AlertRepositoryPort, MongoDBAlertRepository)
    container.register_transient(HealthCheckPort, SystemHealthCheckAdapter)
    container.register_transient(NotificationPort, EmailNotificationAdapter)
    
    container.register_transient(MonitorService, MonitorService)
    container.register_transient(CollectMetricsUseCase, CollectMetricsUseCase)
    container.register_transient(CollectSystemMetricsUseCase, CollectSystemMetricsUseCase)
    container.register_transient(CreateAlertRuleUseCase, CreateAlertRuleUseCase)
    container.register_transient(ProcessMetricAlertUseCase, ProcessMetricAlertUseCase)
    container.register_transient(CheckComponentHealthUseCase, CheckComponentHealthUseCase)
    container.register_transient(PerformHealthCheckUseCase, PerformHealthCheckUseCase)
    
    # Ingest 모듈 등록
    from src.modules.ingest.application.services.document_service import DocumentService
    from src.modules.ingest.infrastructure.repositories.document_repository import DocumentRepository
    
    container.register_transient(DocumentService, DocumentService)
    container.register_transient(DocumentRepository, DocumentRepository)
    
    logger.info("Dependencies registered successfully")


# 의존성 설정
setup_dependencies()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """애플리케이션 생명주기 관리"""
    logger.info("Starting IACSRAG application...")
    
    try:
        # 데이터베이스 연결 초기화
        db = await get_database()
        logger.info("Database connection established")
        
        # 벡터 DB 연결 초기화
        vector_db = await get_vector_db()
        logger.info("Vector database connection established")
        
        # Kafka 클라이언트 초기화
        kafka_client = await get_kafka_client()
        logger.info("Kafka client initialized")
        
        # 애플리케이션 상태를 앱 인스턴스에 저장
        app.state.db = db
        app.state.vector_db = vector_db
        app.state.kafka_client = kafka_client
        
        logger.info("IACSRAG application started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        # 리소스 정리
        logger.info("Shutting down IACSRAG application...")
        
        # Kafka 클라이언트 종료
        if hasattr(app.state, 'kafka_client') and app.state.kafka_client:
            await app.state.kafka_client.close()
            logger.info("Kafka client closed")
        
        # 벡터 DB 연결 종료
        if hasattr(app.state, 'vector_db') and app.state.vector_db:
            await app.state.vector_db.close()
            logger.info("Vector database connection closed")
        
        # 데이터베이스 연결 종료
        if hasattr(app.state, 'db') and app.state.db:
            app.state.db.client.close()
            logger.info("Database connection closed")
        
        logger.info("IACSRAG application shutdown complete")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="IACSRAG - 문서 검색 플랫폼",
    description="RAG(Retrieval-Augmented Generation) 기반 문서 검색 및 질의응답 시스템",
    version="1.0.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    lifespan=lifespan
)


# 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)


# 전역 예외 핸들러
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """입력 검증 오류 핸들러"""
    logger.warning(f"Validation error: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "validation_error",
            "message": exc.message,
            "details": exc.details
        }
    )


@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """리소스 없음 오류 핸들러"""
    logger.warning(f"Resource not found: {exc.message}")
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": exc.message
        }
    )


@app.exception_handler(BusinessLogicError)
async def business_logic_error_handler(request: Request, exc: BusinessLogicError) -> JSONResponse:
    """비즈니스 로직 오류 핸들러"""
    logger.error(f"Business logic error: {exc.message}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "business_logic_error",
            "message": exc.message
        }
    )


@app.exception_handler(ExternalServiceError)
async def external_service_error_handler(request: Request, exc: ExternalServiceError) -> JSONResponse:
    """외부 서비스 오류 핸들러"""
    logger.error(f"External service error: {exc.message}")
    return JSONResponse(
        status_code=503,
        content={
            "error": "external_service_error",
            "message": "외부 서비스에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """일반 예외 핸들러"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "서버 내부 오류가 발생했습니다."
        }
    )


# 헬스체크 엔드포인트
@app.get("/health", tags=["Health"])
async def health_check():
    """애플리케이션 헬스체크"""
    return {
        "status": "healthy",
        "service": "IACSRAG",
        "version": "1.0.0",
        "environment": settings.environment
    }


@app.get("/", tags=["Root"])
async def root():
    """루트 엔드포인트"""
    return {
        "message": "IACSRAG - 문서 검색 플랫폼",
        "version": "1.0.0",
        "docs": "/docs" if settings.environment == "development" else "Documentation not available in production"
    }


# API 라우터 등록
app.include_router(
    search.router,
    prefix="/api/v1",
    tags=["Search"]
)

app.include_router(
    monitor.router,
    prefix="/api/v1",
    tags=["Monitor"]
)


# 개발 서버 실행 함수
def run_dev_server():
    """개발 서버 실행"""
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    if settings.environment == "development":
        run_dev_server()
    else:
        # 프로덕션 환경에서는 gunicorn 등을 사용
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower()
        )
