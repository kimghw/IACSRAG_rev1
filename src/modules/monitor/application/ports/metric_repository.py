"""
Metric Repository Port

메트릭 저장소 포트를 정의합니다.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from src.modules.monitor.domain.entities import (
    SystemMetric, ProcessingStatistics, SystemOverview,
    ComponentType, MetricType
)


class MetricRepositoryPort(ABC):
    """메트릭 저장소 포트"""
    
    @abstractmethod
    async def save_metric(self, metric: SystemMetric) -> None:
        """메트릭 저장"""
        pass
    
    @abstractmethod
    async def get_metric_by_id(self, metric_id: UUID) -> Optional[SystemMetric]:
        """ID로 메트릭 조회"""
        pass
    
    @abstractmethod
    async def get_metrics_by_component(
        self,
        component: ComponentType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[SystemMetric]:
        """컴포넌트별 메트릭 조회"""
        pass
    
    @abstractmethod
    async def get_metrics_by_name(
        self,
        name: str,
        component: Optional[ComponentType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[SystemMetric]:
        """이름으로 메트릭 조회"""
        pass
    
    @abstractmethod
    async def get_metrics_by_type(
        self,
        metric_type: MetricType,
        component: Optional[ComponentType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[SystemMetric]:
        """타입별 메트릭 조회"""
        pass
    
    @abstractmethod
    async def update_metric(self, metric: SystemMetric) -> None:
        """메트릭 업데이트"""
        pass
    
    @abstractmethod
    async def delete_metric(self, metric_id: UUID) -> bool:
        """메트릭 삭제"""
        pass
    
    @abstractmethod
    async def save_processing_statistics(self, stats: ProcessingStatistics) -> None:
        """처리 통계 저장"""
        pass
    
    @abstractmethod
    async def get_processing_statistics_by_component(
        self,
        component: ComponentType
    ) -> Optional[ProcessingStatistics]:
        """컴포넌트별 처리 통계 조회"""
        pass
    
    @abstractmethod
    async def get_all_processing_statistics(self) -> List[ProcessingStatistics]:
        """모든 처리 통계 조회"""
        pass
    
    @abstractmethod
    async def update_processing_statistics(self, stats: ProcessingStatistics) -> None:
        """처리 통계 업데이트"""
        pass
    
    @abstractmethod
    async def save_system_overview(self, overview: SystemOverview) -> None:
        """시스템 개요 저장"""
        pass
    
    @abstractmethod
    async def get_latest_system_overview(self) -> Optional[SystemOverview]:
        """최신 시스템 개요 조회"""
        pass
    
    @abstractmethod
    async def get_system_overview_history(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 100
    ) -> List[SystemOverview]:
        """시스템 개요 히스토리 조회"""
        pass
    
    @abstractmethod
    async def update_system_overview(self, overview: SystemOverview) -> None:
        """시스템 개요 업데이트"""
        pass
    
    @abstractmethod
    async def cleanup_old_metrics(
        self,
        before_date: datetime,
        component: Optional[ComponentType] = None
    ) -> int:
        """오래된 메트릭 정리"""
        pass
    
    @abstractmethod
    async def get_metric_aggregation(
        self,
        metric_name: str,
        component: ComponentType,
        aggregation_type: str,  # "avg", "sum", "min", "max", "count"
        start_time: datetime,
        end_time: datetime,
        interval_minutes: int = 5
    ) -> List[dict]:
        """메트릭 집계 조회"""
        pass
