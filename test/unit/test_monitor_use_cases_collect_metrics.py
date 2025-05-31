"""
Monitor Use Cases - Collect Metrics 테스트
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.core.exceptions import ValidationError, BusinessLogicError
from src.modules.monitor.domain.entities import (
    SystemMetric, ProcessingStatistics, SystemOverview,
    ComponentType, MetricType, HealthStatus
)
from src.modules.monitor.application.use_cases.collect_metrics import (
    CollectMetricsCommand, CollectMetricsResult, CollectMetricsUseCase,
    CollectSystemMetricsUseCase
)


class TestCollectMetricsCommand:
    """CollectMetricsCommand 테스트"""
    
    def test_valid_command_creation(self):
        """유효한 명령 생성 테스트"""
        # Given
        metrics = [
            {"name": "cpu_usage", "value": 75.5, "type": "gauge"},
            {"name": "memory_usage", "value": 80.0, "type": "gauge"}
        ]
        
        # When
        command = CollectMetricsCommand(
            component=ComponentType.PROCESS,
            metrics=metrics
        )
        
        # Then
        assert command.component == ComponentType.PROCESS
        assert len(command.metrics) == 2
        assert command.timestamp is not None
    
    def test_empty_metrics_validation(self):
        """빈 메트릭 데이터 검증 테스트"""
        # When & Then
        with pytest.raises(ValidationError, match="메트릭 데이터가 비어있습니다"):
            CollectMetricsCommand(
                component=ComponentType.PROCESS,
                metrics=[]
            )
    
    def test_missing_metric_name_validation(self):
        """메트릭 이름 누락 검증 테스트"""
        # Given
        metrics = [{"value": 75.5, "type": "gauge"}]
        
        # When & Then
        with pytest.raises(ValidationError, match="메트릭 이름이 필요합니다"):
            CollectMetricsCommand(
                component=ComponentType.PROCESS,
                metrics=metrics
            )
    
    def test_missing_metric_value_validation(self):
        """메트릭 값 누락 검증 테스트"""
        # Given
        metrics = [{"name": "cpu_usage", "type": "gauge"}]
        
        # When & Then
        with pytest.raises(ValidationError, match="메트릭 값이 필요합니다"):
            CollectMetricsCommand(
                component=ComponentType.PROCESS,
                metrics=metrics
            )
    
    def test_missing_metric_type_validation(self):
        """메트릭 타입 누락 검증 테스트"""
        # Given
        metrics = [{"name": "cpu_usage", "value": 75.5}]
        
        # When & Then
        with pytest.raises(ValidationError, match="메트릭 타입이 필요합니다"):
            CollectMetricsCommand(
                component=ComponentType.PROCESS,
                metrics=metrics
            )


class TestCollectMetricsUseCase:
    """CollectMetricsUseCase 테스트"""
    
    @pytest.fixture
    def mock_metric_repository(self):
        return AsyncMock()
    
    @pytest.fixture
    def mock_health_check_service(self):
        return AsyncMock()
    
    @pytest.fixture
    def use_case(self, mock_metric_repository, mock_health_check_service):
        return CollectMetricsUseCase(
            metric_repository=mock_metric_repository,
            health_check_service=mock_health_check_service
        )
    
    @pytest.mark.asyncio
    async def test_successful_metrics_collection(
        self, use_case, mock_metric_repository, mock_health_check_service
    ):
        """성공적인 메트릭 수집 테스트"""
        # Given
        mock_health_check_service.check_component_health.return_value = (
            HealthStatus.healthy(ComponentType.PROCESS, "Component is healthy")
        )
        
        metrics = [
            {
                "name": "cpu_usage",
                "value": 75.5,
                "type": "gauge",
                "description": "CPU usage percentage"
            },
            {
                "name": "memory_usage",
                "value": 80.0,
                "type": "gauge",
                "description": "Memory usage percentage"
            }
        ]
        
        command = CollectMetricsCommand(
            component=ComponentType.PROCESS,
            metrics=metrics
        )
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.success
        assert result.collected_count == 2
        assert result.failed_count == 0
        assert len(result.metric_ids) == 2
        assert len(result.errors) == 0
        
        # 메트릭 저장 호출 확인
        assert mock_metric_repository.save_metric.call_count == 2
    
    @pytest.mark.asyncio
    async def test_unhealthy_component_collection(
        self, use_case, mock_metric_repository, mock_health_check_service
    ):
        """비정상 컴포넌트에서의 메트릭 수집 테스트"""
        # Given
        mock_health_check_service.check_component_health.return_value = (
            HealthStatus.unhealthy(ComponentType.PROCESS, "Component is down")
        )
        
        metrics = [{"name": "cpu_usage", "value": 75.5, "type": "gauge"}]
        command = CollectMetricsCommand(
            component=ComponentType.PROCESS,
            metrics=metrics
        )
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.collected_count == 1
        assert len(result.errors) == 1
        assert "비정상 상태입니다" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_invalid_metric_type_handling(
        self, use_case, mock_metric_repository, mock_health_check_service
    ):
        """잘못된 메트릭 타입 처리 테스트"""
        # Given
        mock_health_check_service.check_component_health.return_value = (
            HealthStatus.healthy(ComponentType.PROCESS, "Component is healthy")
        )
        
        metrics = [
            {"name": "cpu_usage", "value": 75.5, "type": "gauge"},
            {"name": "invalid_metric", "value": 100, "type": "invalid_type"}
        ]
        
        command = CollectMetricsCommand(
            component=ComponentType.PROCESS,
            metrics=metrics
        )
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.collected_count == 1
        assert result.failed_count == 1
        assert len(result.errors) == 1
        assert "지원되지 않는 메트릭 타입" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_processing_statistics_update(
        self, use_case, mock_metric_repository, mock_health_check_service
    ):
        """처리 통계 업데이트 테스트"""
        # Given
        mock_health_check_service.check_component_health.return_value = (
            HealthStatus.healthy(ComponentType.PROCESS, "Component is healthy")
        )
        
        mock_metric_repository.get_processing_statistics_by_component.return_value = None
        
        metrics = [{"name": "processed_count", "value": 10, "type": "counter"}]
        command = CollectMetricsCommand(
            component=ComponentType.PROCESS,
            metrics=metrics
        )
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.success
        mock_metric_repository.update_processing_statistics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_system_overview_update(
        self, use_case, mock_metric_repository, mock_health_check_service
    ):
        """시스템 개요 업데이트 테스트"""
        # Given
        mock_health_check_service.check_component_health.return_value = (
            HealthStatus.healthy(ComponentType.INGEST, "Component is healthy")
        )
        
        mock_metric_repository.get_latest_system_overview.return_value = None
        
        metrics = [{"name": "documents_processed", "value": 5, "type": "counter"}]
        command = CollectMetricsCommand(
            component=ComponentType.INGEST,
            metrics=metrics
        )
        
        # When
        result = await use_case.execute(command)
        
        # Then
        assert result.success
        mock_metric_repository.update_system_overview.assert_called_once()


class TestCollectSystemMetricsUseCase:
    """CollectSystemMetricsUseCase 테스트"""
    
    @pytest.fixture
    def mock_metric_repository(self):
        return AsyncMock()
    
    @pytest.fixture
    def mock_health_check_service(self):
        return AsyncMock()
    
    @pytest.fixture
    def use_case(self, mock_metric_repository, mock_health_check_service):
        return CollectSystemMetricsUseCase(
            metric_repository=mock_metric_repository,
            health_check_service=mock_health_check_service
        )
    
    @pytest.mark.asyncio
    async def test_successful_system_metrics_collection(
        self, use_case, mock_health_check_service
    ):
        """성공적인 시스템 메트릭 수집 테스트"""
        # Given
        mock_health_check_service.check_component_health.return_value = (
            HealthStatus.healthy(ComponentType.PROCESS, "Component is healthy")
        )
        
        mock_health_check_service.get_component_metrics.return_value = {
            "cpu_usage": 75.5,
            "memory_usage": 80.0,
            "response_time": 150.0
        }
        
        # When
        results = await use_case.execute()
        
        # Then
        assert len(results) > 0
        
        # 각 컴포넌트에 대한 결과 확인
        for component, result in results.items():
            assert isinstance(result, CollectMetricsResult)
            if result.collected_count > 0:
                assert result.success
    
    @pytest.mark.asyncio
    async def test_component_metrics_failure_handling(
        self, use_case, mock_health_check_service
    ):
        """컴포넌트 메트릭 수집 실패 처리 테스트"""
        # Given
        mock_health_check_service.check_component_health.return_value = (
            HealthStatus.healthy(ComponentType.PROCESS, "Component is healthy")
        )
        
        # 일부 컴포넌트에서 메트릭 조회 실패
        def side_effect(component):
            if component == ComponentType.DATABASE:
                raise Exception("Database connection failed")
            return {"cpu_usage": 50.0}
        
        mock_health_check_service.get_component_metrics.side_effect = side_effect
        
        # When
        results = await use_case.execute()
        
        # Then
        assert ComponentType.DATABASE in results
        database_result = results[ComponentType.DATABASE]
        assert not database_result.success
        assert database_result.failed_count == 1
        assert "Database connection failed" in database_result.errors[0]
    
    def test_metric_type_determination(self, use_case):
        """메트릭 타입 결정 테스트"""
        # Test counter metrics
        assert use_case._determine_metric_type("total_count", 100) == MetricType.COUNTER
        assert use_case._determine_metric_type("processed_total", 50) == MetricType.COUNTER
        
        # Test gauge metrics
        assert use_case._determine_metric_type("cpu_usage", 75.5) == MetricType.GAUGE
        assert use_case._determine_metric_type("memory_percent", 80.0) == MetricType.GAUGE
        assert use_case._determine_metric_type("error_rate", 0.05) == MetricType.GAUGE
        
        # Test histogram metrics
        assert use_case._determine_metric_type("response_time", 150.0) == MetricType.HISTOGRAM
        assert use_case._determine_metric_type("processing_duration", 200.0) == MetricType.HISTOGRAM
        assert use_case._determine_metric_type("latency", 50.0) == MetricType.HISTOGRAM
        
        # Test default case
        assert use_case._determine_metric_type("unknown_metric", 42) == MetricType.GAUGE


class TestCollectMetricsResult:
    """CollectMetricsResult 테스트"""
    
    def test_successful_result_creation(self):
        """성공적인 결과 생성 테스트"""
        # Given
        metric_ids = [uuid4(), uuid4()]
        
        # When
        result = CollectMetricsResult(
            collected_count=2,
            failed_count=0,
            metric_ids=metric_ids
        )
        
        # Then
        assert result.success
        assert result.collected_count == 2
        assert result.failed_count == 0
        assert len(result.metric_ids) == 2
        assert len(result.errors) == 0
    
    def test_failed_result_creation(self):
        """실패 결과 생성 테스트"""
        # Given
        errors = ["Error 1", "Error 2"]
        
        # When
        result = CollectMetricsResult(
            collected_count=1,
            failed_count=2,
            metric_ids=[uuid4()],
            errors=errors
        )
        
        # Then
        assert not result.success
        assert result.collected_count == 1
        assert result.failed_count == 2
        assert len(result.errors) == 2
    
    def test_partial_success_result(self):
        """부분 성공 결과 테스트"""
        # When
        result = CollectMetricsResult(
            collected_count=3,
            failed_count=1,
            metric_ids=[uuid4(), uuid4(), uuid4()],
            errors=["One metric failed"]
        )
        
        # Then
        assert not result.success  # failed_count > 0이므로 실패
        assert result.collected_count == 3
        assert result.failed_count == 1
