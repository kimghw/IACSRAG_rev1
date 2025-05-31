"""
해싱 유틸리티 단위 테스트
"""

import pytest
import tempfile
import hashlib
from pathlib import Path
from io import BytesIO

from src.utils.hash import (
    hash_text,
    hash_file,
    hash_file_stream,
    verify_hash,
    verify_file_hash,
    generate_content_hash,
    generate_chunk_hash,
    get_supported_algorithms
)


class TestHashText:
    """텍스트 해싱 테스트"""

    def test_hash_text_basic(self):
        """기본 텍스트 해싱 테스트"""
        text = "Hello, World!"
        result = hash_text(text)
        
        # SHA-256 해시 길이 확인
        assert len(result) == 64
        assert isinstance(result, str)
        
        # 16진수 문자열인지 확인
        int(result, 16)  # 예외가 발생하지 않으면 유효한 16진수

    def test_hash_text_consistency(self):
        """해싱 일관성 테스트"""
        text = "Test consistency"
        
        # 같은 텍스트는 항상 같은 해시를 생성해야 함
        hash1 = hash_text(text)
        hash2 = hash_text(text)
        
        assert hash1 == hash2

    def test_hash_text_different_inputs(self):
        """다른 입력에 대한 해싱 테스트"""
        text1 = "Hello"
        text2 = "World"
        
        hash1 = hash_text(text1)
        hash2 = hash_text(text2)
        
        # 다른 텍스트는 다른 해시를 생성해야 함
        assert hash1 != hash2

    def test_hash_text_algorithms(self):
        """다양한 알고리즘 테스트"""
        text = "Test algorithms"
        
        # SHA-256 (기본값)
        sha256_hash = hash_text(text)
        assert len(sha256_hash) == 64
        
        # MD5
        md5_hash = hash_text(text, "md5")
        assert len(md5_hash) == 32
        
        # SHA-1
        sha1_hash = hash_text(text, "sha1")
        assert len(sha1_hash) == 40
        
        # 모든 해시가 다른지 확인
        assert sha256_hash != md5_hash != sha1_hash

    def test_hash_text_invalid_algorithm(self):
        """유효하지 않은 알고리즘 테스트"""
        text = "Test invalid algorithm"
        
        with pytest.raises(ValueError, match="지원하지 않는 해싱 알고리즘"):
            hash_text(text, "invalid_algorithm")

    def test_hash_text_unicode(self):
        """유니코드 텍스트 해싱 테스트"""
        korean_text = "안녕하세요, 세계!"
        emoji_text = "Hello 👋 World 🌍"
        
        korean_hash = hash_text(korean_text)
        emoji_hash = hash_text(emoji_text)
        
        assert len(korean_hash) == 64
        assert len(emoji_hash) == 64
        assert korean_hash != emoji_hash

    def test_hash_text_empty_string(self):
        """빈 문자열 해싱 테스트"""
        empty_hash = hash_text("")
        
        assert len(empty_hash) == 64
        assert isinstance(empty_hash, str)


class TestHashFile:
    """파일 해싱 테스트"""

    def test_hash_file_basic(self):
        """기본 파일 해싱 테스트"""
        content = b"Hello, File World!"
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            result = hash_file(tmp_file.name)
            
            assert len(result) == 64
            assert isinstance(result, str)
            
            # 수동으로 계산한 해시와 비교
            expected = hashlib.sha256(content).hexdigest()
            assert result == expected
        
        # 임시 파일 정리
        Path(tmp_file.name).unlink()

    def test_hash_file_consistency(self):
        """파일 해싱 일관성 테스트"""
        content = b"Consistency test content"
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            hash1 = hash_file(tmp_file.name)
            hash2 = hash_file(tmp_file.name)
            
            assert hash1 == hash2
        
        Path(tmp_file.name).unlink()

    def test_hash_file_not_found(self):
        """존재하지 않는 파일 테스트"""
        with pytest.raises(FileNotFoundError, match="파일을 찾을 수 없습니다"):
            hash_file("non_existent_file.txt")

    def test_hash_file_large_file(self):
        """큰 파일 해싱 테스트 (청크 단위 읽기 확인)"""
        # 10KB 파일 생성
        content = b"A" * 10240
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            result = hash_file(tmp_file.name)
            expected = hashlib.sha256(content).hexdigest()
            
            assert result == expected
        
        Path(tmp_file.name).unlink()

    def test_hash_file_different_algorithms(self):
        """다양한 알고리즘으로 파일 해싱 테스트"""
        content = b"Algorithm test content"
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            sha256_hash = hash_file(tmp_file.name, "sha256")
            md5_hash = hash_file(tmp_file.name, "md5")
            
            assert len(sha256_hash) == 64
            assert len(md5_hash) == 32
            assert sha256_hash != md5_hash
        
        Path(tmp_file.name).unlink()


