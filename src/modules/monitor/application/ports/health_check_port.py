"""
Health Check Port

시스템 건강 상태 확인 포트를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from src.modules.monitor.domain.entities import HealthStatus, ComponentType


class HealthCheckPort(ABC):
    """시스템 건강 상태 확인 포트"""
    
    @abstractmethod
    async def check_component_health(
        self,
        component: ComponentType,
        timeout_seconds: int = 30
    ) -> HealthStatus:
        """컴포넌트 건강 상태 확인"""
        pass
    
    @abstractmethod
    async def check_database_health(
        self,
        connection_string: Optional[str] = None,
        timeout_seconds: int = 10
    ) -> HealthStatus:
        """데이터베이스 건강 상태 확인"""
        pass
    
    @abstractmethod
    async def check_vector_db_health(
        self,
        connection_config: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 10
    ) -> HealthStatus:
        """벡터 데이터베이스 건강 상태 확인"""
        pass
    
    @abstractmethod
    async def check_messaging_health(
        self,
        broker_config: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 10
    ) -> HealthStatus:
        """메시징 시스템 건강 상태 확인"""
        pass
    
    @abstractmethod
    async def check_llm_service_health(
        self,
        service_config: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 30
    ) -> HealthStatus:
        """LLM 서비스 건강 상태 확인"""
        pass
    
    @abstractmethod
    async def check_external_api_health(
        self,
        api_endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 15
    ) -> HealthStatus:
        """외부 API 건강 상태 확인"""
        pass
    
    @abstractmethod
    async def check_file_system_health(
        self,
        paths: List[str],
        check_write_permission: bool = True
    ) -> HealthStatus:
        """파일 시스템 건강 상태 확인"""
        pass
    
    @abstractmethod
    async def check_memory_usage(
        self,
        warning_threshold_percent: float = 80.0,
        critical_threshold_percent: float = 95.0
    ) -> HealthStatus:
        """메모리 사용량 확인"""
        pass
    
    @abstractmethod
    async def check_cpu_usage(
        self,
        warning_threshold_percent: float = 80.0,
        critical_threshold_percent: float = 95.0,
        duration_seconds: int = 5
    ) -> HealthStatus:
        """CPU 사용량 확인"""
        pass
    
    @abstractmethod
    async def check_disk_usage(
        self,
        paths: List[str],
        warning_threshold_percent: float = 80.0,
        critical_threshold_percent: float = 95.0
    ) -> HealthStatus:
        """디스크 사용량 확인"""
        pass
    
    @abstractmethod
    async def check_network_connectivity(
        self,
        hosts: List[str],
        timeout_seconds: int = 5
    ) -> HealthStatus:
        """네트워크 연결 상태 확인"""
        pass
    
    @abstractmethod
    async def check_service_dependencies(
        self,
        component: ComponentType,
        dependency_configs: List[Dict[str, Any]]
    ) -> List[HealthStatus]:
        """서비스 의존성 확인"""
        pass
    
    @abstractmethod
    async def perform_comprehensive_health_check(
        self,
        components: Optional[List[ComponentType]] = None,
        include_system_resources: bool = True,
        timeout_seconds: int = 60
    ) -> Dict[str, HealthStatus]:
        """종합 건강 상태 확인"""
        pass
    
    @abstractmethod
    async def get_system_metrics(self) -> Dict[str, Any]:
        """시스템 메트릭 조회"""
        pass
    
    @abstractmethod
    async def get_component_metrics(
        self,
        component: ComponentType
    ) -> Dict[str, Any]:
        """컴포넌트별 메트릭 조회"""
        pass
    
    @abstractmethod
    async def validate_configuration(
        self,
        component: ComponentType,
        config: Dict[str, Any]
    ) -> HealthStatus:
        """설정 유효성 검증"""
        pass
    
    @abstractmethod
    async def test_component_functionality(
        self,
        component: ComponentType,
        test_data: Optional[Dict[str, Any]] = None
    ) -> HealthStatus:
        """컴포넌트 기능 테스트"""
        pass
    
    @abstractmethod
    async def get_health_check_history(
        self,
        component: Optional[ComponentType] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """건강 상태 확인 히스토리 조회"""
        pass
    
    @abstractmethod
    async def schedule_health_check(
        self,
        component: ComponentType,
        interval_minutes: int,
        enabled: bool = True
    ) -> str:
        """건강 상태 확인 스케줄링"""
        pass
    
    @abstractmethod
    async def cancel_scheduled_health_check(
        self,
        schedule_id: str
    ) -> bool:
        """예약된 건강 상태 확인 취소"""
        pass
    
    @abstractmethod
    async def get_scheduled_health_checks(
        self,
        component: Optional[ComponentType] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """예약된 건강 상태 확인 목록 조회"""
        pass
    
    @abstractmethod
    async def update_health_check_thresholds(
        self,
        component: ComponentType,
        thresholds: Dict[str, Any]
    ) -> bool:
        """건강 상태 확인 임계값 업데이트"""
        pass
    
    @abstractmethod
    async def get_health_check_configuration(
        self,
        component: ComponentType
    ) -> Dict[str, Any]:
        """건강 상태 확인 설정 조회"""
        pass
