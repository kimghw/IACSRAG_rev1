"""
Monitor 모듈 알림 관리 유즈케이스 테스트
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from uuid import UUID, uuid4

from src.core.exceptions import ValidationError, BusinessLogicError, NotFoundError
from src.modules.monitor.domain.entities import (
    AlertRule, Alert, ComponentType
)
from src.modules.monitor.application.use_cases.manage_alerts import (
    CreateAlertRuleCommand,
    ProcessMetricAlertCommand,
    ResolveAlertCommand,
    AlertManagementResult,
    CreateAlertRuleUseCase,
    ProcessMetricAlertUseCase,
    ResolveAlertUseCase,
    BulkResolveAlertsUseCase,
    GetAlertSummaryUseCase
)


class TestCreateAlertRuleCommand:
    """CreateAlertRuleCommand 테스트"""
    
    def test_valid_command_creation(self):
        """유효한 명령 생성 테스트"""
        command = CreateAlertRuleCommand(
            name="High CPU Alert",
            component=ComponentType.PROCESS,
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            severity="high",
            description="CPU usage is too high",
            enabled=True,
            notification_channels=["admin@example.com"],
            cooldown_minutes=5
        )
        
        assert command.name == "High CPU Alert"
        assert command.component == ComponentType.PROCESS
        assert command.metric_name == "cpu_usage"
        assert command.condition == "gt"
        assert command.threshold == 80.0
        assert command.severity == "high"
        assert command.enabled is True
        assert command.notification_channels == ["admin@example.com"]
        assert command.cooldown_minutes == 5
    
    def test_empty_name_validation(self):
        """빈 이름 검증 테스트"""
        with pytest.raises(ValidationError, match="알림 규칙 이름이 필요합니다"):
            CreateAlertRuleCommand(
                name="",
                component=ComponentType.PROCESS,
                metric_name="cpu_usage",
                condition="gt",
                threshold=80.0,
                severity="high"
            )
    
    def test_empty_metric_name_validation(self):
        """빈 메트릭 이름 검증 테스트"""
        with pytest.raises(ValidationError, match="메트릭 이름이 필요합니다"):
            CreateAlertRuleCommand(
                name="Test Alert",
                component=ComponentType.PROCESS,
                metric_name="",
                condition="gt",
                threshold=80.0,
                severity="high"
            )
    
    def test_invalid_condition_validation(self):
        """잘못된 조건 검증 테스트"""
        with pytest.raises(ValidationError, match="지원되지 않는 조건입니다"):
            CreateAlertRuleCommand(
                name="Test Alert",
                component=ComponentType.PROCESS,
                metric_name="cpu_usage",
                condition="invalid",
                threshold=80.0,
                severity="high"
            )
    
    def test_invalid_severity_validation(self):
        """잘못된 심각도 검증 테스트"""
        with pytest.raises(ValidationError, match="지원되지 않는 심각도입니다"):
            CreateAlertRuleCommand(
                name="Test Alert",
                component=ComponentType.PROCESS,
                metric_name="cpu_usage",
                condition="gt",
                threshold=80.0,
                severity="invalid"
            )
    
    def test_negative_cooldown_validation(self):
        """음수 쿨다운 검증 테스트"""
        with pytest.raises(ValidationError, match="쿨다운 시간은 0 이상이어야 합니다"):
            CreateAlertRuleCommand(
                name="Test Alert",
                component=ComponentType.PROCESS,
                metric_name="cpu_usage",
                condition="gt",
                threshold=80.0,
                severity="high",
                cooldown_minutes=-1
            )


class TestCreateAlertRuleUseCase:
    """CreateAlertRuleUseCase 테스트"""
    
    @pytest.fixture
    def alert_repository(self):
        """AlertRepository Mock"""
        return Mock()
    
    @pytest.fixture
    def use_case(self, alert_repository):
        """UseCase 인스턴스"""
        return CreateAlertRuleUseCase(alert_repository)
    
    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, alert_repository):
        """성공적인 알림 규칙 생성 테스트"""
        # Given
        command = CreateAlertRuleCommand(
            name="High CPU Alert",
            component=ComponentType.PROCESS,
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            severity="high"
        )
        
        alert_repository.get_alert_rules_by_metric = AsyncMock(return_value=[])
        alert_repository.save_alert_rule = AsyncMock()
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.success is True
        assert "성공적으로 생성되었습니다" in result.message
        assert result.rule_id is not None
        
        alert_repository.get_alert_rules_by_metric.assert_called_once_with(
            command.metric_name, command.component
        )
        alert_repository.save_alert_rule.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_duplicate_rule_name(self, use_case, alert_repository):
        """중복된 규칙 이름 테스트"""
        # Given
        command = CreateAlertRuleCommand(
            name="High CPU Alert",
            component=ComponentType.PROCESS,
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            severity="high"
        )
        
        existing_rule = Mock()
        existing_rule.name = "High CPU Alert"
        existing_rule.condition = "lt"
        existing_rule.threshold = 50.0
        
        alert_repository.get_alert_rules_by_metric = AsyncMock(
            return_value=[existing_rule]
        )
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.success is False
        assert "동일한 조건의 알림 규칙이 이미 존재합니다" in result.message
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_execute_duplicate_condition(self, use_case, alert_repository):
        """중복된 조건 테스트"""
        # Given
        command = CreateAlertRuleCommand(
            name="New Alert",
            component=ComponentType.PROCESS,
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            severity="high"
        )
        
        existing_rule = Mock()
        existing_rule.name = "Old Alert"
        existing_rule.condition = "gt"
        existing_rule.threshold = 80.0
        
        alert_repository.get_alert_rules_by_metric = AsyncMock(
            return_value=[existing_rule]
        )
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.success is False
        assert "동일한 조건의 알림 규칙이 이미 존재합니다" in result.message


class TestProcessMetricAlertUseCase:
    """ProcessMetricAlertUseCase 테스트"""
    
    @pytest.fixture
    def alert_repository(self):
        """AlertRepository Mock"""
        return Mock()
    
    @pytest.fixture
    def notification_service(self):
        """NotificationService Mock"""
        return Mock()
    
    @pytest.fixture
    def use_case(self, alert_repository, notification_service):
        """UseCase 인스턴스"""
        return ProcessMetricAlertUseCase(alert_repository, notification_service)
    
    @pytest.mark.asyncio
    async def test_execute_no_rules(self, use_case, alert_repository):
        """알림 규칙이 없는 경우 테스트"""
        # Given
        command = ProcessMetricAlertCommand(
            component=ComponentType.PROCESS,
            metric_name="cpu_usage",
            current_value=85.0
        )
        
        alert_repository.get_alert_rules_by_metric = AsyncMock(return_value=[])
        
        # When
        results = await use_case.execute(command)
        
        # Then
        assert len(results) == 1
        assert results[0].success is True
        assert "처리할 알림 규칙이 없습니다" in results[0].message
    
    @pytest.mark.asyncio
    async def test_execute_condition_met(self, use_case, alert_repository, notification_service):
        """조건 충족 시 알림 생성 테스트"""
        # Given
        command = ProcessMetricAlertCommand(
            component=ComponentType.PROCESS,
            metric_name="cpu_usage",
            current_value=85.0,
            timestamp=datetime.utcnow()
        )
        
        rule = Mock()
        rule.rule_id = uuid4()
        rule.name = "High CPU Alert"
        rule.condition = "gt"
        rule.threshold = 80.0
        rule.severity = "high"
        rule.notification_channels = ["admin@example.com"]
        rule.cooldown_minutes = 5
        rule.last_triggered = None
        rule.update_last_triggered = Mock()
        
        alert_repository.get_alert_rules_by_metric = AsyncMock(return_value=[rule])
        alert_repository.save_alert = AsyncMock()
        alert_repository.update_alert_rule = AsyncMock()
        notification_service.send_alert_notification = AsyncMock()
        
        # When
        results = await use_case.execute(command)
        
        # Then
        assert len(results) == 1
        assert results[0].success is True
        assert "알림이 생성되고 발송되었습니다" in results[0].message
        
        alert_repository.save_alert.assert_called_once()
        notification_service.send_alert_notification.assert_called_once()
        rule.update_last_triggered.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_condition_not_met(self, use_case, alert_repository):
        """조건 미충족 테스트"""
        # Given
        command = ProcessMetricAlertCommand(
            component=ComponentType.PROCESS,
            metric_name="cpu_usage",
            current_value=75.0
        )
        
        rule = Mock()
        rule.rule_id = uuid4()
        rule.name = "High CPU Alert"
        rule.condition = "gt"
        rule.threshold = 80.0
        
        alert_repository.get_alert_rules_by_metric = AsyncMock(return_value=[rule])
        
        # When
        results = await use_case.execute(command)
        
        # Then
        assert len(results) == 1
        assert results[0].success is True
        assert "조건 미충족" in results[0].message
    
    @pytest.mark.asyncio
    async def test_execute_in_cooldown(self, use_case, alert_repository):
        """쿨다운 중인 경우 테스트"""
        # Given
        current_time = datetime.utcnow()
        command = ProcessMetricAlertCommand(
            component=ComponentType.PROCESS,
            metric_name="cpu_usage",
            current_value=85.0,
            timestamp=current_time
        )
        
        rule = Mock()
        rule.rule_id = uuid4()
        rule.name = "High CPU Alert"
        rule.condition = "gt"
        rule.threshold = 80.0
        rule.cooldown_minutes = 5
        rule.last_triggered = current_time - timedelta(minutes=3)  # 3분 전
        
        alert_repository.get_alert_rules_by_metric = AsyncMock(return_value=[rule])
        
        # When
        results = await use_case.execute(command)
        
        # Then
        assert len(results) == 1
        assert results[0].success is True
        assert "쿨다운 중" in results[0].message
    
    def test_check_condition_gt(self, use_case):
        """조건 확인 - gt (greater than) 테스트"""
        assert use_case._check_condition(85.0, "gt", 80.0) is True
        assert use_case._check_condition(80.0, "gt", 80.0) is False
        assert use_case._check_condition(75.0, "gt", 80.0) is False
    
    def test_check_condition_gte(self, use_case):
        """조건 확인 - gte (greater than or equal) 테스트"""
        assert use_case._check_condition(85.0, "gte", 80.0) is True
        assert use_case._check_condition(80.0, "gte", 80.0) is True
        assert use_case._check_condition(75.0, "gte", 80.0) is False
    
    def test_check_condition_lt(self, use_case):
        """조건 확인 - lt (less than) 테스트"""
        assert use_case._check_condition(75.0, "lt", 80.0) is True
        assert use_case._check_condition(80.0, "lt", 80.0) is False
        assert use_case._check_condition(85.0, "lt", 80.0) is False
    
    def test_check_condition_lte(self, use_case):
        """조건 확인 - lte (less than or equal) 테스트"""
        assert use_case._check_condition(75.0, "lte", 80.0) is True
        assert use_case._check_condition(80.0, "lte", 80.0) is True
        assert use_case._check_condition(85.0, "lte", 80.0) is False
    
    def test_check_condition_eq(self, use_case):
        """조건 확인 - eq (equal) 테스트"""
        assert use_case._check_condition(80.0, "eq", 80.0) is True
        assert use_case._check_condition(85.0, "eq", 80.0) is False
    
    def test_check_condition_ne(self, use_case):
        """조건 확인 - ne (not equal) 테스트"""
        assert use_case._check_condition(85.0, "ne", 80.0) is True
        assert use_case._check_condition(80.0, "ne", 80.0) is False
    
    def test_generate_alert_message(self, use_case):
        """알림 메시지 생성 테스트"""
        rule = Mock()
        rule.severity = "high"
        rule.component = ComponentType.PROCESS
        rule.metric_name = "cpu_usage"
        rule.threshold = 80.0
        rule.condition = "gt"
        
        message = use_case._generate_alert_message(rule, 85.0)
        
        assert "[HIGH]" in message
        assert "process" in message
        assert "cpu_usage" in message
        assert "85.0" in message
        assert "80.0" in message
        assert "gt" in message


class TestResolveAlertUseCase:
    """ResolveAlertUseCase 테스트"""
    
    @pytest.fixture
    def alert_repository(self):
        """AlertRepository Mock"""
        return Mock()
    
    @pytest.fixture
    def notification_service(self):
        """NotificationService Mock"""
        return Mock()
    
    @pytest.fixture
    def use_case(self, alert_repository, notification_service):
        """UseCase 인스턴스"""
        return ResolveAlertUseCase(alert_repository, notification_service)
    
    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, alert_repository, notification_service):
        """성공적인 알림 해결 테스트"""
        # Given
        alert_id = uuid4()
        command = ResolveAlertCommand(
            alert_id=alert_id,
            resolution_note="Issue resolved",
            resolved_by="admin"
        )
        
        alert = Mock()
        alert.alert_id = alert_id
        alert.rule_id = uuid4()
        alert.is_active = Mock(return_value=True)
        alert.resolve = Mock()
        
        rule = Mock()
        rule.name = "Test Alert"
        rule.notification_channels = ["admin@example.com"]
        
        alert_repository.get_alert_by_id = AsyncMock(return_value=alert)
        alert_repository.update_alert = AsyncMock()
        alert_repository.get_alert_rule_by_id = AsyncMock(return_value=rule)
        notification_service.send_custom_notification = AsyncMock()
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.success is True
        assert "성공적으로 해결되었습니다" in result.message
        
        alert.resolve.assert_called_once_with("Issue resolved", "admin")
        alert_repository.update_alert.assert_called_once()
        notification_service.send_custom_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_alert_not_found(self, use_case, alert_repository):
        """알림을 찾을 수 없는 경우 테스트"""
        # Given
        alert_id = uuid4()
        command = ResolveAlertCommand(alert_id=alert_id)
        
        alert_repository.get_alert_by_id = AsyncMock(return_value=None)
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.success is False
        assert "알림을 찾을 수 없습니다" in result.message
    
    @pytest.mark.asyncio
    async def test_execute_already_resolved(self, use_case, alert_repository):
        """이미 해결된 알림 테스트"""
        # Given
        alert_id = uuid4()
        command = ResolveAlertCommand(alert_id=alert_id)
        
        alert = Mock()
        alert.alert_id = alert_id
        alert.is_active = Mock(return_value=False)
        
        alert_repository.get_alert_by_id = AsyncMock(return_value=alert)
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.success is True
        assert "이미 해결된 알림입니다" in result.message


class TestBulkResolveAlertsUseCase:
    """BulkResolveAlertsUseCase 테스트"""
    
    @pytest.fixture
    def alert_repository(self):
        """AlertRepository Mock"""
        return Mock()
    
    @pytest.fixture
    def notification_service(self):
        """NotificationService Mock"""
        return Mock()
    
    @pytest.fixture
    def use_case(self, alert_repository, notification_service):
        """UseCase 인스턴스"""
        return BulkResolveAlertsUseCase(alert_repository, notification_service)
    
    @pytest.mark.asyncio
    async def test_execute_no_alerts(self, use_case, alert_repository):
        """해결할 알림이 없는 경우 테스트"""
        # Given
        alert_repository.get_active_alerts = AsyncMock(return_value=[])
        
        # When
        result = await use_case.execute()
        
        # Then
        assert result["success"] is True
        assert "해결할 알림이 없습니다" in result["message"]
        assert result["resolved_count"] == 0
        assert result["failed_count"] == 0
    
    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, alert_repository, notification_service):
        """성공적인 일괄 해결 테스트"""
        # Given
        alerts = [
            Mock(alert_id=uuid4(), created_at=datetime.utcnow()),
            Mock(alert_id=uuid4(), created_at=datetime.utcnow()),
            Mock(alert_id=uuid4(), created_at=datetime.utcnow())
        ]
        
        alert_repository.get_active_alerts = AsyncMock(return_value=alerts)
        
        # Mock resolve_alert_use_case
        with patch.object(use_case.resolve_alert_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Mock(success=True)
            
            # When
            result = await use_case.execute(resolved_by="batch_system")
            
            # Then
            assert result["success"] is True
            assert result["resolved_count"] == 3
            assert result["failed_count"] == 0
            assert mock_execute.call_count == 3
    
    @pytest.mark.asyncio
    async def test_execute_with_filters(self, use_case, alert_repository):
        """필터를 사용한 일괄 해결 테스트"""
        # Given
        before_time = datetime.utcnow()
        old_alert = Mock(alert_id=uuid4(), created_at=before_time - timedelta(hours=2))
        new_alert = Mock(alert_id=uuid4(), created_at=before_time + timedelta(hours=1))
        
        alert_repository.get_active_alerts = AsyncMock(
            return_value=[old_alert, new_alert]
        )
        
        # Mock resolve_alert_use_case
        with patch.object(use_case.resolve_alert_use_case, 'execute') as mock_execute:
            mock_execute.return_value = Mock(success=True)
            
            # When
            result = await use_case.execute(
                component=ComponentType.PROCESS,
                severity="high",
                before_time=before_time
            )
            
            # Then
            assert result["resolved_count"] == 1  # Only old_alert
            assert mock_execute.call_count == 1


class TestGetAlertSummaryUseCase:
    """GetAlertSummaryUseCase 테스트"""
    
    @pytest.fixture
    def alert_repository(self):
        """AlertRepository Mock"""
        return Mock()
    
    @pytest.fixture
    def use_case(self, alert_repository):
        """UseCase 인스턴스"""
        return GetAlertSummaryUseCase(alert_repository)
    
    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, alert_repository):
        """성공적인 알림 요약 조회 테스트"""
        # Given
        active_alerts = [
            Mock(severity="high"),
            Mock(severity="high"),
            Mock(severity="medium"),
            Mock(severity="low")
        ]
        
        recent_alerts = [
            Mock(severity="critical"),
            Mock(severity="high"),
            Mock(severity="medium")
        ]
        
        severity_stats = {
            "low": 5,
            "medium": 10,
            "high": 15,
            "critical": 3
        }
        
        total_stats = {
            "total_alerts": 33,
            "resolved_alerts": 25,
            "active_alerts": 8,
            "average_resolution_time": 45.5
        }
        
        top_components = [
            {"component": "processing", "count": 15},
            {"component": "search", "count": 10},
            {"component": "ingest", "count": 8}
        ]
        
        alert_repository.get_active_alerts = AsyncMock(return_value=active_alerts)
        alert_repository.get_recent_alerts = AsyncMock(return_value=recent_alerts)
        alert_repository.get_alert_count_by_severity = AsyncMock(
            return_value=severity_stats
        )
        alert_repository.get_alert_statistics = AsyncMock(return_value=total_stats)
        alert_repository.get_top_alerting_components = AsyncMock(
            return_value=top_components
        )
        
        # When
        result = await use_case.execute(hours=24)
        
        # Then
        assert result["summary_period_hours"] == 24
        assert result["component_filter"] == "all"
        assert result["active_alerts"]["count"] == 4
        assert result["active_alerts"]["by_severity"]["high"] == 2
        assert result["active_alerts"]["by_severity"]["medium"] == 1
        assert result["active_alerts"]["by_severity"]["low"] == 1
        assert result["recent_alerts"]["count"] == 3
        assert result["severity_statistics"] == severity_stats
        assert result["total_statistics"] == total_stats
        assert result["top_alerting_components"] == top_components
        assert "generated_at" in result
    
    @pytest.mark.asyncio
    async def test_execute_with_component_filter(self, use_case, alert_repository):
        """컴포넌트 필터를 사용한 요약 조회 테스트"""
        # Given
        alert_repository.get_active_alerts = AsyncMock(return_value=[])
        alert_repository.get_recent_alerts = AsyncMock(return_value=[])
        alert_repository.get_alert_count_by_severity = AsyncMock(return_value={})
        alert_repository.get_alert_statistics = AsyncMock(return_value={})
        alert_repository.get_top_alerting_components = AsyncMock(return_value=[])
        
        # When
        result = await use_case.execute(
            component=ComponentType.PROCESS,
            hours=48
        )
        
        # Then
        assert result["summary_period_hours"] == 48
        assert result["component_filter"] == "process"
        
        # Verify component filter was passed to repository methods
        alert_repository.get_active_alerts.assert_called_with(
            component=ComponentType.PROCESS
        )
    
    def test_group_alerts_by_severity(self, use_case):
        """알림 심각도별 그룹화 테스트"""
        alerts = [
            Mock(severity="high"),
            Mock(severity="high"),
            Mock(severity="medium"),
            Mock(severity="low"),
            Mock(severity="critical"),
            Mock(severity="unknown")  # Unknown severity
        ]
        
        result = use_case._group_alerts_by_severity(alerts)
        
        assert result["low"] == 1
        assert result["medium"] == 1
        assert result["high"] == 2
        assert result["critical"] == 1