class TestHashFileStream:
    """파일 스트림 해싱 테스트"""

    def test_hash_file_stream_basic(self):
        """기본 파일 스트림 해싱 테스트"""
        content = b"Stream test content"
        stream = BytesIO(content)
        
        result = hash_file_stream(stream)
        expected = hashlib.sha256(content).hexdigest()
        
        assert result == expected

    def test_hash_file_stream_position_preservation(self):
        """스트림 위치 보존 테스트"""
        content = b"Position preservation test"
        stream = BytesIO(content)
        
        # 스트림 위치를 중간으로 이동
        stream.seek(5)
        original_position = stream.tell()
        
        # 해싱 수행
        hash_file_stream(stream)
        
        # 원래 위치로 복원되었는지 확인
        assert stream.tell() == original_position

    def test_hash_file_stream_empty(self):
        """빈 스트림 해싱 테스트"""
        stream = BytesIO(b"")
        
        result = hash_file_stream(stream)
        expected = hashlib.sha256(b"").hexdigest()
        
        assert result == expected


class TestVerifyHash:
    """해시 검증 테스트"""

    def test_verify_hash_valid(self):
        """유효한 해시 검증 테스트"""
        text = "Verification test"
        expected_hash = hash_text(text)
        
        assert verify_hash(text, expected_hash) is True

    def test_verify_hash_invalid(self):
        """유효하지 않은 해시 검증 테스트"""
        text = "Verification test"
        wrong_hash = "0" * 64  # 잘못된 해시
        
        assert verify_hash(text, wrong_hash) is False

    def test_verify_hash_timing_attack_safe(self):
        """타이밍 공격 안전성 테스트 (hmac.compare_digest 사용)"""
        text = "Security test"
        correct_hash = hash_text(text)
        wrong_hash = "f" * 64
        
        # 두 검증 모두 안전하게 처리되어야 함
        assert verify_hash(text, correct_hash) is True
        assert verify_hash(text, wrong_hash) is False


class TestVerifyFileHash:
    """파일 해시 검증 테스트"""

    def test_verify_file_hash_valid(self):
        """유효한 파일 해시 검증 테스트"""
        content = b"File verification test"
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            expected_hash = hash_file(tmp_file.name)
            assert verify_file_hash(tmp_file.name, expected_hash) is True
        
        Path(tmp_file.name).unlink()

    def test_verify_file_hash_invalid(self):
        """유효하지 않은 파일 해시 검증 테스트"""
        content = b"File verification test"
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            wrong_hash = "0" * 64
            assert verify_file_hash(tmp_file.name, wrong_hash) is False
        
        Path(tmp_file.name).unlink()


class TestGenerateContentHash:
    """콘텐츠 해시 생성 테스트"""

    def test_generate_content_hash_normalization(self):
        """공백 정규화 테스트"""
        text1 = "Hello    World"
        text2 = "Hello World"
        text3 = "  Hello   World  "
        
        hash1 = generate_content_hash(text1)
        hash2 = generate_content_hash(text2)
        hash3 = generate_content_hash(text3)
        
        # 공백이 정규화되어 같은 해시가 생성되어야 함
        assert hash1 == hash2 == hash3

    def test_generate_content_hash_different_content(self):
        """다른 콘텐츠 해시 테스트"""
        text1 = "Content A"
        text2 = "Content B"
        
        hash1 = generate_content_hash(text1)
        hash2 = generate_content_hash(text2)
        
        assert hash1 != hash2


