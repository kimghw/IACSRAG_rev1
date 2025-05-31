"""
이메일 알림 어댑터 구현
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
import logging

from src.modules.monitor.application.ports.notification_port import NotificationPort
from src.modules.monitor.domain.entities import Alert
from src.core.exceptions import NotificationError


logger = logging.getLogger(__name__)


class EmailNotificationAdapter(NotificationPort):
    """이메일 알림 어댑터"""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        use_tls: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls
    
    async def send_alert_notification(
        self,
        alert: Alert,
        recipients: List[str],
        template_data: Dict[str, Any] = None
    ) -> bool:
        """알림 이메일 발송"""
        try:
            # 이메일 내용 생성
            subject = f"[{alert.severity.value.upper()}] {alert.component.value} Alert"
            body = self._create_alert_email_body(alert, template_data or {})
            
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
                
                server.login(self.username, self.password)
                server.send_message(message)
            
            logger.info(f"Alert email sent successfully to {recipients}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send alert email: {str(e)}")
            raise NotificationError(f"이메일 발송 실패: {str(e)}")
    
    async def send_health_check_notification(
        self,
        component: str,
        status: str,
        details: Dict[str, Any],
        recipients: List[str]
    ) -> bool:
        """헬스체크 알림 발송"""
        try:
            subject = f"Health Check Alert - {component}"
            body = self._create_health_check_email_body(component, status, details)
            
            message = MIMEMultipart()
            message["From"] = self.from_email
            message["To"] = ", ".join(recipients)
            message["Subject"] = subject
            
            message.attach(MIMEText(body, "html"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                server.login(self.username, self.password)
                server.send_message(message)
            
            logger.info(f"Health check email sent successfully to {recipients}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send health check email: {str(e)}")
            raise NotificationError(f"헬스체크 이메일 발송 실패: {str(e)}")
    
    async def send_custom_notification(
        self,
        subject: str,
        message: str,
        recipients: List[str],
        metadata: Dict[str, Any] = None
    ) -> bool:
        """사용자 정의 알림 발송"""
        try:
            email_message = MIMEMultipart()
            email_message["From"] = self.from_email
            email_message["To"] = ", ".join(recipients)
            email_message["Subject"] = subject
            
            # 메타데이터가 있으면 메시지에 추가
            if metadata:
                message += "\n\n--- Additional Information ---\n"
                for key, value in metadata.items():
                    message += f"{key}: {value}\n"
            
            email_message.attach(MIMEText(message, "plain"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                server.login(self.username, self.password)
                server.send_message(email_message)
            
            logger.info(f"Custom email sent successfully to {recipients}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send custom email: {str(e)}")
            raise NotificationError(f"사용자 정의 이메일 발송 실패: {str(e)}")
    
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
