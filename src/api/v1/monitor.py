"""
Monitor API 엔드포인트

시스템 모니터링 관련 API를 제공합니다.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.dependencies import get_monitor_service
from src.core.exceptions import BusinessLogicError, ValidationError
from src.modules.monitor.domain.entities import ComponentType, MetricType, AlertSeverity
from src.modules.monitor.application.use_cases.collect_metrics import (
    CollectMetricsCommand, CollectSystemMetricsUseCase
)
from src.modules.monitor.application.use_cases.manage_alerts import (
    CreateAlertCommand, UpdateAlertCommand, GetAlertsQuery
)
from src.modules.monitor.application.use_cases.check_health import (
    CheckHealthCommand, CheckSystemHealthUseCase
)


router = APIRouter(prefix="/monitor", tags=["monitor"])


# Request/Response Models
class MetricRequest(BaseModel):
    """메트릭 수집 요청"""
    component: ComponentType
    metrics: List[Dict[str, Any]] = Field(..., description="메트릭 데이터 목록")


class MetricResponse(BaseModel):
    """메트릭 수집 응답"""
    success: bool
    collected_count: int
    failed_count: int
    metric_ids: List[UUID]
    errors: List[str] = []


class SystemMetricsResponse(BaseModel):
    """시스템 메트릭 응답"""
    components: Dict[ComponentType, MetricResponse]
    total_collected: int
    total_failed: int
    collection_time: datetime


class AlertRequest(BaseModel):
    """알림 생성 요청"""
    component: ComponentType
    metric_name: str
    condition: str = Field(..., description="알림 조건 (예: > 80)")
    severity: AlertSeverity
    message: str
    enabled: bool = True


class AlertResponse(BaseModel):
    """알림 응답"""
    alert_id: UUID
    component: ComponentType
    metric_name: str
    condition: str
    severity: AlertSeverity
    message: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class HealthCheckResponse(BaseModel):
    """헬스체크 응답"""
    component: ComponentType
    status: str
    message: str
    last_checked: datetime
    response_time_ms: Optional[float] = None


class SystemHealthResponse(BaseModel):
    """시스템 헬스체크 응답"""
    overall_status: str
    components: List[HealthCheckResponse]
    checked_at: datetime


class ProcessingStatsResponse(BaseModel):
    """처리 통계 응답"""
    component: ComponentType
    total_processed: int
    total_failed: int
    total_retries: int
    average_processing_time: float
    success_rate: float
    last_updated: datetime


class SystemOverviewResponse(BaseModel):
    """시스템 개요 응답"""
    total_documents: int
    total_chunks: int
    total_embeddings: int
    total_searches: int
    average_response_time: float
    system_uptime: float
    last_updated: datetime


# API Endpoints
@router.post("/metrics/collect", response_model=MetricResponse)
async def collect_metrics(
    request: MetricRequest,
    monitor_service = Depends(get_monitor_service)
):
    """
    특정 컴포넌트의 메트릭을 수집합니다.
    """
    try:
        command = CollectMetricsCommand(
            component=request.component,
            metrics=request.metrics
        )
        
        result = await monitor_service.collect_metrics_use_case.execute(command)
        
        return MetricResponse(
            success=result.success,
            collected_count=result.collected_count,
            failed_count=result.failed_count,
            metric_ids=result.metric_ids,
            errors=result.errors
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메트릭 수집 중 오류 발생: {str(e)}")


@router.post("/metrics/collect-system", response_model=SystemMetricsResponse)
async def collect_system_metrics(
    monitor_service = Depends(get_monitor_service)
):
    """
    모든 시스템 컴포넌트의 메트릭을 일괄 수집합니다.
    """
    try:
        collection_start = datetime.utcnow()
        
        results = await monitor_service.collect_system_metrics_use_case.execute()
        
        # 응답 데이터 구성
        component_responses = {}
        total_collected = 0
        total_failed = 0
        
        for component, result in results.items():
            component_responses[component] = MetricResponse(
                success=result.success,
                collected_count=result.collected_count,
                failed_count=result.failed_count,
                metric_ids=result.metric_ids,
                errors=result.errors
            )
            total_collected += result.collected_count
            total_failed += result.failed_count
        
        return SystemMetricsResponse(
            components=component_responses,
            total_collected=total_collected,
            total_failed=total_failed,
            collection_time=collection_start
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시스템 메트릭 수집 중 오류 발생: {str(e)}")


@router.get("/health/{component}", response_model=HealthCheckResponse)
async def check_component_health(
    component: ComponentType,
    monitor_service = Depends(get_monitor_service)
):
    """
    특정 컴포넌트의 헬스체크를 수행합니다.
    """
    try:
        command = CheckHealthCommand(component=component)
        result = await monitor_service.check_health_use_case.execute(command)
        
        return HealthCheckResponse(
            component=result.component,
            status=result.status.value,
            message=result.message,
            last_checked=result.checked_at,
            response_time_ms=result.response_time_ms
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"헬스체크 중 오류 발생: {str(e)}")


@router.get("/health", response_model=SystemHealthResponse)
async def check_system_health(
    monitor_service = Depends(get_monitor_service)
):
    """
    전체 시스템의 헬스체크를 수행합니다.
    """
    try:
        results = await monitor_service.check_system_health_use_case.execute()
        
        # 전체 상태 결정
        overall_status = "healthy"
        if any(not result.status.is_healthy() for result in results.values()):
            overall_status = "unhealthy"
        elif any(result.status.value == "degraded" for result in results.values()):
            overall_status = "degraded"
        
        # 컴포넌트별 응답 구성
        component_responses = []
        for component, result in results.items():
            component_responses.append(HealthCheckResponse(
                component=component,
                status=result.status.value,
                message=result.message,
                last_checked=result.checked_at,
                response_time_ms=result.response_time_ms
            ))
        
        return SystemHealthResponse(
            overall_status=overall_status,
            components=component_responses,
            checked_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시스템 헬스체크 중 오류 발생: {str(e)}")


@router.post("/alerts", response_model=AlertResponse)
async def create_alert(
    request: AlertRequest,
    monitor_service = Depends(get_monitor_service)
):
    """
    새로운 알림 규칙을 생성합니다.
    """
    try:
        command = CreateAlertCommand(
            component=request.component,
            metric_name=request.metric_name,
            condition=request.condition,
            severity=request.severity,
            message=request.message,
            enabled=request.enabled
        )
        
        result = await monitor_service.manage_alerts_use_case.create_alert(command)
        
        return AlertResponse(
            alert_id=result.alert_id,
            component=result.component,
            metric_name=result.metric_name,
            condition=result.condition,
            severity=result.severity,
            message=result.message,
            enabled=result.enabled,
            created_at=result.created_at,
            updated_at=result.updated_at
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 생성 중 오류 발생: {str(e)}")


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    component: Optional[ComponentType] = Query(None, description="컴포넌트 필터"),
    enabled: Optional[bool] = Query(None, description="활성화 상태 필터"),
    severity: Optional[AlertSeverity] = Query(None, description="심각도 필터"),
    monitor_service = Depends(get_monitor_service)
):
    """
    알림 규칙 목록을 조회합니다.
    """
    try:
        query = GetAlertsQuery(
            component=component,
            enabled=enabled,
            severity=severity
        )
        
        alerts = await monitor_service.manage_alerts_use_case.get_alerts(query)
        
        return [
            AlertResponse(
                alert_id=alert.alert_id,
                component=alert.component,
                metric_name=alert.metric_name,
                condition=alert.condition,
                severity=alert.severity,
                message=alert.message,
                enabled=alert.enabled,
                created_at=alert.created_at,
                updated_at=alert.updated_at
            )
            for alert in alerts
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 조회 중 오류 발생: {str(e)}")


@router.get("/stats/processing", response_model=List[ProcessingStatsResponse])
async def get_processing_statistics(
    component: Optional[ComponentType] = Query(None, description="컴포넌트 필터"),
    monitor_service = Depends(get_monitor_service)
):
    """
    처리 통계를 조회합니다.
    """
    try:
        stats_list = await monitor_service.metric_repository.get_processing_statistics(
            component=component
        )
        
        return [
            ProcessingStatsResponse(
                component=stats.component,
                total_processed=stats.total_processed,
                total_failed=stats.total_failed,
                total_retries=stats.total_retries,
                average_processing_time=stats.average_processing_time,
                success_rate=stats.success_rate,
                last_updated=stats.last_updated
            )
            for stats in stats_list
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 통계 조회 중 오류 발생: {str(e)}")


@router.get("/stats/overview", response_model=SystemOverviewResponse)
async def get_system_overview(
    monitor_service = Depends(get_monitor_service)
):
    """
    시스템 전체 개요를 조회합니다.
    """
    try:
        overview = await monitor_service.metric_repository.get_latest_system_overview()
        
        if not overview:
            raise HTTPException(status_code=404, detail="시스템 개요 데이터를 찾을 수 없습니다")
        
        return SystemOverviewResponse(
            total_documents=overview.total_documents,
            total_chunks=overview.total_chunks,
            total_embeddings=overview.total_embeddings,
            total_searches=overview.total_searches,
            average_response_time=overview.average_response_time,
            system_uptime=overview.system_uptime,
            last_updated=overview.last_updated
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시스템 개요 조회 중 오류 발생: {str(e)}")


@router.get("/metrics/history")
async def get_metric_history(
    component: ComponentType = Query(..., description="컴포넌트"),
    metric_name: str = Query(..., description="메트릭 이름"),
    start_time: Optional[datetime] = Query(None, description="시작 시간"),
    end_time: Optional[datetime] = Query(None, description="종료 시간"),
    limit: int = Query(100, ge=1, le=1000, description="조회 개수 제한"),
    monitor_service = Depends(get_monitor_service)
):
    """
    메트릭 히스토리를 조회합니다.
    """
    try:
        # 기본값 설정 (최근 24시간)
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(hours=24)
        
        metrics = await monitor_service.metric_repository.get_metrics_by_time_range(
            component=component,
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        return {
            "component": component,
            "metric_name": metric_name,
            "start_time": start_time,
            "end_time": end_time,
            "count": len(metrics),
            "metrics": [
                {
                    "metric_id": metric.metric_id,
                    "value": metric.current_value,
                    "timestamp": metric.last_updated,
                    "tags": metric.tags,
                    "metadata": metric.metadata
                }
                for metric in metrics
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메트릭 히스토리 조회 중 오류 발생: {str(e)}")
