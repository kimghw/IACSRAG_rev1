"""
MongoDB 기반 알림 리포지토리 구현
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING, ASCENDING

from src.modules.monitor.application.ports.alert_repository import AlertRepositoryPort
from src.modules.monitor.domain.entities import (
    Alert, AlertRule, AlertSeverity, ComponentType, AlertStatus
)
from src.core.exceptions import RepositoryError
from src.utils.datetime import get_current_utc_time


class MongoDBAlertRepository(AlertRepositoryPort):
    """MongoDB 기반 알림 리포지토리"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.alerts_collection = database.alerts
        self.alert_rules_collection = database.alert_rules
    
    async def save_alert(self, alert: Alert) -> None:
        """알림 저장"""
        try:
            alert_doc = {
                "_id": str(alert.alert_id),
                "rule_id": str(alert.rule_id),
                "component": alert.component.value,
                "metric_name": alert.metric_name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "message": alert.message,
                "metric_value": alert.metric_value,
                "threshold": alert.threshold,
                "triggered_at": alert.triggered_at,
                "resolved_at": alert.resolved_at,
                "acknowledged_at": alert.acknowledged_at,
                "acknowledged_by": alert.acknowledged_by,
                "tags": alert.tags,
                "created_at": get_current_utc_time()
            }
            
            await self.alerts_collection.insert_one(alert_doc)
            
        except Exception as e:
            raise RepositoryError(f"알림 저장 실패: {str(e)}")
    
    async def update_alert(self, alert: Alert) -> None:
        """알림 업데이트"""
        try:
            update_doc = {
                "status": alert.status.value,
                "resolved_at": alert.resolved_at,
                "acknowledged_at": alert.acknowledged_at,
                "acknowledged_by": alert.acknowledged_by,
                "updated_at": get_current_utc_time()
            }
            
            await self.alerts_collection.update_one(
                {"_id": str(alert.alert_id)},
                {"$set": update_doc}
            )
            
        except Exception as e:
            raise RepositoryError(f"알림 업데이트 실패: {str(e)}")
    
    async def get_alert_by_id(self, alert_id: UUID) -> Optional[Alert]:
        """ID로 알림 조회"""
        try:
            doc = await self.alerts_collection.find_one({"_id": str(alert_id)})
            
            if not doc:
                return None
            
            return self._doc_to_alert(doc)
            
        except Exception as e:
            raise RepositoryError(f"알림 조회 실패: {str(e)}")
    
    async def get_active_alerts(
        self,
        component: Optional[ComponentType] = None,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """활성 알림 조회"""
        try:
            query = {"status": AlertStatus.ACTIVE.value}
            
            if component:
                query["component"] = component.value
            
            if severity:
                query["severity"] = severity.value
            
            cursor = self.alerts_collection.find(query).sort("triggered_at", DESCENDING)
            docs = await cursor.to_list(length=None)
            
            return [self._doc_to_alert(doc) for doc in docs]
            
        except Exception as e:
            raise RepositoryError(f"활성 알림 조회 실패: {str(e)}")
    
    async def get_recent_alerts(
        self,
        hours: int = 24,
        component: Optional[ComponentType] = None,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """최근 알림 조회"""
        try:
            since = get_current_utc_time() - timedelta(hours=hours)
            query = {"triggered_at": {"$gte": since}}
            
            if component:
                query["component"] = component.value
            
            if severity:
                query["severity"] = severity.value
            
            cursor = self.alerts_collection.find(query).sort("triggered_at", DESCENDING)
            docs = await cursor.to_list(length=None)
            
            return [self._doc_to_alert(doc) for doc in docs]
            
        except Exception as e:
            raise RepositoryError(f"최근 알림 조회 실패: {str(e)}")
    
    async def get_alerts_by_component(
        self, component: ComponentType, limit: int = 100
    ) -> List[Alert]:
        """컴포넌트별 알림 조회"""
        try:
            cursor = self.alerts_collection.find(
                {"component": component.value}
            ).sort("created_at", DESCENDING).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [self._doc_to_alert(doc) for doc in docs]
            
        except Exception as e:
            raise RepositoryError(f"컴포넌트별 알림 조회 실패: {str(e)}")
    
    async def get_alerts_by_rule(
        self, rule_id: UUID, limit: int = 100
    ) -> List[Alert]:
        """규칙별 알림 조회"""
        try:
            cursor = self.alerts_collection.find(
                {"rule_id": str(rule_id)}
            ).sort("created_at", DESCENDING).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [self._doc_to_alert(doc) for doc in docs]
            
        except Exception as e:
            raise RepositoryError(f"규칙별 알림 조회 실패: {str(e)}")
    
    async def get_alerts_by_severity(
        self, severity: AlertSeverity, limit: int = 100
    ) -> List[Alert]:
        """심각도별 알림 조회"""
        try:
            cursor = self.alerts_collection.find(
                {"severity": severity.value}
            ).sort("created_at", DESCENDING).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [self._doc_to_alert(doc) for doc in docs]
            
        except Exception as e:
            raise RepositoryError(f"심각도별 알림 조회 실패: {str(e)}")
    
    async def resolve_alert(self, alert_id: UUID) -> bool:
        """알림 해결"""
        try:
            result = await self.alerts_collection.update_one(
                {"_id": str(alert_id)},
                {
                    "$set": {
                        "status": AlertStatus.RESOLVED.value,
                        "resolved_at": get_current_utc_time(),
                        "updated_at": get_current_utc_time()
                    }
                }
            )
            return result.modified_count > 0
            
        except Exception as e:
            raise RepositoryError(f"알림 해결 실패: {str(e)}")
    
    async def suppress_alert(self, alert_id: UUID, duration_minutes: int) -> bool:
        """알림 억제"""
        try:
            suppress_until = get_current_utc_time() + timedelta(minutes=duration_minutes)
            
            result = await self.alerts_collection.update_one(
                {"_id": str(alert_id)},
                {
                    "$set": {
                        "status": AlertStatus.SUPPRESSED.value,
                        "suppressed_until": suppress_until,
                        "updated_at": get_current_utc_time()
                    }
                }
            )
            return result.modified_count > 0
            
        except Exception as e:
            raise RepositoryError(f"알림 억제 실패: {str(e)}")
    
    async def bulk_resolve_alerts(self, alert_ids: List[UUID]) -> int:
        """대량 알림 해결"""
        try:
            result = await self.alerts_collection.update_many(
                {"_id": {"$in": [str(aid) for aid in alert_ids]}},
                {
                    "$set": {
                        "status": AlertStatus.RESOLVED.value,
                        "resolved_at": get_current_utc_time(),
                        "updated_at": get_current_utc_time()
                    }
                }
            )
            return result.modified_count
            
        except Exception as e:
            raise RepositoryError(f"대량 알림 해결 실패: {str(e)}")
    
    async def get_alert_count_by_severity(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, int]:
        """심각도별 알림 수 조회"""
        try:
            pipeline = [
                {
                    "$match": {
                        "triggered_at": {"$gte": start_time, "$lte": end_time}
                    }
                },
                {
                    "$group": {
                        "_id": "$severity",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            cursor = self.alerts_collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            return {result["_id"]: result["count"] for result in results}
            
        except Exception as e:
            raise RepositoryError(f"심각도별 알림 수 조회 실패: {str(e)}")
    
    async def get_alert_statistics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """알림 통계 조회"""
        try:
            pipeline = [
                {
                    "$match": {
                        "triggered_at": {"$gte": start_time, "$lte": end_time}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_alerts": {"$sum": 1},
                        "active_alerts": {
                            "$sum": {
                                "$cond": [{"$eq": ["$status", "active"]}, 1, 0]
                            }
                        },
                        "resolved_alerts": {
                            "$sum": {
                                "$cond": [{"$eq": ["$status", "resolved"]}, 1, 0]
                            }
                        },
                        "acknowledged_alerts": {
                            "$sum": {
                                "$cond": [{"$ne": ["$acknowledged_at", None]}, 1, 0]
                            }
                        }
                    }
                }
            ]
            
            cursor = self.alerts_collection.aggregate(pipeline)
            results = await cursor.to_list(length=1)
            
            if results:
                return results[0]
            else:
                return {
                    "total_alerts": 0,
                    "active_alerts": 0,
                    "resolved_alerts": 0,
                    "acknowledged_alerts": 0
                }
            
        except Exception as e:
            raise RepositoryError(f"알림 통계 조회 실패: {str(e)}")
    
    async def get_top_alerting_components(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """상위 알림 발생 컴포넌트 조회"""
        try:
            pipeline = [
                {
                    "$match": {
                        "triggered_at": {"$gte": start_time, "$lte": end_time}
                    }
                },
                {
                    "$group": {
                        "_id": "$component",
                        "alert_count": {"$sum": 1},
                        "high_severity_count": {
                            "$sum": {
                                "$cond": [{"$eq": ["$severity", "high"]}, 1, 0]
                            }
                        },
                        "critical_severity_count": {
                            "$sum": {
                                "$cond": [{"$eq": ["$severity", "critical"]}, 1, 0]
                            }
                        }
                    }
                },
                {"$sort": {"alert_count": DESCENDING}},
                {"$limit": limit}
            ]
            
            cursor = self.alerts_collection.aggregate(pipeline)
            return await cursor.to_list(length=limit)
            
        except Exception as e:
            raise RepositoryError(f"상위 알림 발생 컴포넌트 조회 실패: {str(e)}")
    
    async def save_alert_rule(self, rule: AlertRule) -> None:
        """알림 규칙 저장"""
        try:
            rule_doc = {
                "_id": str(rule.rule_id),
                "name": rule.name,
                "component": rule.component.value,
                "metric_name": rule.metric_name,
                "condition": rule.condition,
                "threshold": rule.threshold,
                "severity": rule.severity.value,
                "message": rule.message,
                "enabled": rule.enabled,
                "notification_channels": rule.notification_channels,
                "cooldown_minutes": rule.cooldown_minutes,
                "last_triggered_at": rule.last_triggered_at,
                "created_at": rule.created_at,
                "updated_at": get_current_utc_time()
            }
            
            await self.alert_rules_collection.insert_one(rule_doc)
            
        except Exception as e:
            raise RepositoryError(f"알림 규칙 저장 실패: {str(e)}")
    
    async def update_alert_rule(self, rule: AlertRule) -> None:
        """알림 규칙 업데이트"""
        try:
            update_doc = {
                "condition": rule.condition,
                "threshold": rule.threshold,
                "severity": rule.severity.value,
                "message": rule.message,
                "enabled": rule.enabled,
                "notification_channels": rule.notification_channels,
                "cooldown_minutes": rule.cooldown_minutes,
                "last_triggered_at": rule.last_triggered_at,
                "updated_at": get_current_utc_time()
            }
            
            await self.alert_rules_collection.update_one(
                {"_id": str(rule.rule_id)},
                {"$set": update_doc}
            )
            
        except Exception as e:
            raise RepositoryError(f"알림 규칙 업데이트 실패: {str(e)}")
    
    async def get_alert_rule_by_id(self, rule_id: UUID) -> Optional[AlertRule]:
        """ID로 알림 규칙 조회"""
        try:
            doc = await self.alert_rules_collection.find_one({"_id": str(rule_id)})
            
            if not doc:
                return None
            
            return self._doc_to_alert_rule(doc)
            
        except Exception as e:
            raise RepositoryError(f"알림 규칙 조회 실패: {str(e)}")
    
    async def get_alert_rules_by_metric(
        self,
        metric_name: str,
        component: ComponentType,
        enabled_only: bool = False
    ) -> List[AlertRule]:
        """메트릭별 알림 규칙 조회"""
        try:
            query = {
                "metric_name": metric_name,
                "component": component.value
            }
            
            if enabled_only:
                query["enabled"] = True
            
            cursor = self.alert_rules_collection.find(query)
            docs = await cursor.to_list(length=None)
            
            return [self._doc_to_alert_rule(doc) for doc in docs]
            
        except Exception as e:
            raise RepositoryError(f"메트릭별 알림 규칙 조회 실패: {str(e)}")
    
    async def get_alert_rules_by_component(
        self, component: ComponentType
    ) -> List[AlertRule]:
        """컴포넌트별 알림 규칙 조회"""
        try:
            cursor = self.alert_rules_collection.find(
                {"component": component.value}
            ).sort("created_at", DESCENDING)
            
            docs = await cursor.to_list(length=None)
            return [self._doc_to_alert_rule(doc) for doc in docs]
            
        except Exception as e:
            raise RepositoryError(f"컴포넌트별 알림 규칙 조회 실패: {str(e)}")
    
    async def get_enabled_alert_rules(self) -> List[AlertRule]:
        """활성화된 알림 규칙 조회"""
        try:
            cursor = self.alert_rules_collection.find({"enabled": True})
            docs = await cursor.to_list(length=None)
            
            return [self._doc_to_alert_rule(doc) for doc in docs]
            
        except Exception as e:
            raise RepositoryError(f"활성화된 알림 규칙 조회 실패: {str(e)}")
    
    async def get_all_alert_rules(self) -> List[AlertRule]:
        """모든 알림 규칙 조회"""
        try:
            cursor = self.alert_rules_collection.find({}).sort("created_at", DESCENDING)
            docs = await cursor.to_list(length=None)
            return [self._doc_to_alert_rule(doc) for doc in docs]
            
        except Exception as e:
            raise RepositoryError(f"모든 알림 규칙 조회 실패: {str(e)}")
    
    async def delete_alert_rule(self, rule_id: UUID) -> bool:
        """알림 규칙 삭제"""
        try:
            result = await self.alert_rules_collection.delete_one(
                {"_id": str(rule_id)}
            )
            return result.deleted_count > 0
            
        except Exception as e:
            raise RepositoryError(f"알림 규칙 삭제 실패: {str(e)}")
    
    async def cleanup_old_alerts(
        self, before_date: datetime, component: Optional[ComponentType] = None
    ) -> int:
        """오래된 알림 정리"""
        try:
            query = {"created_at": {"$lt": before_date}}
            
            if component:
                query["component"] = component.value
            
            result = await self.alerts_collection.delete_many(query)
            return result.deleted_count
            
        except Exception as e:
            raise RepositoryError(f"오래된 알림 정리 실패: {str(e)}")
    
    def _doc_to_alert(self, doc: Dict[str, Any]) -> Alert:
        """MongoDB 문서를 Alert 엔티티로 변환"""
        return Alert(
            alert_id=UUID(doc["_id"]),
            rule_id=UUID(doc["rule_id"]),
            component=ComponentType(doc["component"]),
            metric_name=doc["metric_name"],
            severity=AlertSeverity(doc["severity"]),
            status=AlertStatus(doc["status"]),
            message=doc["message"],
            metric_value=doc["metric_value"],
            threshold=doc["threshold"],
            triggered_at=doc["triggered_at"],
            resolved_at=doc.get("resolved_at"),
            acknowledged_at=doc.get("acknowledged_at"),
            acknowledged_by=doc.get("acknowledged_by"),
            tags=doc.get("tags", {})
        )
    
    def _doc_to_alert_rule(self, doc: Dict[str, Any]) -> AlertRule:
        """MongoDB 문서를 AlertRule 엔티티로 변환"""
        return AlertRule(
            rule_id=UUID(doc["_id"]),
            name=doc["name"],
            component=ComponentType(doc["component"]),
            metric_name=doc["metric_name"],
            condition=doc["condition"],
            threshold=doc["threshold"],
            severity=AlertSeverity(doc["severity"]),
            message=doc["message"],
            enabled=doc["enabled"],
            notification_channels=doc.get("notification_channels", []),
            cooldown_minutes=doc.get("cooldown_minutes", 5),
            last_triggered_at=doc.get("last_triggered_at"),
            created_at=doc["created_at"]
        )
