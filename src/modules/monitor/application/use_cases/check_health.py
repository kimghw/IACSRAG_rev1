"""
건강 상태 확인 유즈케이스

시스템 컴포넌트의 건강 상태를 확인하고 모니터링하는 유즈케이스입니다.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from src.core.exceptions import ValidationError, BusinessLogicError
from src.modules.monitor.domain.entities import (
    HealthStatus, ComponentType
)
from src.modules.monitor.application.ports import (
    HealthCheckPort, AlertRepositoryPort, NotificationPort
)


@dataclass
class CheckHealthCommand:
    """건강 상태 확인 명령"""
    component: Optional[str] = None
    include_dependencies: bool = True
    timeout_seconds: int = 30


class CheckComponentHealthCommand:
    """컴포넌트 건강 상태 확인 명령"""
    
    def __init__(
        self,
        component: ComponentType,
        timeout_seconds: int = 30,
        include_dependencies: bool = True
    ):
        self.component = component
        self.timeout_seconds = timeout_seconds
        self.include_dependencies = include_dependencies
        
        self._validate()
    
    def _validate(self):
        """명령 유효성 검증"""
        if self.timeout_seconds <= 0:
            raise ValidationError("타임아웃은 0보다 커야 합니다")
        
        if self.timeout_seconds > 300:  # 5분
            raise ValidationError("타임아웃은 300초를 초과할 수 없습니다")


class PerformHealthCheckCommand:
    """종합 건강 상태 확인 명령"""
    
    def __init__(
        self,
        components: Optional[List[ComponentType]] = None,
        include_system_resources: bool = True,
        timeout_seconds: int = 60,
        generate_alerts: bool = True
    ):
        self.components = components or list(ComponentType)
        self.include_system_resources = include_system_resources
        self.timeout_seconds = timeout_seconds
        self.generate_alerts = generate_alerts
        
        self._validate()
    
    def _validate(self):
        """명령 유효성 검증"""
        if self.timeout_seconds <= 0:
            raise ValidationError("타임아웃은 0보다 커야 합니다")
        
        if self.timeout_seconds > 600:  # 10분
            raise ValidationError("타임아웃은 600초를 초과할 수 없습니다")


class HealthCheckResult:
    """건강 상태 확인 결과"""
    
    def __init__(
        self,
        component: ComponentType,
        status: HealthStatus,
        check_duration_ms: float,
        dependencies: List[HealthStatus] = None,
        recommendations: List[str] = None
    ):
        self.component = component
        self.status = status
        self.check_duration_ms = check_duration_ms
        self.dependencies = dependencies or []
        self.recommendations = recommendations or []
        self.timestamp = datetime.utcnow()


class ComprehensiveHealthCheckResult:
    """종합 건강 상태 확인 결과"""
    
    def __init__(
        self,
        overall_status: str,
        component_results: Dict[ComponentType, HealthCheckResult],
        system_metrics: Dict[str, Any],
        alerts_generated: List[UUID],
        summary: Dict[str, Any]
    ):
        self.overall_status = overall_status
        self.component_results = component_results
        self.system_metrics = system_metrics
        self.alerts_generated = alerts_generated
        self.summary = summary
        self.timestamp = datetime.utcnow()


class CheckComponentHealthUseCase:
    """컴포넌트 건강 상태 확인 유즈케이스"""
    
    def __init__(
        self,
        health_check_service: HealthCheckPort,
        alert_repository: AlertRepositoryPort,
        notification_service: NotificationPort
    ):
        self.health_check_service = health_check_service
        self.alert_repository = alert_repository
        self.notification_service = notification_service
    
    async def execute(self, command: CheckComponentHealthCommand) -> HealthCheckResult:
        """컴포넌트 건강 상태 확인 실행"""
        start_time = datetime.utcnow()
        
        try:
            # 1. 기본 건강 상태 확인
            health_status = await self.health_check_service.check_component_health(
                component=command.component,
                timeout_seconds=command.timeout_seconds
            )
            
            # 2. 의존성 확인 (필요한 경우)
            dependencies = []
            if command.include_dependencies:
                dependencies = await self._check_component_dependencies(
                    command.component
                )
            
            # 3. 건강 상태 기반 권장사항 생성
            recommendations = self._generate_recommendations(
                health_status, dependencies
            )
            
            # 4. 건강 상태가 좋지 않은 경우 알림 처리
            if not health_status.is_healthy():
                await self._handle_unhealthy_component(
                    command.component, health_status
                )
            
            # 5. 결과 생성
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            return HealthCheckResult(
                component=command.component,
                status=health_status,
                check_duration_ms=duration_ms,
                dependencies=dependencies,
                recommendations=recommendations
            )
            
        except Exception as e:
            # 건강 상태 확인 자체가 실패한 경우
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            error_status = HealthStatus.unhealthy(
                component=command.component,
                message=f"건강 상태 확인 실패: {str(e)}",
                details={"error": str(e), "check_failed": True}
            )
            
            return HealthCheckResult(
                component=command.component,
                status=error_status,
                check_duration_ms=duration_ms,
                recommendations=[
                    "건강 상태 확인 서비스 연결을 확인하세요",
                    "컴포넌트 설정을 검토하세요"
                ]
            )
    
    async def _check_component_dependencies(
        self, component: ComponentType
    ) -> List[HealthStatus]:
        """컴포넌트 의존성 확인"""
        try:
            dependency_configs = self._get_dependency_configs(component)
            
            if not dependency_configs:
                return []
            
            return await self.health_check_service.check_service_dependencies(
                component=component,
                dependency_configs=dependency_configs
            )
            
        except Exception as e:
            return [HealthStatus.unhealthy(
                component=component,
                message=f"의존성 확인 실패: {str(e)}"
            )]
    
    def _get_dependency_configs(self, component: ComponentType) -> List[Dict[str, Any]]:
        """컴포넌트별 의존성 설정 조회"""
        dependency_map = {
            ComponentType.INGEST: [
                {"type": "database", "name": "mongodb"},
                {"type": "messaging", "name": "kafka"}
            ],
            ComponentType.PROCESS: [
                {"type": "database", "name": "mongodb"},
                {"type": "vector_db", "name": "qdrant"},
                {"type": "messaging", "name": "kafka"}
            ],
            ComponentType.SEARCH: [
                {"type": "vector_db", "name": "qdrant"},
                {"type": "llm", "name": "openai"}
            ],
            ComponentType.DATABASE: [],
            ComponentType.VECTOR_DB: [],
            ComponentType.MESSAGING: [],
            ComponentType.LLM: []
        }
        
        return dependency_map.get(component, [])
    
    def _generate_recommendations(
        self, health_status: HealthStatus, dependencies: List[HealthStatus]
    ) -> List[str]:
        """건강 상태 기반 권장사항 생성"""
        recommendations = []
        
        if not health_status.is_healthy():
            if health_status.status == "degraded":
                recommendations.extend([
                    "성능 모니터링을 강화하세요",
                    "리소스 사용량을 확인하세요",
                    "로그를 검토하여 경고 메시지를 확인하세요"
                ])
            elif health_status.status == "unhealthy":
                recommendations.extend([
                    "즉시 시스템 관리자에게 연락하세요",
                    "서비스 재시작을 고려하세요",
                    "백업 시스템으로 전환을 검토하세요"
                ])
        
        # 의존성 문제 확인
        unhealthy_deps = [dep for dep in dependencies if not dep.is_healthy()]
        if unhealthy_deps:
            recommendations.append(
                f"{len(unhealthy_deps)}개의 의존성 서비스에 문제가 있습니다"
            )
        
        return recommendations
    
    async def _handle_unhealthy_component(
        self, component: ComponentType, health_status: HealthStatus
    ):
        """비정상 컴포넌트 처리"""
        try:
            # 시스템 건강 상태 알림 발송
            await self.notification_service.send_system_health_notification(
                component=component,
                status=health_status.status,
                message=health_status.message,
                recipients=["admin@example.com"],  # 설정에서 가져와야 함
                notification_type="email"
            )
            
        except Exception as e:
            # 알림 발송 실패는 건강 상태 확인을 실패시키지 않음
            pass


class PerformHealthCheckUseCase:
    """종합 건강 상태 확인 유즈케이스"""
    
    def __init__(
        self,
        health_check_service: HealthCheckPort,
        alert_repository: AlertRepositoryPort,
        notification_service: NotificationPort
    ):
        self.health_check_service = health_check_service
        self.alert_repository = alert_repository
        self.notification_service = notification_service
        self.check_component_use_case = CheckComponentHealthUseCase(
            health_check_service, alert_repository, notification_service
        )
    
    async def execute(self, command: PerformHealthCheckCommand) -> ComprehensiveHealthCheckResult:
        """종합 건강 상태 확인 실행"""
        try:
            component_results = {}
            alerts_generated = []
            
            # 1. 각 컴포넌트 건강 상태 확인
            for component in command.components:
                try:
                    check_command = CheckComponentHealthCommand(
                        component=component,
                        timeout_seconds=min(command.timeout_seconds // len(command.components), 30),
                        include_dependencies=True
                    )
                    
                    result = await self.check_component_use_case.execute(check_command)
                    component_results[component] = result
                    
                except Exception as e:
                    # 개별 컴포넌트 확인 실패
                    error_status = HealthStatus.unhealthy(
                        component=component,
                        message=f"확인 실패: {str(e)}"
                    )
                    
                    component_results[component] = HealthCheckResult(
                        component=component,
                        status=error_status,
                        check_duration_ms=0.0
                    )
            
            # 2. 시스템 리소스 확인 (필요한 경우)
            system_metrics = {}
            if command.include_system_resources:
                system_metrics = await self._check_system_resources()
            
            # 3. 전체 상태 평가
            overall_status = self._evaluate_overall_status(
                component_results, system_metrics
            )
            
            # 4. 요약 정보 생성
            summary = self._generate_summary(component_results, system_metrics)
            
            # 5. 알림 생성 (필요한 경우)
            if command.generate_alerts:
                alerts_generated = await self._generate_health_alerts(
                    component_results, overall_status
                )
            
            return ComprehensiveHealthCheckResult(
                overall_status=overall_status,
                component_results=component_results,
                system_metrics=system_metrics,
                alerts_generated=alerts_generated,
                summary=summary
            )
            
        except Exception as e:
            raise BusinessLogicError(f"종합 건강 상태 확인 실패: {str(e)}")
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """시스템 리소스 확인"""
        try:
            system_metrics = await self.health_check_service.get_system_metrics()
            
            # 추가 리소스 확인
            memory_status = await self.health_check_service.check_memory_usage()
            cpu_status = await self.health_check_service.check_cpu_usage()
            disk_status = await self.health_check_service.check_disk_usage(["/"])
            
            return {
                "metrics": system_metrics,
                "memory": {
                    "status": memory_status.status,
                    "message": memory_status.message,
                    "details": memory_status.details
                },
                "cpu": {
                    "status": cpu_status.status,
                    "message": cpu_status.message,
                    "details": cpu_status.details
                },
                "disk": {
                    "status": disk_status.status,
                    "message": disk_status.message,
                    "details": disk_status.details
                }
            }
            
        except Exception as e:
            return {
                "error": f"시스템 리소스 확인 실패: {str(e)}"
            }
    
    def _evaluate_overall_status(
        self,
        component_results: Dict[ComponentType, HealthCheckResult],
        system_metrics: Dict[str, Any]
    ) -> str:
        """전체 상태 평가"""
        unhealthy_count = 0
        degraded_count = 0
        total_count = len(component_results)
        
        for result in component_results.values():
            if result.status.status == "unhealthy":
                unhealthy_count += 1
            elif result.status.status == "degraded":
                degraded_count += 1
        
        # 시스템 리소스 상태 확인
        resource_issues = 0
        if "memory" in system_metrics and system_metrics["memory"]["status"] != "healthy":
            resource_issues += 1
        if "cpu" in system_metrics and system_metrics["cpu"]["status"] != "healthy":
            resource_issues += 1
        if "disk" in system_metrics and system_metrics["disk"]["status"] != "healthy":
            resource_issues += 1
        
        # 전체 상태 결정
        if unhealthy_count > 0 or resource_issues >= 2:
            return "unhealthy"
        elif degraded_count > 0 or resource_issues >= 1:
            return "degraded"
        else:
            return "healthy"
    
    def _generate_summary(
        self,
        component_results: Dict[ComponentType, HealthCheckResult],
        system_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """요약 정보 생성"""
        total_components = len(component_results)
        healthy_components = sum(
            1 for result in component_results.values()
            if result.status.is_healthy()
        )
        
        avg_response_time = sum(
            result.check_duration_ms for result in component_results.values()
        ) / total_components if total_components > 0 else 0
        
        return {
            "total_components": total_components,
            "healthy_components": healthy_components,
            "unhealthy_components": total_components - healthy_components,
            "health_percentage": (healthy_components / total_components * 100) if total_components > 0 else 0,
            "average_response_time_ms": avg_response_time,
            "system_resources_ok": "error" not in system_metrics,
            "check_timestamp": datetime.utcnow().isoformat()
        }
    
    async def _generate_health_alerts(
        self,
        component_results: Dict[ComponentType, HealthCheckResult],
        overall_status: str
    ) -> List[UUID]:
        """건강 상태 기반 알림 생성"""
        alerts_generated = []
        
        try:
            # 전체 시스템 상태가 좋지 않은 경우 알림
            if overall_status in ["unhealthy", "degraded"]:
                await self.notification_service.send_custom_notification(
                    title=f"시스템 상태 경고: {overall_status.upper()}",
                    message=f"전체 시스템 상태가 {overall_status}입니다. 즉시 확인이 필요합니다.",
                    recipients=["admin@example.com"],
                    priority="high" if overall_status == "unhealthy" else "medium"
                )
            
            # 개별 컴포넌트 문제 알림
            for component, result in component_results.items():
                if not result.status.is_healthy():
                    await self.notification_service.send_system_health_notification(
                        component=component,
                        status=result.status.status,
                        message=result.status.message,
                        recipients=["admin@example.com"]
                    )
            
        except Exception as e:
            # 알림 생성 실패는 건강 상태 확인을 실패시키지 않음
            pass
        
        return alerts_generated


class ScheduleHealthCheckUseCase:
    """건강 상태 확인 스케줄링 유즈케이스"""
    
    def __init__(self, health_check_service: HealthCheckPort):
        self.health_check_service = health_check_service
    
    async def execute(
        self,
        component: ComponentType,
        interval_minutes: int,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """건강 상태 확인 스케줄링 실행"""
        try:
            # 스케줄 생성
            schedule_id = await self.health_check_service.schedule_health_check(
                component=component,
                interval_minutes=interval_minutes,
                enabled=enabled
            )
            
            return {
                "success": True,
                "schedule_id": schedule_id,
                "component": component.value,
                "interval_minutes": interval_minutes,
                "enabled": enabled,
                "message": f"{component.value} 컴포넌트의 건강 상태 확인이 {interval_minutes}분 간격으로 스케줄되었습니다"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"건강 상태 확인 스케줄링 실패: {str(e)}"
            }


# 별칭 클래스 (API 호환성을 위해)
CheckSystemHealthUseCase = PerformHealthCheckUseCase
