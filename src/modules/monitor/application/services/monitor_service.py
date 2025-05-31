"""
Monitor Service

모니터링 관련 유즈케이스들을 조합하는 서비스입니다.
"""

from src.modules.monitor.application.use_cases.collect_metrics import (
    CollectMetricsUseCase, CollectSystemMetricsUseCase
)
from src.modules.monitor.application.use_cases.check_health import (
    CheckComponentHealthUseCase, PerformHealthCheckUseCase
)
from src.modules.monitor.application.use_cases.manage_alerts import (
    CreateAlertRuleUseCase, ProcessMetricAlertUseCase, 
    ResolveAlertUseCase, BulkResolveAlertsUseCase, GetAlertSummaryUseCase
)
from src.modules.monitor.application.ports import (
    MetricRepositoryPort, AlertRepositoryPort, 
    HealthCheckPort, NotificationPort
)


class MonitorService:
    """모니터링 서비스"""
    
    def __init__(
        self,
        metric_repository: MetricRepositoryPort,
        alert_repository: AlertRepositoryPort,
        health_check_service: HealthCheckPort,
        notification_service: NotificationPort
    ):
        self.metric_repository = metric_repository
        self.alert_repository = alert_repository
        self.health_check_service = health_check_service
        self.notification_service = notification_service
        
        # 유즈케이스 인스턴스 생성
        self.collect_metrics_use_case = CollectMetricsUseCase(
            metric_repository, health_check_service
        )
        
        self.collect_system_metrics_use_case = CollectSystemMetricsUseCase(
            metric_repository, health_check_service
        )
        
        self.check_health_use_case = CheckComponentHealthUseCase(
            health_check_service, alert_repository, notification_service
        )
        
        self.check_system_health_use_case = PerformHealthCheckUseCase(
            health_check_service, alert_repository, notification_service
        )
        
        self.create_alert_rule_use_case = CreateAlertRuleUseCase(
            alert_repository
        )
        
        self.process_metric_alert_use_case = ProcessMetricAlertUseCase(
            alert_repository, notification_service
        )
        
        self.resolve_alert_use_case = ResolveAlertUseCase(
            alert_repository, notification_service
        )
        
        self.bulk_resolve_alerts_use_case = BulkResolveAlertsUseCase(
            alert_repository, notification_service
        )
        
        self.get_alert_summary_use_case = GetAlertSummaryUseCase(
            alert_repository
        )
