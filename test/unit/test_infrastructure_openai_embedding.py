"""
OpenAI 임베딩 서비스 단위 테스트
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import List, Dict, Any

from src.core.config import Settings
from src.core.exceptions import EmbeddingServiceError, ConfigurationError
from src.infrastructure.embeddings.openai_embedding_service import OpenAIEmbeddingService
from src.modules.process.domain.entities import EmbeddingResult


class TestOpenAIEmbeddingService:
    """OpenAI 임베딩 서비스 테스트"""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock 설정"""
        settings = Mock(spec=Settings)
        settings.openai_api_key = "test-api-key"
        settings.openai_embedding_model = "text-embedding-3-small"
        return settings
    
    @pytest.fixture
    def invalid_settings(self):
        """잘못된 설정"""
        settings = Mock(spec=Settings)
        settings.openai_api_key = ""
        settings.openai_embedding_model = ""
        return settings
    
    @pytest.fixture
    def sample_texts(self):
        """샘플 텍스트 목록"""
        return [
            "This is a sample text for embedding.",
            "Another text to test the embedding service.",
            "Third text for comprehensive testing."
        ]
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API 응답"""
        mock_response = Mock()
        mock_response.data = []
        
        for i in range(3):
            embedding_data = Mock()
            embedding_data.index = i
            embedding_data.embedding = [0.1 + i * 0.1] * 1536  # 1536차원 벡터
            mock_response.data.append(embedding_data)
        
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.total_tokens = 50
        
        return mock_response
    
    @pytest.fixture
    def mock_health_check_response(self):
        """Health check용 Mock OpenAI API 응답"""
        mock_response = Mock()
        mock_response.data = []
        
        embedding_data = Mock()
        embedding_data.index = 0
        embedding_data.embedding = [0.1] * 1536
        mock_response.data.append(embedding_data)
        
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.total_tokens = 10
        
        return mock_response
    
    def test_init_with_valid_settings(self, mock_settings):
        """유효한 설정으로 초기화 테스트"""
        # When
        service = OpenAIEmbeddingService(mock_settings)
        
        # Then
        assert service.settings == mock_settings
        assert service.model == "text-embedding-3-small"
        assert service.max_batch_size == 100
        assert service.max_tokens_per_request == 8191
    
    def test_init_with_invalid_api_key(self, invalid_settings):
        """잘못된 API 키로 초기화 시 오류 테스트"""
        # When & Then
        with pytest.raises(ConfigurationError, match="OpenAI API key is required"):
            OpenAIEmbeddingService(invalid_settings)
    
    def test_init_with_invalid_model(self, mock_settings):
        """잘못된 모델로 초기화 시 오류 테스트"""
        # Given
        mock_settings.openai_embedding_model = ""
        
        # When & Then
        with pytest.raises(ConfigurationError, match="OpenAI embedding model is required"):
            OpenAIEmbeddingService(mock_settings)
    
    @patch('src.infrastructure.embeddings.openai_embedding_service.AsyncOpenAI')
    async def test_generate_embeddings_success(
        self,
        mock_openai_client,
        mock_settings,
        sample_texts,
        mock_openai_response
    ):
        """정상적인 임베딩 생성 테스트"""
        # Given
        mock_client_instance = AsyncMock()
        mock_openai_client.return_value = mock_client_instance
        mock_client_instance.embeddings.create.return_value = mock_openai_response
        
        service = OpenAIEmbeddingService(mock_settings)
        service.client = mock_client_instance
        
        # When
        results = await service.generate_embeddings(sample_texts)
        
        # Then
        assert len(results) == 3
        for i, result in enumerate(results):
            assert isinstance(result, EmbeddingResult)
            assert result.text == sample_texts[i]
            assert len(result.vector) == 1536
            assert result.model == "text-embedding-3-small"
            assert result.dimensions == 1536
            assert "index" in result.metadata
            assert "usage" in result.metadata
        
        # API 호출 검증
        mock_client_instance.embeddings.create.assert_called_once_with(
            input=sample_texts,
            model="text-embedding-3-small",
            encoding_format="float"
        )
    
    @patch('src.infrastructure.embeddings.openai_embedding_service.AsyncOpenAI')
    async def test_generate_embeddings_empty_input(
        self,
        mock_openai_client,
        mock_settings
    ):
        """빈 입력으로 임베딩 생성 테스트"""
        # Given
        service = OpenAIEmbeddingService(mock_settings)
        
        # When
        results = await service.generate_embeddings([])
        
        # Then
        assert results == []
    
    @patch('src.infrastructure.embeddings.openai_embedding_service.AsyncOpenAI')
    async def test_generate_embeddings_with_custom_model(
        self,
        mock_openai_client,
        mock_settings,
        sample_texts,
        mock_openai_response
    ):
        """커스텀 모델로 임베딩 생성 테스트"""
        # Given
        mock_client_instance = AsyncMock()
        mock_openai_client.return_value = mock_client_instance
        mock_client_instance.embeddings.create.return_value = mock_openai_response
        
        service = OpenAIEmbeddingService(mock_settings)
        service.client = mock_client_instance
        
        # When
        results = await service.generate_embeddings(
            sample_texts,
            model_name="text-embedding-3-large"
        )
        
        # Then
        assert len(results) == 3
        
        # 커스텀 모델로 API 호출 검증
        mock_client_instance.embeddings.create.assert_called_once_with(
            input=sample_texts,
            model="text-embedding-3-large",
            encoding_format="float"
        )
    
    @patch('src.infrastructure.embeddings.openai_embedding_service.AsyncOpenAI')
    async def test_generate_embeddings_batch_processing(
        self,
        mock_openai_client,
        mock_settings
    ):
        """배치 처리 테스트"""
        # Given
        mock_client_instance = AsyncMock()
        mock_openai_client.return_value = mock_client_instance
        
        # 120개 텍스트 생성 (배치 크기 50보다 큰 수)
        large_texts = [f"Text {i}" for i in range(120)]
        
        # 배치별 응답 설정
        def create_mock_response(batch_size):
            mock_response = Mock()
            mock_response.data = []
            for i in range(batch_size):
                embedding_data = Mock()
                embedding_data.index = i
                embedding_data.embedding = [0.1] * 1536
                mock_response.data.append(embedding_data)
            mock_response.usage = Mock()
            mock_response.usage.prompt_tokens = batch_size * 10
            mock_response.usage.total_tokens = batch_size * 10
            return mock_response
        
        # 3번의 배치 호출 (50, 50, 20)
        mock_client_instance.embeddings.create.side_effect = [
            create_mock_response(50),
            create_mock_response(50),
            create_mock_response(20)
        ]
        
        service = OpenAIEmbeddingService(mock_settings)
        service.client = mock_client_instance
        
        # When
        results = await service.generate_embeddings(large_texts, batch_size=50)
        
        # Then
        assert len(results) == 120
        assert mock_client_instance.embeddings.create.call_count == 3
    
    @patch('src.infrastructure.embeddings.openai_embedding_service.AsyncOpenAI')
    async def test_generate_embeddings_rate_limit_retry(
        self,
        mock_openai_client,
        mock_settings,
        sample_texts,
        mock_openai_response
    ):
        """레이트 리미트 재시도 테스트"""
        # Given
        import openai
        
        mock_client_instance = AsyncMock()
        mock_openai_client.return_value = mock_client_instance
        
        # 첫 번째 호출은 레이트 리미트 오류, 두 번째는 성공
        mock_client_instance.embeddings.create.side_effect = [
            openai.RateLimitError("Rate limit exceeded", response=Mock(), body=None),
            mock_openai_response
        ]
        
        service = OpenAIEmbeddingService(mock_settings)
        service.client = mock_client_instance
        
        # When
        results = await service.generate_embeddings(sample_texts)
        
        # Then
        assert len(results) == 3
        assert mock_client_instance.embeddings.create.call_count == 2
    
    @patch('src.infrastructure.embeddings.openai_embedding_service.AsyncOpenAI')
    async def test_generate_embeddings_api_error(
        self,
        mock_openai_client,
        mock_settings,
        sample_texts
    ):
        """API 오류 시 예외 처리 테스트"""
        # Given
        import openai
        
        mock_client_instance = AsyncMock()
        mock_openai_client.return_value = mock_client_instance
        # OpenAI APIError는 message만 필요
        mock_client_instance.embeddings.create.side_effect = Exception("API Error")
        
        service = OpenAIEmbeddingService(mock_settings)
        service.client = mock_client_instance
        
        # When & Then
        with pytest.raises(EmbeddingServiceError, match="Embedding generation failed"):
            await service.generate_embeddings(sample_texts)
    
    def test_validate_token_limits(self, mock_settings):
        """토큰 수 제한 검증 테스트"""
        # Given
        service = OpenAIEmbeddingService(mock_settings)
        
        # 긴 텍스트 생성 (토큰 제한 초과)
        long_text = " ".join(["word"] * 10000)  # 약 13000 토큰
        short_text = "Short text"
        
        texts = [long_text, short_text]
        
        # When
        validated_texts = service._validate_token_limits(texts)
        
        # Then
        assert len(validated_texts) == 2
        assert len(validated_texts[0].split()) < len(long_text.split())  # 잘림
        assert validated_texts[1] == short_text  # 변경 없음
    
    async def test_get_embedding_dimensions(self, mock_settings):
        """임베딩 차원 수 반환 테스트"""
        # Given
        service = OpenAIEmbeddingService(mock_settings)
        
        # When & Then
        assert await service.get_embedding_dimensions() == 1536  # 기본 모델
        assert await service.get_embedding_dimensions("text-embedding-3-small") == 1536
        assert await service.get_embedding_dimensions("text-embedding-3-large") == 3072
        assert await service.get_embedding_dimensions("text-embedding-ada-002") == 1536
        assert await service.get_embedding_dimensions("unknown-model") == 1536  # 기본값
    
    @patch('src.infrastructure.embeddings.openai_embedding_service.AsyncOpenAI')
    async def test_health_check_success(
        self,
        mock_openai_client,
        mock_settings,
        mock_health_check_response
    ):
        """정상 상태 확인 테스트"""
        # Given
        mock_client_instance = AsyncMock()
        mock_openai_client.return_value = mock_client_instance
        mock_client_instance.embeddings.create.return_value = mock_health_check_response
        
        service = OpenAIEmbeddingService(mock_settings)
        service.client = mock_client_instance
        
        # When
        health_status = await service.health_check()
        
        # Then
        assert health_status["status"] == "healthy"
        assert health_status["model"] == "text-embedding-3-small"
        assert health_status["dimensions"] == 1536
        assert health_status["test_embedding_generated"] is True
    
    @patch('src.infrastructure.embeddings.openai_embedding_service.AsyncOpenAI')
    async def test_health_check_failure(
        self,
        mock_openai_client,
        mock_settings
    ):
        """상태 확인 실패 테스트"""
        # Given
        mock_client_instance = AsyncMock()
        mock_openai_client.return_value = mock_client_instance
        mock_client_instance.embeddings.create.side_effect = Exception("Connection failed")
        
        service = OpenAIEmbeddingService(mock_settings)
        service.client = mock_client_instance
        
        # When
        health_status = await service.health_check()
        
        # Then
        assert health_status["status"] == "unhealthy"
        assert "error" in health_status
        assert health_status["model"] == "text-embedding-3-small"
    
    async def test_get_supported_models(self, mock_settings):
        """지원되는 모델 목록 반환 테스트"""
        # Given
        service = OpenAIEmbeddingService(mock_settings)
        
        # When
        models = await service.get_supported_models()
        
        # Then
        expected_models = [
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002"
        ]
        assert models == expected_models
    
    @patch('src.infrastructure.embeddings.openai_embedding_service.AsyncOpenAI')
    async def test_close(self, mock_openai_client, mock_settings):
        """리소스 정리 테스트"""
        # Given
        mock_client_instance = AsyncMock()
        mock_openai_client.return_value = mock_client_instance
        
        service = OpenAIEmbeddingService(mock_settings)
        service.client = mock_client_instance
        
        # When
        await service.close()
        
        # Then
        mock_client_instance.close.assert_called_once()
    
    @patch('src.infrastructure.embeddings.openai_embedding_service.AsyncOpenAI')
    async def test_generate_embeddings_unexpected_error(
        self,
        mock_openai_client,
        mock_settings,
        sample_texts
    ):
        """예상치 못한 오류 처리 테스트"""
        # Given
        mock_client_instance = AsyncMock()
        mock_openai_client.return_value = mock_client_instance
        mock_client_instance.embeddings.create.side_effect = RuntimeError("Unexpected error")
        
        service = OpenAIEmbeddingService(mock_settings)
        service.client = mock_client_instance
        
        # When & Then
        with pytest.raises(EmbeddingServiceError, match="Embedding generation failed"):
            await service.generate_embeddings(sample_texts)
    
    def test_validate_config_missing_api_key(self):
        """API 키 누락 시 설정 검증 테스트"""
        # Given
        settings = Mock(spec=Settings)
        settings.openai_api_key = None
        settings.openai_embedding_model = "text-embedding-3-small"
        
        # When & Then
        with pytest.raises(ConfigurationError, match="OpenAI API key is required"):
            OpenAIEmbeddingService(settings)
    
    def test_validate_config_missing_model(self):
        """모델명 누락 시 설정 검증 테스트"""
        # Given
        settings = Mock(spec=Settings)
        settings.openai_api_key = "test-key"
        settings.openai_embedding_model = None
        
        # When & Then
        with pytest.raises(ConfigurationError, match="OpenAI embedding model is required"):
            OpenAIEmbeddingService(settings)


class TestOpenAIEmbeddingServiceIntegration:
    """OpenAI 임베딩 서비스 통합 테스트 (실제 API 호출 시뮬레이션)"""
    
    @pytest.fixture
    def real_settings(self):
        """실제 설정 (테스트용)"""
        settings = Mock(spec=Settings)
        settings.openai_api_key = "sk-test-key-for-testing"
        settings.openai_embedding_model = "text-embedding-3-small"
        return settings
    
    @pytest.mark.asyncio
    async def test_full_workflow_simulation(self, real_settings):
        """전체 워크플로우 시뮬레이션 테스트"""
        # Given
        service = OpenAIEmbeddingService(real_settings)
        
        # Mock 클라이언트로 교체 (실제 API 호출 방지)
        mock_client = AsyncMock()
        service.client = mock_client
        
        # Mock 응답 설정 - 두 번의 호출을 위해 다른 응답 준비
        def create_mock_response(text_count):
            mock_response = Mock()
            mock_response.data = []
            for i in range(text_count):
                embedding_data = Mock()
                embedding_data.index = i
                embedding_data.embedding = [0.1 + i * 0.1] * 1536
                mock_response.data.append(embedding_data)
            
            mock_response.usage = Mock()
            mock_response.usage.prompt_tokens = text_count * 10
            mock_response.usage.total_tokens = text_count * 10
            return mock_response
        
        # 첫 번째 호출(generate_embeddings)과 두 번째 호출(health_check)을 위한 응답
        mock_client.embeddings.create.side_effect = [
            create_mock_response(2),  # generate_embeddings 호출
            create_mock_response(1)   # health_check 호출
        ]
        
        texts = ["Hello world", "Test embedding"]
        
        # When
        results = await service.generate_embeddings(texts)
        
        # Then
        assert len(results) == 2
        assert all(isinstance(r, EmbeddingResult) for r in results)
        assert all(len(r.vector) == 1536 for r in results)
        assert all(r.model == "text-embedding-3-small" for r in results)
        
        # 상태 확인
        health_status = await service.health_check()
        assert health_status["status"] == "healthy"
        
        # 지원 모델 확인
        models = await service.get_supported_models()
        assert len(models) == 3
        
        # 리소스 정리
        await service.close()
