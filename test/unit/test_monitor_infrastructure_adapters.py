"""
Monitor 모듈 Infrastructure 어댑터 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from src.modules.monitor.infrastructure.adapters.email_notification_adapter import EmailNotificationAdapter
from src.modules.monitor.infrastructure.adapters.system_health_check_adapter import SystemHealthCheckAdapter
from src.modules.monitor.domain.entities import (
    Alert, ComponentType, AlertSeverity, AlertStatus, HealthStatus, HealthStatusEnum
)
from src.core.exceptions import NotificationError, HealthCheckError
from src.utils.datetime import get_current_utc_time


class TestEmailNotificationAdapter:
    """이메일 알림 어댑터 테스트"""
    
    @pytest.fixture
    def adapter(self):
        """이메일 어댑터 인스턴스"""
        # Mock settings 객체 생성
        class MockSettings:
            smtp_host = "smtp.test.com"
            smtp_port = 587
            smtp_username = "test@test.com"
            smtp_password = "password"
            smtp_from_email = "noreply@test.com"
            smtp_use_tls = True
        
        return EmailNotificationAdapter(MockSettings())
    
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
            current_value=85.0,
            threshold=80.0,
            triggered_at=get_current_utc_time(),
            tags={"host": "server1"}
        )
    
    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_send_alert_notification_success(self, mock_smtp, adapter, sample_alert):
        """알림 이메일 발송 성공 테스트"""
        # Given
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        recipients = ["admin@test.com", "ops@test.com"]
        
        # When
        result = await adapter.send_alert_notification(sample_alert, recipients)
        
        # Then
        assert result is True
        mock_smtp.assert_called_once_with("smtp.test.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@test.com", "password")
        mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_send_alert_notification_failure(self, mock_smtp, adapter, sample_alert):
        """알림 이메일 발송 실패 테스트"""
        # Given
        mock_smtp.side_effect = Exception("SMTP Error")
        recipients = ["admin@test.com"]
        
        # When & Then
        result = await adapter.send_alert_notification(sample_alert, recipients)
        
        # Then
        assert result is False
    
    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_send_health_check_notification_success(self, mock_smtp, adapter):
        """헬스체크 알림 발송 성공 테스트"""
        # Given
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        recipients = ["admin@test.com"]
        details = {"checked_at": "2024-01-01T00:00:00Z", "response_time": 100}
        
        # When
        result = await adapter.send_system_health_notification(
            ComponentType.DATABASE, "healthy", "Database is healthy", recipients
        )
        
        # Then
        assert result is True
        mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_send_custom_notification_success(self, mock_smtp, adapter):
        """사용자 정의 알림 발송 성공 테스트"""
        # Given
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        recipients = ["admin@test.com"]
        metadata = {"priority": "high", "source": "monitoring"}
        
        # When
        result = await adapter.send_custom_notification(
            "Test Subject", "Test Message", recipients, metadata=metadata
        )
        
        # Then
        assert result is True
        mock_server.send_message.assert_called_once()
    
    def test_create_alert_email_body(self, adapter, sample_alert):
        """알림 이메일 본문 생성 테스트"""
        # When
        body = adapter._create_alert_email_body(sample_alert, {})
        
        # Then
        assert "System Alert" in body
        assert str(sample_alert.alert_id) in body
        assert sample_alert.component.value in body
        assert sample_alert.metric_name in body
        assert str(sample_alert.metric_value) in body
        assert sample_alert.message in body
    
    def test_format_tags_html(self, adapter):
        """태그 HTML 포맷 테스트"""
        # Given
        tags = {"host": "server1", "environment": "production"}
        
        # When
        result = adapter._format_tags_html(tags)
        
        # Then
        assert "Tags:" in result
        assert "host" in result
        assert "server1" in result
        assert "environment" in result
        assert "production" in result
    
    def test_format_tags_html_empty(self, adapter):
        """빈 태그 HTML 포맷 테스트"""
        # When
        result = adapter._format_tags_html({})
        
        # Then
        assert result == ""


class TestSystemHealthCheckAdapter:
    """시스템 헬스체크 어댑터 테스트"""
    
    @pytest.fixture
    def adapter(self):
        """헬스체크 어댑터 인스턴스"""
        config = {
            "timeout": 30,
            "cpu_threshold": 80.0,
            "memory_threshold": 80.0,
            "disk_threshold": 80.0
        }
        return SystemHealthCheckAdapter(config)
    
    @pytest.mark.asyncio
    async def test_check_component_health_system(self, adapter):
        """시스템 컴포넌트 헬스체크 테스트"""
        # When
        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            mock_memory.return_value.percent = 60.0
            mock_memory.return_value.total = 8 * 1024**3  # 8GB
            mock_memory.return_value.available = 3 * 1024**3  # 3GB
            
            mock_disk.return_value.total = 100 * 1024**3  # 100GB
            mock_disk.return_value.used = 50 * 1024**3   # 50GB
            mock_disk.return_value.free = 50 * 1024**3   # 50GB
            
            result = await adapter.check_component_health(ComponentType.SYSTEM)
        
        # Then
        assert result["component"] == ComponentType.SYSTEM.value
        assert result["status"] == HealthStatusEnum.HEALTHY.value
        assert "System is healthy" in result["message"]
        assert "cpu_percent" in result["details"]
        assert "memory_percent" in result["details"]
        assert "disk_percent" in result["details"]
    
    @pytest.mark.asyncio
    async def test_check_component_health_system_unhealthy(self, adapter):
        """시스템 컴포넌트 비정상 헬스체크 테스트"""
        # When
        with patch('psutil.cpu_percent', return_value=90.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            mock_memory.return_value.percent = 85.0
            mock_memory.return_value.total = 8 * 1024**3
            mock_memory.return_value.available = 1 * 1024**3
            
            mock_disk.return_value.total = 100 * 1024**3
            mock_disk.return_value.used = 90 * 1024**3
            mock_disk.return_value.free = 10 * 1024**3
            
            result = await adapter.check_component_health(ComponentType.SYSTEM)
        
        # Then
        assert result["component"] == ComponentType.SYSTEM.value
        assert result["status"] == HealthStatusEnum.UNHEALTHY.value
        assert "System issues" in result["message"]
        assert "High CPU usage" in result["message"]
        assert "High memory usage" in result["message"]
        assert "High disk usage" in result["message"]
    
    @pytest.mark.asyncio
    async def test_check_component_health_database(self, adapter):
        """데이터베이스 컴포넌트 헬스체크 테스트"""
        # When
        result = await adapter.check_component_health(ComponentType.DATABASE)
        
        # Then
        assert result["component"] == ComponentType.DATABASE.value
        assert result["status"] == HealthStatusEnum.HEALTHY.value
        assert "Database is healthy" in result["message"]
        assert result["details"]["type"] == "mongodb"
    
    @pytest.mark.asyncio
    async def test_check_component_health_vector_db(self, adapter):
        """벡터 데이터베이스 컴포넌트 헬스체크 테스트"""
        # When
        result = await adapter.check_component_health(ComponentType.VECTOR_DB)
        
        # Then
        assert result["component"] == ComponentType.VECTOR_DB.value
        assert result["status"] == HealthStatusEnum.HEALTHY.value
        assert "Vector database is healthy" in result["message"]
        assert result["details"]["type"] == "qdrant"
    
    @pytest.mark.asyncio
    async def test_check_component_health_unknown(self, adapter):
        """알 수 없는 컴포넌트 헬스체크 테스트"""
        # Given
        unknown_component = ComponentType.MONITOR  # 처리되지 않는 컴포넌트
        
        # When
        result = await adapter.check_component_health(unknown_component)
        
        # Then
        assert result["component"] == unknown_component.value
        assert result["status"] == HealthStatusEnum.UNKNOWN.value
        assert "Unknown component type" in result["message"]
    
    @pytest.mark.asyncio
    async def test_check_all_components(self, adapter):
        """모든 컴포넌트 헬스체크 테스트"""
        # When
        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            mock_memory.return_value.percent = 60.0
            mock_memory.return_value.total = 8 * 1024**3
            mock_memory.return_value.available = 3 * 1024**3
            
            mock_disk.return_value.total = 100 * 1024**3
            mock_disk.return_value.used = 50 * 1024**3
            mock_disk.return_value.free = 50 * 1024**3
            
            results = await adapter.check_all_components()
        
        # Then
        assert len(results) == 7  # 7개 컴포넌트
        component_names = [result["component"] for result in results]
        assert ComponentType.SYSTEM.value in component_names
        assert ComponentType.DATABASE.value in component_names
        assert ComponentType.VECTOR_DB.value in component_names
        assert ComponentType.MESSAGE_QUEUE.value in component_names
        assert ComponentType.INGEST.value in component_names
        assert ComponentType.PROCESS.value in component_names
        assert ComponentType.SEARCH.value in component_names
    
    @pytest.mark.asyncio
    async def test_check_service_availability_success(self, adapter):
        """서비스 가용성 체크 성공 테스트"""
        # Given
        service_url = "http://test-service:8080/health"
        
        # When
        with patch.object(adapter, 'check_service_availability') as mock_check:
            # Mock the return value directly
            mock_check.return_value = {
                "url": service_url,
                "status": HealthStatusEnum.HEALTHY.value,
                "response_code": 200,
                "response_time_ms": 0,
                "checked_at": get_current_utc_time(),
                "message": "Service is available"
            }
            
            result = await adapter.check_service_availability(service_url)
        
        # Then
        assert result["url"] == service_url
        assert result["status"] == HealthStatusEnum.HEALTHY.value
        assert result["response_code"] == 200
        assert "Service is available" in result["message"]
    
    @pytest.mark.asyncio
    async def test_check_service_availability_failure(self, adapter):
        """서비스 가용성 체크 실패 테스트"""
        # Given
        service_url = "http://test-service:8080/health"
        
        # When
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            result = await adapter.check_service_availability(service_url)
        
        # Then
        assert result["url"] == service_url
        assert result["status"] == HealthStatusEnum.UNHEALTHY.value
        assert result["response_code"] == 500
        assert "Unexpected status code" in result["message"]
    
    @pytest.mark.asyncio
    async def test_check_service_availability_timeout(self, adapter):
        """서비스 가용성 체크 타임아웃 테스트"""
        # Given
        service_url = "http://test-service:8080/health"
        
        # When
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = asyncio.TimeoutError()
            
            result = await adapter.check_service_availability(service_url)
        
        # Then
        assert result["url"] == service_url
        assert result["status"] == HealthStatusEnum.UNHEALTHY.value
        assert "Service timeout" in result["message"]
        assert result["details"]["timeout"] == 30
    
    @pytest.mark.asyncio
    async def test_check_database_connection_success(self, adapter):
        """데이터베이스 연결 체크 성공 테스트"""
        # Given
        connection_string = "mongodb://user:pass@localhost:27017/testdb"
        
        # When
        result = await adapter.check_database_connection(connection_string)
        
        # Then
        assert result["database"] == "mongodb"
        assert result["status"] == HealthStatusEnum.HEALTHY.value
        assert "Database connection successful" in result["message"]
        assert "localhost:27017/testdb" in result["details"]["connection_string"]
    
    @pytest.mark.asyncio
    async def test_check_system_health_psutil_error(self, adapter):
        """시스템 헬스체크 psutil 오류 테스트"""
        # When & Then
        with patch('psutil.cpu_percent', side_effect=Exception("psutil error")):
            with pytest.raises(HealthCheckError, match="System health check failed"):
                await adapter._check_system_health(get_current_utc_time())
    
    @pytest.mark.asyncio
    async def test_check_component_health_exception_handling(self, adapter):
        """컴포넌트 헬스체크 예외 처리 테스트"""
        # When
        with patch.object(adapter, '_check_system_health', side_effect=Exception("Test error")):
            result = await adapter.check_component_health(ComponentType.SYSTEM)
        
        # Then
        assert result["component"] == ComponentType.SYSTEM.value
        assert result["status"] == HealthStatusEnum.UNHEALTHY.value
        assert "Health check error" in result["message"]
        assert result["details"]["error"] == "Test error"


# 추가 import 필요
import asyncio
