"""
의존성 주입 모듈 단위 테스트
"""

import pytest
from abc import ABC, abstractmethod
from typing import Protocol

from src.core.dependencies import (
    DependencyContainer,
    ServiceCollection,
    ServiceDescriptor,
    ServiceLifetime,
    DependencyScope,
    get_container,
    inject,
    injectable,
    auto_inject
)


# 테스트용 인터페이스와 구현체들
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


class ServiceWithDependency:
    def __init__(self, repository: IRepository):
        self.repository = repository
    
    def process(self, data: str) -> bool:
        return self.repository.save(data)


class ServiceWithMultipleDependencies:
    def __init__(self, service: ITestService, repository: IRepository):
        self.service = service
        self.repository = repository
    
    def execute(self) -> str:
        value = self.service.get_value()
        self.repository.save(value)
        return value


class ServiceWithOptionalDependency:
    def __init__(self, service: ITestService, optional_param: str = "default"):
        self.service = service
        self.optional_param = optional_param


class TestDependencyContainer:
    """의존성 컨테이너 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 새로운 컨테이너 생성"""
        self.container = DependencyContainer()
    
    def test_register_and_get_instance(self):
        """인스턴스 등록 및 조회 테스트"""
        service = TestService()
        self.container.register_instance(ITestService, service)
        
        retrieved = self.container.get(ITestService)
        assert retrieved is service
    
    def test_register_and_get_singleton(self):
        """싱글톤 등록 및 조회 테스트"""
        self.container.register_singleton(ITestService, TestService)
        
        instance1 = self.container.get(ITestService)
        instance2 = self.container.get(ITestService)
        
        assert isinstance(instance1, TestService)
        assert instance1 is instance2  # 같은 인스턴스여야 함
    
    def test_register_and_get_transient(self):
        """일시적 서비스 등록 및 조회 테스트"""
        self.container.register_transient(ITestService, TestService)
        
        instance1 = self.container.get(ITestService)
        instance2 = self.container.get(ITestService)
        
        assert isinstance(instance1, TestService)
        assert isinstance(instance2, TestService)
        assert instance1 is not instance2  # 다른 인스턴스여야 함
    
    def test_register_factory(self):
        """팩토리 함수 등록 테스트"""
        def create_service() -> ITestService:
            return TestService()
        
        self.container.register_factory(ITestService, create_service)
        
        instance = self.container.get(ITestService)
        assert isinstance(instance, TestService)
    
    def test_dependency_injection(self):
        """의존성 주입 테스트"""
        self.container.register_singleton(IRepository, TestRepository)
        self.container.register_transient(ServiceWithDependency, ServiceWithDependency)
        
        service = self.container.get(ServiceWithDependency)
        
        assert isinstance(service, ServiceWithDependency)
        assert isinstance(service.repository, TestRepository)
        assert service.process("test_data") is True
    
    def test_multiple_dependencies(self):
        """다중 의존성 주입 테스트"""
        self.container.register_singleton(ITestService, TestService)
        self.container.register_singleton(IRepository, TestRepository)
        self.container.register_transient(ServiceWithMultipleDependencies, ServiceWithMultipleDependencies)
        
        service = self.container.get(ServiceWithMultipleDependencies)
        
        assert isinstance(service, ServiceWithMultipleDependencies)
        assert isinstance(service.service, TestService)
        assert isinstance(service.repository, TestRepository)
        assert service.execute() == "test_value"
    
    def test_optional_dependency(self):
        """선택적 의존성 테스트"""
        self.container.register_singleton(ITestService, TestService)
        self.container.register_transient(ServiceWithOptionalDependency, ServiceWithOptionalDependency)
        
        service = self.container.get(ServiceWithOptionalDependency)
        
        assert isinstance(service, ServiceWithOptionalDependency)
        assert isinstance(service.service, TestService)
        assert service.optional_param == "default"
    
    def test_service_not_registered_error(self):
        """등록되지 않은 서비스 조회 시 에러 테스트"""
        with pytest.raises(ValueError, match="Service not registered"):
            self.container.get(ITestService)
    
    def test_clear_container(self):
        """컨테이너 초기화 테스트"""
        self.container.register_instance(ITestService, TestService())
        assert len(self.container._services) > 0
        
        self.container.clear()
        assert len(self.container._services) == 0
        assert len(self.container._factories) == 0
        assert len(self.container._singletons) == 0
        assert len(self.container._interfaces) == 0


class TestServiceCollection:
    """서비스 컬렉션 테스트"""
    
    def test_add_singleton(self):
        """싱글톤 서비스 추가 테스트"""
        collection = ServiceCollection()
        collection.add_singleton(ITestService, TestService)
        
        container = collection.build_container()
        
        instance1 = container.get(ITestService)
        instance2 = container.get(ITestService)
        
        assert instance1 is instance2
    
    def test_add_transient(self):
        """일시적 서비스 추가 테스트"""
        collection = ServiceCollection()
        collection.add_transient(ITestService, TestService)
        
        container = collection.build_container()
        
        instance1 = container.get(ITestService)
        instance2 = container.get(ITestService)
        
        assert instance1 is not instance2
    
    def test_add_instance(self):
        """인스턴스 추가 테스트"""
        service = TestService()
        collection = ServiceCollection()
        collection.add_instance(ITestService, service)
        
        container = collection.build_container()
        
        retrieved = container.get(ITestService)
        assert retrieved is service
    
    def test_add_factory(self):
        """팩토리 추가 테스트"""
        def create_service() -> ITestService:
            return TestService()
        
        collection = ServiceCollection()
        collection.add_factory(ITestService, create_service)
        
        container = collection.build_container()
        
        instance = container.get(ITestService)
        assert isinstance(instance, TestService)
    
    def test_fluent_interface(self):
        """플루언트 인터페이스 테스트"""
        collection = (ServiceCollection()
                     .add_singleton(ITestService, TestService)
                     .add_transient(IRepository, TestRepository))
        
        container = collection.build_container()
        
        service = container.get(ITestService)
        repository = container.get(IRepository)
        
        assert isinstance(service, TestService)
        assert isinstance(repository, TestRepository)


