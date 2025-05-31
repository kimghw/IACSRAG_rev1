"""
Monitor Domain Entities

모니터링 도메인의 엔티티와 값 객체를 정의합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from src.utils.datetime import utc_now, get_current_utc_datetime


class MetricType(str, Enum):
    """메트릭 타입"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(str, Enum):
    """알림 심각도"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """알림 상태"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ACKNOWLEDGED = "acknowledged"


class ComponentType(str, Enum):
    """시스템 컴포넌트 타입"""
    INGEST = "ingest"
    PROCESS = "process"
    SEARCH = "search"
    VECTOR_DB = "vector_db"
    LLM = "llm"
    DATABASE = "database"
    MESSAGING = "messaging"


class ProcessingStatus(str, Enum):
    """처리 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Metric:
    """메트릭 엔티티"""
    metric_id: UUID
    component: ComponentType
    metric_name: str
    metric_type: MetricType
    value: float
    unit: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=get_current_utc_datetime)
    
    @classmethod
    def create(
        cls,
        component: ComponentType,
        metric_name: str,
        metric_type: MetricType,
        value: float,
        unit: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> "Metric":
        """새로운 메트릭 생성"""
        return cls(
            metric_id=uuid4(),
            component=component,
            metric_name=metric_name,
            metric_type=metric_type,
            value=value,
            unit=unit,
            tags=tags or {}
        )


@dataclass
class MetricValue:
    """메트릭 값 객체"""
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be datetime object")
        if not isinstance(self.value, (int, float)):
            raise ValueError("value must be numeric")


@dataclass
class SystemMetric:
    """시스템 메트릭 엔티티"""
    metric_id: UUID
    name: str
    metric_type: MetricType
    component: ComponentType
    description: str
    values: List[MetricValue] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    
    @classmethod
    def create(
        cls,
        name: str,
        metric_type: MetricType,
        component: ComponentType,
        description: str
    ) -> "SystemMetric":
        """새로운 시스템 메트릭 생성"""
        return cls(
            metric_id=uuid4(),
            name=name,
            metric_type=metric_type,
            component=component,
            description=description
        )
    
    def add_value(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """메트릭 값 추가"""
        metric_value = MetricValue(
            value=value,
            timestamp=utc_now(),
            labels=labels or {}
        )
        self.values.append(metric_value)
        self.updated_at = utc_now()
    
    def record_value(
        self,
        value: float,
        timestamp: Optional[datetime] = None,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """메트릭 값 기록 (별칭 메서드)"""
        self.add_value(value, tags or {})
        if timestamp:
            # 타임스탬프가 제공된 경우 마지막 값의 타임스탬프 업데이트
            if self.values:
                self.values[-1].timestamp = timestamp
    
    def get_latest_value(self) -> Optional[MetricValue]:
        """최신 메트릭 값 조회"""
        if not self.values:
            return None
        return max(self.values, key=lambda v: v.timestamp)
    
    def get_values_in_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[MetricValue]:
        """시간 범위 내 메트릭 값 조회"""
        return [
            value for value in self.values
            if start_time <= value.timestamp <= end_time
        ]


@dataclass
class ProcessingStatistics:
    """처리 통계 엔티티"""
    stats_id: UUID
    component: ComponentType
    total_processed: int = 0
    total_failed: int = 0
    total_retries: int = 0
    average_processing_time: float = 0.0
    peak_processing_time: float = 0.0
    throughput_per_minute: float = 0.0
    error_rate: float = 0.0
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    
    @classmethod
    def create(cls, component: ComponentType) -> "ProcessingStatistics":
        """새로운 처리 통계 생성"""
        return cls(
            stats_id=uuid4(),
            component=component
        )
    
    def update_processing_stats(
        self,
        processed_count: int,
        failed_count: int,
        retry_count: int,
        processing_time: float
    ) -> None:
        """처리 통계 업데이트"""
        self.total_processed += processed_count
        self.total_failed += failed_count
        self.total_retries += retry_count
        
        # 평균 처리 시간 계산
        if self.total_processed > 0:
            total_time = (self.average_processing_time * (self.total_processed - processed_count) + 
                         processing_time * processed_count)
            self.average_processing_time = total_time / self.total_processed
        
        # 최대 처리 시간 업데이트
        if processing_time > self.peak_processing_time:
            self.peak_processing_time = processing_time
        
        # 에러율 계산
        total_attempts = self.total_processed + self.total_failed
        if total_attempts > 0:
            self.error_rate = self.total_failed / total_attempts
        
        self.updated_at = utc_now()
    
    def calculate_throughput(self, time_window_minutes: int = 1) -> None:
        """처리량 계산 (분당)"""
        if time_window_minutes > 0:
            self.throughput_per_minute = self.total_processed / time_window_minutes
        self.updated_at = utc_now()


@dataclass
class HealthStatus:
    """시스템 건강 상태"""
    component: ComponentType
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    last_check: datetime
    response_time_ms: Optional[float] = None
    error_details: Optional[Dict[str, Any]] = None
    
    @classmethod
    def healthy(
        cls,
        component: ComponentType,
        message: str = "All systems operational",
        response_time_ms: Optional[float] = None
    ) -> "HealthStatus":
        """건강한 상태 생성"""
        return cls(
            component=component,
            status="healthy",
            message=message,
            last_check=utc_now(),
            response_time_ms=response_time_ms
        )
    
    @classmethod
    def degraded(
        cls,
        component: ComponentType,
        message: str,
        response_time_ms: Optional[float] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> "HealthStatus":
        """성능 저하 상태 생성"""
        return cls(
            component=component,
            status="degraded",
            message=message,
            last_check=utc_now(),
            response_time_ms=response_time_ms,
            error_details=error_details
        )
    
    @classmethod
    def unhealthy(
        cls,
        component: ComponentType,
        message: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> "HealthStatus":
        """비정상 상태 생성"""
        return cls(
            component=component,
            status="unhealthy",
            message=message,
            last_check=utc_now(),
            error_details=error_details
        )
    
    def is_healthy(self) -> bool:
        """건강 상태 확인"""
        return self.status == "healthy"
    
    def is_degraded(self) -> bool:
        """성능 저하 상태 확인"""
        return self.status == "degraded"
    
    def is_unhealthy(self) -> bool:
        """비정상 상태 확인"""
        return self.status == "unhealthy"


@dataclass
class SystemOverview:
    """시스템 전체 개요"""
    overview_id: UUID
    total_documents: int = 0
    total_chunks: int = 0
    total_searches: int = 0
    total_answers_generated: int = 0
    average_search_time_ms: float = 0.0
    average_answer_time_ms: float = 0.0
    system_uptime_seconds: float = 0.0
    health_statuses: List[HealthStatus] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    last_updated: datetime = field(default_factory=utc_now)
    
    @classmethod
    def create(cls) -> "SystemOverview":
        """새로운 시스템 개요 생성"""
        return cls(overview_id=uuid4())
    
    def update_document_stats(self, document_count: int, chunk_count: int) -> None:
        """문서 통계 업데이트"""
        self.total_documents = document_count
        self.total_chunks = chunk_count
        self.updated_at = utc_now()
    
    def update_search_stats(
        self,
        search_count: int,
        answer_count: int,
        avg_search_time: float,
        avg_answer_time: float
    ) -> None:
        """검색 통계 업데이트"""
        self.total_searches = search_count
        self.total_answers_generated = answer_count
        self.average_search_time_ms = avg_search_time
        self.average_answer_time_ms = avg_answer_time
        self.updated_at = utc_now()
    
    def update_health_status(self, health_status: HealthStatus) -> None:
        """건강 상태 업데이트"""
        # 기존 컴포넌트 상태 제거
        self.health_statuses = [
            status for status in self.health_statuses
            if status.component != health_status.component
        ]
        # 새로운 상태 추가
        self.health_statuses.append(health_status)
        self.updated_at = utc_now()
    
    def get_overall_health(self) -> str:
        """전체 시스템 건강 상태 계산"""
        if not self.health_statuses:
            return "unknown"
        
        unhealthy_count = sum(1 for status in self.health_statuses if status.is_unhealthy())
        degraded_count = sum(1 for status in self.health_statuses if status.is_degraded())
        
        if unhealthy_count > 0:
            return "unhealthy"
        elif degraded_count > 0:
            return "degraded"
        else:
            return "healthy"
    
    def get_component_health(self, component: ComponentType) -> Optional[HealthStatus]:
        """특정 컴포넌트 건강 상태 조회"""
        for status in self.health_statuses:
            if status.component == component:
                return status
        return None


@dataclass
class AlertRule:
    """알림 규칙 엔티티"""
    rule_id: UUID
    name: str
    component: ComponentType
    metric_name: str
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    severity: AlertSeverity
    message: str
    enabled: bool = True
    notification_channels: List[str] = field(default_factory=list)
    cooldown_minutes: int = 5
    last_triggered_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=get_current_utc_datetime)
    updated_at: datetime = field(default_factory=get_current_utc_datetime)
    
    @classmethod
    def create(
        cls,
        name: str,
        component: ComponentType,
        metric_name: str,
        condition: str,
        threshold: float,
        severity: str,
        description: str = ""
    ) -> "AlertRule":
        """새로운 알림 규칙 생성"""
        return cls(
            rule_id=uuid4(),
            name=name,
            component=component,
            metric_name=metric_name,
            condition=condition,
            threshold=threshold,
            severity=AlertSeverity(severity),
            message=description or f"{name}: {metric_name} {condition} {threshold}"
        )
    
    def evaluate(self, metric_value: float) -> bool:
        """알림 규칙 평가"""
        if not self.enabled:
            return False
        
        if self.condition == "gt":
            return metric_value > self.threshold
        elif self.condition == "gte":
            return metric_value >= self.threshold
        elif self.condition == "lt":
            return metric_value < self.threshold
        elif self.condition == "lte":
            return metric_value <= self.threshold
        elif self.condition == "eq":
            return metric_value == self.threshold
        else:
            return False
    
    def update_threshold(self, new_threshold: float) -> None:
        """임계값 업데이트"""
        self.threshold = new_threshold
    
    def toggle_enabled(self) -> None:
        """활성화 상태 토글"""
        self.enabled = not self.enabled


@dataclass
class Alert:
    """알림 엔티티"""
    alert_id: UUID
    rule_id: UUID
    component: ComponentType
    metric_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    metric_value: float
    threshold: float
    triggered_at: datetime = field(default_factory=get_current_utc_datetime)
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        rule: AlertRule,
        metric_value: float,
        message: str
    ) -> "Alert":
        """새로운 알림 생성"""
        return cls(
            alert_id=uuid4(),
            rule_id=rule.rule_id,
            component=rule.component,
            metric_name=rule.metric_name,
            severity=AlertSeverity(rule.severity),
            status=AlertStatus.ACTIVE,
            message=message,
            metric_value=metric_value,
            threshold=rule.threshold
        )
    
    def resolve(self) -> None:
        """알림 해결"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = get_current_utc_datetime()
    
    def suppress(self) -> None:
        """알림 억제"""
        self.status = AlertStatus.SUPPRESSED
    
    def acknowledge(self, acknowledged_by: str) -> None:
        """알림 확인"""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = get_current_utc_datetime()
        self.acknowledged_by = acknowledged_by
    
    def is_active(self) -> bool:
        """활성 알림 여부 확인"""
        return self.status == AlertStatus.ACTIVE
    
    def duration_minutes(self) -> float:
        """알림 지속 시간 (분)"""
        end_time = self.resolved_at or utc_now()
        duration = end_time - self.triggered_at
        return duration.total_seconds() / 60