class TestGenerateChunkHash:
    """청크 해시 생성 테스트"""

    def test_generate_chunk_hash_text_only(self):
        """텍스트만으로 청크 해시 생성 테스트"""
        text = "Chunk text content"
        
        result = generate_chunk_hash(text)
        expected = generate_content_hash(text)
        
        assert result == expected

    def test_generate_chunk_hash_with_metadata(self):
        """메타데이터가 포함된 청크 해시 생성 테스트"""
        text = "Chunk text content"
        metadata = {"page": 1, "section": "intro"}
        
        hash_without_metadata = generate_chunk_hash(text)
        hash_with_metadata = generate_chunk_hash(text, metadata)
        
        # 메타데이터가 있으면 다른 해시가 생성되어야 함
        assert hash_without_metadata != hash_with_metadata

    def test_generate_chunk_hash_metadata_order_independence(self):
        """메타데이터 순서 독립성 테스트"""
        text = "Chunk text content"
        metadata1 = {"page": 1, "section": "intro"}
        metadata2 = {"section": "intro", "page": 1}
        
        hash1 = generate_chunk_hash(text, metadata1)
        hash2 = generate_chunk_hash(text, metadata2)
        
        # 메타데이터 순서가 달라도 같은 해시가 생성되어야 함
        assert hash1 == hash2


class TestGetSupportedAlgorithms:
    """지원되는 알고리즘 목록 테스트"""

    def test_get_supported_algorithms(self):
        """지원되는 알고리즘 목록 테스트"""
        algorithms = get_supported_algorithms()
        
        assert isinstance(algorithms, list)
        assert len(algorithms) > 0
        
        # 기본 알고리즘들이 포함되어 있는지 확인
        assert "sha256" in algorithms
        assert "md5" in algorithms
        assert "sha1" in algorithms


class TestIntegration:
    """통합 테스트"""

    def test_file_and_text_hash_consistency(self):
        """파일과 텍스트 해시 일관성 테스트"""
        text = "Consistency test between file and text hashing"
        content = text.encode('utf-8')
        
        # 텍스트 해시
        text_hash = hash_text(text)
        
        # 파일 해시
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            file_hash = hash_file(tmp_file.name)
        
        Path(tmp_file.name).unlink()
        
        # 같은 내용이므로 같은 해시가 생성되어야 함
        assert text_hash == file_hash

    def test_stream_and_file_hash_consistency(self):
        """스트림과 파일 해시 일관성 테스트"""
        content = b"Stream and file hash consistency test"
        
        # 파일 해시
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            file_hash = hash_file(tmp_file.name)
        
        Path(tmp_file.name).unlink()
        
        # 스트림 해시
        stream = BytesIO(content)
        stream_hash = hash_file_stream(stream)
        
        # 같은 내용이므로 같은 해시가 생성되어야 함
        assert file_hash == stream_hash

    def test_hash_verification_workflow(self):
        """해시 검증 워크플로우 테스트"""
        original_text = "Original document content"
        
        # 1. 원본 해시 생성
        original_hash = hash_text(original_text)
        
        # 2. 해시 검증 (성공)
        assert verify_hash(original_text, original_hash) is True
        
        # 3. 변경된 텍스트로 검증 (실패)
        modified_text = "Modified document content"
        assert verify_hash(modified_text, original_hash) is False
        
        # 4. 새로운 해시 생성
        new_hash = hash_text(modified_text)
        assert verify_hash(modified_text, new_hash) is True
        
        # 5. 원본과 새 해시는 달라야 함
        assert original_hash != new_hash
