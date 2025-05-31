"""
이메일 알림 어댑터 구현
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import uuid

from src.modules.monitor.application.ports.notification_port import NotificationPort
from src.modules.monitor.domain.entities import Alert, ComponentType
from src.core.exceptions import NotificationError


logger = logging.getLogger(__name__)


class EmailNotificationAdapter(NotificationPort):
    """이메일 알림 어댑터"""
    
    def __init__(self, settings):
        """설정 객체로 초기화"""
        self.smtp_host = getattr(settings, 'smtp_host', 'localhost')
        self.smtp_port = getattr(settings, 'smtp_port', 587)
        self.username = getattr(settings, 'smtp_username', '')
        self.password = getattr(settings, 'smtp_password', '')
        self.from_email = getattr(settings, 'smtp_from_email', 'noreply@iacsrag.com')
        self.use_tls = getattr(settings, 'smtp_use_tls', True)
        self._notification_history = []
        self._scheduled_notifications = {}
        self._templates = {
            "email": {
                "alert": "Default alert template",
                "health_check": "Default health check template",
                "summary": "Default summary template"
            }
        }
    
    async def send_alert_notification(
        self,
        alert: Alert,
        recipients: List[str],
        notification_type: str = "email"
    ) -> bool:
        """알림 이메일 발송"""
        try:
            # 이메일 내용 생성
            subject = f"[{alert.severity.value.upper()}] {alert.component.value} Alert"
            body = self._create_alert_email_body(alert, {})
            
            # 이메일 메시지 생성
            message = MIMEMultipart()
            message["From"] = self.from_email
            message["To"] = ", ".join(recipients)
            message["Subject"] = subject
            
            message.attach(MIMEText(body, "html"))
            
            # SMTP 서버 연결 및 발송
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(message)
            
            # 히스토리 기록
            self._notification_history.append({
                "id": str(uuid.uuid4()),
                "type": "alert",
                "recipients": recipients,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "sent"
            })
            
            logger.info(f"Alert email sent successfully to {recipients}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send alert email: {str(e)}")
            return False
    
    async def send_system_health_notification(
        self,
        component: ComponentType,
        status: str,
        message: str,
        recipients: List[str],
        notification_type: str = "email"
    ) -> bool:
        """시스템 건강 상태 알림 발송"""
        try:
            subject = f"Health Check Alert - {component.value}"
            body = self._create_health_check_email_body(component.value, status, {"message": message})
            
            email_message = MIMEMultipart()
            email_message["From"] = self.from_email
            email_message["To"] = ", ".join(recipients)
            email_message["Subject"] = subject
            
            email_message.attach(MIMEText(body, "html"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(email_message)
            
            logger.info(f"Health check email sent successfully to {recipients}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send health check email: {str(e)}")
            return False
    
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
        try:
            subject = f"Metric Threshold Alert - {metric_name}"
            body = f"""
            <html>
            <body>
                <h2>Metric Threshold Alert</h2>
                <p><strong>Metric:</strong> {metric_name}</p>
                <p><strong>Component:</strong> {component.value}</p>
                <p><strong>Current Value:</strong> {current_value}</p>
                <p><strong>Threshold:</strong> {threshold}</p>
                <p><strong>Condition:</strong> {condition}</p>
            </body>
            </html>
            """
            
            message = MIMEMultipart()
            message["From"] = self.from_email
            message["To"] = ", ".join(recipients)
            message["Subject"] = subject
            message.attach(MIMEText(body, "html"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(message)
            
            return True
        except Exception as e:
            logger.error(f"Failed to send metric threshold email: {str(e)}")
            return False
    
    async def send_bulk_alert_notification(
        self,
        alerts: List[Alert],
        recipients: List[str],
        notification_type: str = "email",
        summary_format: bool = True
    ) -> bool:
        """알림 일괄 발송"""
        try:
            subject = f"Bulk Alert Summary - {len(alerts)} alerts"
            body = "<html><body><h2>Alert Summary</h2><ul>"
            for alert in alerts:
                body += f"<li>{alert.component.value} - {alert.severity.value} - {alert.message}</li>"
            body += "</ul></body></html>"
            
            message = MIMEMultipart()
            message["From"] = self.from_email
            message["To"] = ", ".join(recipients)
            message["Subject"] = subject
            message.attach(MIMEText(body, "html"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(message)
            
            return True
        except Exception as e:
            logger.error(f"Failed to send bulk alert email: {str(e)}")
            return False
    
    async def send_daily_summary_notification(
        self,
        summary_data: Dict[str, Any],
        recipients: List[str],
        notification_type: str = "email"
    ) -> bool:
        """일일 요약 알림 발송"""
        try:
            subject = "Daily System Summary"
            body = "<html><body><h2>Daily Summary</h2>"
            for key, value in summary_data.items():
                body += f"<p><strong>{key}:</strong> {value}</p>"
            body += "</body></html>"
            
            message = MIMEMultipart()
            message["From"] = self.from_email
            message["To"] = ", ".join(recipients)
            message["Subject"] = subject
            message.attach(MIMEText(body, "html"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(message)
            
            return True
        except Exception as e:
            logger.error(f"Failed to send daily summary email: {str(e)}")
            return False
    
    async def send_weekly_report_notification(
        self,
        report_data: Dict[str, Any],
        recipients: List[str],
        notification_type: str = "email"
    ) -> bool:
        """주간 리포트 알림 발송"""
        try:
            subject = "Weekly System Report"
            body = "<html><body><h2>Weekly Report</h2>"
            for key, value in report_data.items():
                body += f"<p><strong>{key}:</strong> {value}</p>"
            body += "</body></html>"
            
            message = MIMEMultipart()
            message["From"] = self.from_email
            message["To"] = ", ".join(recipients)
            message["Subject"] = subject
            message.attach(MIMEText(body, "html"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(message)
            
            return True
        except Exception as e:
            logger.error(f"Failed to send weekly report email: {str(e)}")
            return False
    
    async def send_custom_notification(
        self,
        title: str,
        message: str,
        recipients: List[str],
        notification_type: str = "email",
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """사용자 정의 알림 발송"""
        try:
            email_message = MIMEMultipart()
            email_message["From"] = self.from_email
            email_message["To"] = ", ".join(recipients)
            email_message["Subject"] = f"[{priority.upper()}] {title}"
            
            # 메타데이터가 있으면 메시지에 추가
            if metadata:
                message += "\n\n--- Additional Information ---\n"
                for key, value in metadata.items():
                    message += f"{key}: {value}\n"
            
            email_message.attach(MIMEText(message, "plain"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(email_message)
            
            logger.info(f"Custom email sent successfully to {recipients}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send custom email: {str(e)}")
            return False
    
    async def validate_recipients(
        self,
        recipients: List[str],
        notification_type: str
    ) -> List[str]:
        """수신자 유효성 검증"""
        valid_recipients = []
        for recipient in recipients:
            if "@" in recipient and "." in recipient.split("@")[1]:
                valid_recipients.append(recipient)
        return valid_recipients
    
    async def get_notification_templates(
        self,
        notification_type: str
    ) -> Dict[str, str]:
        """알림 템플릿 조회"""
        return self._templates.get(notification_type, {})
    
    async def update_notification_template(
        self,
        template_name: str,
        notification_type: str,
        template_content: str
    ) -> bool:
        """알림 템플릿 업데이트"""
        if notification_type not in self._templates:
            self._templates[notification_type] = {}
        self._templates[notification_type][template_name] = template_content
        return True
    
    async def get_notification_history(
        self,
        recipient: Optional[str] = None,
        notification_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """알림 발송 히스토리 조회"""
        history = self._notification_history
        
        if recipient:
            history = [h for h in history if recipient in h.get("recipients", [])]
        
        if notification_type:
            history = [h for h in history if h.get("type") == notification_type]
        
        return history[:limit]
    
    async def get_notification_statistics(
        self,
        start_time: str,
        end_time: str,
        notification_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """알림 발송 통계 조회"""
        stats = {
            "total": len(self._notification_history),
            "by_type": {},
            "by_status": {}
        }
        
        for notification in self._notification_history:
            n_type = notification.get("type", "unknown")
            n_status = notification.get("status", "unknown")
            
            stats["by_type"][n_type] = stats["by_type"].get(n_type, 0) + 1
            stats["by_status"][n_status] = stats["by_status"].get(n_status, 0) + 1
        
        return stats
    
    async def test_notification_channel(
        self,
        notification_type: str,
        test_recipient: str
    ) -> bool:
        """알림 채널 테스트"""
        return await self.send_custom_notification(
            "Test Notification",
            "This is a test notification",
            [test_recipient],
            notification_type
        )
    
    async def configure_notification_channel(
        self,
        notification_type: str,
        configuration: Dict[str, Any]
    ) -> bool:
        """알림 채널 설정"""
        if notification_type == "email":
            self.smtp_host = configuration.get("smtp_host", self.smtp_host)
            self.smtp_port = configuration.get("smtp_port", self.smtp_port)
            self.username = configuration.get("username", self.username)
            self.password = configuration.get("password", self.password)
            self.from_email = configuration.get("from_email", self.from_email)
            self.use_tls = configuration.get("use_tls", self.use_tls)
            return True
        return False
    
    async def get_supported_notification_types(self) -> List[str]:
        """지원되는 알림 타입 조회"""
        return ["email"]
    
    async def schedule_notification(
        self,
        notification_data: Dict[str, Any],
        schedule_time: str,
        recurring: bool = False,
        recurring_pattern: Optional[str] = None
    ) -> str:
        """알림 예약"""
        notification_id = str(uuid.uuid4())
        self._scheduled_notifications[notification_id] = {
            "data": notification_data,
            "schedule_time": schedule_time,
            "recurring": recurring,
            "recurring_pattern": recurring_pattern,
            "status": "scheduled"
        }
        return notification_id
    
    async def cancel_scheduled_notification(
        self,
        notification_id: str
    ) -> bool:
        """예약된 알림 취소"""
        if notification_id in self._scheduled_notifications:
            self._scheduled_notifications[notification_id]["status"] = "cancelled"
            return True
        return False
    
    async def get_scheduled_notifications(
        self,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """예약된 알림 목록 조회"""
        notifications = []
        for nid, notification in self._scheduled_notifications.items():
            if not active_only or notification["status"] == "scheduled":
                notifications.append({
                    "id": nid,
                    **notification
                })
        return notifications
    
    def _create_alert_email_body(self, alert: Alert, template_data: Dict[str, Any]) -> str:
        """알림 이메일 본문 생성"""
        severity_color = {
            "low": "#28a745",
            "medium": "#ffc107", 
            "high": "#fd7e14",
            "critical": "#dc3545"
        }.get(alert.severity.value.lower(), "#6c757d")
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto;">
                <div style="background-color: {severity_color}; color: white; padding: 15px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">🚨 System Alert</h2>
                </div>
                
                <div style="border: 1px solid #ddd; border-top: none; padding: 20px; border-radius: 0 0 5px 5px;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; font-weight: bold; width: 150px;">Alert ID:</td>
                            <td style="padding: 8px;">{alert.alert_id}</td>
                        </tr>
                        <tr style="background-color: #f8f9fa;">
                            <td style="padding: 8px; font-weight: bold;">Component:</td>
                            <td style="padding: 8px;">{alert.component.value}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Metric:</td>
                            <td style="padding: 8px;">{alert.metric_name}</td>
                        </tr>
                        <tr style="background-color: #f8f9fa;">
                            <td style="padding: 8px; font-weight: bold;">Severity:</td>
                            <td style="padding: 8px; color: {severity_color}; font-weight: bold;">
                                {alert.severity.value.upper()}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Current Value:</td>
                            <td style="padding: 8px;">{alert.metric_value}</td>
                        </tr>
                        <tr style="background-color: #f8f9fa;">
                            <td style="padding: 8px; font-weight: bold;">Threshold:</td>
                            <td style="padding: 8px;">{alert.threshold}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Triggered At:</td>
                            <td style="padding: 8px;">{alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                        </tr>
                    </table>
                    
                    <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                        <h4 style="margin: 0 0 10px 0;">Message:</h4>
                        <p style="margin: 0;">{alert.message}</p>
                    </div>
                    
                    {self._format_tags_html(alert.tags) if alert.tags else ""}
                    
                    <div style="margin-top: 20px; padding: 10px; background-color: #e9ecef; border-radius: 5px; font-size: 12px; color: #6c757d;">
                        This is an automated alert from the IACSRAG monitoring system.
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    def _create_health_check_email_body(
        self, component: str, status: str, details: Dict[str, Any]
    ) -> str:
        """헬스체크 이메일 본문 생성"""
        status_color = "#28a745" if status.lower() == "healthy" else "#dc3545"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto;">
                <div style="background-color: {status_color}; color: white; padding: 15px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">🏥 Health Check Report</h2>
                </div>
                
                <div style="border: 1px solid #ddd; border-top: none; padding: 20px; border-radius: 0 0 5px 5px;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; font-weight: bold; width: 150px;">Component:</td>
                            <td style="padding: 8px;">{component}</td>
                        </tr>
                        <tr style="background-color: #f8f9fa;">
                            <td style="padding: 8px; font-weight: bold;">Status:</td>
                            <td style="padding: 8px; color: {status_color}; font-weight: bold;">
                                {status.upper()}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Checked At:</td>
                            <td style="padding: 8px;">{details.get('checked_at', 'N/A')}</td>
                        </tr>
                    </table>
                    
                    {self._format_details_html(details)}
                    
                    <div style="margin-top: 20px; padding: 10px; background-color: #e9ecef; border-radius: 5px; font-size: 12px; color: #6c757d;">
                        This is an automated health check report from the IACSRAG monitoring system.
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    def _format_tags_html(self, tags: Dict[str, Any]) -> str:
        """태그를 HTML 형식으로 포맷"""
        if not tags:
            return ""
        
        tags_html = '<div style="margin-top: 20px;"><h4 style="margin: 0 0 10px 0;">Tags:</h4><ul style="margin: 0; padding-left: 20px;">'
        for key, value in tags.items():
            tags_html += f'<li><strong>{key}:</strong> {value}</li>'
        tags_html += '</ul></div>'
        
        return tags_html
    
    def _format_details_html(self, details: Dict[str, Any]) -> str:
        """상세 정보를 HTML 형식으로 포맷"""
        if not details or len(details) <= 1:  # checked_at만 있는 경우
            return ""
        
        details_html = '<div style="margin-top: 20px;"><h4 style="margin: 0 0 10px 0;">Details:</h4><ul style="margin: 0; padding-left: 20px;">'
        for key, value in details.items():
            if key != 'checked_at':  # checked_at은 이미 표시됨
                details_html += f'<li><strong>{key}:</strong> {value}</li>'
        details_html += '</ul></div>'
        
        return details_html
