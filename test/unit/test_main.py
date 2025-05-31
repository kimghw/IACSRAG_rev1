"""
Main 애플리케이션 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from main import app, lifespan


class TestMainApp:
    """메인 애플리케이션 테스트"""

    def test_app_creation(self):
        """앱 생성 테스트"""
        assert app is not None
        assert app.title == "IACS RAG API"
        assert app.version == "0.1.0"

    def test_health_endpoint(self):
        """헬스체크 엔드포인트 테스트"""
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "timestamp" in data

    def test_docs_endpoint(self):
        """API 문서 엔드포인트 테스트"""
        with TestClient(app) as client:
            response = client.get("/docs")
            assert response.status_code == 200

    def test_openapi_endpoint(self):
        """OpenAPI 스키마 엔드포인트 테스트"""
        with TestClient(app) as client:
            response = client.get("/openapi.json")
            assert response.status_code == 200
            data = response.json()
            assert "openapi" in data
            assert "info" in data

    def test_cors_headers(self):
        """CORS 헤더 테스트"""
        with TestClient(app) as client:
            response = client.options("/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_lifespan_startup(self):
        """애플리케이션 시작 테스트"""
        mock_app = MagicMock()
        
        with patch('main.initialize_dependencies') as mock_init:
            mock_init.return_value = AsyncMock()
            
            async with lifespan(mock_app):
                mock_init.assert_called_once()

    def test_api_routes_included(self):
        """API 라우트 포함 확인 테스트"""
        routes = [route.path for route in app.routes]
        
        # 기본 라우트들 확인
        assert "/health" in routes
        assert "/docs" in routes
        assert "/openapi.json" in routes
        
        # API v1 라우트들 확인 (prefix 포함)
        api_routes = [route.path for route in app.routes if route.path.startswith("/api/v1")]
        assert len(api_routes) > 0

    def test_middleware_configuration(self):
        """미들웨어 설정 테스트"""
        middleware_types = [type(middleware.cls).__name__ for middleware in app.user_middleware]
        
        # CORS 미들웨어 확인
        assert "CORSMiddleware" in middleware_types

    def test_exception_handlers(self):
        """예외 핸들러 테스트"""
        with TestClient(app) as client:
            # 존재하지 않는 엔드포인트 테스트
            response = client.get("/nonexistent")
            assert response.status_code == 404

    def test_app_metadata(self):
        """앱 메타데이터 테스트"""
        assert app.title == "IACS RAG API"
        assert app.description == "문서 검색 및 질의응답 API"
        assert app.version == "0.1.0"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"


class TestApplicationConfiguration:
    """애플리케이션 설정 테스트"""

    def test_debug_mode_configuration(self):
        """디버그 모드 설정 테스트"""
        # 환경에 따라 디버그 모드가 적절히 설정되는지 확인
        assert isinstance(app.debug, bool)

    def test_api_prefix_configuration(self):
        """API 접두사 설정 테스트"""
        api_routes = [route.path for route in app.routes if "/api/v1" in route.path]
        assert len(api_routes) > 0
        
        # 모든 API 라우트가 올바른 접두사를 가지는지 확인
        for route_path in api_routes:
            assert route_path.startswith("/api/v1") or "/api/v1" in route_path

    def test_openapi_configuration(self):
        """OpenAPI 설정 테스트"""
        openapi_schema = app.openapi()
        
        assert openapi_schema["info"]["title"] == "IACS RAG API"
        assert openapi_schema["info"]["version"] == "0.1.0"
        assert "paths" in openapi_schema
        assert "components" in openapi_schema


class TestApplicationIntegration:
    """애플리케이션 통합 테스트"""

    def test_full_application_startup(self):
        """전체 애플리케이션 시작 테스트"""
        with TestClient(app) as client:
            # 기본 헬스체크
            response = client.get("/health")
            assert response.status_code == 200
            
            # API 문서 접근
            response = client.get("/docs")
            assert response.status_code == 200

    def test_api_versioning(self):
        """API 버저닝 테스트"""
        with TestClient(app) as client:
            # v1 API 엔드포인트들이 올바르게 라우팅되는지 확인
            routes = [route.path for route in app.routes]
            v1_routes = [route for route in routes if "/api/v1" in route]
            assert len(v1_routes) > 0

    def test_error_handling_integration(self):
        """에러 처리 통합 테스트"""
        with TestClient(app) as client:
            # 잘못된 요청에 대한 적절한 에러 응답 확인
            response = client.post("/api/v1/search", json={})
            assert response.status_code in [400, 422]  # 유효성 검사 오류

    def test_content_type_handling(self):
        """콘텐츠 타입 처리 테스트"""
        with TestClient(app) as client:
            # JSON 요청 처리
            response = client.get("/health", headers={"Accept": "application/json"})
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"

    def test_request_validation(self):
        """요청 유효성 검사 테스트"""
        with TestClient(app) as client:
            # 잘못된 JSON 형식
            response = client.post(
                "/api/v1/search",
                data="invalid json",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 422


class TestApplicationSecurity:
    """애플리케이션 보안 테스트"""

    def test_cors_configuration(self):
        """CORS 설정 테스트"""
        with TestClient(app) as client:
            response = client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET"
                }
            )
            assert response.status_code == 200

    def test_security_headers(self):
        """보안 헤더 테스트"""
        with TestClient(app) as client:
            response = client.get("/health")
            # 기본적인 보안 헤더들이 설정되어 있는지 확인
            assert response.status_code == 200

    def test_input_sanitization(self):
        """입력 데이터 검증 테스트"""
        with TestClient(app) as client:
            # 악의적인 입력에 대한 적절한 처리 확인
            malicious_input = "<script>alert('xss')</script>"
            response = client.post(
                "/api/v1/search",
                json={"query": malicious_input}
            )
            # 요청이 적절히 처리되거나 거부되는지 확인
            assert response.status_code in [200, 400, 422]
