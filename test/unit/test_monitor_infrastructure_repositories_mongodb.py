"""
Monitor 모듈 MongoDB 리포지토리 단위 테스트
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4, UUID

from src.modules.monitor.infrastructure.repositories.mongodb_metric_repository import MongoDBMetricRepository
from src.modules.monitor.infrastructure.repositories.mongodb_alert_repository import MongoDBAlertRepository
from src.modules.monitor.domain.entities import (
    SystemMetric, Alert, ComponentType, MetricType, AlertSeverity, AlertStatus,
    ProcessingStatistics, SystemOverview, MetricValue, HealthStatus, AlertRule
)
from src.core.exceptions import RepositoryError
from src.utils.datetime import get_current_utc_time


class TestMongoDBMetricRepository:
    """MongoDB 메트릭 리포지토리 테스트"""
    
    @pytest.fixture
    def mock_database(self):
        """Mock 데이터베이스"""
        mock_db = MagicMock()
        mock_db.metrics = AsyncMock()
        mock_db.processing_statistics = AsyncMock()
        mock_db.system_overview = AsyncMock()
        return mock_db
    
    @pytest.fixture
    def repository(self, mock_database):
        """메트릭 리포지토리 인스턴스"""
        return MongoDBMetricRepository(mock_database)
    
    @pytest.fixture
    def sample_metric(self):
        """샘플 메트릭"""
        metric = SystemMetric(
            metric_id=uuid4(),
            name="cpu_usage",
            metric_type=MetricType.GAUGE,
            component=ComponentType.INGEST,
            description="CPU usage percentage"
        )
        # 메트릭 값 추가
        metric.add_value(85.5, {"host": "server1"})
        metric.add_value(90.2, {"host": "server1"})
        return metric
    
    @pytest.fixture
    def sample_processing_stats(self):
        """샘플 처리 통계"""
        return ProcessingStatistics(
            stats_id=uuid4(),
            component=ComponentType.PROCESS,
            total_processed=1000,
            total_failed=10,
            total_retries=5,
            average_processing_time=250.5,
            peak_processing_time=500.0,
            throughput_per_minute=120.0,
            error_rate=0.01
        )
    
    @pytest.fixture
    def sample_system_overview(self):
        """샘플 시스템 개요"""
        health_statuses = [
            HealthStatus(
                component=ComponentType.INGEST,
                status="healthy",
                message="All systems operational",
                last_check=get_current_utc_time(),
                response_time_ms=50.0
            ),
            HealthStatus(
                component=ComponentType.PROCESS,
                status="warning",
                message="High CPU usage",
                last_check=get_current_utc_time(),
                response_time_ms=120.0
            )
        ]
        
        return SystemOverview(
            overview_id=uuid4(),
            total_documents=5000,
            total_chunks=25000,
            total_searches=1000,
            total_answers_generated=800,
            average_search_time_ms=150.0,
            average_answer_time_ms=300.0,
            system_uptime_seconds=86400,
            health_statuses=health_statuses
        )
    
    @pytest.mark.asyncio
    async def test_save_metric_success(self, repository, sample_metric, mock_database):
        """메트릭 저장 성공 테스트"""
        # Given
        mock_database.metrics.insert_one.return_value = AsyncMock()
        
        # When
        await repository.save_metric(sample_metric)
        
        # Then
        mock_database.metrics.insert_one.assert_called_once()
        call_args = mock_database.metrics.insert_one.call_args[0][0]
        assert call_args["_id"] == str(sample_metric.metric_id)
        assert call_args["name"] == sample_metric.name
        assert call_args["component"] == sample_metric.component.value
        assert call_args["metric_type"] == sample_metric.metric_type.value
        assert call_args["description"] == sample_metric.description
        assert len(call_args["values"]) == 2
        assert call_args["values"][0]["value"] == 85.5
        assert call_args["values"][0]["labels"] == {"host": "server1"}
    
    @pytest.mark.asyncio
    async def test_save_metric_failure(self, repository, sample_metric, mock_database):
        """메트릭 저장 실패 테스트"""
        # Given
        mock_database.metrics.insert_one.side_effect = Exception("Database error")
        
        # When & Then
        with pytest.raises(RepositoryError, match="메트릭 저장 실패"):
            await repository.save_metric(sample_metric)
    
    @pytest.mark.asyncio
    async def test_get_metric_by_id_found(self, repository, sample_metric, mock_database):
        """메트릭 ID로 조회 성공 테스트"""
        # Given
        mock_doc = {
            "_id": str(sample_metric.metric_id),
            "name": sample_metric.name,
            "metric_type": sample_metric.metric_type.value,
            "component": sample_metric.component.value,
            "description": sample_metric.description,
            "values": [
                {"value": 85.5, "timestamp": get_current_utc_time(), "labels": {"host": "server1"}},
                {"value": 90.2, "timestamp": get_current_utc_time(), "labels": {"host": "server1"}}
            ],
            "created_at": sample_metric.created_at,
            "updated_at": sample_metric.updated_at
        }
        mock_database.metrics.find_one.return_value = mock_doc
        
        # When
        result = await repository.get_metric_by_id(sample_metric.metric_id)
        
        # Then
        assert result is not None
        assert result.metric_id == sample_metric.metric_id
        assert result.name == sample_metric.name
        assert result.component == sample_metric.component
        assert len(result.values) == 2
        assert result.values[0].value == 85.5
    
    @pytest.mark.asyncio
    async def test_get_metric_by_id_not_found(self, repository, mock_database):
        """메트릭 ID로 조회 실패 테스트"""
        # Given
        mock_database.metrics.find_one.return_value = None
        metric_id = uuid4()
        
        # When
        result = await repository.get_metric_by_id(metric_id)
        
        # Then
        assert result is None


class TestMongoDBAlertRepository:
    """MongoDB 알림 리포지토리 테스트"""
    
    @pytest.fixture
    def mock_database(self):
        """Mock 데이터베이스"""
        mock_db = MagicMock()
        mock_db.alerts = AsyncMock()
        mock_db.alert_rules = AsyncMock()
        return mock_db
    
    @pytest.fixture
    def repository(self, mock_database):
        """알림 리포지토리 인스턴스"""
        return MongoDBAlertRepository(mock_database)
    
    @pytest.fixture
    def sample_alert(self):
        """샘플 알림"""
        return Alert(
            alert_id=uuid4(),
            rule_id=uuid4(),
            component=ComponentType.INGEST,
            metric_name="cpu_usage",
            severity=AlertSeverity.HIGH,
            status=AlertStatus.ACTIVE,
            message="CPU usage is high",
            metric_value=85.0,
            threshold=80.0,
            triggered_at=get_current_utc_time(),
            tags={"host": "server1"}
        )
    
    @pytest.fixture
    def sample_alert_rule(self):
        """샘플 알림 규칙"""
        return AlertRule(
            rule_id=uuid4(),
            name="High CPU Usage Alert",
            component=ComponentType.INGEST,
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            message="CPU usage is high",
            enabled=True,
            notification_channels=["email", "slack"],
            cooldown_minutes=5
        )
    
    @pytest.mark.asyncio
    async def test_save_alert_success(self, repository, sample_alert, mock_database):
        """알림 저장 성공 테스트"""
        # Given
        mock_database.alerts.insert_one.return_value = AsyncMock()
        
        # When
        await repository.save_alert(sample_alert)
        
        # Then
        mock_database.alerts.insert_one.assert_called_once()
        call_args = mock_database.alerts.insert_one.call_args[0][0]
        assert call_args["_id"] == str(sample_alert.alert_id)
        assert call_args["component"] == sample_alert.component.value
        assert call_args["severity"] == sample_alert.severity.value
        assert call_args["status"] == sample_alert.status.value
        assert call_args["metric_value"] == sample_alert.metric_value
        assert call_args["threshold"] == sample_alert.threshold
    
    @pytest.mark.asyncio
    async def test_save_alert_failure(self, repository, sample_alert, mock_database):
        """알림 저장 실패 테스트"""
        # Given
        mock_database.alerts.insert_one.side_effect = Exception("Database error")
        
        # When & Then
        with pytest.raises(RepositoryError, match="알림 저장 실패"):
            await repository.save_alert(sample_alert)
    
    @pytest.mark.asyncio
    async def test_get_alert_by_id_found(self, repository, sample_alert, mock_database):
        """알림 ID로 조회 성공 테스트"""
        # Given
        mock_doc = {
            "_id": str(sample_alert.alert_id),
            "rule_id": str(sample_alert.rule_id),
            "component": sample_alert.component.value,
            "metric_name": sample_alert.metric_name,
            "severity": sample_alert.severity.value,
            "status": sample_alert.status.value,
            "message": sample_alert.message,
            "metric_value": sample_alert.metric_value,
            "threshold": sample_alert.threshold,
            "triggered_at": sample_alert.triggered_at,
            "resolved_at": None,
            "acknowledged_at": None,
            "acknowledged_by": None,
            "tags": sample_alert.tags
        }
        mock_database.alerts.find_one.return_value = mock_doc
        
        # When
        result = await repository.get_alert_by_id(sample_alert.alert_id)
        
        # Then
        assert result is not None
        assert result.alert_id == sample_alert.alert_id
        assert result.component == sample_alert.component
        assert result.severity == sample_alert.severity
        assert result.metric_value == sample_alert.metric_value
    
    @pytest.mark.asyncio
    async def test_get_alert_by_id_not_found(self, repository, mock_database):
        """알림 ID로 조회 실패 테스트"""
        # Given
        mock_database.alerts.find_one.return_value = None
        alert_id = uuid4()
        
        # When
        result = await repository.get_alert_by_id(alert_id)
        
        # Then
        assert result is None
    
    @pytest.mark.asyncio
    async def test_save_alert_rule_success(self, repository, sample_alert_rule, mock_database):
        """알림 규칙 저장 성공 테스트"""
        # Given
        mock_database.alert_rules.insert_one.return_value = AsyncMock()
        
        # When
        await repository.save_alert_rule(sample_alert_rule)
        
        # Then
        mock_database.alert_rules.insert_one.assert_called_once()
        call_args = mock_database.alert_rules.insert_one.call_args[0][0]
        assert call_args["_id"] == str(sample_alert_rule.rule_id)
        assert call_args["component"] == sample_alert_rule.component.value
        assert call_args["condition"] == sample_alert_rule.condition
        assert call_args["threshold"] == sample_alert_rule.threshold
        assert call_args["enabled"] == sample_alert_rule.enabled
        assert call_args["metric_name"] == sample_alert_rule.metric_name
        assert call_args["severity"] == sample_alert_rule.severity.value
        assert call_args["message"] == sample_alert_rule.message
        assert call_args["notification_channels"] == sample_alert_rule.notification_channels
        assert call_args["cooldown_minutes"] == sample_alert_rule.cooldown_minutes
    
    @pytest.mark.asyncio
    async def test_save_alert_rule_failure(self, repository, sample_alert_rule, mock_database):
        """알림 규칙 저장 실패 테스트"""
        # Given
        mock_database.alert_rules.insert_one.side_effect = Exception("Database error")
        
        # When & Then
        with pytest.raises(RepositoryError, match="알림 규칙 저장 실패"):
            await repository.save_alert_rule(sample_alert_rule)
    
    @pytest.mark.asyncio
    async def test_get_alert_rule_by_id_found(self, repository, sample_alert_rule, mock_database):
        """알림 규칙 ID로 조회 성공 테스트"""
        # Given
        mock_doc = {
            "_id": str(sample_alert_rule.rule_id),
            "name": sample_alert_rule.name,
            "component": sample_alert_rule.component.value,
            "metric_name": sample_alert_rule.metric_name,
            "condition": sample_alert_rule.condition,
            "threshold": sample_alert_rule.threshold,
            "severity": sample_alert_rule.severity.value,
            "message": sample_alert_rule.message,
            "enabled": sample_alert_rule.enabled,
            "notification_channels": sample_alert_rule.notification_channels,
            "cooldown_minutes": sample_alert_rule.cooldown_minutes,
            "last_triggered_at": None,
            "created_at": sample_alert_rule.created_at
        }
        mock_database.alert_rules.find_one.return_value = mock_doc
        
        # When
        result = await repository.get_alert_rule_by_id(sample_alert_rule.rule_id)
        
        # Then
        assert result is not None
        assert result.rule_id == sample_alert_rule.rule_id
        assert result.component == sample_alert_rule.component
        assert result.metric_name == sample_alert_rule.metric_name
        assert result.condition == sample_alert_rule.condition
        assert result.threshold == sample_alert_rule.threshold
        assert result.enabled == sample_alert_rule.enabled
    
    @pytest.mark.asyncio
    async def test_get_alert_rule_by_id_not_found(self, repository, mock_database):
        """알림 규칙 ID로 조회 실패 테스트"""
        # Given
        mock_database.alert_rules.find_one.return_value = None
        rule_id = uuid4()
        
        # When
        result = await repository.get_alert_rule_by_id(rule_id)
        
        # Then
        assert result is None
