"""
Infrastructure adapters 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.modules.monitor.infrastructure.adapters.system_health_check_adapter import SystemHealthCheckAdapter
from src.modules.monitor.infrastructure.adapters.email_notification_adapter import EmailNotificationAdapter
from src.modules.monitor.application.ports.health_check_port import HealthCheckResult
from src.modules.monitor.domain.entities import AlertSeverity


class TestSystemHealthCheckAdapter:
    """시스템 헬스체크 어댑터 테스트"""

    @pytest.fixture
    def adapter(self):
        return SystemHealthCheckAdapter()

    @pytest.mark.asyncio
    async def test_check_cpu_usage(self, adapter):
        """CPU 사용률 체크 테스트"""
        with patch('psutil.cpu_percent', return_value=50.0):
            result = await adapter.check_cpu_usage()
            assert isinstance(result, HealthCheckResult)
            assert result.is_healthy is True
            assert result.value == 50.0

    @pytest.mark.asyncio
    async def test_check_memory_usage(self, adapter):
        """메모리 사용률 체크 테스트"""
        mock_memory = MagicMock()
        mock_memory.percent = 60.0
        with patch('psutil.virtual_memory', return_value=mock_memory):
            result = await adapter.check_memory_usage()
            assert isinstance(result, HealthCheckResult)
            assert result.is_healthy is True
            assert result.value == 60.0

    @pytest.mark.asyncio
    async def test_check_disk_usage(self, adapter):
        """디스크 사용률 체크 테스트"""
        mock_disk = MagicMock()
        mock_disk.percent = 70.0
        with patch('psutil.disk_usage', return_value=mock_disk):
            result = await adapter.check_disk_usage()
            assert isinstance(result, HealthCheckResult)
            assert result.is_healthy is True
            assert result.value == 70.0

    @pytest.mark.asyncio
    async def test_check_database_health(self, adapter):
        """데이터베이스 헬스체크 테스트"""
        result = await adapter.check_database_health()
        assert isinstance(result, HealthCheckResult)

    @pytest.mark.asyncio
    async def test_check_external_api_health(self, adapter):
        """외부 API 헬스체크 테스트"""
        result = await adapter.check_external_api_health()
        assert isinstance(result, HealthCheckResult)

    @pytest.mark.asyncio
    async def test_check_file_system_health(self, adapter):
        """파일 시스템 헬스체크 테스트"""
        result = await adapter.check_file_system_health()
        assert isinstance(result, HealthCheckResult)

    @pytest.mark.asyncio
    async def test_check_llm_service_health(self, adapter):
        """LLM 서비스 헬스체크 테스트"""
        result = await adapter.check_llm_service_health()
        assert isinstance(result, HealthCheckResult)

    @pytest.mark.asyncio
    async def test_check_messaging_health(self, adapter):
        """메시징 헬스체크 테스트"""
        result = await adapter.check_messaging_health()
        assert isinstance(result, HealthCheckResult)

    @pytest.mark.asyncio
    async def test_check_vector_db_health(self, adapter):
        """벡터 DB 헬스체크 테스트"""
        result = await adapter.check_vector_db_health()
        assert isinstance(result, HealthCheckResult)

    @pytest.mark.asyncio
    async def test_schedule_health_check(self, adapter):
        """헬스체크 스케줄링 테스트"""
        callback = AsyncMock()
        task_id = await adapter.schedule_health_check(
            interval_seconds=60,
            callback=callback
        )
        assert task_id is not None

    @pytest.mark.asyncio
    async def test_cancel_scheduled_health_check(self, adapter):
        """스케줄된 헬스체크 취소 테스트"""
        callback = AsyncMock()
        task_id = await adapter.schedule_health_check(
            interval_seconds=60,
            callback=callback
        )
        result = await adapter.cancel_scheduled_health_check(task_id)
        assert result is True


class TestEmailNotificationAdapter:
    """이메일 알림 어댑터 테스트"""

    @pytest.fixture
    def adapter(self):
        return EmailNotificationAdapter()

    @pytest.mark.asyncio
    async def test_send_alert_notification(self, adapter):
        """알림 발송 테스트"""
        with patch('smtplib.SMTP_SSL') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = await adapter.send_alert_notification(
                recipient="test@example.com",
                subject="Test Alert",
                message="Test message",
                severity=AlertSeverity.HIGH
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_send_system_notification(self, adapter):
        """시스템 알림 발송 테스트"""
        with patch('smtplib.SMTP_SSL') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = await adapter.send_system_notification(
                recipients=["test@example.com"],
                subject="System Alert",
                message="System message"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_send_batch_notifications(self, adapter):
        """배치 알림 발송 테스트"""
        notifications = [
            {
                "recipient": "test1@example.com",
                "subject": "Alert 1",
                "message": "Message 1",
                "severity": AlertSeverity.MEDIUM
            },
            {
                "recipient": "test2@example.com", 
                "subject": "Alert 2",
                "message": "Message 2",
                "severity": AlertSeverity.LOW
            }
        ]
        
        with patch('smtplib.SMTP_SSL') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            results = await adapter.send_batch_notifications(notifications)
            assert len(results) == 2
            assert all(results)

    @pytest.mark.asyncio
    async def test_validate_email_configuration(self, adapter):
        """이메일 설정 검증 테스트"""
        result = await adapter.validate_email_configuration()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_notification_status(self, adapter):
        """알림 상태 조회 테스트"""
        status = await adapter.get_notification_status()
        assert isinstance(status, dict)
        assert "is_configured" in status
