"""
Monitor Application Ports 테스트
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

from src.modules.monitor.application.ports import (
    MetricRepositoryPort, AlertRepositoryPort, 
    NotificationPort, HealthCheckPort
)
from src.modules.monitor.domain.entities import (
    SystemMetric, ProcessingStatistics, SystemOverview,
    AlertRule, Alert, HealthStatus, ComponentType, MetricType
)


class MockMetricRepository(MetricRepositoryPort):
    """Mock 메트릭 저장소"""
    
    def __init__(self):
        self.metrics: Dict[str, SystemMetric] = {}
        self.processing_stats: Dict[ComponentType, ProcessingStatistics] = {}
        self.system_overviews: List[SystemOverview] = []
    
    async def save_metric(self, metric: SystemMetric) -> None:
        self.metrics[str(metric.metric_id)] = metric
    
    async def get_metric_by_id(self, metric_id) -> Optional[SystemMetric]:
        return self.metrics.get(str(metric_id))
    
    async def get_metrics_by_component(
        self, component: ComponentType, start_time=None, end_time=None
    ) -> List[SystemMetric]:
        return [m for m in self.metrics.values() if m.component == component]
    
    async def get_metrics_by_name(
        self, name: str, component=None, start_time=None, end_time=None
    ) -> List[SystemMetric]:
        return [m for m in self.metrics.values() if m.name == name]
    
    async def get_metrics_by_type(
        self, metric_type: MetricType, component=None, start_time=None, end_time=None
    ) -> List[SystemMetric]:
        return [m for m in self.metrics.values() if m.metric_type == metric_type]
    
    async def update_metric(self, metric: SystemMetric) -> None:
        self.metrics[str(metric.metric_id)] = metric
    
    async def delete_metric(self, metric_id) -> bool:
        if str(metric_id) in self.metrics:
            del self.metrics[str(metric_id)]
            return True
        return False
    
    async def save_processing_statistics(self, stats: ProcessingStatistics) -> None:
        self.processing_stats[stats.component] = stats
    
    async def get_processing_statistics_by_component(
        self, component: ComponentType
    ) -> Optional[ProcessingStatistics]:
        return self.processing_stats.get(component)
    
    async def get_all_processing_statistics(self) -> List[ProcessingStatistics]:
        return list(self.processing_stats.values())
    
    async def update_processing_statistics(self, stats: ProcessingStatistics) -> None:
        self.processing_stats[stats.component] = stats
    
    async def save_system_overview(self, overview: SystemOverview) -> None:
        self.system_overviews.append(overview)
    
    async def get_latest_system_overview(self) -> Optional[SystemOverview]:
        return self.system_overviews[-1] if self.system_overviews else None
    
    async def get_system_overview_history(
        self, start_time: datetime, end_time: datetime, limit: int = 100
    ) -> List[SystemOverview]:
        return self.system_overviews[:limit]
    
    async def update_system_overview(self, overview: SystemOverview) -> None:
        if self.system_overviews:
            self.system_overviews[-1] = overview
    
    async def cleanup_old_metrics(
        self, before_date: datetime, component=None
    ) -> int:
        return 0
    
    async def get_metric_aggregation(
        self, metric_name: str, component: ComponentType, aggregation_type: str,
        start_time: datetime, end_time: datetime, interval_minutes: int = 5
    ) -> List[dict]:
        return []


class MockAlertRepository(AlertRepositoryPort):
    """Mock 알림 저장소"""
    
    def __init__(self):
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alerts: Dict[str, Alert] = {}
    
    async def save_alert_rule(self, rule: AlertRule) -> None:
        self.alert_rules[str(rule.rule_id)] = rule
    
    async def get_alert_rule_by_id(self, rule_id) -> Optional[AlertRule]:
        return self.alert_rules.get(str(rule_id))
    
    async def get_alert_rules_by_component(
        self, component: ComponentType, enabled_only: bool = True
    ) -> List[AlertRule]:
        rules = [r for r in self.alert_rules.values() if r.component == component]
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules
    
    async def get_alert_rules_by_metric(
        self, metric_name: str, component=None, enabled_only: bool = True
    ) -> List[AlertRule]:
        rules = [r for r in self.alert_rules.values() if r.metric_name == metric_name]
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules
    
    async def get_all_alert_rules(self, enabled_only: bool = True) -> List[AlertRule]:
        rules = list(self.alert_rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules
    
    async def update_alert_rule(self, rule: AlertRule) -> None:
        self.alert_rules[str(rule.rule_id)] = rule
    
    async def delete_alert_rule(self, rule_id) -> bool:
        if str(rule_id) in self.alert_rules:
            del self.alert_rules[str(rule_id)]
            return True
        return False
    
    async def save_alert(self, alert: Alert) -> None:
        self.alerts[str(alert.alert_id)] = alert
    
    async def get_alert_by_id(self, alert_id) -> Optional[Alert]:
        return self.alerts.get(str(alert_id))
    
    async def get_alerts_by_rule(
        self, rule_id, status=None, start_time=None, end_time=None
    ) -> List[Alert]:
        alerts = [a for a in self.alerts.values() if a.rule_id == rule_id]
        if status:
            alerts = [a for a in alerts if a.status == status]
        return alerts
    
    async def get_alerts_by_component(
        self, component: ComponentType, status=None, start_time=None, end_time=None
    ) -> List[Alert]:
        alerts = [a for a in self.alerts.values() if a.component == component]
        if status:
            alerts = [a for a in alerts if a.status == status]
        return alerts
    
    async def get_alerts_by_severity(
        self, severity: str, status=None, start_time=None, end_time=None
    ) -> List[Alert]:
        alerts = [a for a in self.alerts.values() if a.severity == severity]
        if status:
            alerts = [a for a in alerts if a.status == status]
        return alerts
    
    async def get_active_alerts(
        self, component=None, severity=None
    ) -> List[Alert]:
        alerts = [a for a in self.alerts.values() if a.is_active()]
        if component:
            alerts = [a for a in alerts if a.component == component]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts
    
    async def get_recent_alerts(
        self, hours: int = 24, component=None, status=None
    ) -> List[Alert]:
        return list(self.alerts.values())
    
    async def update_alert(self, alert: Alert) -> None:
        self.alerts[str(alert.alert_id)] = alert
    
    async def resolve_alert(self, alert_id) -> bool:
        if str(alert_id) in self.alerts:
            self.alerts[str(alert_id)].resolve()
            return True
        return False
    
    async def suppress_alert(self, alert_id) -> bool:
        if str(alert_id) in self.alerts:
            self.alerts[str(alert_id)].suppress()
            return True
        return False
    
    async def bulk_resolve_alerts(
        self, rule_id=None, component=None, before_time=None
    ) -> int:
        return 0
    
    async def cleanup_old_alerts(self, before_date: datetime, status=None) -> int:
        return 0
    
    async def get_alert_statistics(
        self, start_time: datetime, end_time: datetime, component=None
    ) -> dict:
        return {"total": len(self.alerts)}
    
    async def get_alert_count_by_severity(
        self, start_time: datetime, end_time: datetime, component=None
    ) -> dict:
        return {"high": 0, "medium": 0, "low": 0}
    
    async def get_top_alerting_components(
        self, start_time: datetime, end_time: datetime, limit: int = 10
    ) -> List[dict]:
        return []


class MockNotificationService(NotificationPort):
    """Mock 알림 발송 서비스"""
    
    def __init__(self):
        self.sent_notifications = []
    
    async def send_alert_notification(
        self, alert: Alert, recipients: List[str], notification_type: str = "email"
    ) -> bool:
        self.sent_notifications.append({
            "type": "alert",
            "alert_id": alert.alert_id,
            "recipients": recipients,
            "notification_type": notification_type
        })
        return True
    
    async def send_system_health_notification(
        self, component: ComponentType, status: str, message: str,
        recipients: List[str], notification_type: str = "email"
    ) -> bool:
        self.sent_notifications.append({
            "type": "health",
            "component": component,
            "status": status,
            "recipients": recipients
        })
        return True
    
    async def send_metric_threshold_notification(
        self, metric_name: str, component: ComponentType, current_value: float,
        threshold: float, condition: str, recipients: List[str],
        notification_type: str = "email"
    ) -> bool:
        return True
    
    async def send_bulk_alert_notification(
        self, alerts: List[Alert], recipients: List[str],
        notification_type: str = "email", summary_format: bool = True
    ) -> bool:
        return True
    
    async def send_daily_summary_notification(
        self, summary_data: Dict[str, Any], recipients: List[str],
        notification_type: str = "email"
    ) -> bool:
        return True
    
    async def send_weekly_report_notification(
        self, report_data: Dict[str, Any], recipients: List[str],
        notification_type: str = "email"
    ) -> bool:
        return True
    
    async def send_custom_notification(
        self, title: str, message: str, recipients: List[str],
        notification_type: str = "email", priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        return True
    
    async def validate_recipients(
        self, recipients: List[str], notification_type: str
    ) -> List[str]:
        return recipients
    
    async def get_notification_templates(
        self, notification_type: str
    ) -> Dict[str, str]:
        return {"default": "Default template"}
    
    async def update_notification_template(
        self, template_name: str, notification_type: str, template_content: str
    ) -> bool:
        return True
    
    async def get_notification_history(
        self, recipient=None, notification_type=None, start_time=None,
        end_time=None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        return self.sent_notifications[:limit]
    
    async def get_notification_statistics(
        self, start_time: str, end_time: str, notification_type=None
    ) -> Dict[str, Any]:
        return {"total_sent": len(self.sent_notifications)}
    
    async def test_notification_channel(
        self, notification_type: str, test_recipient: str
    ) -> bool:
        return True
    
    async def configure_notification_channel(
        self, notification_type: str, configuration: Dict[str, Any]
    ) -> bool:
        return True
    
    async def get_supported_notification_types(self) -> List[str]:
        return ["email", "slack", "webhook", "sms"]
    
    async def schedule_notification(
        self, notification_data: Dict[str, Any], schedule_time: str,
        recurring: bool = False, recurring_pattern: Optional[str] = None
    ) -> str:
        return str(uuid4())
    
    async def cancel_scheduled_notification(self, notification_id: str) -> bool:
        return True
    
    async def get_scheduled_notifications(
        self, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        return []


class MockHealthCheckService(HealthCheckPort):
    """Mock 건강 상태 확인 서비스"""
    
    async def check_component_health(
        self, component: ComponentType, timeout_seconds: int = 30
    ) -> HealthStatus:
        return HealthStatus.healthy(component, "Component is healthy")
    
    async def check_database_health(
        self, connection_string=None, timeout_seconds: int = 10
    ) -> HealthStatus:
        return HealthStatus.healthy(ComponentType.DATABASE, "Database is healthy")
    
    async def check_vector_db_health(
        self, connection_config=None, timeout_seconds: int = 10
    ) -> HealthStatus:
        return HealthStatus.healthy(ComponentType.VECTOR_DB, "Vector DB is healthy")
    
    async def check_messaging_health(
        self, broker_config=None, timeout_seconds: int = 10
    ) -> HealthStatus:
        return HealthStatus.healthy(ComponentType.MESSAGING, "Messaging is healthy")
    
    async def check_llm_service_health(
        self, service_config=None, timeout_seconds: int = 30
    ) -> HealthStatus:
        return HealthStatus.healthy(ComponentType.LLM, "LLM service is healthy")
    
    async def check_external_api_health(
        self, api_endpoint: str, headers=None, timeout_seconds: int = 15
    ) -> HealthStatus:
        return HealthStatus.healthy(ComponentType.SEARCH, "External API is healthy")
    
    async def check_file_system_health(
        self, paths: List[str], check_write_permission: bool = True
    ) -> HealthStatus:
        return HealthStatus.healthy(ComponentType.INGEST, "File system is healthy")
    
    async def check_memory_usage(
        self, warning_threshold_percent: float = 80.0,
        critical_threshold_percent: float = 95.0
    ) -> HealthStatus:
        return HealthStatus.healthy(ComponentType.PROCESS, "Memory usage is normal")
    
    async def check_cpu_usage(
        self, warning_threshold_percent: float = 80.0,
        critical_threshold_percent: float = 95.0, duration_seconds: int = 5
    ) -> HealthStatus:
        return HealthStatus.healthy(ComponentType.PROCESS, "CPU usage is normal")
    
    async def check_disk_usage(
        self, paths: List[str], warning_threshold_percent: float = 80.0,
        critical_threshold_percent: float = 95.0
    ) -> HealthStatus:
        return HealthStatus.healthy(ComponentType.INGEST, "Disk usage is normal")
    
    async def check_network_connectivity(
        self, hosts: List[str], timeout_seconds: int = 5
    ) -> HealthStatus:
        return HealthStatus.healthy(ComponentType.SEARCH, "Network is healthy")
    
    async def check_service_dependencies(
        self, component: ComponentType, dependency_configs: List[Dict[str, Any]]
    ) -> List[HealthStatus]:
        return [HealthStatus.healthy(component, "Dependencies are healthy")]
    
    async def perform_comprehensive_health_check(
        self, components=None, include_system_resources: bool = True,
        timeout_seconds: int = 60
    ) -> Dict[str, HealthStatus]:
        return {
            "database": HealthStatus.healthy(ComponentType.DATABASE, "Healthy"),
            "vector_db": HealthStatus.healthy(ComponentType.VECTOR_DB, "Healthy")
        }
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        return {"cpu_usage": 50.0, "memory_usage": 60.0}
    
    async def get_component_metrics(self, component: ComponentType) -> Dict[str, Any]:
        return {"response_time": 100.0, "error_rate": 0.01}
    
    async def validate_configuration(
        self, component: ComponentType, config: Dict[str, Any]
    ) -> HealthStatus:
        return HealthStatus.healthy(component, "Configuration is valid")
    
    async def test_component_functionality(
        self, component: ComponentType, test_data=None
    ) -> HealthStatus:
        return HealthStatus.healthy(component, "Functionality test passed")
    
    async def get_health_check_history(
        self, component=None, start_time=None, end_time=None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        return []
    
    async def schedule_health_check(
        self, component: ComponentType, interval_minutes: int, enabled: bool = True
    ) -> str:
        return str(uuid4())
    
    async def cancel_scheduled_health_check(self, schedule_id: str) -> bool:
        return True
    
    async def get_scheduled_health_checks(
        self, component=None, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        return []
    
    async def update_health_check_thresholds(
        self, component: ComponentType, thresholds: Dict[str, Any]
    ) -> bool:
        return True
    
    async def get_health_check_configuration(
        self, component: ComponentType
    ) -> Dict[str, Any]:
        return {"enabled": True, "interval": 5}


class TestMetricRepositoryPort:
    """MetricRepositoryPort 테스트"""
    
    @pytest.fixture
    def mock_repository(self):
        return MockMetricRepository()
    
    @pytest.mark.asyncio
    async def test_save_and_get_metric(self, mock_repository):
        """메트릭 저장 및 조회 테스트"""
        # Given
        metric = SystemMetric.create(
            name="test_metric",
            metric_type=MetricType.COUNTER,
            component=ComponentType.PROCESS,
            description="Test metric"
        )
        
        # When
        await mock_repository.save_metric(metric)
        retrieved_metric = await mock_repository.get_metric_by_id(metric.metric_id)
        
        # Then
        assert retrieved_metric is not None
        assert retrieved_metric.name == "test_metric"
        assert retrieved_metric.metric_type == MetricType.COUNTER
        assert retrieved_metric.component == ComponentType.PROCESS
    
    @pytest.mark.asyncio
    async def test_get_metrics_by_component(self, mock_repository):
        """컴포넌트별 메트릭 조회 테스트"""
        # Given
        metric1 = SystemMetric.create("metric1", MetricType.COUNTER, ComponentType.PROCESS, "Test metric 1")
        metric2 = SystemMetric.create("metric2", MetricType.GAUGE, ComponentType.PROCESS, "Test metric 2")
        metric3 = SystemMetric.create("metric3", MetricType.COUNTER, ComponentType.SEARCH, "Test metric 3")
        
        await mock_repository.save_metric(metric1)
        await mock_repository.save_metric(metric2)
        await mock_repository.save_metric(metric3)
        
        # When
        process_metrics = await mock_repository.get_metrics_by_component(ComponentType.PROCESS)
        search_metrics = await mock_repository.get_metrics_by_component(ComponentType.SEARCH)
        
        # Then
        assert len(process_metrics) == 2
        assert len(search_metrics) == 1
        assert all(m.component == ComponentType.PROCESS for m in process_metrics)
        assert all(m.component == ComponentType.SEARCH for m in search_metrics)
    
    @pytest.mark.asyncio
    async def test_processing_statistics_operations(self, mock_repository):
        """처리 통계 연산 테스트"""
        # Given
        stats = ProcessingStatistics.create(ComponentType.PROCESS)
        stats.update_processing_stats(10, 2, 1, 5.0)
        
        # When
        await mock_repository.save_processing_statistics(stats)
        retrieved_stats = await mock_repository.get_processing_statistics_by_component(
            ComponentType.PROCESS
        )
        
        # Then
        assert retrieved_stats is not None
        assert retrieved_stats.total_processed == 10
        assert retrieved_stats.total_failed == 2
        assert retrieved_stats.total_retries == 1
    
    @pytest.mark.asyncio
    async def test_system_overview_operations(self, mock_repository):
        """시스템 개요 연산 테스트"""
        # Given
        overview = SystemOverview.create()
        overview.update_document_stats(100, 500)
        overview.update_search_stats(50, 45, 150.0, 2000.0)
        
        # When
        await mock_repository.save_system_overview(overview)
        latest_overview = await mock_repository.get_latest_system_overview()
        
        # Then
        assert latest_overview is not None
        assert latest_overview.total_documents == 100
        assert latest_overview.total_chunks == 500
        assert latest_overview.total_searches == 50


class TestAlertRepositoryPort:
    """AlertRepositoryPort 테스트"""
    
    @pytest.fixture
    def mock_repository(self):
        return MockAlertRepository()
    
    @pytest.mark.asyncio
    async def test_alert_rule_operations(self, mock_repository):
        """알림 규칙 연산 테스트"""
        # Given
        rule = AlertRule.create(
            name="High Error Rate",
            component=ComponentType.PROCESS,
            metric_name="error_rate",
            condition="gt",
            threshold=0.05,
            severity="high"
        )
        
        # When
        await mock_repository.save_alert_rule(rule)
        retrieved_rule = await mock_repository.get_alert_rule_by_id(rule.rule_id)
        
        # Then
        assert retrieved_rule is not None
        assert retrieved_rule.name == "High Error Rate"
        assert retrieved_rule.component == ComponentType.PROCESS
        assert retrieved_rule.threshold == 0.05
    
    @pytest.mark.asyncio
    async def test_alert_operations(self, mock_repository):
        """알림 연산 테스트"""
        # Given
        rule = AlertRule.create(
            "Test Rule", ComponentType.PROCESS, "error_rate", "gt", 0.05, "high"
        )
        await mock_repository.save_alert_rule(rule)
        
        alert = Alert.create(rule, 0.08, "Error rate is too high")
        
        # When
        await mock_repository.save_alert(alert)
        retrieved_alert = await mock_repository.get_alert_by_id(alert.alert_id)
        
        # Then
        assert retrieved_alert is not None
        assert retrieved_alert.rule_id == rule.rule_id
        assert retrieved_alert.current_value == 0.08
        assert retrieved_alert.is_active()
    
    @pytest.mark.asyncio
    async def test_get_active_alerts(self, mock_repository):
        """활성 알림 조회 테스트"""
        # Given
        rule = AlertRule.create(
            "Test Rule", ComponentType.PROCESS, "error_rate", "gt", 0.05, "high"
        )
        await mock_repository.save_alert_rule(rule)
        
        alert1 = Alert.create(rule, 0.08, "Active alert")
        alert2 = Alert.create(rule, 0.09, "Another active alert")
        alert2.resolve()  # 해결된 알림
        
        await mock_repository.save_alert(alert1)
        await mock_repository.save_alert(alert2)
        
        # When
        active_alerts = await mock_repository.get_active_alerts()
        
        # Then
        assert len(active_alerts) == 1
        assert active_alerts[0].alert_id == alert1.alert_id


class TestNotificationPort:
    """NotificationPort 테스트"""
    
    @pytest.fixture
    def mock_service(self):
        return MockNotificationService()
    
    @pytest.mark.asyncio
    async def test_send_alert_notification(self, mock_service):
        """알림 발송 테스트"""
        # Given
        rule = AlertRule.create(
            "Test Rule", ComponentType.PROCESS, "error_rate", "gt", 0.05, "high"
        )
        alert = Alert.create(rule, 0.08, "Error rate is too high")
        recipients = ["admin@example.com", "ops@example.com"]
        
        # When
        result = await mock_service.send_alert_notification(
            alert, recipients, "email"
        )
        
        # Then
        assert result is True
        assert len(mock_service.sent_notifications) == 1
        notification = mock_service.sent_notifications[0]
        assert notification["type"] == "alert"
        assert notification["alert_id"] == alert.alert_id
        assert notification["recipients"] == recipients
    
    @pytest.mark.asyncio
    async def test_send_system_health_notification(self, mock_service):
        """시스템 건강 상태 알림 발송 테스트"""
        # Given
        component = ComponentType.DATABASE
        status = "degraded"
        message = "Database response time is high"
        recipients = ["admin@example.com"]
        
        # When
        result = await mock_service.send_system_health_notification(
            component, status, message, recipients
        )
        
        # Then
        assert result is True
        assert len(mock_service.sent_notifications) == 1
        notification = mock_service.sent_notifications[0]
        assert notification["type"] == "health"
        assert notification["component"] == component
        assert notification["status"] == status
    
    @pytest.mark.asyncio
    async def test_get_supported_notification_types(self, mock_service):
        """지원되는 알림 타입 조회 테스트"""
        # When
        types = await mock_service.get_supported_notification_types()
        
        # Then
        assert "email" in types
        assert "slack" in types
        assert "webhook" in types
        assert "sms" in types


class TestHealthCheckPort:
    """HealthCheckPort 테스트"""
    
    @pytest.fixture
    def mock_service(self):
        return MockHealthCheckService()
    
    @pytest.mark.asyncio
    async def test_check_component_health(self, mock_service):
        """컴포넌트 건강 상태 확인 테스트"""
        # When
        health_status = await mock_service.check_component_health(
            ComponentType.DATABASE
        )
        
        # Then
        assert health_status.component == ComponentType.DATABASE
        assert health_status.is_healthy()
        assert health_status.message == "Component is healthy"
    
    @pytest.mark.asyncio
    async def test_perform_comprehensive_health_check(self, mock_service):
        """종합 건강 상태 확인 테스트"""
        # When
        health_results = await mock_service.perform_comprehensive_health_check()
        
        # Then
        assert "database" in health_results
        assert "vector_db" in health_results
        assert health_results["database"].is_healthy()
        assert health_results["vector_db"].is_healthy()
    
    @pytest.mark.asyncio
    async def test_get_system_metrics(self, mock_service):
        """시스템 메트릭 조회 테스트"""
        # When
        metrics = await mock_service.get_system_metrics()
        
        # Then
        assert "cpu_usage" in metrics
        assert "memory_usage" in metrics
        assert metrics["cpu_usage"] == 50.0
        assert metrics["memory_usage"] == 60.0
    
    @pytest.mark.asyncio
    async def test_schedule_health_check(self, mock_service):
        """건강 상태 확인 스케줄링 테스트"""
        # When
        schedule_id = await mock_service.schedule_health_check(
            ComponentType.DATABASE, interval_minutes=5
        )
        
        # Then
        assert schedule_id is not None
        assert len(schedule_id) > 0
    
    @pytest.mark.asyncio
    async def test_validate_configuration(self, mock_service):
        """설정 유효성 검증 테스트"""
        # Given
        config = {"host": "localhost", "port": 5432}
        
        # When
        validation_result = await mock_service.validate_configuration(
            ComponentType.DATABASE, config
        )
        
        # Then
        assert validation_result.is_healthy()
        assert validation_result.message == "Configuration is valid"
