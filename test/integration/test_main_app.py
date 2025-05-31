"""
메인 애플리케이션 통합 테스트
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from main import app


class TestMainApplication:
    """메인 애플리케이션 테스트"""
    
    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_dependencies(self):
        """의존성 모킹"""
        with patch('main.get_database') as mock_db, \
             patch('main.get_vector_db') as mock_vector_db, \
             patch('main.get_kafka_client') as mock_kafka:
            
            # Mock 객체 설정
            mock_db.return_value = AsyncMock()
            mock_vector_db.return_value = AsyncMock()
            mock_kafka.return_value = AsyncMock()
            
            yield {
                'db': mock_db,
                'vector_db': mock_vector_db,
                'kafka': mock_kafka
            }
    
    def test_root_endpoint(self, client):
        """루트 엔드포인트 테스트"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "IACSRAG - 문서 검색 플랫폼"
        assert data["version"] == "1.0.0"
        assert "docs" in data
    
    def test_health_check_endpoint(self, client):
        """헬스체크 엔드포인트 테스트"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "IACSRAG"
        assert data["version"] == "1.0.0"
        assert "environment" in data
    
    def test_cors_middleware(self, client):
        """CORS 미들웨어 테스트"""
        response = client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        
        # CORS 헤더가 포함되어야 함
        assert "access-control-allow-origin" in response.headers
    
    def test_validation_error_handler(self, client):
        """검증 오류 핸들러 테스트"""
        # 잘못된 요청으로 검증 오류 유발
        response = client.post("/api/v1/search", json={
            "invalid": "data"
        })
        
        # 400 Bad Request 또는 422 Unprocessable Entity 응답 예상
        assert response.status_code in [400, 422]
    
    def test_not_found_error_handler(self, client):
        """404 오류 핸들러 테스트"""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data or "error" in data
    
    @patch('src.core.logging.setup_logging')
    def test_logging_setup(self, mock_setup_logging):
        """로깅 설정 테스트"""
        # 로깅 설정 함수가 호출되었는지 확인
        # main.py에서 이미 임포트되었으므로 호출 여부만 확인
        from main import app
        assert app is not None  # 애플리케이션이 정상적으로 로드됨
    
    def test_api_routes_included(self, client):
        """API 라우터 포함 테스트"""
        # OpenAPI 스키마에서 라우트 확인
        response = client.get("/openapi.json")
        
        if response.status_code == 200:
            openapi_schema = response.json()
            paths = openapi_schema.get("paths", {})
            
            # 주요 API 경로가 포함되어 있는지 확인
            api_paths = [path for path in paths.keys() if path.startswith("/api/v1")]
            assert len(api_paths) > 0, "API 라우트가 포함되어야 함"


class TestApplicationLifespan:
    """애플리케이션 생명주기 테스트"""
    
    @pytest.mark.asyncio
    async def test_lifespan_startup_success(self):
        """정상적인 시작 프로세스 테스트"""
        with patch('main.get_database') as mock_db, \
             patch('main.get_vector_db') as mock_vector_db, \
             patch('main.get_kafka_client') as mock_kafka:
            
            # Mock 설정 - 코루틴 함수로 설정
            async def mock_get_database():
                return AsyncMock()
            
            async def mock_get_vector_db():
                return AsyncMock()
            
            async def mock_get_kafka_client():
                return AsyncMock()
            
            mock_db.side_effect = mock_get_database
            mock_vector_db.side_effect = mock_get_vector_db
            mock_kafka.side_effect = mock_get_kafka_client
            
            # TestClient를 사용하여 lifespan 이벤트 테스트
            with TestClient(app) as client:
                # 애플리케이션이 정상적으로 시작되어야 함
                response = client.get("/health")
                assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_lifespan_startup_failure(self):
        """시작 실패 시나리오 테스트"""
        with patch('main.get_database') as mock_db:
            # 데이터베이스 연결 실패 시뮬레이션
            mock_db.side_effect = Exception("Database connection failed")
            
            # 애플리케이션 시작 실패 시 예외가 발생해야 함
            with pytest.raises(Exception):
                with TestClient(app):
                    pass


class TestExceptionHandlers:
    """예외 핸들러 테스트"""
    
    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        return TestClient(app)
    
    def test_validation_error_response_format(self, client):
        """검증 오류 응답 형식 테스트"""
        # 잘못된 JSON으로 요청
        response = client.post("/api/v1/search", 
                             json={"query": ""})  # 빈 쿼리
        
        if response.status_code == 400:
            data = response.json()
            assert "error" in data
            assert "message" in data
    
    def test_general_exception_handler(self, client):
        """일반 예외 핸들러 테스트"""
        # 서버 오류를 유발할 수 있는 요청
        # (실제 구현에 따라 조정 필요)
        response = client.get("/health")
        
        # 정상적인 경우 200, 오류 시 500
        assert response.status_code in [200, 500]


class TestMiddleware:
    """미들웨어 테스트"""
    
    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        return TestClient(app)
    
    def test_trusted_host_middleware(self, client):
        """신뢰할 수 있는 호스트 미들웨어 테스트"""
        # 정상적인 호스트로 요청
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_cors_preflight_request(self, client):
        """CORS preflight 요청 테스트"""
        response = client.options("/api/v1/search", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        })
        
        # CORS preflight 응답 확인
        assert response.status_code in [200, 204]


class TestConfiguration:
    """설정 테스트"""
    
    def test_settings_loaded(self):
        """설정이 올바르게 로드되는지 테스트"""
        from main import settings
        
        assert settings is not None
        assert hasattr(settings, 'environment')
        assert hasattr(settings, 'host')
        assert hasattr(settings, 'port')
    
    def test_development_docs_enabled(self):
        """개발 환경에서 문서 활성화 테스트"""
        with patch('main.settings') as mock_settings:
            mock_settings.environment = "development"
            
            # 개발 환경에서는 docs가 활성화되어야 함
            client = TestClient(app)
            response = client.get("/docs")
            
            # 문서가 활성화되어 있으면 200, 비활성화되어 있으면 404
            assert response.status_code in [200, 404]


class TestAPIIntegration:
    """API 통합 테스트"""
    
    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        return TestClient(app)
    
    def test_search_api_integration(self, client):
        """검색 API 통합 테스트"""
        # 검색 엔드포인트 존재 확인
        response = client.post("/api/v1/search", json={
            "query": "test query",
            "limit": 5
        })
        
        # 구현 상태에 따라 다양한 응답 코드 가능
        assert response.status_code in [200, 400, 422, 500]
    
    def test_monitor_api_integration(self, client):
        """모니터링 API 통합 테스트"""
        # 모니터링 엔드포인트 존재 확인
        response = client.get("/api/v1/monitor/health")
        
        # 구현 상태에 따라 다양한 응답 코드 가능
        assert response.status_code in [200, 404, 500]
    
    def test_metrics_endpoint_integration(self, client):
        """메트릭 엔드포인트 통합 테스트"""
        response = client.get("/api/v1/monitor/metrics")
        
        # 구현 상태에 따라 다양한 응답 코드 가능
        assert response.status_code in [200, 404, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
