"""
Alert Repository Port

알림 저장소 포트를 정의합니다.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from src.modules.monitor.domain.entities import (
    AlertRule, Alert, ComponentType
)


class AlertRepositoryPort(ABC):
    """알림 저장소 포트"""
    
    @abstractmethod
    async def save_alert_rule(self, rule: AlertRule) -> None:
        """알림 규칙 저장"""
        pass
    
    @abstractmethod
    async def get_alert_rule_by_id(self, rule_id: UUID) -> Optional[AlertRule]:
        """ID로 알림 규칙 조회"""
        pass
    
    @abstractmethod
    async def get_alert_rules_by_component(
        self,
        component: ComponentType,
        enabled_only: bool = True
    ) -> List[AlertRule]:
        """컴포넌트별 알림 규칙 조회"""
        pass
    
    @abstractmethod
    async def get_alert_rules_by_metric(
        self,
        metric_name: str,
        component: Optional[ComponentType] = None,
        enabled_only: bool = True
    ) -> List[AlertRule]:
        """메트릭별 알림 규칙 조회"""
        pass
    
    @abstractmethod
    async def get_all_alert_rules(
        self,
        enabled_only: bool = True
    ) -> List[AlertRule]:
        """모든 알림 규칙 조회"""
        pass
    
    @abstractmethod
    async def update_alert_rule(self, rule: AlertRule) -> None:
        """알림 규칙 업데이트"""
        pass
    
    @abstractmethod
    async def delete_alert_rule(self, rule_id: UUID) -> bool:
        """알림 규칙 삭제"""
        pass
    
    @abstractmethod
    async def save_alert(self, alert: Alert) -> None:
        """알림 저장"""
        pass
    
    @abstractmethod
    async def get_alert_by_id(self, alert_id: UUID) -> Optional[Alert]:
        """ID로 알림 조회"""
        pass
    
    @abstractmethod
    async def get_alerts_by_rule(
        self,
        rule_id: UUID,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Alert]:
        """규칙별 알림 조회"""
        pass
    
    @abstractmethod
    async def get_alerts_by_component(
        self,
        component: ComponentType,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Alert]:
        """컴포넌트별 알림 조회"""
        pass
    
    @abstractmethod
    async def get_alerts_by_severity(
        self,
        severity: str,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Alert]:
        """심각도별 알림 조회"""
        pass
    
    @abstractmethod
    async def get_active_alerts(
        self,
        component: Optional[ComponentType] = None,
        severity: Optional[str] = None
    ) -> List[Alert]:
        """활성 알림 조회"""
        pass
    
    @abstractmethod
    async def get_recent_alerts(
        self,
        hours: int = 24,
        component: Optional[ComponentType] = None,
        status: Optional[str] = None
    ) -> List[Alert]:
        """최근 알림 조회"""
        pass
    
    @abstractmethod
    async def update_alert(self, alert: Alert) -> None:
        """알림 업데이트"""
        pass
    
    @abstractmethod
    async def resolve_alert(self, alert_id: UUID) -> bool:
        """알림 해결"""
        pass
    
    @abstractmethod
    async def suppress_alert(self, alert_id: UUID) -> bool:
        """알림 억제"""
        pass
    
    @abstractmethod
    async def bulk_resolve_alerts(
        self,
        rule_id: Optional[UUID] = None,
        component: Optional[ComponentType] = None,
        before_time: Optional[datetime] = None
    ) -> int:
        """알림 일괄 해결"""
        pass
    
    @abstractmethod
    async def cleanup_old_alerts(
        self,
        before_date: datetime,
        status: Optional[str] = None
    ) -> int:
        """오래된 알림 정리"""
        pass
    
    @abstractmethod
    async def get_alert_statistics(
        self,
        start_time: datetime,
        end_time: datetime,
        component: Optional[ComponentType] = None
    ) -> dict:
        """알림 통계 조회"""
        pass
    
    @abstractmethod
    async def get_alert_count_by_severity(
        self,
        start_time: datetime,
        end_time: datetime,
        component: Optional[ComponentType] = None
    ) -> dict:
        """심각도별 알림 수 조회"""
        pass
    
    @abstractmethod
    async def get_top_alerting_components(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 10
    ) -> List[dict]:
        """알림 발생이 많은 컴포넌트 조회"""
        pass
