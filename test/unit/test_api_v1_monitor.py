"""
Monitor API 엔드포인트 테스트
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.monitor import router
from src.modules.monitor.domain.entities import (
    ComponentType, MetricType, AlertSeverity, HealthStatus
)
from src.modules.monitor.application.use_cases.collect_metrics import (
    CollectMetricsResult
)
from src.modules.monitor.application.use_cases.check_health import (
    HealthCheckResult
)


@pytest.fixture
def app():
    """테스트용 FastAPI 앱"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """테스트 클라이언트"""
    return TestClient(app)


@pytest.fixture
def mock_monitor_service():
    """Mock 모니터 서비스"""
    service = Mock()
    service.collect_metrics_use_case = AsyncMock()
    service.collect_system_metrics_use_case = AsyncMock()
    service.check_health_use_case = AsyncMock()
    service.check_system_health_use_case = AsyncMock()
    service.create_alert_rule_use_case = AsyncMock()
    service.get_alert_summary_use_case = AsyncMock()
    service.metric_repository = AsyncMock()
    return service


class TestMetricsAPI:
    """메트릭 API 테스트"""
    
    def test_collect_metrics_success(self, client, mock_monitor_service, monkeypatch):
        """메트릭 수집 성공 테스트"""
        # Given
        metric_ids = [uuid4(), uuid4()]
        mock_result = CollectMetricsResult(
            collected_count=2,
            failed_count=0,
            metric_ids=metric_ids,
            errors=[]
        )
        mock_monitor_service.collect_metrics_use_case.execute.return_value = mock_result
        
        def mock_get_monitor_service():
            return mock_monitor_service
        
        monkeypatch.setattr("src.api.v1.monitor.get_monitor_service", mock_get_monitor_service)
        
        request_data = {
            "component": "PROCESS",
            "metrics": [
                {"name": "cpu_usage", "value": 75.5, "type": "gauge"},
                {"name": "memory_usage", "value": 80.0, "type": "gauge"}
            ]
        }
        
        # When
        response = client.post("/monitor/metrics/collect", json=request_data)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["collected_count"] == 2
        assert data["failed_count"] == 0
        assert len(data["metric_ids"]) == 2
        assert len(data["errors"]) == 0
    
    def test_collect_metrics_validation_error(self, client, mock_monitor_service, monkeypatch):
        """메트릭 수집 검증 오류 테스트"""
        # Given
        def mock_get_monitor_service():
            return mock_monitor_service
        
        monkeypatch.setattr("src.api.v1.monitor.get_monitor_service", mock_get_monitor_service)
        
        request_data = {
            "component": "PROCESS",
            "metrics": []  # 빈 메트릭 리스트
        }
        
        # When
        response = client.post("/monitor/metrics/collect", json=request_data)
        
        # Then
        assert response.status_code == 422  # Validation error
    
    def test_collect_system_metrics_success(self, client, mock_monitor_service, monkeypatch):
        """시스템 메트릭 수집 성공 테스트"""
        # Given
        results = {
            ComponentType.PROCESS: CollectMetricsResult(
                collected_count=3,
                failed_count=0,
                metric_ids=[uuid4(), uuid4(), uuid4()],
                errors=[]
            ),
            ComponentType.DATABASE: CollectMetricsResult(
                collected_count=2,
                failed_count=1,
                metric_ids=[uuid4(), uuid4()],
                errors=["Connection timeout"]
            )
        }
        mock_monitor_service.collect_system_metrics_use_case.execute.return_value = results
        
        def mock_get_monitor_service():
            return mock_monitor_service
        
        monkeypatch.setattr("src.api.v1.monitor.get_monitor_service", mock_get_monitor_service)
        
        # When
        response = client.post("/monitor/metrics/collect-system")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_collected"] == 5
        assert data["total_failed"] == 1
        assert len(data["components"]) == 2
        assert "PROCESS" in data["components"]
        assert "DATABASE" in data["components"]


class TestHealthAPI:
    """헬스체크 API 테스트"""
    
    def test_check_component_health_success(self, client, mock_monitor_service, monkeypatch):
        """컴포넌트 헬스체크 성공 테스트"""
        # Given
        mock_result = HealthCheckResult(
            component=ComponentType.PROCESS,
            status=HealthStatus.healthy(ComponentType.PROCESS, "All systems operational"),
            check_duration_ms=150.0
        )
        mock_monitor_service.check_health_use_case.execute.return_value = mock_result
        
        def mock_get_monitor_service():
            return mock_monitor_service
        
        monkeypatch.setattr("src.api.v1.monitor.get_monitor_service", mock_get_monitor_service)
        
        # When
        response = client.get("/monitor/health/PROCESS")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["component"] == "PROCESS"
        assert data["status"] == "healthy"
        assert data["message"] == "All systems operational"
        assert data["response_time_ms"] == 150.0
    
    def test_check_system_health_success(self, client, mock_monitor_service, monkeypatch):
        """시스템 헬스체크 성공 테스트"""
        # Given
        results = {
            ComponentType.PROCESS: HealthCheckResult(
                component=ComponentType.PROCESS,
                status=HealthStatus.healthy(ComponentType.PROCESS, "Healthy"),
                check_duration_ms=100.0
            ),
            ComponentType.DATABASE: HealthCheckResult(
                component=ComponentType.DATABASE,
                status=HealthStatus.unhealthy(ComponentType.DATABASE, "Connection failed"),
                check_duration_ms=0.0
            )
        }
        mock_monitor_service.check_system_health_use_case.execute.return_value = results
        
        def mock_get_monitor_service():
            return mock_monitor_service
        
        monkeypatch.setattr("src.api.v1.monitor.get_monitor_service", mock_get_monitor_service)
        
        # When
        response = client.get("/monitor/health")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "unhealthy"  # DATABASE가 unhealthy이므로
        assert len(data["components"]) == 2


class TestAlertsAPI:
    """알림 API 테스트"""
    
    def test_create_alert_success(self, client, mock_monitor_service, monkeypatch):
        """알림 생성 성공 테스트"""
        # Given
        alert_id = uuid4()
        mock_alert = Mock()
        mock_alert.alert_id = alert_id
        mock_alert.component = ComponentType.PROCESS
        mock_alert.metric_name = "cpu_usage"
        mock_alert.condition = "> 80"
        mock_alert.severity = AlertSeverity.HIGH
        mock_alert.message = "High CPU usage detected"
        mock_alert.enabled = True
        mock_alert.created_at = datetime.utcnow()
        mock_alert.updated_at = datetime.utcnow()
        
        mock_monitor_service.create_alert_rule_use_case.execute.return_value = mock_alert
        
        def mock_get_monitor_service():
            return mock_monitor_service
        
        monkeypatch.setattr("src.api.v1.monitor.get_monitor_service", mock_get_monitor_service)
        
        request_data = {
            "component": "PROCESS",
            "metric_name": "cpu_usage",
            "condition": "> 80",
            "severity": "HIGH",
            "message": "High CPU usage detected",
            "enabled": True
        }
        
        # When
        response = client.post("/monitor/alerts", json=request_data)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["component"] == "PROCESS"
        assert data["metric_name"] == "cpu_usage"
        assert data["condition"] == "> 80"
        assert data["severity"] == "HIGH"
        assert data["message"] == "High CPU usage detected"
        assert data["enabled"] is True
    
    def test_get_alerts_success(self, client, mock_monitor_service, monkeypatch):
        """알림 조회 성공 테스트"""
        # Given
        alert1 = Mock()
        alert1.alert_id = uuid4()
        alert1.component = ComponentType.PROCESS
        alert1.metric_name = "cpu_usage"
        alert1.condition = "> 80"
        alert1.severity = AlertSeverity.HIGH
        alert1.message = "High CPU usage"
        alert1.enabled = True
        alert1.created_at = datetime.utcnow()
        alert1.updated_at = datetime.utcnow()
        
        alert2 = Mock()
        alert2.alert_id = uuid4()
        alert2.component = ComponentType.DATABASE
        alert2.metric_name = "connection_count"
        alert2.condition = "> 100"
        alert2.severity = AlertSeverity.MEDIUM
        alert2.message = "High connection count"
        alert2.enabled = False
        alert2.created_at = datetime.utcnow()
        alert2.updated_at = datetime.utcnow()
        
        mock_monitor_service.get_alert_summary_use_case.execute.return_value = [alert1, alert2]
        
        def mock_get_monitor_service():
            return mock_monitor_service
        
        monkeypatch.setattr("src.api.v1.monitor.get_monitor_service", mock_get_monitor_service)
        
        # When
        response = client.get("/monitor/alerts")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["component"] == "PROCESS"
        assert data[1]["component"] == "DATABASE"


class TestStatsAPI:
    """통계 API 테스트"""
    
    def test_get_processing_statistics_success(self, client, mock_monitor_service, monkeypatch):
        """처리 통계 조회 성공 테스트"""
        # Given
        stats1 = Mock()
        stats1.component = ComponentType.PROCESS
        stats1.total_processed = 1000
        stats1.total_failed = 50
        stats1.total_retries = 10
        stats1.average_processing_time = 2.5
        stats1.success_rate = 0.95
        stats1.last_updated = datetime.utcnow()
        
        stats2 = Mock()
        stats2.component = ComponentType.INGEST
        stats2.total_processed = 500
        stats2.total_failed = 25
        stats2.total_retries = 5
        stats2.average_processing_time = 1.8
        stats2.success_rate = 0.95
        stats2.last_updated = datetime.utcnow()
        
        mock_monitor_service.metric_repository.get_processing_statistics.return_value = [stats1, stats2]
        
        def mock_get_monitor_service():
            return mock_monitor_service
        
        monkeypatch.setattr("src.api.v1.monitor.get_monitor_service", mock_get_monitor_service)
        
        # When
        response = client.get("/monitor/stats/processing")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["component"] == "PROCESS"
        assert data[0]["total_processed"] == 1000
        assert data[0]["success_rate"] == 0.95
    
    def test_get_system_overview_success(self, client, mock_monitor_service, monkeypatch):
        """시스템 개요 조회 성공 테스트"""
        # Given
        overview = Mock()
        overview.total_documents = 1000
        overview.total_chunks = 5000
        overview.total_embeddings = 5000
        overview.total_searches = 200
        overview.average_response_time = 1.5
        overview.system_uptime = 86400.0  # 24 hours
        overview.last_updated = datetime.utcnow()
        
        mock_monitor_service.metric_repository.get_latest_system_overview.return_value = overview
        
        def mock_get_monitor_service():
            return mock_monitor_service
        
        monkeypatch.setattr("src.api.v1.monitor.get_monitor_service", mock_get_monitor_service)
        
        # When
        response = client.get("/monitor/stats/overview")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 1000
        assert data["total_chunks"] == 5000
        assert data["total_embeddings"] == 5000
        assert data["total_searches"] == 200
        assert data["average_response_time"] == 1.5
        assert data["system_uptime"] == 86400.0
    
    def test_get_system_overview_not_found(self, client, mock_monitor_service, monkeypatch):
        """시스템 개요 조회 실패 테스트 (데이터 없음)"""
        # Given
        mock_monitor_service.metric_repository.get_latest_system_overview.return_value = None
        
        def mock_get_monitor_service():
            return mock_monitor_service
        
        monkeypatch.setattr("src.api.v1.monitor.get_monitor_service", mock_get_monitor_service)
        
        # When
        response = client.get("/monitor/stats/overview")
        
        # Then
        assert response.status_code == 404
        assert "시스템 개요 데이터를 찾을 수 없습니다" in response.json()["detail"]


class TestMetricHistoryAPI:
    """메트릭 히스토리 API 테스트"""
    
    def test_get_metric_history_success(self, client, mock_monitor_service, monkeypatch):
        """메트릭 히스토리 조회 성공 테스트"""
        # Given
        metric1 = Mock()
        metric1.metric_id = uuid4()
        metric1.current_value = 75.5
        metric1.last_updated = datetime.utcnow()
        metric1.tags = {"component": "PROCESS"}
        metric1.metadata = {"source": "system_monitor"}
        
        metric2 = Mock()
        metric2.metric_id = uuid4()
        metric2.current_value = 80.0
        metric2.last_updated = datetime.utcnow() - timedelta(minutes=5)
        metric2.tags = {"component": "PROCESS"}
        metric2.metadata = {"source": "system_monitor"}
        
        mock_monitor_service.metric_repository.get_metrics_by_time_range.return_value = [metric1, metric2]
        
        def mock_get_monitor_service():
            return mock_monitor_service
        
        monkeypatch.setattr("src.api.v1.monitor.get_monitor_service", mock_get_monitor_service)
        
        # When
        response = client.get("/monitor/metrics/history?component=PROCESS&metric_name=cpu_usage")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["component"] == "PROCESS"
        assert data["metric_name"] == "cpu_usage"
        assert data["count"] == 2
        assert len(data["metrics"]) == 2
        assert data["metrics"][0]["value"] == 75.5
        assert data["metrics"][1]["value"] == 80.0
    
    def test_get_metric_history_with_time_range(self, client, mock_monitor_service, monkeypatch):
        """시간 범위를 지정한 메트릭 히스토리 조회 테스트"""
        # Given
        mock_monitor_service.metric_repository.get_metrics_by_time_range.return_value = []
        
        def mock_get_monitor_service():
            return mock_monitor_service
        
        monkeypatch.setattr("src.api.v1.monitor.get_monitor_service", mock_get_monitor_service)
        
        start_time = "2024-01-01T00:00:00"
        end_time = "2024-01-01T23:59:59"
        
        # When
        response = client.get(
            f"/monitor/metrics/history?component=PROCESS&metric_name=cpu_usage"
            f"&start_time={start_time}&end_time={end_time}&limit=50"
        )
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["component"] == "PROCESS"
        assert data["metric_name"] == "cpu_usage"
        assert data["count"] == 0
        
        # Repository 호출 확인
        mock_monitor_service.metric_repository.get_metrics_by_time_range.assert_called_once()
        call_args = mock_monitor_service.metric_repository.get_metrics_by_time_range.call_args
        assert call_args[1]["component"] == ComponentType.PROCESS
        assert call_args[1]["metric_name"] == "cpu_usage"
        assert call_args[1]["limit"] == 50


class TestErrorHandling:
    """에러 처리 테스트"""
    
    def test_internal_server_error(self, client, mock_monitor_service, monkeypatch):
        """내부 서버 오류 테스트"""
        # Given
        mock_monitor_service.collect_metrics_use_case.execute.side_effect = Exception("Database connection failed")
        
        def mock_get_monitor_service():
            return mock_monitor_service
        
        monkeypatch.setattr("src.api.v1.monitor.get_monitor_service", mock_get_monitor_service)
        
        request_data = {
            "component": "PROCESS",
            "metrics": [{"name": "cpu_usage", "value": 75.5, "type": "gauge"}]
        }
        
        # When
        response = client.post("/monitor/metrics/collect", json=request_data)
        
        # Then
        assert response.status_code == 500
        assert "메트릭 수집 중 오류 발생" in response.json()["detail"]
    
    def test_invalid_component_type(self, client, mock_monitor_service, monkeypatch):
        """잘못된 컴포넌트 타입 테스트"""
        # Given
        def mock_get_monitor_service():
            return mock_monitor_service
        
        monkeypatch.setattr("src.api.v1.monitor.get_monitor_service", mock_get_monitor_service)
        
        request_data = {
            "component": "INVALID_COMPONENT",
            "metrics": [{"name": "cpu_usage", "value": 75.5, "type": "gauge"}]
        }
        
        # When
        response = client.post("/monitor/metrics/collect", json=request_data)
        
        # Then
        assert response.status_code == 422  # Validation error
