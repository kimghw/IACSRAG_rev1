"""
메트릭 수집 유즈케이스

시스템 메트릭을 수집하고 저장하는 유즈케이스입니다.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from src.core.exceptions import ValidationError, BusinessLogicError
from src.modules.monitor.domain.entities import (
    SystemMetric, ProcessingStatistics, SystemOverview,
    ComponentType, MetricType
)
from src.modules.monitor.application.ports import (
    MetricRepositoryPort, HealthCheckPort
)
from src.utils.datetime import utc_now


class CollectMetricsCommand:
    """메트릭 수집 명령"""
    
    def __init__(
        self,
        component: ComponentType,
        metrics: List[Dict[str, Any]],
        timestamp: Optional[datetime] = None
    ):
        self.component = component
        self.metrics = metrics
        self.timestamp = timestamp or utc_now()
        
        self._validate()
    
    def _validate(self):
        """명령 유효성 검증"""
        if not self.metrics:
            raise ValidationError("메트릭 데이터가 비어있습니다")
        
        for metric in self.metrics:
            if "name" not in metric:
                raise ValidationError("메트릭 이름이 필요합니다")
            if "value" not in metric:
                raise ValidationError("메트릭 값이 필요합니다")
            if "type" not in metric:
                raise ValidationError("메트릭 타입이 필요합니다")


class CollectMetricsResult:
    """메트릭 수집 결과"""
    
    def __init__(
        self,
        collected_count: int,
        failed_count: int,
        metric_ids: List[UUID],
        errors: List[str] = None
    ):
        self.collected_count = collected_count
        self.failed_count = failed_count
        self.metric_ids = metric_ids
        self.errors = errors or []
        self.success = failed_count == 0


class CollectMetricsUseCase:
    """메트릭 수집 유즈케이스"""
    
    def __init__(
        self,
        metric_repository: MetricRepositoryPort,
        health_check_service: HealthCheckPort
    ):
        self.metric_repository = metric_repository
        self.health_check_service = health_check_service
    
    async def execute(self, command: CollectMetricsCommand) -> CollectMetricsResult:
        """메트릭 수집 실행"""
        collected_count = 0
        failed_count = 0
        metric_ids = []
        errors = []
        
        try:
            # 1. 컴포넌트 건강 상태 확인
            health_status = await self.health_check_service.check_component_health(
                command.component
            )
            
            if not health_status.is_healthy():
                errors.append(f"컴포넌트 {command.component.value}가 비정상 상태입니다")
            
            # 2. 각 메트릭 처리
            for metric_data in command.metrics:
                try:
                    metric = await self._create_metric(
                        command.component,
                        metric_data,
                        command.timestamp
                    )
                    
                    await self.metric_repository.save_metric(metric)
                    metric_ids.append(metric.metric_id)
                    collected_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    errors.append(f"메트릭 '{metric_data.get('name', 'unknown')}' 처리 실패: {str(e)}")
            
            # 3. 처리 통계 업데이트
            if command.component in [ComponentType.PROCESS, ComponentType.INGEST]:
                await self._update_processing_statistics(
                    command.component,
                    collected_count,
                    failed_count
                )
            
            # 4. 시스템 개요 업데이트 (필요한 경우)
            if collected_count > 0:
                await self._update_system_overview_if_needed(command.component)
            
            return CollectMetricsResult(
                collected_count=collected_count,
                failed_count=failed_count,
                metric_ids=metric_ids,
                errors=errors
            )
            
        except Exception as e:
            raise BusinessLogicError(f"메트릭 수집 중 오류 발생: {str(e)}")
    
    async def _create_metric(
        self,
        component: ComponentType,
        metric_data: Dict[str, Any],
        timestamp: datetime
    ) -> SystemMetric:
        """메트릭 엔티티 생성"""
        try:
            metric_type = MetricType(metric_data["type"])
        except ValueError:
            raise ValidationError(f"지원되지 않는 메트릭 타입: {metric_data['type']}")
        
        metric = SystemMetric.create(
            name=metric_data["name"],
            metric_type=metric_type,
            component=component,
            description=metric_data.get("description", "")
        )
        
        # 메트릭 값 설정
        metric.record_value(
            value=metric_data["value"],
            timestamp=timestamp,
            tags=metric_data.get("tags", {}),
            metadata=metric_data.get("metadata", {})
        )
        
        return metric
    
    async def _update_processing_statistics(
        self,
        component: ComponentType,
        success_count: int,
        failure_count: int
    ):
        """처리 통계 업데이트"""
        try:
            stats = await self.metric_repository.get_processing_statistics_by_component(
                component
            )
            
            if stats is None:
                stats = ProcessingStatistics.create(component)
            
            stats.update_processing_stats(
                processed_count=success_count,
                failed_count=failure_count,
                retry_count=0,
                processing_time=0.0
            )
            
            await self.metric_repository.update_processing_statistics(stats)
            
        except Exception as e:
            # 통계 업데이트 실패는 메트릭 수집 자체를 실패시키지 않음
            pass
    
    async def _update_system_overview_if_needed(self, component: ComponentType):
        """필요한 경우 시스템 개요 업데이트"""
        try:
            overview = await self.metric_repository.get_latest_system_overview()
            
            if overview is None:
                overview = SystemOverview.create()
            
            # 컴포넌트별로 관련 통계 업데이트
            if component == ComponentType.INGEST:
                # 문서 관련 통계는 별도 로직에서 처리
                pass
            elif component == ComponentType.SEARCH:
                # 검색 관련 통계는 별도 로직에서 처리
                pass
            
            # 마지막 업데이트 시간 갱신
            overview.last_updated = utc_now()
            
            await self.metric_repository.update_system_overview(overview)
            
        except Exception as e:
            # 시스템 개요 업데이트 실패는 메트릭 수집 자체를 실패시키지 않음
            pass


class CollectSystemMetricsUseCase:
    """시스템 메트릭 일괄 수집 유즈케이스"""
    
    def __init__(
        self,
        metric_repository: MetricRepositoryPort,
        health_check_service: HealthCheckPort
    ):
        self.metric_repository = metric_repository
        self.health_check_service = health_check_service
        self.collect_metrics_use_case = CollectMetricsUseCase(
            metric_repository, health_check_service
        )
    
    async def execute(self) -> Dict[ComponentType, CollectMetricsResult]:
        """모든 컴포넌트의 시스템 메트릭 수집"""
        results = {}
        
        # 각 컴포넌트별로 시스템 메트릭 수집
        for component in ComponentType:
            try:
                system_metrics = await self._get_system_metrics_for_component(component)
                
                if system_metrics:
                    command = CollectMetricsCommand(
                        component=component,
                        metrics=system_metrics
                    )
                    
                    result = await self.collect_metrics_use_case.execute(command)
                    results[component] = result
                else:
                    # 메트릭이 없는 경우도 결과에 포함
                    results[component] = CollectMetricsResult(
                        collected_count=0,
                        failed_count=0,
                        metric_ids=[],
                        errors=[]
                    )
                
            except Exception as e:
                results[component] = CollectMetricsResult(
                    collected_count=0,
                    failed_count=1,
                    metric_ids=[],
                    errors=[f"컴포넌트 {component.value} 메트릭 수집 실패: {str(e)}"]
                )
        
        return results
    
    async def _get_system_metrics_for_component(
        self, component: ComponentType
    ) -> List[Dict[str, Any]]:
        """컴포넌트별 시스템 메트릭 조회"""
        # 건강 상태 확인 서비스를 통해 메트릭 조회
        component_metrics = await self.health_check_service.get_component_metrics(
            component
        )
        
        # 메트릭 데이터를 표준 형식으로 변환
        metrics = []
        for name, value in component_metrics.items():
            metric_type = self._determine_metric_type(name, value)
            
            metrics.append({
                "name": name,
                "value": value,
                "type": metric_type.value,
                "description": f"{component.value} {name} metric",
                "tags": {"component": component.value},
                "metadata": {"source": "system_monitor"}
            })
        
        return metrics
    
    def _determine_metric_type(self, name: str, value: Any) -> MetricType:
        """메트릭 이름과 값을 기반으로 메트릭 타입 결정"""
        name_lower = name.lower()
        
        if "count" in name_lower or "total" in name_lower:
            return MetricType.COUNTER
        elif "rate" in name_lower or "percent" in name_lower or "usage" in name_lower:
            return MetricType.GAUGE
        elif "time" in name_lower or "duration" in name_lower or "latency" in name_lower:
            return MetricType.HISTOGRAM
        else:
            return MetricType.GAUGE
