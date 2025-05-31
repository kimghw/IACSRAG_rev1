"""
Notification Port

알림 발송 포트를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from src.modules.monitor.domain.entities import Alert, ComponentType


class NotificationPort(ABC):
    """알림 발송 포트"""
    
    @abstractmethod
    async def send_alert_notification(
        self,
        alert: Alert,
        recipients: List[str],
        notification_type: str = "email"  # "email", "slack", "webhook", "sms"
    ) -> bool:
        """알림 발송"""
        pass
    
    @abstractmethod
    async def send_system_health_notification(
        self,
        component: ComponentType,
        status: str,
        message: str,
        recipients: List[str],
        notification_type: str = "email"
    ) -> bool:
        """시스템 건강 상태 알림 발송"""
        pass
    
    @abstractmethod
    async def send_metric_threshold_notification(
        self,
        metric_name: str,
        component: ComponentType,
        current_value: float,
        threshold: float,
        condition: str,
        recipients: List[str],
        notification_type: str = "email"
    ) -> bool:
        """메트릭 임계값 초과 알림 발송"""
        pass
    
    @abstractmethod
    async def send_bulk_alert_notification(
        self,
        alerts: List[Alert],
        recipients: List[str],
        notification_type: str = "email",
        summary_format: bool = True
    ) -> bool:
        """알림 일괄 발송"""
        pass
    
    @abstractmethod
    async def send_daily_summary_notification(
        self,
        summary_data: Dict[str, Any],
        recipients: List[str],
        notification_type: str = "email"
    ) -> bool:
        """일일 요약 알림 발송"""
        pass
    
    @abstractmethod
    async def send_weekly_report_notification(
        self,
        report_data: Dict[str, Any],
        recipients: List[str],
        notification_type: str = "email"
    ) -> bool:
        """주간 리포트 알림 발송"""
        pass
    
    @abstractmethod
    async def send_custom_notification(
        self,
        title: str,
        message: str,
        recipients: List[str],
        notification_type: str = "email",
        priority: str = "normal",  # "low", "normal", "high", "critical"
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """사용자 정의 알림 발송"""
        pass
    
    @abstractmethod
    async def validate_recipients(
        self,
        recipients: List[str],
        notification_type: str
    ) -> List[str]:
        """수신자 유효성 검증"""
        pass
    
    @abstractmethod
    async def get_notification_templates(
        self,
        notification_type: str
    ) -> Dict[str, str]:
        """알림 템플릿 조회"""
        pass
    
    @abstractmethod
    async def update_notification_template(
        self,
        template_name: str,
        notification_type: str,
        template_content: str
    ) -> bool:
        """알림 템플릿 업데이트"""
        pass
    
    @abstractmethod
    async def get_notification_history(
        self,
        recipient: Optional[str] = None,
        notification_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """알림 발송 히스토리 조회"""
        pass
    
    @abstractmethod
    async def get_notification_statistics(
        self,
        start_time: str,
        end_time: str,
        notification_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """알림 발송 통계 조회"""
        pass
    
    @abstractmethod
    async def test_notification_channel(
        self,
        notification_type: str,
        test_recipient: str
    ) -> bool:
        """알림 채널 테스트"""
        pass
    
    @abstractmethod
    async def configure_notification_channel(
        self,
        notification_type: str,
        configuration: Dict[str, Any]
    ) -> bool:
        """알림 채널 설정"""
        pass
    
    @abstractmethod
    async def get_supported_notification_types(self) -> List[str]:
        """지원되는 알림 타입 조회"""
        pass
    
    @abstractmethod
    async def schedule_notification(
        self,
        notification_data: Dict[str, Any],
        schedule_time: str,
        recurring: bool = False,
        recurring_pattern: Optional[str] = None
    ) -> str:
        """알림 예약"""
        pass
    
    @abstractmethod
    async def cancel_scheduled_notification(
        self,
        notification_id: str
    ) -> bool:
        """예약된 알림 취소"""
        pass
    
    @abstractmethod
    async def get_scheduled_notifications(
        self,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """예약된 알림 목록 조회"""
        pass
