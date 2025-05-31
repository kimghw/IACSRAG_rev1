"""
ID 생성 유틸리티 단위 테스트
"""

import pytest
import uuid
from unittest.mock import patch
from datetime import datetime

from src.utils.id_generator import (
    generate_uuid,
    generate_short_id,
    generate_document_id,
    generate_chunk_id,
    generate_user_id,
    generate_session_id,
    is_valid_uuid
)


class TestGenerateUuid:
    """UUID 생성 테스트"""

    def test_generate_uuid_format(self):
        """UUID 형식 테스트"""
        result = generate_uuid()
        
        # UUID 형식 검증
        assert isinstance(result, str)
        assert len(result) == 36  # UUID4 길이
        assert result.count('-') == 4  # 하이픈 개수
        
        # 실제 UUID로 파싱 가능한지 확인
        parsed_uuid = uuid.UUID(result)
        assert str(parsed_uuid) == result

    def test_generate_uuid_uniqueness(self):
        """UUID 고유성 테스트"""
        uuids = [generate_uuid() for _ in range(100)]
        
        # 모든 UUID가 고유한지 확인
        assert len(set(uuids)) == 100


class TestGenerateShortId:
    """짧은 ID 생성 테스트"""

    def test_generate_short_id_default_length(self):
        """기본 길이 테스트"""
        result = generate_short_id()
        
        assert isinstance(result, str)
        assert len(result) == 8

    def test_generate_short_id_custom_length(self):
        """커스텀 길이 테스트"""
        for length in [4, 12, 16, 32]:
            result = generate_short_id(length)
            assert len(result) == length

    def test_generate_short_id_characters(self):
        """문자 구성 테스트"""
        result = generate_short_id(100)  # 충분히 긴 ID로 테스트
        
        # 영숫자만 포함되는지 확인
        assert result.isalnum()

    def test_generate_short_id_uniqueness(self):
        """고유성 테스트"""
        ids = [generate_short_id() for _ in range(100)]
        
        # 대부분 고유해야 함 (확률적으로 중복 가능하지만 매우 낮음)
        assert len(set(ids)) >= 95


class TestGenerateDocumentId:
    """문서 ID 생성 테스트"""

    @patch('src.utils.id_generator.datetime')
    def test_generate_document_id_default(self, mock_datetime):
        """기본 문서 ID 생성 테스트"""
        # Mock 시간 설정
        mock_datetime.utcnow.return_value = datetime(2024, 5, 31, 14, 30, 45)
        
        with patch('src.utils.id_generator.generate_short_id', return_value='abc123'):
            result = generate_document_id()
            
            assert result.startswith('doc_20240531_143045_')
            assert result.endswith('abc123')

    @patch('src.utils.id_generator.datetime')
    def test_generate_document_id_with_prefix(self, mock_datetime):
        """접두사가 있는 문서 ID 생성 테스트"""
        mock_datetime.utcnow.return_value = datetime(2024, 5, 31, 14, 30, 45)
        
        with patch('src.utils.id_generator.generate_short_id', return_value='abc123'):
            result = generate_document_id('pdf')
            
            assert result.startswith('pdf_20240531_143045_')
            assert result.endswith('abc123')

    def test_generate_document_id_format(self):
        """문서 ID 형식 테스트"""
        result = generate_document_id()
        
        parts = result.split('_')
        assert len(parts) == 4  # prefix_date_time_random
        assert parts[0] == 'doc'
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # HHMMSS
        assert len(parts[3]) == 6  # random suffix


class TestGenerateChunkId:
    """청크 ID 생성 테스트"""

    def test_generate_chunk_id_format(self):
        """청크 ID 형식 테스트"""
        document_id = "doc_20240531_143045_abc123"
        chunk_index = 5
        
        result = generate_chunk_id(document_id, chunk_index)
        
        assert result == "doc_20240531_143045_abc123_chunk_005"

    def test_generate_chunk_id_zero_padding(self):
        """0 패딩 테스트"""
        document_id = "test_doc"
        
        # 다양한 인덱스로 테스트
        test_cases = [
            (0, "test_doc_chunk_000"),
            (1, "test_doc_chunk_001"),
            (10, "test_doc_chunk_010"),
            (100, "test_doc_chunk_100"),
            (999, "test_doc_chunk_999"),
        ]
        
        for index, expected in test_cases:
            result = generate_chunk_id(document_id, index)
            assert result == expected


