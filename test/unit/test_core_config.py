"""
핵심 설정 모듈 단위 테스트
"""

import pytest
from unittest.mock import patch
from pydantic import ValidationError

from src.core.config import Settings


class TestSettings:
    """Settings 클래스 테스트"""
    
    def test_default_values(self):
        """기본값 설정 테스트"""
        with patch.dict('os.environ', {
            'MONGODB_URL': 'mongodb://test:27017',
            'MONGODB_DATABASE': 'test_db',
            'QDRANT_URL': 'http://test:6333',
            'KAFKA_BOOTSTRAP_SERVERS': 'test:9092',
            'KAFKA_TOPIC_DOCUMENT_UPLOADED': 'test.uploaded',
            'KAFKA_TOPIC_TEXT_EXTRACTED': 'test.extracted',
            'KAFKA_TOPIC_CHUNKS_CREATED': 'test.chunks',
            'KAFKA_TOPIC_EMBEDDINGS_GENERATED': 'test.embeddings',
            'KAFKA_CONSUMER_GROUP_ID': 'test-group',
            'OPENAI_API_KEY': 'test-key',
            'SECRET_KEY': 'test-secret'
        }, clear=True):
            # .env 파일을 사용하지 않도록 설정
            settings = Settings(_env_file=None)
            
            assert settings.app_name == "IACS RAG Platform"
            assert settings.app_version == "0.1.0"
            assert settings.debug is False
            assert settings.log_level == "INFO"
            assert settings.api_v1_prefix == "/api/v1"
            assert settings.host == "0.0.0.0"
            assert settings.port == 8000
    
    def test_required_fields_validation(self):
        """필수 필드 검증 테스트"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            
            # 필수 필드들이 누락되었는지 확인
            errors = exc_info.value.errors()
            # 실제 필드명은 대문자로 된 환경변수명으로 나타남
            required_fields = {
                'MONGODB_URL', 'MONGODB_DATABASE', 'QDRANT_URL',
                'KAFKA_BOOTSTRAP_SERVERS', 'OPENAI_API_KEY', 'SECRET_KEY'
            }
            
            error_fields = {error['loc'][0] for error in errors}
            assert required_fields.issubset(error_fields)
    
    def test_allowed_file_types_list_property(self):
        """허용된 파일 타입 리스트 속성 테스트"""
        with patch.dict('os.environ', {
            'MONGODB_URL': 'mongodb://test:27017',
            'MONGODB_DATABASE': 'test_db',
            'QDRANT_URL': 'http://test:6333',
            'KAFKA_BOOTSTRAP_SERVERS': 'test:9092',
            'KAFKA_TOPIC_DOCUMENT_UPLOADED': 'test.uploaded',
            'KAFKA_TOPIC_TEXT_EXTRACTED': 'test.extracted',
            'KAFKA_TOPIC_CHUNKS_CREATED': 'test.chunks',
            'KAFKA_TOPIC_EMBEDDINGS_GENERATED': 'test.embeddings',
            'KAFKA_CONSUMER_GROUP_ID': 'test-group',
            'OPENAI_API_KEY': 'test-key',
            'SECRET_KEY': 'test-secret',
            'ALLOWED_FILE_TYPES': 'pdf, docx, txt, xlsx'
        }, clear=True):
            settings = Settings(_env_file=None)
            
            expected = ['pdf', 'docx', 'txt', 'xlsx']
            assert settings.allowed_file_types_list == expected
    
    def test_max_file_size_bytes_property(self):
        """최대 파일 크기 바이트 변환 테스트"""
        with patch.dict('os.environ', {
            'MONGODB_URL': 'mongodb://test:27017',
            'MONGODB_DATABASE': 'test_db',
            'QDRANT_URL': 'http://test:6333',
            'KAFKA_BOOTSTRAP_SERVERS': 'test:9092',
            'KAFKA_TOPIC_DOCUMENT_UPLOADED': 'test.uploaded',
            'KAFKA_TOPIC_TEXT_EXTRACTED': 'test.extracted',
            'KAFKA_TOPIC_CHUNKS_CREATED': 'test.chunks',
            'KAFKA_TOPIC_EMBEDDINGS_GENERATED': 'test.embeddings',
            'KAFKA_CONSUMER_GROUP_ID': 'test-group',
            'OPENAI_API_KEY': 'test-key',
            'SECRET_KEY': 'test-secret'
        }, clear=True):
            # MB 테스트
            with patch.dict('os.environ', {'MAX_FILE_SIZE': '10MB'}):
                settings = Settings(_env_file=None)
                assert settings.max_file_size_bytes == 10 * 1024 * 1024
            
            # KB 테스트
            with patch.dict('os.environ', {'MAX_FILE_SIZE': '500KB'}):
                settings = Settings(_env_file=None)
                assert settings.max_file_size_bytes == 500 * 1024
            
            # GB 테스트
            with patch.dict('os.environ', {'MAX_FILE_SIZE': '1GB'}):
                settings = Settings(_env_file=None)
                assert settings.max_file_size_bytes == 1 * 1024 * 1024 * 1024
            
            # 숫자만 있는 경우 (바이트)
            with patch.dict('os.environ', {'MAX_FILE_SIZE': '1024'}):
                settings = Settings(_env_file=None)
                assert settings.max_file_size_bytes == 1024
    
    def test_environment_variable_override(self):
        """환경 변수 오버라이드 테스트"""
        with patch.dict('os.environ', {
            'MONGODB_URL': 'mongodb://test:27017',
            'MONGODB_DATABASE': 'test_db',
            'QDRANT_URL': 'http://test:6333',
            'KAFKA_BOOTSTRAP_SERVERS': 'test:9092',
            'KAFKA_TOPIC_DOCUMENT_UPLOADED': 'test.uploaded',
            'KAFKA_TOPIC_TEXT_EXTRACTED': 'test.extracted',
            'KAFKA_TOPIC_CHUNKS_CREATED': 'test.chunks',
            'KAFKA_TOPIC_EMBEDDINGS_GENERATED': 'test.embeddings',
            'KAFKA_CONSUMER_GROUP_ID': 'test-group',
            'OPENAI_API_KEY': 'test-key',
            'SECRET_KEY': 'test-secret',
            'APP_NAME': 'Custom App Name',
            'DEBUG': 'true',
            'PORT': '9000',
            'CHUNK_SIZE': '2000'
        }, clear=True):
            settings = Settings(_env_file=None)
            
            assert settings.app_name == "Custom App Name"
            assert settings.debug is True
            assert settings.port == 9000
            assert settings.chunk_size == 2000
    
    def test_optional_fields(self):
        """선택적 필드 테스트"""
        with patch.dict('os.environ', {
            'MONGODB_URL': 'mongodb://test:27017',
            'MONGODB_DATABASE': 'test_db',
            'QDRANT_URL': 'http://test:6333',
            'KAFKA_BOOTSTRAP_SERVERS': 'test:9092',
            'KAFKA_TOPIC_DOCUMENT_UPLOADED': 'test.uploaded',
            'KAFKA_TOPIC_TEXT_EXTRACTED': 'test.extracted',
            'KAFKA_TOPIC_CHUNKS_CREATED': 'test.chunks',
            'KAFKA_TOPIC_EMBEDDINGS_GENERATED': 'test.embeddings',
            'KAFKA_CONSUMER_GROUP_ID': 'test-group',
            'OPENAI_API_KEY': 'test-key',
            'SECRET_KEY': 'test-secret'
        }, clear=True):
            settings = Settings(_env_file=None)
            
            # 선택적 필드들이 기본값을 가지는지 확인
            assert settings.qdrant_api_key is None
            assert settings.redis_url is None
            assert settings.cache_ttl == 3600
            assert settings.enable_metrics is True
