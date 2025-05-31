"""
Monitor Infrastructure Repositories 테스트
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.monitor.infrastructure.repositories.mongodb_metric_repository import MongoDBMetricRepository
from src.modules.monitor.infrastructure.repositories.mongodb_alert_repository import MongoDBAlertRepository
from src.modules.monitor.domain.entities import (
    Metric, Alert, AlertRule, ComponentType, MetricType, AlertSeverity, AlertStatus,
    ProcessingStatistics, SystemOverview
)
from src.core.exceptions import RepositoryError
from src.utils.datetime import get_current_utc_time


@pytest.fixture
def mock_database():
    """Mock MongoDB 데이터베이스"""
    db = Mock()
    db.metrics = AsyncMock()
    db.processing_statistics = AsyncMock()
    db.system_overview = AsyncMock()
    db.alerts = AsyncMock()
    db.alert_rules = AsyncMock()
    return db


@pytest.fixture
def metric_repository(mock_database):
    """메트릭 리포지토리 인스턴스"""
    return MongoDBMetricRepository(mock_database)


@pytest.fixture
def alert_repository(mock_database):
    """알림 리포지토리 인스턴스"""
    return MongoDBAlertRepository(mock_database)


@pytest.fixture
def sample_metric():
    """샘플 메트릭"""
    return Metric(
        metric_id=uuid4(),
        component=ComponentType.PROCESS,
        metric_name="cpu_usage",
        metric_type=MetricType.GAUGE,
        value=75.5,
        unit="percent",
        tags={"host": "server1"},
        timestamp=get_current_utc_time()
    )


@pytest.fixture
def sample_alert():
    """샘플 알림"""
    return Alert(
        alert_id=uuid4(),
        rule_id=uuid4(),
        component=ComponentType.PROCESS,
        metric_name="cpu_usage",
        severity=AlertSeverity.HIGH,
        status=AlertStatus.ACTIVE,
        message="High CPU usage detected",
        metric_value=85.0,
        threshold=80.0,
        triggered_at=get_current_utc_time(),
        tags={"host": "server1"}
    )


@pytest.fixture
def sample_alert_rule():
    """샘플 알림 규칙"""
    return AlertRule(
        rule_id=uuid4(),
        component=ComponentType.PROCESS,
        metric_name="cpu_usage",
        condition="> 80",
        threshold=80.0,
        severity=AlertSeverity.HIGH,
        message="High CPU usage detected",
        enabled=True,
        notification_channels=["email", "slack"],
        cooldown_minutes=5,
        created_at=get_current_utc_time()
    )


class TestMongoDBMetricRepository:
    """MongoDB 메트릭 리포지토리 테스트"""
    
    @pytest.mark.asyncio
    async def test_save_metric_success(self, metric_repository, sample_metric, mock_database):
        """메트릭 저장 성공 테스트"""
        # Given
        mock_database.metrics.insert_one = AsyncMock()
        
        # When
        await metric_repository.save_metric(sample_metric)
        
        # Then
        mock_database.metrics.insert_one.assert_called_once()
        call_args = mock_database.metrics.insert_one.call_args[0][0]
        assert call_args["_id"] == str(sample_metric.metric_id)
        assert call_args["component"] == sample_metric.component.value
        assert call_args["metric_name"] == sample_metric.metric_name
        assert call_args["value"] == sample_metric.value
    
    @pytest.mark.asyncio
    async def test_save_metric_failure(self, metric_repository, sample_metric, mock_database):
        """메트릭 저장 실패 테스트"""
        # Given
        mock_database.metrics.insert_one = AsyncMock(side_effect=Exception("DB Error"))
        
        # When & Then
        with pytest.raises(RepositoryError, match="메트릭 저장 실패"):
            await metric_repository.save_metric(sample_metric)
    
    @pytest.mark.asyncio
    async def test_get_metrics_by_component(self, metric_repository, mock_database):
        """컴포넌트별 메트릭 조회 테스트"""
        # Given
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "_id": str(uuid4()),
                "component": "process",
                "metric_name": "cpu_usage",
                "metric_type": "gauge",
                "value": 75.5,
                "unit": "percent",
                "tags": {},
                "timestamp": get_current_utc_time()
            }
        ])
        
        mock_database.metrics.find.return_value.sort.return_value.limit.return_value = mock_cursor
        
        # When
        metrics = await metric_repository.get_metrics_by_component(ComponentType.PROCESS)
        
        # Then
        assert len(metrics) == 1
        assert metrics[0].component == ComponentType.PROCESS
        assert metrics[0].metric_name == "cpu_usage"
        mock_database.metrics.find.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_latest_metrics(self, metric_repository, mock_database):
        """최신 메트릭 조회 테스트"""
        # Given
        mock_database.metrics.find_one = AsyncMock(return_value={
            "_id": str(uuid4()),
            "component": "process",
            "metric_name": "cpu_usage",
            "metric_type": "gauge",
            "value": 75.5,
            "unit": "percent",
            "tags": {},
            "timestamp": get_current_utc_time()
        })
        
        # When
        metrics = await metric_repository.get_latest_metrics(
            ComponentType.PROCESS, ["cpu_usage"]
        )
        
        # Then
        assert len(metrics) == 1
        assert metrics[0].metric_name == "cpu_usage"
        mock_database.metrics.find_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_old_metrics(self, metric_repository, mock_database):
        """오래된 메트릭 삭제 테스트"""
        # Given
        mock_result = Mock()
        mock_result.deleted_count = 5
        mock_database.metrics.delete_many = AsyncMock(return_value=mock_result)
        
        older_than = get_current_utc_time() - timedelta(days=7)
        
        # When
        deleted_count = await metric_repository.delete_old_metrics(older_than)
        
        # Then
        assert deleted_count == 5
        mock_database.metrics.delete_many.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_processing_statistics(self, metric_repository, mock_database):
        """처리 통계 업데이트 테스트"""
        # Given
        stats = ProcessingStatistics(
            component=ComponentType.PROCESS,
            total_processed=100,
            total_failed=5,
            average_processing_time_ms=150.0,
            updated_at=get_current_utc_time()
        )
        
        mock_database.processing_statistics.replace_one = AsyncMock()
        
        # When
        await metric_repository.update_processing_statistics(stats)
        
        # Then
        mock_database.processing_statistics.replace_one.assert_called_once()
        call_args = mock_database.processing_statistics.replace_one.call_args
        assert call_args[1]["upsert"] is True
    
    @pytest.mark.asyncio
    async def test_update_system_overview(self, metric_repository, mock_database):
        """시스템 개요 업데이트 테스트"""
        # Given
        overview = SystemOverview(
            total_documents=1000,
            total_chunks=5000,
            total_embeddings=5000,
            storage_used_mb=250.5,
            active_processing_jobs=3,
            system_health_score=95.0,
            updated_at=get_current_utc_time()
        )
        
        mock_database.system_overview.insert_one = AsyncMock()
        
        # When
        await metric_repository.update_system_overview(overview)
        
        # Then
        mock_database.system_overview.insert_one.assert_called_once()


class TestMongoDBAlertRepository:
    """MongoDB 알림 리포지토리 테스트"""
    
    @pytest.mark.asyncio
    async def test_save_alert_success(self, alert_repository, sample_alert, mock_database):
        """알림 저장 성공 테스트"""
        # Given
        mock_database.alerts.insert_one = AsyncMock()
        
        # When
        await alert_repository.save_alert(sample_alert)
        
        # Then
        mock_database.alerts.insert_one.assert_called_once()
        call_args = mock_database.alerts.insert_one.call_args[0][0]
        assert call_args["_id"] == str(sample_alert.alert_id)
        assert call_args["component"] == sample_alert.component.value
        assert call_args["severity"] == sample_alert.severity.value
        assert call_args["status"] == sample_alert.status.value
    
    @pytest.mark.asyncio
    async def test_update_alert(self, alert_repository, sample_alert, mock_database):
        """알림 업데이트 테스트"""
        # Given
        sample_alert.acknowledge("admin")
        mock_database.alerts.update_one = AsyncMock()
        
        # When
        await alert_repository.update_alert(sample_alert)
        
        # Then
        mock_database.alerts.update_one.assert_called_once()
        call_args = mock_database.alerts.update_one.call_args
        assert call_args[0][0]["_id"] == str(sample_alert.alert_id)
        assert "acknowledged_by" in call_args[0][1]["$set"]
    
    @pytest.mark.asyncio
    async def test_get_alert_by_id_found(self, alert_repository, sample_alert, mock_database):
        """ID로 알림 조회 - 발견됨"""
        # Given
        mock_database.alerts.find_one = AsyncMock(return_value={
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
            "tags": sample_alert.tags
        })
        
        # When
        alert = await alert_repository.get_alert_by_id(sample_alert.alert_id)
        
        # Then
        assert alert is not None
        assert alert.alert_id == sample_alert.alert_id
        assert alert.component == sample_alert.component
        assert alert.severity == sample_alert.severity
    
    @pytest.mark.asyncio
    async def test_get_alert_by_id_not_found(self, alert_repository, mock_database):
        """ID로 알림 조회 - 발견되지 않음"""
        # Given
        mock_database.alerts.find_one = AsyncMock(return_value=None)
        
        # When
        alert = await alert_repository.get_alert_by_id(uuid4())
        
        # Then
        assert alert is None
    
    @pytest.mark.asyncio
    async def test_get_active_alerts(self, alert_repository, mock_database):
        """활성 알림 조회 테스트"""
        # Given
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "_id": str(uuid4()),
                "rule_id": str(uuid4()),
                "component": "process",
                "metric_name": "cpu_usage",
                "severity": "high",
                "status": "active",
                "message": "High CPU usage",
                "metric_value": 85.0,
                "threshold": 80.0,
                "triggered_at": get_current_utc_time(),
                "tags": {}
            }
        ])
        
        mock_database.alerts.find.return_value.sort.return_value = mock_cursor
        
        # When
        alerts = await alert_repository.get_active_alerts()
        
        # Then
        assert len(alerts) == 1
        assert alerts[0].status == AlertStatus.ACTIVE
        mock_database.alerts.find.assert_called_once_with({"status": "active"})
    
    @pytest.mark.asyncio
    async def test_save_alert_rule(self, alert_repository, sample_alert_rule, mock_database):
        """알림 규칙 저장 테스트"""
        # Given
        mock_database.alert_rules.insert_one = AsyncMock()
        
        # When
        await alert_repository.save_alert_rule(sample_alert_rule)
        
        # Then
        mock_database.alert_rules.insert_one.assert_called_once()
        call_args = mock_database.alert_rules.insert_one.call_args[0][0]
        assert call_args["_id"] == str(sample_alert_rule.rule_id)
        assert call_args["component"] == sample_alert_rule.component.value
        assert call_args["enabled"] == sample_alert_rule.enabled
    
    @pytest.mark.asyncio
    async def test_get_alert_rules_by_metric(self, alert_repository, mock_database):
        """메트릭별 알림 규칙 조회 테스트"""
        # Given
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "_id": str(uuid4()),
                "component": "process",
                "metric_name": "cpu_usage",
                "condition": "> 80",
                "threshold": 80.0,
                "severity": "high",
                "message": "High CPU usage",
                "enabled": True,
                "notification_channels": ["email"],
                "cooldown_minutes": 5,
                "created_at": get_current_utc_time()
            }
        ])
        
        mock_database.alert_rules.find.return_value = mock_cursor
        
        # When
        rules = await alert_repository.get_alert_rules_by_metric(
            "cpu_usage", ComponentType.PROCESS, enabled_only=True
        )
        
        # Then
        assert len(rules) == 1
        assert rules[0].metric_name == "cpu_usage"
        assert rules[0].enabled is True
        mock_database.alert_rules.find.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_alert_rule_success(self, alert_repository, mock_database):
        """알림 규칙 삭제 성공 테스트"""
        # Given
        mock_result = Mock()
        mock_result.deleted_count = 1
        mock_database.alert_rules.delete_one = AsyncMock(return_value=mock_result)
        
        rule_id = uuid4()
        
        # When
        result = await alert_repository.delete_alert_rule(rule_id)
        
        # Then
        assert result is True
        mock_database.alert_rules.delete_one.assert_called_once_with(
            {"_id": str(rule_id)}
        )
    
    @pytest.mark.asyncio
    async def test_delete_alert_rule_not_found(self, alert_repository, mock_database):
        """알림 규칙 삭제 - 규칙 없음"""
        # Given
        mock_result = Mock()
        mock_result.deleted_count = 0
        mock_database.alert_rules.delete_one = AsyncMock(return_value=mock_result)
        
        rule_id = uuid4()
        
        # When
        result = await alert_repository.delete_alert_rule(rule_id)
        
        # Then
        assert result is False


class TestRepositoryErrorHandling:
    """리포지토리 에러 처리 테스트"""
    
    @pytest.mark.asyncio
    async def test_metric_repository_database_error(self, metric_repository, sample_metric, mock_database):
        """메트릭 리포지토리 데이터베이스 에러"""
        # Given
        mock_database.metrics.insert_one = AsyncMock(side_effect=Exception("Connection failed"))
        
        # When & Then
        with pytest.raises(RepositoryError):
            await metric_repository.save_metric(sample_metric)
    
    @pytest.mark.asyncio
    async def test_alert_repository_database_error(self, alert_repository, sample_alert, mock_database):
        """알림 리포지토리 데이터베이스 에러"""
        # Given
        mock_database.alerts.insert_one = AsyncMock(side_effect=Exception("Connection failed"))
        
        # When & Then
        with pytest.raises(RepositoryError):
            await alert_repository.save_alert(sample_alert)


class TestRepositoryInitialization:
    """리포지토리 초기화 테스트"""
    
    def test_metric_repository_initialization(self, mock_database):
        """메트릭 리포지토리 초기화 테스트"""
        # When
        repo = MongoDBMetricRepository(mock_database)
        
        # Then
        assert repo.db == mock_database
        assert repo.metrics_collection == mock_database.metrics
        assert repo.processing_stats_collection == mock_database.processing_statistics
        assert repo.system_overview_collection == mock_database.system_overview
    
    def test_alert_repository_initialization(self, mock_database):
        """알림 리포지토리 초기화 테스트"""
        # When
        repo = MongoDBAlertRepository(mock_database)
        
        # Then
        assert repo.db == mock_database
        assert repo.alerts_collection == mock_database.alerts
        assert repo.alert_rules_collection == mock_database.alert_rules
