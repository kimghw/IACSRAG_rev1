"""
의존성 주입 컨테이너 및 관리
"""

from typing import Any, Dict, Type, TypeVar, Callable, Optional, get_type_hints
from abc import ABC, abstractmethod
import inspect
from functools import wraps

from .logging import LoggerMixin, get_logger

T = TypeVar('T')

logger = get_logger(__name__)


class DependencyContainer:
    """의존성 주입 컨테이너"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._interfaces: Dict[Type, Type] = {}
    
    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> None:
        """싱글톤으로 서비스 등록"""
        key = self._get_key(interface)
        self._interfaces[interface] = implementation
        logger.debug(f"Registered singleton: {key} -> {implementation.__name__}")
    
    def register_transient(self, interface: Type[T], implementation: Type[T]) -> None:
        """일시적(Transient) 서비스 등록"""
        key = self._get_key(interface)
        self._factories[key] = implementation
        logger.debug(f"Registered transient: {key} -> {implementation.__name__}")
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """인스턴스 직접 등록"""
        key = self._get_key(interface)
        self._services[key] = instance
        logger.debug(f"Registered instance: {key}")
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """팩토리 함수 등록"""
        key = self._get_key(interface)
        self._factories[key] = factory
        logger.debug(f"Registered factory: {key}")
    
    def get(self, interface: Type[T]) -> T:
        """서비스 인스턴스 반환"""
        key = self._get_key(interface)
        
        # 직접 등록된 인스턴스 확인
        if key in self._services:
            return self._services[key]
        
        # 싱글톤 캐시 확인
        if key in self._singletons:
            return self._singletons[key]
        
        # 팩토리 또는 구현체로 생성
        if key in self._factories:
            factory_or_class = self._factories[key]
            
            if inspect.isclass(factory_or_class):
                # 클래스인 경우 의존성 주입으로 생성
                instance = self._create_instance(factory_or_class)
            else:
                # 팩토리 함수인 경우 직접 호출
                instance = factory_or_class()
            
            return instance
        
        # 인터페이스에 등록된 구현체 확인
        if interface in self._interfaces:
            implementation = self._interfaces[interface]
            instance = self._create_instance(implementation)
            
            # 싱글톤으로 캐시
            self._singletons[key] = instance
            return instance
        
        raise ValueError(f"Service not registered: {interface}")
    
    def _create_instance(self, cls: Type[T]) -> T:
        """의존성 주입으로 인스턴스 생성"""
        try:
            # 생성자 시그니처 분석
            signature = inspect.signature(cls.__init__)
            type_hints = get_type_hints(cls.__init__)
            
            kwargs = {}
            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue
                
                # 기본값이 있는 경우 먼저 확인
                if param.default is not param.empty:
                    # 기본값이 있는 파라미터는 주입하지 않음
                    continue
                
                # 타입 힌트가 있는 경우 의존성 주입
                if param_name in type_hints:
                    param_type = type_hints[param_name]
                    # 기본 타입들은 주입하지 않음
                    if param_type in (str, int, float, bool, list, dict, tuple, set):
                        logger.warning(f"Skipping injection for basic type '{param_type.__name__}' in parameter '{param_name}' of {cls.__name__}")
                        continue
                    
                    try:
                        kwargs[param_name] = self.get(param_type)
                    except ValueError:
                        logger.warning(f"Cannot inject dependency for parameter '{param_name}' of type '{param_type}' in {cls.__name__}")
                        continue
                else:
                    logger.warning(f"No type hint for parameter '{param_name}' in {cls.__name__}")
            
            instance = cls(**kwargs)
            logger.debug(f"Created instance: {cls.__name__}")
            return instance
            
        except Exception as e:
            logger.error(f"Failed to create instance of {cls.__name__}: {e}")
            raise
    
    def _get_key(self, interface: Type) -> str:
        """인터페이스에서 키 생성"""
        return f"{interface.__module__}.{interface.__name__}"
    
    def clear(self) -> None:
        """모든 등록된 서비스 제거"""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        self._interfaces.clear()
        logger.debug("Container cleared")


# 전역 컨테이너 인스턴스
_container = DependencyContainer()


def get_container() -> DependencyContainer:
    """전역 컨테이너 반환"""
    return _container


def inject(interface: Type[T]) -> T:
    """의존성 주입 헬퍼 함수"""
    return _container.get(interface)


def injectable(cls: Type[T]) -> Type[T]:
    """클래스를 주입 가능하도록 마킹하는 데코레이터"""
    cls._injectable = True
    return cls


def auto_inject(func: Callable) -> Callable:
    """함수 파라미터에 자동 의존성 주입하는 데코레이터"""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 함수 시그니처 분석
        signature = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        # 누락된 파라미터에 대해 의존성 주입
        bound_args = signature.bind_partial(*args, **kwargs)
        
        for param_name, param in signature.parameters.items():
            if param_name not in bound_args.arguments:
                if param_name in type_hints:
                    param_type = type_hints[param_name]
                    try:
                        injected_value = _container.get(param_type)
                        bound_args.arguments[param_name] = injected_value
                    except ValueError:
                        # 주입할 수 없는 경우 기본값 사용 또는 에러
                        if param.default is not param.empty:
                            bound_args.arguments[param_name] = param.default
                        else:
                            raise ValueError(f"Cannot inject dependency for parameter '{param_name}'")
        
        return func(*bound_args.args, **bound_args.kwargs)
    
    return wrapper


class ServiceLifetime:
    """서비스 생명주기 열거형"""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"  # 향후 구현 예정


class ServiceDescriptor:
    """서비스 등록 정보"""
    
    def __init__(
        self,
        interface: Type,
        implementation: Type = None,
        factory: Callable = None,
        instance: Any = None,
        lifetime: str = ServiceLifetime.TRANSIENT
    ):
        self.interface = interface
        self.implementation = implementation
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime
    
    def register_to(self, container: DependencyContainer) -> None:
        """컨테이너에 서비스 등록"""
        if self.instance is not None:
            container.register_instance(self.interface, self.instance)
        elif self.factory is not None:
            container.register_factory(self.interface, self.factory)
        elif self.implementation is not None:
            if self.lifetime == ServiceLifetime.SINGLETON:
                container.register_singleton(self.interface, self.implementation)
            else:
                container.register_transient(self.interface, self.implementation)
        else:
            raise ValueError("No implementation, factory, or instance provided")


class ServiceCollection:
    """서비스 컬렉션 빌더"""
    
    def __init__(self):
        self._descriptors: list[ServiceDescriptor] = []
    
    def add_singleton(self, interface: Type[T], implementation: Type[T] = None) -> 'ServiceCollection':
        """싱글톤 서비스 추가"""
        impl = implementation or interface
        descriptor = ServiceDescriptor(
            interface=interface,
            implementation=impl,
            lifetime=ServiceLifetime.SINGLETON
        )
        self._descriptors.append(descriptor)
        return self
    
    def add_transient(self, interface: Type[T], implementation: Type[T] = None) -> 'ServiceCollection':
        """일시적 서비스 추가"""
        impl = implementation or interface
        descriptor = ServiceDescriptor(
            interface=interface,
            implementation=impl,
            lifetime=ServiceLifetime.TRANSIENT
        )
        self._descriptors.append(descriptor)
        return self
    
    def add_instance(self, interface: Type[T], instance: T) -> 'ServiceCollection':
        """인스턴스 직접 추가"""
        descriptor = ServiceDescriptor(
            interface=interface,
            instance=instance
        )
        self._descriptors.append(descriptor)
        return self
    
    def add_factory(self, interface: Type[T], factory: Callable[[], T]) -> 'ServiceCollection':
        """팩토리 함수 추가"""
        descriptor = ServiceDescriptor(
            interface=interface,
            factory=factory
        )
        self._descriptors.append(descriptor)
        return self
    
    def build_container(self) -> DependencyContainer:
        """컨테이너 빌드"""
        container = DependencyContainer()
        
        for descriptor in self._descriptors:
            descriptor.register_to(container)
        
        logger.info(f"Built container with {len(self._descriptors)} services")
        return container


# 컨텍스트 매니저를 위한 스코프 관리 (향후 확장용)
class DependencyScope:
    """의존성 스코프 관리"""
    
    def __init__(self, container: DependencyContainer):
        self.container = container
        self._scoped_instances: Dict[str, Any] = {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._scoped_instances.clear()
    
    def get_scoped(self, interface: Type[T]) -> T:
        """스코프된 인스턴스 반환"""
        key = self.container._get_key(interface)
        
        if key not in self._scoped_instances:
            self._scoped_instances[key] = self.container.get(interface)
        
        return self._scoped_instances[key]
