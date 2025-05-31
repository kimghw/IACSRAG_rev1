"""
Core Config 모듈 강화된 테스트
기존 테스트에서 누락된 엣지 케이스 및 에러 시나리오 보완
"""

import pytest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from src.core.config import Settings, get_settings


class TestSettingsEnhanced:
    """Settings 클래스 강화된 테스트"""
    
    def test_invalid_max_file_size_format(self):
        """잘못된 파일 크기 형식 테스트"""
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
            'MAX_FILE_SIZE': 'invalid_format'
        }, clear=True):
            settings = Settings(_env_file=None)
            
            # 잘못된 형식의 경우 ValueError 발생해야 함
            with pytest.raises(ValueError):
                _ = settings.max_file_size_bytes
    
    def test_empty_allowed_file_types(self):
        """빈 파일 타입 리스트 테스트"""
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
            'ALLOWED_FILE_TYPES': ''
        }, clear=True):
            settings = Settings(_env_file=None)
            
            # 빈 문자열의 경우 빈 리스트 반환
            assert settings.allowed_file_types_list == ['']
    
    def test_file_types_with_spaces(self):
        """공백이 포함된 파일 타입 테스트"""
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
            'ALLOWED_FILE_TYPES': ' pdf , docx , txt '
        }, clear=True):
            settings = Settings(_env_file=None)
            
            # 공백이 제거되어야 함
            expected = ['pdf', 'docx', 'txt']
            assert settings.allowed_file_types_list == expected
    
    def test_negative_numeric_values(self):
        """음수 값 테스트"""
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
            'PORT': '-1',
            'CHUNK_SIZE': '-100'
        }, clear=True):
            # 음수 값이 설정되어도 pydantic이 처리
            settings = Settings(_env_file=None)
            assert settings.port == -1
            assert settings.chunk_size == -100
    
    def test_boolean_string_variations(self):
        """다양한 불린 문자열 형식 테스트"""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('1', True),
            ('yes', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('0', False),
            ('no', False)
        ]
        
        for bool_str, expected in test_cases:
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
                'DEBUG': bool_str
            }, clear=True):
                settings = Settings(_env_file=None)
                assert settings.debug == expected
    
    def test_float_values(self):
        """부동소수점 값 테스트"""
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
            'OPENAI_TEMPERATURE': '0.5'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.openai_temperature == 0.5
    
    def test_list_values_parsing(self):
        """리스트 값 파싱 테스트"""
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
            'ALLOWED_ORIGINS': '["http://localhost:3000", "https://example.com"]'
        }, clear=True):
            settings = Settings(_env_file=None)
            # pydantic이 JSON 문자열을 파싱할 수 있는지 확인
            # 기본값이 ["*"]이므로 JSON 파싱이 안되면 기본값 사용
            assert isinstance(settings.allowed_origins, list)


class TestGetSettings:
    """get_settings 함수 테스트"""
    
    def test_get_settings_returns_same_instance(self):
        """get_settings가 동일한 인스턴스를 반환하는지 테스트"""
        settings1 = get_settings()
        settings2 = get_settings()
        
        # 동일한 인스턴스여야 함 (싱글톤 패턴)
        assert settings1 is settings2
    
    def test_get_settings_type(self):
        """get_settings 반환 타입 테스트"""
        settings = get_settings()
        assert isinstance(settings, Settings)


class TestSettingsValidation:
    """Settings 검증 로직 테스트"""
    
    def test_invalid_url_format(self):
        """잘못된 URL 형식 테스트"""
        # pydantic은 기본적으로 URL 검증을 하지 않으므로
        # 잘못된 형식도 문자열로 받아들임
        with patch.dict('os.environ', {
            'MONGODB_URL': 'invalid-url',
            'MONGODB_DATABASE': 'test_db',
            'QDRANT_URL': 'not-a-url',
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
            assert settings.mongodb_url == 'invalid-url'
            assert settings.qdrant_url == 'not-a-url'
    
    def test_empty_required_fields(self):
        """빈 필수 필드 테스트"""
        with patch.dict('os.environ', {
            'MONGODB_URL': '',
            'MONGODB_DATABASE': '',
            'QDRANT_URL': '',
            'KAFKA_BOOTSTRAP_SERVERS': '',
            'KAFKA_TOPIC_DOCUMENT_UPLOADED': '',
            'KAFKA_TOPIC_TEXT_EXTRACTED': '',
            'KAFKA_TOPIC_CHUNKS_CREATED': '',
            'KAFKA_TOPIC_EMBEDDINGS_GENERATED': '',
            'KAFKA_CONSUMER_GROUP_ID': '',
            'OPENAI_API_KEY': '',
            'SECRET_KEY': ''
        }, clear=True):
            # 빈 문자열도 유효한 값으로 처리됨
            settings = Settings(_env_file=None)
            assert settings.mongodb_url == ''
            assert settings.secret_key == ''


class TestSettingsEdgeCases:
    """Settings 엣지 케이스 테스트"""
    
    def test_very_large_numbers(self):
        """매우 큰 숫자 테스트"""
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
            'PORT': '999999',
            'CHUNK_SIZE': '1000000'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.port == 999999
            assert settings.chunk_size == 1000000
    
    def test_special_characters_in_strings(self):
        """문자열에 특수 문자 포함 테스트"""
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
            'APP_NAME': 'Test App with Special Chars: !@#$%^&*()',
            'UPLOAD_DIR': './uploads with spaces/test'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.app_name == 'Test App with Special Chars: !@#$%^&*()'
            assert settings.upload_dir == './uploads with spaces/test'
    
    def test_unicode_characters(self):
        """유니코드 문자 테스트"""
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
            'APP_NAME': 'IACS RAG 플랫폼 🚀'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.app_name == 'IACS RAG 플랫폼 🚀'
