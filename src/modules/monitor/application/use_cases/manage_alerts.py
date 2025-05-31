"""
알림 관리 유즈케이스

알림 규칙 생성, 알림 발생, 알림 처리 등을 관리하는 유즈케이스입니다.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from src.core.exceptions import ValidationError, BusinessLogicError, NotFoundError
from src.modules.monitor.domain.entities import (
    AlertRule, Alert, ComponentType
)
from src.modules.monitor.application.ports import (
    AlertRepositoryPort, MetricRepositoryPort, NotificationPort
)


@dataclass
class CreateAlertCommand:
    """알림 생성 명령"""
    component: str
    metric_name: str
    condition: str
    severity: str
    message: str
    enabled: bool = True


@dataclass
class UpdateAlertCommand:
    """알림 업데이트 명령"""
    alert_id: str
    status: Optional[str] = None
    resolution_note: Optional[str] = None
    resolved_by: Optional[str] = None


@dataclass
class GetAlertsQuery:
    """알림 조회 쿼리"""
    component: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    limit: int = 100
    offset: int = 0


class CreateAlertRuleCommand:
    """알림 규칙 생성 명령"""
    
    def __init__(
        self,
        name: str,
        component: ComponentType,
        metric_name: str,
        condition: str,
        threshold: float,
        severity: str,
        description: str = "",
        enabled: bool = True,
        notification_channels: List[str] = None,
        cooldown_minutes: int = 5
    ):
        self.name = name
        self.component = component
        self.metric_name = metric_name
        self.condition = condition
        self.threshold = threshold
        self.severity = severity
        self.description = description
        self.enabled = enabled
        self.notification_channels = notification_channels or []
        self.cooldown_minutes = cooldown_minutes
        
        self._validate()
    
    def _validate(self):
        """명령 유효성 검증"""
        if not self.name.strip():
            raise ValidationError("알림 규칙 이름이 필요합니다")
        
        if not self.metric_name.strip():
            raise ValidationError("메트릭 이름이 필요합니다")
        
        if self.condition not in ["gt", "gte", "lt", "lte", "eq", "ne"]:
            raise ValidationError("지원되지 않는 조건입니다")
        
        if self.severity not in ["low", "medium", "high", "critical"]:
            raise ValidationError("지원되지 않는 심각도입니다")
        
        if self.cooldown_minutes < 0:
            raise ValidationError("쿨다운 시간은 0 이상이어야 합니다")


class ProcessMetricAlertCommand:
    """메트릭 알림 처리 명령"""
    
    def __init__(
        self,
        component: ComponentType,
        metric_name: str,
        current_value: float,
        timestamp: Optional[datetime] = None
    ):
        self.component = component
        self.metric_name = metric_name
        self.current_value = current_value
        self.timestamp = timestamp or datetime.utcnow()


class ResolveAlertCommand:
    """알림 해결 명령"""
    
    def __init__(
        self,
        alert_id: UUID,
        resolution_note: str = "",
        resolved_by: str = "system"
    ):
        self.alert_id = alert_id
        self.resolution_note = resolution_note
        self.resolved_by = resolved_by


class AlertManagementResult:
    """알림 관리 결과"""
    
    def __init__(
        self,
        success: bool,
        message: str,
        alert_id: Optional[UUID] = None,
        rule_id: Optional[UUID] = None,
        errors: List[str] = None
    ):
        self.success = success
        self.message = message
        self.alert_id = alert_id
        self.rule_id = rule_id
        self.errors = errors or []


class CreateAlertRuleUseCase:
    """알림 규칙 생성 유즈케이스"""
    
    def __init__(self, alert_repository: AlertRepositoryPort):
        self.alert_repository = alert_repository
    
    async def execute(self, command: CreateAlertRuleCommand) -> AlertManagementResult:
        """알림 규칙 생성 실행"""
        try:
            # 1. 중복 규칙 확인
            existing_rules = await self.alert_repository.get_alert_rules_by_metric(
                command.metric_name, command.component
            )
            
            for rule in existing_rules:
                if (rule.name == command.name or 
                    (rule.condition == command.condition and 
                     rule.threshold == command.threshold)):
                    raise BusinessLogicError(
                        f"동일한 조건의 알림 규칙이 이미 존재합니다: {rule.name}"
                    )
            
            # 2. 알림 규칙 생성
            alert_rule = AlertRule.create(
                name=command.name,
                component=command.component,
                metric_name=command.metric_name,
                condition=command.condition,
                threshold=command.threshold,
                severity=command.severity,
                description=command.description,
                enabled=command.enabled,
                notification_channels=command.notification_channels,
                cooldown_minutes=command.cooldown_minutes
            )
            
            # 3. 저장
            await self.alert_repository.save_alert_rule(alert_rule)
            
            return AlertManagementResult(
                success=True,
                message=f"알림 규칙 '{command.name}'이 성공적으로 생성되었습니다",
                rule_id=alert_rule.rule_id
            )
            
        except Exception as e:
            return AlertManagementResult(
                success=False,
                message=f"알림 규칙 생성 실패: {str(e)}",
                errors=[str(e)]
            )


class ProcessMetricAlertUseCase:
    """메트릭 알림 처리 유즈케이스"""
    
    def __init__(
        self,
        alert_repository: AlertRepositoryPort,
        notification_service: NotificationPort
    ):
        self.alert_repository = alert_repository
        self.notification_service = notification_service
    
    async def execute(self, command: ProcessMetricAlertCommand) -> List[AlertManagementResult]:
        """메트릭 알림 처리 실행"""
        results = []
        
        try:
            # 1. 해당 메트릭에 대한 활성 알림 규칙 조회
            alert_rules = await self.alert_repository.get_alert_rules_by_metric(
                command.metric_name, command.component, enabled_only=True
            )
            
            if not alert_rules:
                return [AlertManagementResult(
                    success=True,
                    message="처리할 알림 규칙이 없습니다"
                )]
            
            # 2. 각 규칙에 대해 조건 확인 및 알림 처리
            for rule in alert_rules:
                result = await self._process_single_rule(rule, command)
                results.append(result)
            
            return results
            
        except Exception as e:
            return [AlertManagementResult(
                success=False,
                message=f"메트릭 알림 처리 실패: {str(e)}",
                errors=[str(e)]
            )]
    
    async def _process_single_rule(
        self, rule: AlertRule, command: ProcessMetricAlertCommand
    ) -> AlertManagementResult:
        """단일 규칙에 대한 알림 처리"""
        try:
            # 1. 조건 확인
            condition_met = self._check_condition(
                command.current_value, rule.condition, rule.threshold
            )
            
            if not condition_met:
                return AlertManagementResult(
                    success=True,
                    message=f"규칙 '{rule.name}': 조건 미충족",
                    rule_id=rule.rule_id
                )
            
            # 2. 쿨다운 확인
            if await self._is_in_cooldown(rule, command.timestamp):
                return AlertManagementResult(
                    success=True,
                    message=f"규칙 '{rule.name}': 쿨다운 중",
                    rule_id=rule.rule_id
                )
            
            # 3. 알림 생성
            alert = Alert.create(
                rule=rule,
                current_value=command.current_value,
                message=self._generate_alert_message(rule, command.current_value),
                timestamp=command.timestamp
            )
            
            # 4. 알림 저장
            await self.alert_repository.save_alert(alert)
            
            # 5. 알림 발송
            if rule.notification_channels:
                await self.notification_service.send_alert_notification(
                    alert=alert,
                    recipients=rule.notification_channels,
                    notification_type="email"
                )
            
            # 6. 규칙의 마지막 알림 시간 업데이트
            rule.update_last_triggered(command.timestamp)
            await self.alert_repository.update_alert_rule(rule)
            
            return AlertManagementResult(
                success=True,
                message=f"알림이 생성되고 발송되었습니다: {rule.name}",
                alert_id=alert.alert_id,
                rule_id=rule.rule_id
            )
            
        except Exception as e:
            return AlertManagementResult(
                success=False,
                message=f"규칙 '{rule.name}' 처리 실패: {str(e)}",
                rule_id=rule.rule_id,
                errors=[str(e)]
            )
    
    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        """조건 확인"""
        if condition == "gt":
            return value > threshold
        elif condition == "gte":
            return value >= threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "lte":
            return value <= threshold
        elif condition == "eq":
            return value == threshold
        elif condition == "ne":
            return value != threshold
        else:
            return False
    
    async def _is_in_cooldown(self, rule: AlertRule, current_time: datetime) -> bool:
        """쿨다운 확인"""
        if rule.last_triggered is None:
            return False
        
        cooldown_period = timedelta(minutes=rule.cooldown_minutes)
        return current_time - rule.last_triggered < cooldown_period
    
    def _generate_alert_message(self, rule: AlertRule, current_value: float) -> str:
        """알림 메시지 생성"""
        return (
            f"[{rule.severity.upper()}] {rule.component.value} 컴포넌트의 "
            f"{rule.metric_name} 메트릭이 임계값을 초과했습니다. "
            f"현재값: {current_value}, 임계값: {rule.threshold} ({rule.condition})"
        )


class ResolveAlertUseCase:
    """알림 해결 유즈케이스"""
    
    def __init__(
        self,
        alert_repository: AlertRepositoryPort,
        notification_service: NotificationPort
    ):
        self.alert_repository = alert_repository
        self.notification_service = notification_service
    
    async def execute(self, command: ResolveAlertCommand) -> AlertManagementResult:
        """알림 해결 실행"""
        try:
            # 1. 알림 조회
            alert = await self.alert_repository.get_alert_by_id(command.alert_id)
            if not alert:
                raise NotFoundError(f"알림을 찾을 수 없습니다: {command.alert_id}")
            
            # 2. 이미 해결된 알림인지 확인
            if not alert.is_active():
                return AlertManagementResult(
                    success=True,
                    message="이미 해결된 알림입니다",
                    alert_id=command.alert_id
                )
            
            # 3. 알림 해결
            alert.resolve(command.resolution_note, command.resolved_by)
            
            # 4. 업데이트 저장
            await self.alert_repository.update_alert(alert)
            
            # 5. 해결 알림 발송 (필요한 경우)
            rule = await self.alert_repository.get_alert_rule_by_id(alert.rule_id)
            if rule and rule.notification_channels:
                await self.notification_service.send_custom_notification(
                    title=f"알림 해결: {rule.name}",
                    message=f"알림이 해결되었습니다. 해결자: {command.resolved_by}",
                    recipients=rule.notification_channels,
                    priority="normal"
                )
            
            return AlertManagementResult(
                success=True,
                message="알림이 성공적으로 해결되었습니다",
                alert_id=command.alert_id
            )
            
        except Exception as e:
            return AlertManagementResult(
                success=False,
                message=f"알림 해결 실패: {str(e)}",
                alert_id=command.alert_id,
                errors=[str(e)]
            )


class BulkResolveAlertsUseCase:
    """알림 일괄 해결 유즈케이스"""
    
    def __init__(
        self,
        alert_repository: AlertRepositoryPort,
        notification_service: NotificationPort
    ):
        self.alert_repository = alert_repository
        self.notification_service = notification_service
        self.resolve_alert_use_case = ResolveAlertUseCase(
            alert_repository, notification_service
        )
    
    async def execute(
        self,
        component: Optional[ComponentType] = None,
        severity: Optional[str] = None,
        before_time: Optional[datetime] = None,
        resolved_by: str = "system"
    ) -> Dict[str, Any]:
        """알림 일괄 해결 실행"""
        try:
            # 1. 해결할 알림 조회
            active_alerts = await self.alert_repository.get_active_alerts(
                component=component,
                severity=severity
            )
            
            if before_time:
                active_alerts = [
                    alert for alert in active_alerts 
                    if alert.created_at < before_time
                ]
            
            if not active_alerts:
                return {
                    "success": True,
                    "message": "해결할 알림이 없습니다",
                    "resolved_count": 0,
                    "failed_count": 0
                }
            
            # 2. 각 알림 해결
            resolved_count = 0
            failed_count = 0
            errors = []
            
            for alert in active_alerts:
                try:
                    command = ResolveAlertCommand(
                        alert_id=alert.alert_id,
                        resolution_note="일괄 해결",
                        resolved_by=resolved_by
                    )
                    
                    result = await self.resolve_alert_use_case.execute(command)
                    
                    if result.success:
                        resolved_count += 1
                    else:
                        failed_count += 1
                        errors.extend(result.errors)
                        
                except Exception as e:
                    failed_count += 1
                    errors.append(f"알림 {alert.alert_id} 해결 실패: {str(e)}")
            
            return {
                "success": failed_count == 0,
                "message": f"{resolved_count}개 알림 해결, {failed_count}개 실패",
                "resolved_count": resolved_count,
                "failed_count": failed_count,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"일괄 해결 실패: {str(e)}",
                "resolved_count": 0,
                "failed_count": 0,
                "errors": [str(e)]
            }


class GetAlertSummaryUseCase:
    """알림 요약 조회 유즈케이스"""
    
    def __init__(self, alert_repository: AlertRepositoryPort):
        self.alert_repository = alert_repository
    
    async def execute(
        self,
        component: Optional[ComponentType] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """알림 요약 조회 실행"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # 1. 활성 알림 조회
            active_alerts = await self.alert_repository.get_active_alerts(
                component=component
            )
            
            # 2. 최근 알림 조회
            recent_alerts = await self.alert_repository.get_recent_alerts(
                hours=hours,
                component=component
            )
            
            # 3. 심각도별 통계
            severity_stats = await self.alert_repository.get_alert_count_by_severity(
                start_time=start_time,
                end_time=end_time,
                component=component
            )
            
            # 4. 전체 통계
            total_stats = await self.alert_repository.get_alert_statistics(
                start_time=start_time,
                end_time=end_time,
                component=component
            )
            
            # 5. 상위 알림 발생 컴포넌트
            top_components = await self.alert_repository.get_top_alerting_components(
                start_time=start_time,
                end_time=end_time,
                limit=5
            )
            
            return {
                "summary_period_hours": hours,
                "component_filter": component.value if component else "all",
                "active_alerts": {
                    "count": len(active_alerts),
                    "by_severity": self._group_alerts_by_severity(active_alerts)
                },
                "recent_alerts": {
                    "count": len(recent_alerts),
                    "by_severity": self._group_alerts_by_severity(recent_alerts)
                },
                "severity_statistics": severity_stats,
                "total_statistics": total_stats,
                "top_alerting_components": top_components,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise BusinessLogicError(f"알림 요약 조회 실패: {str(e)}")
    
    def _group_alerts_by_severity(self, alerts: List[Alert]) -> Dict[str, int]:
        """알림을 심각도별로 그룹화"""
        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        
        for alert in alerts:
            if alert.severity in severity_counts:
                severity_counts[alert.severity] += 1
        
        return severity_counts
