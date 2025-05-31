"""
Monitor Domain Entities 테스트
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.modules.monitor.domain.entities import (
    MetricType, ComponentType, ProcessingStatus,
    MetricValue, SystemMetric, ProcessingStatistics,
    HealthStatus, SystemOverview, AlertRule, Alert
)
from src.utils.datetime import utc_now


class TestMetricValue:
    """MetricValue 테스트"""
    
    def test_create_metric_value(self):
        """메트릭 값 생성 테스트"""
        # Given
        value = 100.5
        timestamp = utc_now()
        labels = {"service": "api", "version": "1.0"}
        
        # When
        metric_value = MetricValue(
            value=value,
            timestamp=timestamp,
            labels=labels
        )
        
        # Then
        assert metric_value.value == value
        assert metric_value.timestamp == timestamp
        assert metric_value.labels == labels
    
    def test_metric_value_validation(self):
        """메트릭 값 검증 테스트"""
        # Given
        timestamp = utc_now()
        
        # When & Then - 잘못된 값 타입
        with pytest.raises(ValueError, match="value must be numeric"):
            MetricValue(value="invalid", timestamp=timestamp)
        
        # When & Then - 잘못된 타임스탬프 타입
        with pytest.raises(ValueError, match="timestamp must be datetime object"):
            MetricValue(value=100, timestamp="invalid")


class TestSystemMetric:
    """SystemMetric 테스트"""
    
    def test_create_system_metric(self):
        """시스템 메트릭 생성 테스트"""
        # Given
        name = "api_requests_total"
        metric_type = MetricType.COUNTER
        component = ComponentType.SEARCH
        description = "Total API requests"
        
        # When
        metric = SystemMetric.create(
            name=name,
            metric_type=metric_type,
            component=component,
            description=description
        )
        
        # Then
        assert metric.name == name
        assert metric.metric_type == metric_type
        assert metric.component == component
        assert metric.description == description
        assert len(metric.values) == 0
        assert metric.metric_id is not None
        assert metric.created_at is not None
        assert metric.updated_at is not None
    
    def test_add_value(self):
        """메트릭 값 추가 테스트"""
        # Given
        metric = SystemMetric.create(
            name="test_metric",
            metric_type=MetricType.GAUGE,
            component=ComponentType.PROCESS,
            description="Test metric"
        )
        
        # When
        metric.add_value(100.0, {"label": "test"})
        
        # Then
        assert len(metric.values) == 1
        assert metric.values[0].value == 100.0
        assert metric.values[0].labels == {"label": "test"}
    
    def test_get_latest_value(self):
        """최신 메트릭 값 조회 테스트"""
        # Given
        metric = SystemMetric.create(
            name="test_metric",
            metric_type=MetricType.GAUGE,
            component=ComponentType.PROCESS,
            description="Test metric"
        )
        
        # When - 값이 없는 경우
        latest = metric.get_latest_value()
        
        # Then
        assert latest is None
        
        # When - 값 추가 후
        metric.add_value(100.0)
        metric.add_value(200.0)
        latest = metric.get_latest_value()
        
        # Then
        assert latest is not None
        assert latest.value == 200.0
    
    def test_get_values_in_range(self):
        """시간 범위 내 메트릭 값 조회 테스트"""
        # Given
        metric = SystemMetric.create(
            name="test_metric",
            metric_type=MetricType.GAUGE,
            component=ComponentType.PROCESS,
            description="Test metric"
        )
        
        now = utc_now()
        start_time = now - timedelta(hours=1)
        end_time = now + timedelta(hours=1)
        
        # 범위 내 값
        metric.values.append(MetricValue(100.0, now))
        # 범위 밖 값
        metric.values.append(MetricValue(200.0, now - timedelta(hours=2)))
        
        # When
        values_in_range = metric.get_values_in_range(start_time, end_time)
        
        # Then
        assert len(values_in_range) == 1
        assert values_in_range[0].value == 100.0


class TestProcessingStatistics:
    """ProcessingStatistics 테스트"""
    
    def test_create_processing_statistics(self):
        """처리 통계 생성 테스트"""
        # Given
        component = ComponentType.INGEST
        
        # When
        stats = ProcessingStatistics.create(component)
        
        # Then
        assert stats.component == component
        assert stats.total_processed == 0
        assert stats.total_failed == 0
        assert stats.total_retries == 0
        assert stats.average_processing_time == 0.0
        assert stats.peak_processing_time == 0.0
        assert stats.throughput_per_minute == 0.0
        assert stats.error_rate == 0.0
        assert stats.stats_id is not None
    
    def test_update_processing_stats(self):
        """처리 통계 업데이트 테스트"""
        # Given
        stats = ProcessingStatistics.create(ComponentType.PROCESS)
        
        # When - 첫 번째 업데이트
        stats.update_processing_stats(
            processed_count=10,
            failed_count=2,
            retry_count=1,
            processing_time=5.0
        )
        
        # Then
        assert stats.total_processed == 10
        assert stats.total_failed == 2
        assert stats.total_retries == 1
        assert stats.average_processing_time == 5.0
        assert stats.peak_processing_time == 5.0
        assert stats.error_rate == 2 / 12  # 2 failed / (10 processed + 2 failed)
        
        # When - 두 번째 업데이트
        stats.update_processing_stats(
            processed_count=5,
            failed_count=1,
            retry_count=0,
            processing_time=3.0
        )
        
        # Then
        assert stats.total_processed == 15
        assert stats.total_failed == 3
        assert stats.total_retries == 1
        # 평균 처리 시간: (10*5.0 + 5*3.0) / 15 = 4.33...
        assert abs(stats.average_processing_time - 4.333333333333333) < 0.001
        assert stats.peak_processing_time == 5.0  # 최대값 유지
        assert stats.error_rate == 3 / 18  # 3 failed / (15 processed + 3 failed)
    
    def test_calculate_throughput(self):
        """처리량 계산 테스트"""
        # Given
        stats = ProcessingStatistics.create(ComponentType.PROCESS)
        stats.total_processed = 60
        
        # When
        stats.calculate_throughput(time_window_minutes=2)
        
        # Then
        assert stats.throughput_per_minute == 30.0  # 60 / 2


class TestHealthStatus:
    """HealthStatus 테스트"""
    
    def test_healthy_status(self):
        """건강한 상태 테스트"""
        # Given
        component = ComponentType.DATABASE
        message = "Database is running smoothly"
        response_time = 50.0
        
        # When
        status = HealthStatus.healthy(component, message, response_time)
        
        # Then
        assert status.component == component
        assert status.status == "healthy"
        assert status.message == message
        assert status.response_time_ms == response_time
        assert status.is_healthy()
        assert not status.is_degraded()
        assert not status.is_unhealthy()
    
    def test_degraded_status(self):
        """성능 저하 상태 테스트"""
        # Given
        component = ComponentType.VECTOR_DB
        message = "High response time detected"
        response_time = 500.0
        error_details = {"avg_response_time": 450.0}
        
        # When
        status = HealthStatus.degraded(component, message, response_time, error_details)
        
        # Then
        assert status.component == component
        assert status.status == "degraded"
        assert status.message == message
        assert status.response_time_ms == response_time
        assert status.error_details == error_details
        assert not status.is_healthy()
        assert status.is_degraded()
        assert not status.is_unhealthy()
    
    def test_unhealthy_status(self):
        """비정상 상태 테스트"""
        # Given
        component = ComponentType.LLM
        message = "Service unavailable"
        error_details = {"error": "Connection timeout"}
        
        # When
        status = HealthStatus.unhealthy(component, message, error_details)
        
        # Then
        assert status.component == component
        assert status.status == "unhealthy"
        assert status.message == message
        assert status.error_details == error_details
        assert not status.is_healthy()
        assert not status.is_degraded()
        assert status.is_unhealthy()


class TestSystemOverview:
    """SystemOverview 테스트"""
    
    def test_create_system_overview(self):
        """시스템 개요 생성 테스트"""
        # When
        overview = SystemOverview.create()
        
        # Then
        assert overview.overview_id is not None
        assert overview.total_documents == 0
        assert overview.total_chunks == 0
        assert overview.total_searches == 0
        assert overview.total_answers_generated == 0
        assert overview.average_search_time_ms == 0.0
        assert overview.average_answer_time_ms == 0.0
        assert overview.system_uptime_seconds == 0.0
        assert len(overview.health_statuses) == 0
    
    def test_update_document_stats(self):
        """문서 통계 업데이트 테스트"""
        # Given
        overview = SystemOverview.create()
        
        # When
        overview.update_document_stats(document_count=100, chunk_count=500)
        
        # Then
        assert overview.total_documents == 100
        assert overview.total_chunks == 500
    
    def test_update_search_stats(self):
        """검색 통계 업데이트 테스트"""
        # Given
        overview = SystemOverview.create()
        
        # When
        overview.update_search_stats(
            search_count=50,
            answer_count=45,
            avg_search_time=150.0,
            avg_answer_time=2000.0
        )
        
        # Then
        assert overview.total_searches == 50
        assert overview.total_answers_generated == 45
        assert overview.average_search_time_ms == 150.0
        assert overview.average_answer_time_ms == 2000.0
    
    def test_update_health_status(self):
        """건강 상태 업데이트 테스트"""
        # Given
        overview = SystemOverview.create()
        
        # When - 첫 번째 상태 추가
        status1 = HealthStatus.healthy(ComponentType.DATABASE)
        overview.update_health_status(status1)
        
        # Then
        assert len(overview.health_statuses) == 1
        assert overview.health_statuses[0].component == ComponentType.DATABASE
        
        # When - 같은 컴포넌트 상태 업데이트
        status2 = HealthStatus.degraded(ComponentType.DATABASE, "Performance issue")
        overview.update_health_status(status2)
        
        # Then
        assert len(overview.health_statuses) == 1
        assert overview.health_statuses[0].status == "degraded"
        
        # When - 다른 컴포넌트 상태 추가
        status3 = HealthStatus.healthy(ComponentType.VECTOR_DB)
        overview.update_health_status(status3)
        
        # Then
        assert len(overview.health_statuses) == 2
    
    def test_get_overall_health(self):
        """전체 시스템 건강 상태 계산 테스트"""
        # Given
        overview = SystemOverview.create()
        
        # When - 상태가 없는 경우
        health = overview.get_overall_health()
        
        # Then
        assert health == "unknown"
        
        # When - 모든 컴포넌트가 건강한 경우
        overview.update_health_status(HealthStatus.healthy(ComponentType.DATABASE))
        overview.update_health_status(HealthStatus.healthy(ComponentType.VECTOR_DB))
        health = overview.get_overall_health()
        
        # Then
        assert health == "healthy"
        
        # When - 일부 컴포넌트가 성능 저하인 경우
        overview.update_health_status(HealthStatus.degraded(ComponentType.LLM, "Slow response"))
        health = overview.get_overall_health()
        
        # Then
        assert health == "degraded"
        
        # When - 일부 컴포넌트가 비정상인 경우
        overview.update_health_status(HealthStatus.unhealthy(ComponentType.MESSAGING, "Connection failed"))
        health = overview.get_overall_health()
        
        # Then
        assert health == "unhealthy"
    
    def test_get_component_health(self):
        """특정 컴포넌트 건강 상태 조회 테스트"""
        # Given
        overview = SystemOverview.create()
        status = HealthStatus.healthy(ComponentType.DATABASE)
        overview.update_health_status(status)
        
        # When
        db_health = overview.get_component_health(ComponentType.DATABASE)
        missing_health = overview.get_component_health(ComponentType.LLM)
        
        # Then
        assert db_health is not None
        assert db_health.component == ComponentType.DATABASE
        assert missing_health is None


class TestAlertRule:
    """AlertRule 테스트"""
    
    def test_create_alert_rule(self):
        """알림 규칙 생성 테스트"""
        # Given
        name = "High Error Rate"
        component = ComponentType.PROCESS
        metric_name = "error_rate"
        condition = "gt"
        threshold = 0.05
        severity = "high"
        description = "Alert when error rate exceeds 5%"
        
        # When
        rule = AlertRule.create(
            name=name,
            component=component,
            metric_name=metric_name,
            condition=condition,
            threshold=threshold,
            severity=severity,
            description=description
        )
        
        # Then
        assert rule.name == name
        assert rule.component == component
        assert rule.metric_name == metric_name
        assert rule.condition == condition
        assert rule.threshold == threshold
        assert rule.severity == severity
        assert rule.message == description
        assert rule.enabled is True
        assert rule.rule_id is not None
    
    def test_evaluate_conditions(self):
        """알림 규칙 평가 테스트"""
        # Given
        rule_gt = AlertRule.create("Test GT", ComponentType.PROCESS, "metric", "gt", 10.0, "medium")
        rule_gte = AlertRule.create("Test GTE", ComponentType.PROCESS, "metric", "gte", 10.0, "medium")
        rule_lt = AlertRule.create("Test LT", ComponentType.PROCESS, "metric", "lt", 10.0, "medium")
        rule_lte = AlertRule.create("Test LTE", ComponentType.PROCESS, "metric", "lte", 10.0, "medium")
        rule_eq = AlertRule.create("Test EQ", ComponentType.PROCESS, "metric", "eq", 10.0, "medium")
        
        # When & Then
        assert rule_gt.evaluate(15.0) is True
        assert rule_gt.evaluate(10.0) is False
        assert rule_gt.evaluate(5.0) is False
        
        assert rule_gte.evaluate(15.0) is True
        assert rule_gte.evaluate(10.0) is True
        assert rule_gte.evaluate(5.0) is False
        
        assert rule_lt.evaluate(5.0) is True
        assert rule_lt.evaluate(10.0) is False
        assert rule_lt.evaluate(15.0) is False
        
        assert rule_lte.evaluate(5.0) is True
        assert rule_lte.evaluate(10.0) is True
        assert rule_lte.evaluate(15.0) is False
        
        assert rule_eq.evaluate(10.0) is True
        assert rule_eq.evaluate(5.0) is False
        assert rule_eq.evaluate(15.0) is False
    
    def test_evaluate_disabled_rule(self):
        """비활성화된 규칙 평가 테스트"""
        # Given
        rule = AlertRule.create("Test", ComponentType.PROCESS, "metric", "gt", 10.0, "medium")
        rule.enabled = False
        
        # When
        result = rule.evaluate(15.0)
        
        # Then
        assert result is False
    
    def test_update_threshold(self):
        """임계값 업데이트 테스트"""
        # Given
        rule = AlertRule.create("Test", ComponentType.PROCESS, "metric", "gt", 10.0, "medium")
        original_updated_at = rule.updated_at
        
        # When
        rule.update_threshold(20.0)
        
        # Then
        assert rule.threshold == 20.0
    
    def test_toggle_enabled(self):
        """활성화 상태 토글 테스트"""
        # Given
        rule = AlertRule.create("Test", ComponentType.PROCESS, "metric", "gt", 10.0, "medium")
        original_enabled = rule.enabled
        original_updated_at = rule.updated_at
        
        # When
        rule.toggle_enabled()
        
        # Then
        assert rule.enabled != original_enabled


class TestAlert:
    """Alert 테스트"""
    
    def test_create_alert(self):
        """알림 생성 테스트"""
        # Given
        rule = AlertRule.create("Test Rule", ComponentType.PROCESS, "error_rate", "gt", 0.05, "high")
        current_value = 0.08
        message = "Error rate is too high"
        
        # When
        alert = Alert.create(rule, current_value, message)
        
        # Then
        assert alert.rule_id == rule.rule_id
        assert alert.component == rule.component
        assert alert.metric_name == rule.metric_name
        assert alert.metric_value == current_value
        assert alert.threshold == rule.threshold
        assert alert.severity == rule.severity
        assert alert.message == message
        assert alert.status == "active"
        assert alert.alert_id is not None
        assert alert.triggered_at is not None
        assert alert.resolved_at is None
    
    def test_resolve_alert(self):
        """알림 해결 테스트"""
        # Given
        rule = AlertRule.create("Test Rule", ComponentType.PROCESS, "error_rate", "gt", 0.05, "high")
        alert = Alert.create(rule, 0.08, "Error rate is too high")
        
        # When
        alert.resolve()
        
        # Then
        assert alert.status == "resolved"
        assert alert.resolved_at is not None
        assert not alert.is_active()
    
    def test_suppress_alert(self):
        """알림 억제 테스트"""
        # Given
        rule = AlertRule.create("Test Rule", ComponentType.PROCESS, "error_rate", "gt", 0.05, "high")
        alert = Alert.create(rule, 0.08, "Error rate is too high")
        
        # When
        alert.suppress()
        
        # Then
        assert alert.status == "suppressed"
        assert not alert.is_active()
    
    def test_is_active(self):
        """활성 알림 여부 확인 테스트"""
        # Given
        rule = AlertRule.create("Test Rule", ComponentType.PROCESS, "error_rate", "gt", 0.05, "high")
        alert = Alert.create(rule, 0.08, "Error rate is too high")
        
        # When & Then
        assert alert.is_active() is True
        
        alert.resolve()
        assert alert.is_active() is False
        
        # 새로운 알림 생성 후 억제
        alert2 = Alert.create(rule, 0.08, "Error rate is too high")
        alert2.suppress()
        assert alert2.is_active() is False
    
    def test_duration_minutes(self):
        """알림 지속 시간 계산 테스트"""
        # Given
        rule = AlertRule.create("Test Rule", ComponentType.PROCESS, "error_rate", "gt", 0.05, "high")
        alert = Alert.create(rule, 0.08, "Error rate is too high")
        
        # When - 해결되지 않은 알림
        duration = alert.duration_minutes()
        
        # Then
        assert duration >= 0  # 현재 시간까지의 지속 시간
        
        # When - 알림 해결
        alert.resolve()
        duration_resolved = alert.duration_minutes()
        
        # Then
        assert duration_resolved >= 0
        assert duration_resolved >= duration  # 해결 시간이 더 길거나 같음
