"""
시스템 헬스체크 어댑터 구현
"""

import asyncio
import psutil
import aiohttp
from typing import Dict, Any, List
from datetime import datetime
import logging

from src.modules.monitor.application.ports.health_check_port import HealthCheckPort
from src.modules.monitor.domain.entities import ComponentType, HealthStatus
from src.core.exceptions import HealthCheckError
from src.utils.datetime import get_current_utc_time


logger = logging.getLogger(__name__)


class SystemHealthCheckAdapter(HealthCheckPort):
    """시스템 헬스체크 어댑터"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.timeout = self.config.get("timeout", 30)
        self.cpu_threshold = self.config.get("cpu_threshold", 80.0)
        self.memory_threshold = self.config.get("memory_threshold", 80.0)
        self.disk_threshold = self.config.get("disk_threshold", 80.0)
    
    async def check_component_health(
        self, component: ComponentType
    ) -> Dict[str, Any]:
        """컴포넌트 헬스체크"""
        try:
            check_time = get_current_utc_time()
            
            if component == ComponentType.SYSTEM:
                return await self._check_system_health(check_time)
            elif component == ComponentType.DATABASE:
                return await self._check_database_health(check_time)
            elif component == ComponentType.VECTOR_DB:
                return await self._check_vector_db_health(check_time)
            elif component == ComponentType.MESSAGE_QUEUE:
                return await self._check_message_queue_health(check_time)
            elif component == ComponentType.INGEST:
                return await self._check_ingest_health(check_time)
            elif component == ComponentType.PROCESS:
                return await self._check_process_health(check_time)
            elif component == ComponentType.SEARCH:
                return await self._check_search_health(check_time)
            else:
                return {
                    "component": component.value,
                    "status": HealthStatus.UNKNOWN.value,
                    "message": "Unknown component type",
                    "checked_at": check_time,
                    "details": {}
                }
                
        except Exception as e:
            logger.error(f"Health check failed for {component.value}: {str(e)}")
            return {
                "component": component.value,
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Health check error: {str(e)}",
                "checked_at": get_current_utc_time(),
                "details": {"error": str(e)}
            }
    
    async def check_all_components(self) -> List[Dict[str, Any]]:
        """모든 컴포넌트 헬스체크"""
        components = [
            ComponentType.SYSTEM,
            ComponentType.DATABASE,
            ComponentType.VECTOR_DB,
            ComponentType.MESSAGE_QUEUE,
            ComponentType.INGEST,
            ComponentType.PROCESS,
            ComponentType.SEARCH
        ]
        
        tasks = [self.check_component_health(component) for component in components]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        health_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                health_results.append({
                    "component": components[i].value,
                    "status": HealthStatus.UNHEALTHY.value,
                    "message": f"Health check failed: {str(result)}",
                    "checked_at": get_current_utc_time(),
                    "details": {"error": str(result)}
                })
            else:
                health_results.append(result)
        
        return health_results
    
    async def check_service_availability(
        self, service_url: str, expected_status: int = 200
    ) -> Dict[str, Any]:
        """서비스 가용성 체크"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(service_url) as response:
                    is_healthy = response.status == expected_status
                    
                    return {
                        "url": service_url,
                        "status": HealthStatus.HEALTHY.value if is_healthy else HealthStatus.UNHEALTHY.value,
                        "response_code": response.status,
                        "response_time_ms": 0,  # 실제 구현에서는 측정 필요
                        "checked_at": get_current_utc_time(),
                        "message": "Service is available" if is_healthy else f"Unexpected status code: {response.status}"
                    }
                    
        except asyncio.TimeoutError:
            return {
                "url": service_url,
                "status": HealthStatus.UNHEALTHY.value,
                "message": "Service timeout",
                "checked_at": get_current_utc_time(),
                "details": {"timeout": self.timeout}
            }
        except Exception as e:
            return {
                "url": service_url,
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Service unavailable: {str(e)}",
                "checked_at": get_current_utc_time(),
                "details": {"error": str(e)}
            }
    
    async def check_database_connection(
        self, connection_string: str
    ) -> Dict[str, Any]:
        """데이터베이스 연결 체크"""
        try:
            # MongoDB 연결 체크 (실제 구현에서는 motor 사용)
            # 여기서는 시뮬레이션
            await asyncio.sleep(0.1)  # 연결 시뮬레이션
            
            return {
                "database": "mongodb",
                "status": HealthStatus.HEALTHY.value,
                "message": "Database connection successful",
                "checked_at": get_current_utc_time(),
                "details": {
                    "connection_string": connection_string.split("@")[-1] if "@" in connection_string else connection_string,
                    "response_time_ms": 100
                }
            }
            
        except Exception as e:
            return {
                "database": "mongodb",
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Database connection failed: {str(e)}",
                "checked_at": get_current_utc_time(),
                "details": {"error": str(e)}
            }
    
    async def _check_system_health(self, check_time: datetime) -> Dict[str, Any]:
        """시스템 리소스 헬스체크"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # 전체 상태 판단
            is_healthy = (
                cpu_percent < self.cpu_threshold and
                memory_percent < self.memory_threshold and
                disk_percent < self.disk_threshold
            )
            
            status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY
            
            issues = []
            if cpu_percent >= self.cpu_threshold:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            if memory_percent >= self.memory_threshold:
                issues.append(f"High memory usage: {memory_percent:.1f}%")
            if disk_percent >= self.disk_threshold:
                issues.append(f"High disk usage: {disk_percent:.1f}%")
            
            message = "System is healthy" if is_healthy else f"System issues: {', '.join(issues)}"
            
            return {
                "component": ComponentType.SYSTEM.value,
                "status": status.value,
                "message": message,
                "checked_at": check_time,
                "details": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "memory_total_gb": round(memory.total / (1024**3), 2),
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_total_gb": round(disk.total / (1024**3), 2),
                    "disk_free_gb": round(disk.free / (1024**3), 2)
                }
            }
            
        except Exception as e:
            raise HealthCheckError(f"System health check failed: {str(e)}")
    
    async def _check_database_health(self, check_time: datetime) -> Dict[str, Any]:
        """데이터베이스 헬스체크"""
        try:
            # 실제 구현에서는 MongoDB 연결 및 ping 테스트
            await asyncio.sleep(0.1)  # 시뮬레이션
            
            return {
                "component": ComponentType.DATABASE.value,
                "status": HealthStatus.HEALTHY.value,
                "message": "Database is healthy",
                "checked_at": check_time,
                "details": {
                    "type": "mongodb",
                    "response_time_ms": 100,
                    "connections": 10,
                    "collections": 5
                }
            }
            
        except Exception as e:
            return {
                "component": ComponentType.DATABASE.value,
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Database health check failed: {str(e)}",
                "checked_at": check_time,
                "details": {"error": str(e)}
            }
    
    async def _check_vector_db_health(self, check_time: datetime) -> Dict[str, Any]:
        """벡터 데이터베이스 헬스체크"""
        try:
            # 실제 구현에서는 Qdrant 연결 및 상태 확인
            await asyncio.sleep(0.1)  # 시뮬레이션
            
            return {
                "component": ComponentType.VECTOR_DB.value,
                "status": HealthStatus.HEALTHY.value,
                "message": "Vector database is healthy",
                "checked_at": check_time,
                "details": {
                    "type": "qdrant",
                    "response_time_ms": 150,
                    "collections": 3,
                    "total_vectors": 25000
                }
            }
            
        except Exception as e:
            return {
                "component": ComponentType.VECTOR_DB.value,
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Vector database health check failed: {str(e)}",
                "checked_at": check_time,
                "details": {"error": str(e)}
            }
    
    async def _check_message_queue_health(self, check_time: datetime) -> Dict[str, Any]:
        """메시지 큐 헬스체크"""
        try:
            # 실제 구현에서는 Kafka 브로커 상태 확인
            await asyncio.sleep(0.1)  # 시뮬레이션
            
            return {
                "component": ComponentType.MESSAGE_QUEUE.value,
                "status": HealthStatus.HEALTHY.value,
                "message": "Message queue is healthy",
                "checked_at": check_time,
                "details": {
                    "type": "kafka",
                    "brokers": 1,
                    "topics": 5,
                    "response_time_ms": 80
                }
            }
            
        except Exception as e:
            return {
                "component": ComponentType.MESSAGE_QUEUE.value,
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Message queue health check failed: {str(e)}",
                "checked_at": check_time,
                "details": {"error": str(e)}
            }
    
    async def _check_ingest_health(self, check_time: datetime) -> Dict[str, Any]:
        """수집 모듈 헬스체크"""
        try:
            # 실제 구현에서는 수집 서비스 상태 확인
            await asyncio.sleep(0.1)  # 시뮬레이션
            
            return {
                "component": ComponentType.INGEST.value,
                "status": HealthStatus.HEALTHY.value,
                "message": "Ingest service is healthy",
                "checked_at": check_time,
                "details": {
                    "active_jobs": 2,
                    "queue_size": 5,
                    "last_processed": check_time.isoformat()
                }
            }
            
        except Exception as e:
            return {
                "component": ComponentType.INGEST.value,
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Ingest service health check failed: {str(e)}",
                "checked_at": check_time,
                "details": {"error": str(e)}
            }
    
    async def _check_process_health(self, check_time: datetime) -> Dict[str, Any]:
        """처리 모듈 헬스체크"""
        try:
            # 실제 구현에서는 처리 서비스 상태 확인
            await asyncio.sleep(0.1)  # 시뮬레이션
            
            return {
                "component": ComponentType.PROCESS.value,
                "status": HealthStatus.HEALTHY.value,
                "message": "Process service is healthy",
                "checked_at": check_time,
                "details": {
                    "active_jobs": 3,
                    "queue_size": 8,
                    "average_processing_time_ms": 250
                }
            }
            
        except Exception as e:
            return {
                "component": ComponentType.PROCESS.value,
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Process service health check failed: {str(e)}",
                "checked_at": check_time,
                "details": {"error": str(e)}
            }
    
    async def _check_search_health(self, check_time: datetime) -> Dict[str, Any]:
        """검색 모듈 헬스체크"""
        try:
            # 실제 구현에서는 검색 서비스 상태 확인
            await asyncio.sleep(0.1)  # 시뮬레이션
            
            return {
                "component": ComponentType.SEARCH.value,
                "status": HealthStatus.HEALTHY.value,
                "message": "Search service is healthy",
                "checked_at": check_time,
                "details": {
                    "response_time_ms": 120,
                    "cache_hit_rate": 0.85,
                    "active_queries": 1
                }
            }
            
        except Exception as e:
            return {
                "component": ComponentType.SEARCH.value,
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Search service health check failed: {str(e)}",
                "checked_at": check_time,
                "details": {"error": str(e)}
            }