class TestGenerateUserId:
    """사용자 ID 생성 테스트"""

    def test_generate_user_id_format(self):
        """사용자 ID 형식 테스트"""
        result = generate_user_id()
        
        assert result.startswith('user_')
        assert len(result) == 17  # 'user_' + 12자
        
        # 접두사 제거 후 영숫자 확인
        suffix = result[5:]
        assert suffix.isalnum()
        assert len(suffix) == 12

    def test_generate_user_id_uniqueness(self):
        """사용자 ID 고유성 테스트"""
        ids = [generate_user_id() for _ in range(50)]
        assert len(set(ids)) == 50


class TestGenerateSessionId:
    """세션 ID 생성 테스트"""

    def test_generate_session_id_format(self):
        """세션 ID 형식 테스트"""
        result = generate_session_id()
        
        assert result.startswith('sess_')
        assert len(result) == 21  # 'sess_' + 16자
        
        # 접두사 제거 후 영숫자 확인
        suffix = result[5:]
        assert suffix.isalnum()
        assert len(suffix) == 16

    def test_generate_session_id_uniqueness(self):
        """세션 ID 고유성 테스트"""
        ids = [generate_session_id() for _ in range(50)]
        assert len(set(ids)) == 50


class TestIsValidUuid:
    """UUID 검증 테스트"""

    def test_is_valid_uuid_valid_cases(self):
        """유효한 UUID 테스트"""
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
            str(uuid.uuid4()),
            generate_uuid(),
        ]
        
        for valid_uuid in valid_uuids:
            assert is_valid_uuid(valid_uuid) is True

    def test_is_valid_uuid_invalid_cases(self):
        """유효하지 않은 UUID 테스트"""
        invalid_uuids = [
            "invalid-uuid",
            "550e8400-e29b-41d4-a716",  # 너무 짧음
            "550e8400-e29b-41d4-a716-446655440000-extra",  # 너무 김
            "550e8400-e29b-41d4-a716-44665544000g",  # 잘못된 문자
            "",
            "not-a-uuid-at-all",
            "123456789",
            None,
        ]
        
        for invalid_uuid in invalid_uuids:
            if invalid_uuid is not None:
                assert is_valid_uuid(invalid_uuid) is False

    def test_is_valid_uuid_edge_cases(self):
        """엣지 케이스 테스트"""
        # 대소문자 혼합
        mixed_case = "550E8400-e29b-41D4-A716-446655440000"
        assert is_valid_uuid(mixed_case) is True
        
        # 소문자
        lowercase = "550e8400-e29b-41d4-a716-446655440000"
        assert is_valid_uuid(lowercase) is True
        
        # 대문자
        uppercase = "550E8400-E29B-41D4-A716-446655440000"
        assert is_valid_uuid(uppercase) is True


class TestIntegration:
    """통합 테스트"""

    def test_document_workflow(self):
        """문서 처리 워크플로우 테스트"""
        # 문서 ID 생성
        doc_id = generate_document_id('pdf')
        
        # 청크 ID들 생성
        chunk_ids = [generate_chunk_id(doc_id, i) for i in range(5)]
        
        # 모든 청크 ID가 고유하고 올바른 형식인지 확인
        assert len(set(chunk_ids)) == 5
        
        for i, chunk_id in enumerate(chunk_ids):
            assert chunk_id.startswith(doc_id)
            assert chunk_id.endswith(f"_chunk_{i:03d}")

    def test_user_session_workflow(self):
        """사용자 세션 워크플로우 테스트"""
        # 사용자 ID 생성
        user_id = generate_user_id()
        
        # 세션 ID 생성
        session_id = generate_session_id()
        
        # 형식 확인
        assert user_id.startswith('user_')
        assert session_id.startswith('sess_')
        
        # 고유성 확인
        assert user_id != session_id

    def test_all_generators_produce_strings(self):
        """모든 생성기가 문자열을 반환하는지 테스트"""
        generators = [
            generate_uuid,
            generate_short_id,
            generate_document_id,
            generate_user_id,
            generate_session_id,
        ]
        
        for generator in generators:
            result = generator()
            assert isinstance(result, str)
            assert len(result) > 0
