"""
Core Dependencies 모듈 강화된 테스트
기존 테스트에서 누락된 부분들과 에러 시나리오 보완
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Protocol, Optional
import inspect

from src.core.dependencies import (
    DependencyContainer,
    ServiceCollection,
    ServiceDescriptor,
    ServiceLifetime,
    DependencyScope,
    get_container,
    inject,
    injectable,
    auto_inject,
    get_vector_database,
    get_search_use_case,
    get_answer_use_case,
    get_document_service,
    get_document_repository,
    get_mongodb_client,
    get_qdrant_client,
    get_monitor_service,
    get_database,
    get_vector_db
)

# 기존 테스트 파일에서 클래스들을 직접 정의
from abc import ABC, abstractmethod

class ITestService(ABC):
    @abstractmethod
    def get_value(self) -> str:
        pass

class TestService(ITestService):
    def get_value(self) -> str:
        return "test_value"

class IRepository(ABC):
    @abstractmethod
    def save(self, data: str) -> bool:
        pass

class TestRepository(IRepository):
    def save(self, data: str) -> bool:
        return True


# 테스트용 추가 인터페이스와 구현체들
class IComplexService(Protocol):
    def complex_operation(self) -> str:
        pass


class ComplexService:
    def __init__(self, dependency1: str, dependency2: int, optional_param: str = "default"):
        self.dependency1 = dependency1
        self.dependency2 = dependency2
        self.optional_param = optional_param
    
    def complex_operation(self) -> str:
        return f"{self.dependency1}_{self.dependency2}_{self.optional_param}"


class ServiceWithCircularDependency:
    def __init__(self, other_service: 'AnotherServiceWithCircularDependency'):
        self.other_service = other_service


class AnotherServiceWithCircularDependency:
    def __init__(self, service: ServiceWithCircularDependency):
        self.service = service


class ServiceWithMissingDependency:
    def __init__(self, missing_service: 'NonExistentService'):
        self.missing_service = missing_service


class ServiceWithBasicTypeDependencies:
    def __init__(self, name: str, count: int, active: bool):
        self.name = name
        self.count = count
        self.active = active


class TestDependencyContainerEnhanced:
    """의존성 컨테이너 강화된 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 새로운 컨테이너 생성"""
        self.container = DependencyContainer()
    
    def test_create_instance_with_basic_type_dependencies(self):
        """기본 타입 의존성이 있는 인스턴스 생성 테스트"""
        # 기본 타입 의존성은 주입되지 않아야 함
        with pytest.raises(TypeError):
            # 필수 파라미터가 제공되지 않아 TypeError 발생
            self.container._create_instance(ServiceWithBasicTypeDependencies)
    
    def test_create_instance_with_missing_dependency(self):
        """누락된 의존성이 있는 인스턴스 생성 테스트"""
        self.container.register_transient(ServiceWithMissingDependency, ServiceWithMissingDependency)
        
        # 누락된 의존성으로 인해 생성 실패
        with pytest.raises(Exception):
            self.container.get(ServiceWithMissingDependency)
    
    def test_get_key_method(self):
        """_get_key 메서드 테스트"""
        from src.core.dependencies import DependencyContainer
        
        container = DependencyContainer()
        key = container._get_key(DependencyContainer)
        
        expected = f"{DependencyContainer.__module__}.{DependencyContainer.__name__}"
        assert key == expected
    
    def test_register_same_interface_multiple_times(self):
        """동일한 인터페이스를 여러 번 등록하는 테스트"""
        # 첫 번째 등록
        self.container.register_singleton(ITestService, TestService)
        
        # 두 번째 등록 (덮어쓰기)
        self.container.register_transient(ITestService, TestService)
        
        # 마지막 등록이 우선됨
        instance1 = self.container.get(ITestService)
        instance2 = self.container.get(ITestService)
        
        # transient로 등록했으므로 다른 인스턴스여야 함
        assert instance1 is not instance2
    
    def test_factory_with_exception(self):
        """예외를 발생시키는 팩토리 테스트"""
        def failing_factory():
            raise RuntimeError("Factory failed")
        
        self.container.register_factory(ITestService, failing_factory)
        
        with pytest.raises(RuntimeError, match="Factory failed"):
            self.container.get(ITestService)
    
    def test_singleton_creation_with_exception(self):
        """싱글톤 생성 시 예외 발생 테스트"""
        class FailingService:
            def __init__(self):
                raise ValueError("Cannot create service")
        
        self.container.register_singleton(FailingService, FailingService)
        
        with pytest.raises(ValueError, match="Cannot create service"):
            self.container.get(FailingService)


class TestServiceCollectionEnhanced:
    """서비스 컬렉션 강화된 테스트"""
    
    def test_add_singleton_without_implementation(self):
        """구현체 없이 싱글톤 추가 테스트"""
        collection = ServiceCollection()
        collection.add_singleton(TestService)  # 인터페이스와 구현체가 동일
        
        container = collection.build_container()
        
        instance1 = container.get(TestService)
        instance2 = container.get(TestService)
        
        assert instance1 is instance2
    
    def test_add_transient_without_implementation(self):
        """구현체 없이 일시적 서비스 추가 테스트"""
        collection = ServiceCollection()
        collection.add_transient(TestService)  # 인터페이스와 구현체가 동일
        
        container = collection.build_container()
        
        instance1 = container.get(TestService)
        instance2 = container.get(TestService)
        
        assert instance1 is not instance2
    
    def test_empty_service_collection(self):
        """빈 서비스 컬렉션 테스트"""
        collection = ServiceCollection()
        container = collection.build_container()
        
        # 빈 컨테이너에서 서비스 요청 시 에러
        with pytest.raises(ValueError, match="Service not registered"):
            container.get(ITestService)


class TestServiceDescriptorEnhanced:
    """서비스 디스크립터 강화된 테스트"""
    
    def test_descriptor_with_scoped_lifetime(self):
        """스코프 생명주기 디스크립터 테스트"""
        descriptor = ServiceDescriptor(
            interface=ITestService,
            implementation=TestService,
            lifetime=ServiceLifetime.SCOPED
        )
        
        container = DependencyContainer()
        descriptor.register_to(container)
        
        # SCOPED는 현재 TRANSIENT로 처리됨
        instance1 = container.get(ITestService)
        instance2 = container.get(ITestService)
        
        assert instance1 is not instance2
    
    def test_descriptor_with_all_none_values(self):
        """모든 값이 None인 디스크립터 테스트"""
        descriptor = ServiceDescriptor(interface=ITestService)
        container = DependencyContainer()
        
        with pytest.raises(ValueError, match="No implementation, factory, or instance provided"):
            descriptor.register_to(container)


class TestAutoInjectEnhanced:
    """자동 주입 데코레이터 강화된 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 컨테이너 초기화"""
        container = get_container()
        container.clear()
    
    def test_auto_inject_with_missing_dependency(self):
        """누락된 의존성이 있는 자동 주입 테스트"""
        @auto_inject
        def process_with_missing_service(data: str, service: ITestService) -> str:
            return f"{data}_{service.get_value()}"
        
        with pytest.raises(ValueError, match="Cannot inject dependency"):
            process_with_missing_service("input")
    
    def test_auto_inject_with_default_parameter(self):
        """기본값이 있는 파라미터의 자동 주입 테스트"""
        container = get_container()
        container.register_singleton(ITestService, TestService)
        
        @auto_inject
        def process_with_default(data: str, service: ITestService, optional: str = "default") -> str:
            return f"{data}_{service.get_value()}_{optional}"
        
        result = process_with_default("input")
        assert result == "input_test_value_default"
    
    def test_auto_inject_with_no_type_hints(self):
        """타입 힌트가 없는 파라미터의 자동 주입 테스트"""
        @auto_inject
        def process_without_hints(data, service) -> str:
            return f"{data}_{service}"
        
        # 타입 힌트가 없으면 주입되지 않음
        with pytest.raises(TypeError):
            process_without_hints("input")


class TestFastAPIDependencyFunctions:
    """FastAPI 의존성 함수들 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 컨테이너 초기화"""
        container = get_container()
        container.clear()
    
    def test_get_vector_database_without_registration(self):
        """등록되지 않은 Vector Database 의존성 테스트"""
        with pytest.raises(ValueError, match="Service not registered"):
            get_vector_database()
    
    def test_get_search_use_case_without_registration(self):
        """등록되지 않은 Search Use Case 의존성 테스트"""
        with pytest.raises(ValueError, match="Service not registered"):
            get_search_use_case()
    
    def test_get_answer_use_case_without_registration(self):
        """등록되지 않은 Answer Use Case 의존성 테스트"""
        with pytest.raises(ValueError, match="Service not registered"):
            get_answer_use_case()
    
    def test_get_document_service_without_registration(self):
        """등록되지 않은 Document Service 의존성 테스트"""
        with pytest.raises(ValueError, match="Service not registered"):
            get_document_service()
    
    def test_get_document_repository_without_registration(self):
        """등록되지 않은 Document Repository 의존성 테스트"""
        with pytest.raises(ValueError, match="Service not registered"):
            get_document_repository()
    
    def test_get_mongodb_client_without_registration(self):
        """등록되지 않은 MongoDB Client 의존성 테스트"""
        with pytest.raises(ValueError, match="Service not registered"):
            get_mongodb_client()
    
    def test_get_qdrant_client_without_registration(self):
        """등록되지 않은 Qdrant Client 의존성 테스트"""
        with pytest.raises(ValueError, match="Service not registered"):
            get_qdrant_client()
    
    def test_get_monitor_service_without_registration(self):
        """등록되지 않은 Monitor Service 의존성 테스트"""
        with pytest.raises(ValueError, match="Service not registered"):
            get_monitor_service()
    
    def test_get_database_without_registration(self):
        """등록되지 않은 Database 의존성 테스트"""
        with pytest.raises(ValueError, match="Service not registered"):
            get_database()
    
    def test_get_vector_db_without_registration(self):
        """등록되지 않은 Vector DB 의존성 테스트"""
        with pytest.raises(ValueError, match="Service not registered"):
            get_vector_db()


class TestDependencyScopeEnhanced:
    """의존성 스코프 강화된 테스트"""
    
    def test_scope_with_exception_in_context(self):
        """컨텍스트 내에서 예외 발생 시 스코프 테스트"""
        container = DependencyContainer()
        container.register_transient(ITestService, TestService)
        
        try:
            with DependencyScope(container) as scope:
                instance1 = scope.get_scoped(ITestService)
                assert isinstance(instance1, TestService)
                
                # 예외 발생
                raise RuntimeError("Test exception")
        except RuntimeError:
            pass
        
        # 스코프가 정상적으로 정리되었는지 확인
        # 새로운 스코프에서는 다른 인스턴스가 생성되어야 함
        with DependencyScope(container) as scope:
            instance2 = scope.get_scoped(ITestService)
            assert isinstance(instance2, TestService)
    
    def test_scope_get_scoped_with_unregistered_service(self):
        """등록되지 않은 서비스의 스코프 조회 테스트"""
        container = DependencyContainer()
        
        with DependencyScope(container) as scope:
            with pytest.raises(ValueError, match="Service not registered"):
                scope.get_scoped(ITestService)


class TestInjectableDecorator:
    """Injectable 데코레이터 테스트"""
    
    def test_injectable_decorator_adds_attribute(self):
        """Injectable 데코레이터가 속성을 추가하는지 테스트"""
        @injectable
        class TestInjectableService:
            pass
        
        assert hasattr(TestInjectableService, '_injectable')
        assert TestInjectableService._injectable is True
    
    def test_injectable_decorator_preserves_class(self):
        """Injectable 데코레이터가 클래스를 보존하는지 테스트"""
        @injectable
        class TestInjectableService:
            def method(self):
                return "test"
        
        instance = TestInjectableService()
        assert instance.method() == "test"
        assert TestInjectableService._injectable is True


class TestContainerErrorHandling:
    """컨테이너 에러 처리 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 새로운 컨테이너 생성"""
        self.container = DependencyContainer()
    
    def test_create_instance_with_complex_constructor(self):
        """복잡한 생성자를 가진 클래스 인스턴스 생성 테스트"""
        # 기본 타입 파라미터는 주입되지 않으므로 생성 실패
        with pytest.raises(Exception):
            self.container._create_instance(ComplexService)
    
    def test_create_instance_logging(self):
        """인스턴스 생성 시 로깅 테스트"""
        with patch('src.core.dependencies.logger') as mock_logger:
            instance = self.container._create_instance(TestService)
            
            # 로그가 호출되었는지 확인
            mock_logger.debug.assert_called()
            assert isinstance(instance, TestService)
    
    def test_register_methods_logging(self):
        """등록 메서드들의 로깅 테스트"""
        with patch('src.core.dependencies.logger') as mock_logger:
            self.container.register_singleton(ITestService, TestService)
            self.container.register_transient(ITestService, TestService)
            self.container.register_instance(ITestService, TestService())
            self.container.register_factory(ITestService, lambda: TestService())
            
            # 각 등록 메서드에서 로그가 호출되었는지 확인
            assert mock_logger.debug.call_count >= 4
    
    def test_clear_logging(self):
        """컨테이너 클리어 시 로깅 테스트"""
        with patch('src.core.dependencies.logger') as mock_logger:
            self.container.clear()
            
            mock_logger.debug.assert_called_with("Container cleared")


class TestGlobalContainer:
    """전역 컨테이너 테스트"""
    
    def test_get_container_returns_same_instance(self):
        """get_container가 동일한 인스턴스를 반환하는지 테스트"""
        container1 = get_container()
        container2 = get_container()
        
        assert container1 is container2
    
    def test_inject_function(self):
        """inject 함수 테스트"""
        container = get_container()
        container.clear()
        container.register_singleton(ITestService, TestService)
        
        service = inject(ITestService)
        assert isinstance(service, TestService)
        
        # 정리
        container.clear()


class TestDependencyContainerEdgeCases:
    """의존성 컨테이너 엣지 케이스 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 새로운 컨테이너 생성"""
        self.container = DependencyContainer()
    
    def test_get_with_class_factory(self):
        """클래스를 팩토리로 등록했을 때 테스트"""
        self.container.register_factory(ITestService, TestService)
        
        instance = self.container.get(ITestService)
        assert isinstance(instance, TestService)
    
    def test_get_with_function_factory(self):
        """함수를 팩토리로 등록했을 때 테스트"""
        def create_service():
            return TestService()
        
        self.container.register_factory(ITestService, create_service)
        
        instance = self.container.get(ITestService)
        assert isinstance(instance, TestService)
    
    def test_create_instance_with_no_type_hints(self):
        """타입 힌트가 없는 클래스 인스턴스 생성 테스트"""
        class ServiceWithoutHints:
            def __init__(self, param):
                self.param = param
        
        # 타입 힌트가 없으면 주입되지 않음
        with pytest.raises(TypeError):
            self.container._create_instance(ServiceWithoutHints)
    
    def test_create_instance_with_optional_parameters(self):
        """선택적 파라미터가 있는 클래스 인스턴스 생성 테스트"""
        class ServiceWithOptional:
            def __init__(self, required: ITestService, optional: str = "default"):
                self.required = required
                self.optional = optional
        
        self.container.register_singleton(ITestService, TestService)
        
        instance = self.container._create_instance(ServiceWithOptional)
        assert isinstance(instance, ServiceWithOptional)
        assert isinstance(instance.required, TestService)
        assert instance.optional == "default"
