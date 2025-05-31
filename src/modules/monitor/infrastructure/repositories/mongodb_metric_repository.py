"""
MongoDB 기반 메트릭 리포지토리 구현
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING, ASCENDING

from src.modules.monitor.application.ports.metric_repository import MetricRepositoryPort
from src.modules.monitor.domain.entities import (
    Metric, SystemMetric, ComponentType, MetricType, ProcessingStatistics, SystemOverview,
    MetricValue, HealthStatus
)
from src.core.exceptions import RepositoryError
from src.utils.datetime import get_current_utc_time


class MongoDBMetricRepository(MetricRepositoryPort):
    """MongoDB 기반 메트릭 리포지토리"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.metrics_collection = database.metrics
        self.processing_stats_collection = database.processing_statistics
        self.system_overview_collection = database.system_overview
    
    async def save_metric(self, metric: SystemMetric) -> None:
        """메트릭 저장"""
        try:
            metric_doc = {
                "_id": str(metric.metric_id),
                "name": metric.name,
                "component": metric.component.value,
                "metric_type": metric.metric_type.value,
                "description": metric.description,
                "values": [{
                    "value": value.value,
                    "timestamp": value.timestamp,
                    "labels": value.labels
                } for value in metric.values],
                "created_at": metric.created_at,
                "updated_at": metric.updated_at
            }
            
            await self.metrics_collection.insert_one(metric_doc)
            
        except Exception as e:
            raise RepositoryError(f"메트릭 저장 실패: {str(e)}")
    
    async def get_metric_by_id(self, metric_id: UUID) -> Optional[SystemMetric]:
        """ID로 메트릭 조회"""
        try:
            doc = await self.metrics_collection.find_one({"_id": str(metric_id)})
            if not doc:
                return None
            return self._doc_to_system_metric(doc)
        except Exception as e:
            raise RepositoryError(f"메트릭 조회 실패: {str(e)}")
    
    async def get_metrics_by_component(
        self,
        component: ComponentType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[SystemMetric]:
        """컴포넌트별 메트릭 조회"""
        try:
            query = {"component": component.value}
            
            if start_time or end_time:
                time_filter = {}
                if start_time:
                    time_filter["$gte"] = start_time
                if end_time:
                    time_filter["$lte"] = end_time
                query["updated_at"] = time_filter
            
            cursor = self.metrics_collection.find(query).sort("updated_at", DESCENDING).limit(100)
            docs = await cursor.to_list(length=100)
            
            return [self._doc_to_system_metric(doc) for doc in docs]
            
        except Exception as e:
            raise RepositoryError(f"메트릭 조회 실패: {str(e)}")
    
    async def get_metrics_by_name(
        self,
        name: str,
        component: Optional[ComponentType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[SystemMetric]:
        """메트릭명별 조회"""
        try:
            query = {"name": name}
            
            if component:
                query["component"] = component.value
            
            if start_time or end_time:
                time_filter = {}
                if start_time:
                    time_filter["$gte"] = start_time
                if end_time:
                    time_filter["$lte"] = end_time
                query["updated_at"] = time_filter
            
            cursor = self.metrics_collection.find(query).sort("updated_at", DESCENDING).limit(100)
            docs = await cursor.to_list(length=100)
            
            return [self._doc_to_system_metric(doc) for doc in docs]
            
        except Exception as e:
            raise RepositoryError(f"메트릭 조회 실패: {str(e)}")
    
    async def get_metrics_by_type(
        self,
        metric_type: MetricType,
        component: Optional[ComponentType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[SystemMetric]:
        """타입별 메트릭 조회"""
        try:
            query = {"metric_type": metric_type.value}
            
            if component:
                query["component"] = component.value
            
            if start_time or end_time:
                time_filter = {}
                if start_time:
                    time_filter["$gte"] = start_time
                if end_time:
                    time_filter["$lte"] = end_time
                query["updated_at"] = time_filter
            
            cursor = self.metrics_collection.find(query).sort("updated_at", DESCENDING).limit(100)
            docs = await cursor.to_list(length=100)
            
            return [self._doc_to_system_metric(doc) for doc in docs]
            
        except Exception as e:
            raise RepositoryError(f"메트릭 조회 실패: {str(e)}")
    
    async def get_latest_metrics(
        self, component: ComponentType, metric_names: List[str]
    ) -> List[SystemMetric]:
        """최신 메트릭 조회"""
        try:
            metrics = []
            for metric_name in metric_names:
                doc = await self.metrics_collection.find_one(
                    {
                        "component": component.value,
                        "name": metric_name
                    },
                    sort=[("updated_at", DESCENDING)]
                )
                if doc:
                    metrics.append(self._doc_to_system_metric(doc))
            
            return metrics
            
        except Exception as e:
            raise RepositoryError(f"최신 메트릭 조회 실패: {str(e)}")
    
    async def update_metric(self, metric: SystemMetric) -> None:
        """메트릭 업데이트"""
        try:
            metric_doc = {
                "name": metric.name,
                "component": metric.component.value,
                "metric_type": metric.metric_type.value,
                "description": metric.description,
                "values": [{
                    "value": value.value,
                    "timestamp": value.timestamp,
                    "labels": value.labels
                } for value in metric.values],
                "updated_at": metric.updated_at
            }
            
            await self.metrics_collection.update_one(
                {"_id": str(metric.metric_id)},
                {"$set": metric_doc}
            )
            
        except Exception as e:
            raise RepositoryError(f"메트릭 업데이트 실패: {str(e)}")
    
    async def delete_metric(self, metric_id: UUID) -> bool:
        """메트릭 삭제"""
        try:
            result = await self.metrics_collection.delete_one({"_id": str(metric_id)})
            return result.deleted_count > 0
        except Exception as e:
            raise RepositoryError(f"메트릭 삭제 실패: {str(e)}")
    
    async def delete_old_metrics(self, older_than: datetime) -> int:
        """오래된 메트릭 삭제"""
        try:
            result = await self.metrics_collection.delete_many(
                {"updated_at": {"$lt": older_than}}
            )
            return result.deleted_count
            
        except Exception as e:
            raise RepositoryError(f"오래된 메트릭 삭제 실패: {str(e)}")
    
    async def save_processing_statistics(self, stats: ProcessingStatistics) -> None:
        """처리 통계 저장"""
        try:
            stats_doc = {
                "_id": str(stats.stats_id),
                "component": stats.component.value,
                "total_processed": stats.total_processed,
                "total_failed": stats.total_failed,
                "total_retries": stats.total_retries,
                "average_processing_time": stats.average_processing_time,
                "peak_processing_time": stats.peak_processing_time,
                "throughput_per_minute": stats.throughput_per_minute,
                "error_rate": stats.error_rate,
                "created_at": stats.created_at,
                "updated_at": stats.updated_at
            }
            
            await self.processing_stats_collection.replace_one(
                {"_id": str(stats.stats_id)},
                stats_doc,
                upsert=True
            )
            
        except Exception as e:
            raise RepositoryError(f"처리 통계 저장 실패: {str(e)}")
    
    async def get_processing_statistics_by_component(
        self, component: ComponentType
    ) -> Optional[ProcessingStatistics]:
        """컴포넌트별 처리 통계 조회"""
        try:
            doc = await self.processing_stats_collection.find_one(
                {"component": component.value},
                sort=[("updated_at", DESCENDING)]
            )
            
            if not doc:
                return None
            
            return ProcessingStatistics(
                stats_id=UUID(doc["_id"]),
                component=ComponentType(doc["component"]),
                total_processed=doc["total_processed"],
                total_failed=doc["total_failed"],
                total_retries=doc.get("total_retries", 0),
                average_processing_time=doc["average_processing_time"],
                peak_processing_time=doc.get("peak_processing_time", 0.0),
                throughput_per_minute=doc.get("throughput_per_minute", 0.0),
                error_rate=doc.get("error_rate", 0.0),
                created_at=doc.get("created_at", get_current_utc_time()),
                updated_at=doc["updated_at"]
            )
            
        except Exception as e:
            raise RepositoryError(f"처리 통계 조회 실패: {str(e)}")
    
    async def get_all_processing_statistics(self) -> List[ProcessingStatistics]:
        """모든 처리 통계 조회"""
        try:
            cursor = self.processing_stats_collection.find({}).sort("updated_at", DESCENDING)
            docs = await cursor.to_list(length=None)
            
            return [
                ProcessingStatistics(
                    stats_id=UUID(doc["_id"]),
                    component=ComponentType(doc["component"]),
                    total_processed=doc["total_processed"],
                    total_failed=doc["total_failed"],
                    total_retries=doc.get("total_retries", 0),
                    average_processing_time=doc["average_processing_time"],
                    peak_processing_time=doc.get("peak_processing_time", 0.0),
                    throughput_per_minute=doc.get("throughput_per_minute", 0.0),
                    error_rate=doc.get("error_rate", 0.0),
                    created_at=doc.get("created_at", get_current_utc_time()),
                    updated_at=doc["updated_at"]
                )
                for doc in docs
            ]
            
        except Exception as e:
            raise RepositoryError(f"처리 통계 조회 실패: {str(e)}")
    
    async def update_processing_statistics(
        self, stats: ProcessingStatistics
    ) -> None:
        """처리 통계 업데이트"""
        try:
            await self.save_processing_statistics(stats)
            
        except Exception as e:
            raise RepositoryError(f"처리 통계 업데이트 실패: {str(e)}")
    
    async def save_system_overview(self, overview: SystemOverview) -> None:
        """시스템 개요 저장"""
        try:
            overview_doc = {
                "_id": str(overview.overview_id),
                "total_documents": overview.total_documents,
                "total_chunks": overview.total_chunks,
                "total_searches": overview.total_searches,
                "total_answers_generated": overview.total_answers_generated,
                "average_search_time_ms": overview.average_search_time_ms,
                "average_answer_time_ms": overview.average_answer_time_ms,
                "system_uptime_seconds": overview.system_uptime_seconds,
                "health_statuses": [{
                    "component": status.component.value,
                    "status": status.status,
                    "message": status.message,
                    "last_check": status.last_check,
                    "response_time_ms": status.response_time_ms,
                    "error_details": status.error_details
                } for status in overview.health_statuses],
                "created_at": overview.created_at,
                "updated_at": overview.updated_at,
                "last_updated": overview.last_updated
            }
            
            await self.system_overview_collection.replace_one(
                {"_id": str(overview.overview_id)},
                overview_doc,
                upsert=True
            )
            
        except Exception as e:
            raise RepositoryError(f"시스템 개요 저장 실패: {str(e)}")
    
    async def get_latest_system_overview(self) -> Optional[SystemOverview]:
        """최신 시스템 개요 조회"""
        try:
            doc = await self.system_overview_collection.find_one(
                {},
                sort=[("updated_at", DESCENDING)]
            )
            
            if not doc:
                return None
            
            health_statuses = []
            for status_doc in doc.get("health_statuses", []):
                health_statuses.append(HealthStatus(
                    component=ComponentType(status_doc["component"]),
                    status=status_doc["status"],
                    message=status_doc["message"],
                    last_check=status_doc["last_check"],
                    response_time_ms=status_doc.get("response_time_ms"),
                    error_details=status_doc.get("error_details")
                ))
            
            return SystemOverview(
                overview_id=UUID(doc["_id"]),
                total_documents=doc["total_documents"],
                total_chunks=doc["total_chunks"],
                total_searches=doc["total_searches"],
                total_answers_generated=doc["total_answers_generated"],
                average_search_time_ms=doc["average_search_time_ms"],
                average_answer_time_ms=doc["average_answer_time_ms"],
                system_uptime_seconds=doc.get("system_uptime_seconds", 0),
                health_statuses=health_statuses,
                created_at=doc.get("created_at", get_current_utc_time()),
                updated_at=doc["updated_at"],
                last_updated=doc["last_updated"]
            )
            
        except Exception as e:
            raise RepositoryError(f"시스템 개요 조회 실패: {str(e)}")
    
    async def get_system_overview_history(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 100
    ) -> List[SystemOverview]:
        """시스템 개요 히스토리 조회"""
        try:
            query = {
                "updated_at": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }
            
            cursor = self.system_overview_collection.find(query).sort("updated_at", DESCENDING).limit(limit)
            docs = await cursor.to_list(length=limit)
            
            overviews = []
            for doc in docs:
                health_statuses = []
                for status_doc in doc.get("health_statuses", []):
                    health_statuses.append(HealthStatus(
                        component=ComponentType(status_doc["component"]),
                        status=status_doc["status"],
                        message=status_doc["message"],
                        last_check=status_doc["last_check"],
                        response_time_ms=status_doc.get("response_time_ms"),
                        error_details=status_doc.get("error_details")
                    ))
                
                overviews.append(SystemOverview(
                    overview_id=UUID(doc["_id"]),
                    total_documents=doc["total_documents"],
                    total_chunks=doc["total_chunks"],
                    total_searches=doc["total_searches"],
                    total_answers_generated=doc["total_answers_generated"],
                    average_search_time_ms=doc["average_search_time_ms"],
                    average_answer_time_ms=doc["average_answer_time_ms"],
                    system_uptime_seconds=doc.get("system_uptime_seconds", 0),
                    health_statuses=health_statuses,
                    created_at=doc.get("created_at", get_current_utc_time()),
                    updated_at=doc["updated_at"],
                    last_updated=doc["last_updated"]
                ))
            
            return overviews
            
        except Exception as e:
            raise RepositoryError(f"시스템 개요 히스토리 조회 실패: {str(e)}")
    
    async def update_system_overview(self, overview: SystemOverview) -> None:
        """시스템 개요 업데이트"""
        try:
            await self.save_system_overview(overview)
            
        except Exception as e:
            raise RepositoryError(f"시스템 개요 업데이트 실패: {str(e)}")
    
    async def cleanup_old_metrics(
        self,
        before_date: datetime,
        component: Optional[ComponentType] = None
    ) -> int:
        """오래된 메트릭 정리"""
        try:
            query = {"updated_at": {"$lt": before_date}}
            
            if component:
                query["component"] = component.value
            
            result = await self.metrics_collection.delete_many(query)
            return result.deleted_count
            
        except Exception as e:
            raise RepositoryError(f"오래된 메트릭 정리 실패: {str(e)}")
    
    async def get_metric_aggregation(
        self,
        metric_name: str,
        component: ComponentType,
        aggregation_type: str,
        start_time: datetime,
        end_time: datetime,
        interval_minutes: int = 5
    ) -> List[dict]:
        """메트릭 집계 조회"""
        try:
            pipeline = [
                {
                    "$match": {
                        "name": metric_name,
                        "component": component.value,
                        "updated_at": {
                            "$gte": start_time,
                            "$lte": end_time
                        }
                    }
                },
                {
                    "$unwind": "$values"
                },
                {
                    "$match": {
                        "values.timestamp": {
                            "$gte": start_time,
                            "$lte": end_time
                        }
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {
                                "format": "%Y-%m-%d %H:%M",
                                "date": "$values.timestamp"
                            }
                        },
                        "timestamp": {"$first": "$values.timestamp"},
                        "value": self._get_aggregation_operation(aggregation_type)
                    }
                },
                {
                    "$sort": {"timestamp": 1}
                }
            ]
            
            cursor = self.metrics_collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            return [{
                "timestamp": result["timestamp"],
                "value": result["value"]
            } for result in results]
            
        except Exception as e:
            raise RepositoryError(f"메트릭 집계 조회 실패: {str(e)}")
    
    def _get_aggregation_operation(self, aggregation_type: str) -> dict:
        """집계 타입에 따른 MongoDB 연산 반환"""
        operations = {
            "avg": {"$avg": "$values.value"},
            "sum": {"$sum": "$values.value"},
            "min": {"$min": "$values.value"},
            "max": {"$max": "$values.value"},
            "count": {"$sum": 1}
        }
        
        return operations.get(aggregation_type, {"$avg": "$values.value"})
    
    def _doc_to_system_metric(self, doc: Dict[str, Any]) -> SystemMetric:
        """MongoDB 문서를 SystemMetric 엔티티로 변환"""
        metric = SystemMetric(
            metric_id=UUID(doc["_id"]),
            name=doc["name"],
            metric_type=MetricType(doc["metric_type"]),
            component=ComponentType(doc["component"]),
            description=doc["description"]
        )
        
        # 값들 복원
        for value_doc in doc.get("values", []):
            metric.values.append(MetricValue(
                value=value_doc["value"],
                timestamp=value_doc["timestamp"],
                labels=value_doc.get("labels", {})
            ))
        
        metric.created_at = doc.get("created_at", metric.created_at)
        metric.updated_at = doc.get("updated_at", metric.updated_at)
        
        return metric