class TestServiceDescriptor:
    """서비스 디스크립터 테스트"""
    
    def test_singleton_descriptor(self):
        """싱글톤 디스크립터 테스트"""
        descriptor = ServiceDescriptor(
            interface=ITestService,
            implementation=TestService,
            lifetime=ServiceLifetime.SINGLETON
        )
        
        container = DependencyContainer()
        descriptor.register_to(container)
        
        instance1 = container.get(ITestService)
        instance2 = container.get(ITestService)
        
        assert instance1 is instance2
    
    def test_transient_descriptor(self):
        """일시적 디스크립터 테스트"""
        descriptor = ServiceDescriptor(
            interface=ITestService,
            implementation=TestService,
            lifetime=ServiceLifetime.TRANSIENT
        )
        
        container = DependencyContainer()
        descriptor.register_to(container)
        
        instance1 = container.get(ITestService)
        instance2 = container.get(ITestService)
        
        assert instance1 is not instance2
    
    def test_instance_descriptor(self):
        """인스턴스 디스크립터 테스트"""
        service = TestService()
        descriptor = ServiceDescriptor(
            interface=ITestService,
            instance=service
        )
        
        container = DependencyContainer()
        descriptor.register_to(container)
        
        retrieved = container.get(ITestService)
        assert retrieved is service
    
    def test_factory_descriptor(self):
        """팩토리 디스크립터 테스트"""
        def create_service() -> ITestService:
            return TestService()
        
        descriptor = ServiceDescriptor(
            interface=ITestService,
            factory=create_service
        )
        
        container = DependencyContainer()
        descriptor.register_to(container)
        
        instance = container.get(ITestService)
        assert isinstance(instance, TestService)
    
    def test_invalid_descriptor(self):
        """잘못된 디스크립터 테스트"""
        descriptor = ServiceDescriptor(interface=ITestService)
        container = DependencyContainer()
        
        with pytest.raises(ValueError, match="No implementation, factory, or instance provided"):
            descriptor.register_to(container)


class TestDecorators:
    """데코레이터 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 컨테이너 초기화"""
        container = get_container()
        container.clear()
    
    def test_injectable_decorator(self):
        """주입 가능 데코레이터 테스트"""
        @injectable
        class InjectableService:
            def get_data(self) -> str:
                return "injectable_data"
        
        assert hasattr(InjectableService, '_injectable')
        assert InjectableService._injectable is True
    
    def test_auto_inject_decorator(self):
        """자동 주입 데코레이터 테스트"""
        container = get_container()
        container.register_singleton(ITestService, TestService)
        
        @auto_inject
        def process_with_service(data: str, service: ITestService) -> str:
            return f"{data}_{service.get_value()}"
        
        result = process_with_service("input")
        assert result == "input_test_value"
    
    def test_auto_inject_with_provided_args(self):
        """제공된 인자가 있는 자동 주입 테스트"""
        container = get_container()
        container.register_singleton(ITestService, TestService)
        
        @auto_inject
        def process_with_service(data: str, service: ITestService) -> str:
            return f"{data}_{service.get_value()}"
        
        custom_service = TestService()
        result = process_with_service("input", custom_service)
        assert result == "input_test_value"
    
    def test_inject_helper_function(self):
        """주입 헬퍼 함수 테스트"""
        container = get_container()
        container.register_singleton(ITestService, TestService)
        
        service = inject(ITestService)
        assert isinstance(service, TestService)
        assert service.get_value() == "test_value"


class TestDependencyScope:
    """의존성 스코프 테스트"""
    
    def test_scoped_instances(self):
        """스코프된 인스턴스 테스트"""
        container = DependencyContainer()
        container.register_transient(ITestService, TestService)
        
        with DependencyScope(container) as scope:
            instance1 = scope.get_scoped(ITestService)
            instance2 = scope.get_scoped(ITestService)
            
            # 같은 스코프 내에서는 같은 인스턴스
            assert instance1 is instance2
        
        # 새로운 스코프에서는 다른 인스턴스
        with DependencyScope(container) as scope:
            instance3 = scope.get_scoped(ITestService)
            assert instance3 is not instance1


class TestIntegration:
    """통합 테스트"""
    
    def test_complex_dependency_graph(self):
        """복잡한 의존성 그래프 테스트"""
        collection = (ServiceCollection()
                     .add_singleton(ITestService, TestService)
                     .add_singleton(IRepository, TestRepository)
                     .add_transient(ServiceWithDependency, ServiceWithDependency)
                     .add_transient(ServiceWithMultipleDependencies, ServiceWithMultipleDependencies))
        
        container = collection.build_container()
        
        # 단일 의존성 서비스
        service1 = container.get(ServiceWithDependency)
        assert isinstance(service1, ServiceWithDependency)
        assert service1.process("test") is True
        
        # 다중 의존성 서비스
        service2 = container.get(ServiceWithMultipleDependencies)
        assert isinstance(service2, ServiceWithMultipleDependencies)
        assert service2.execute() == "test_value"
        
        # 싱글톤 확인
        service3 = container.get(ServiceWithDependency)
        assert service1.repository is service3.repository  # 같은 싱글톤 인스턴스
