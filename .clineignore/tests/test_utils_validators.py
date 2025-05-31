"""
검증 유틸리티 단위 테스트
"""

import pytest
import tempfile
from pathlib import Path

from src.utils.validators import (
    validate_email,
    validate_file_extension,
    validate_file_size,
    validate_file,
    validate_text_content,
    validate_chunk_size,
    validate_search_query,
    validate_pagination,
    is_safe_filename,
    get_file_type,
    SUPPORTED_DOCUMENT_EXTENSIONS,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_ARCHIVE_EXTENSIONS,
    MAX_FILE_SIZE
)


class TestValidateEmail:
    """이메일 검증 테스트"""

    def test_validate_email_valid(self):
        """유효한 이메일 테스트"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.kr",
            "admin+tag@company.org",
            "123@numbers.com",
            "a@b.co",
        ]
        
        for email in valid_emails:
            is_valid, error = validate_email(email)
            assert is_valid is True
            assert error is None

    def test_validate_email_invalid(self):
        """유효하지 않은 이메일 테스트"""
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user..name@domain.com",
            "user@domain",
            "",
            "user name@domain.com",  # 공백 포함
        ]
        
        for email in invalid_emails:
            is_valid, error = validate_email(email)
            assert is_valid is False
            assert error is not None
            assert isinstance(error, str)


class TestValidateFileExtension:
    """파일 확장자 검증 테스트"""

    def test_validate_file_extension_default_allowed(self):
        """기본 허용 확장자 테스트"""
        valid_files = [
            "document.pdf",
            "text.txt",
            "markdown.md",
            "word.docx",
            "web.html",
        ]
        
        for file_path in valid_files:
            is_valid, error = validate_file_extension(file_path)
            assert is_valid is True
            assert error is None

    def test_validate_file_extension_custom_allowed(self):
        """커스텀 허용 확장자 테스트"""
        allowed_extensions = [".jpg", ".png", ".gif"]
        
        valid_files = [
            "image.jpg",
            "photo.PNG",  # 대소문자 혼합
            "animation.gif",
        ]
        
        for file_path in valid_files:
            is_valid, error = validate_file_extension(file_path, allowed_extensions)
            assert is_valid is True
            assert error is None

    def test_validate_file_extension_invalid(self):
        """유효하지 않은 확장자 테스트"""
        invalid_files = [
            "executable.exe",
            "script.bat",
            "archive.rar",
            "no_extension",
        ]
        
        for file_path in invalid_files:
            is_valid, error = validate_file_extension(file_path)
            assert is_valid is False
            assert error is not None

    def test_validate_file_extension_no_extension(self):
        """확장자 없는 파일 테스트"""
        is_valid, error = validate_file_extension("filename_without_extension")
        assert is_valid is False
        assert "파일 확장자가 없습니다" in error

    def test_validate_file_extension_case_insensitive(self):
        """대소문자 구분 없는 확장자 테스트"""
        test_cases = [
            "document.PDF",
            "text.TXT",
            "markdown.MD",
        ]
        
        for file_path in test_cases:
            is_valid, error = validate_file_extension(file_path)
            assert is_valid is True
            assert error is None


class TestValidateFileSize:
    """파일 크기 검증 테스트"""

    def test_validate_file_size_valid(self):
        """유효한 파일 크기 테스트"""
        content = b"Small file content"
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            is_valid, error = validate_file_size(tmp_file.name)
            assert is_valid is True
            assert error is None
        
        Path(tmp_file.name).unlink()

    def test_validate_file_size_custom_limit(self):
        """커스텀 크기 제한 테스트"""
        content = b"A" * 1000  # 1KB
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            # 500바이트 제한 (실패해야 함)
            is_valid, error = validate_file_size(tmp_file.name, max_size=500)
            assert is_valid is False
            assert "파일 크기가 너무 큽니다" in error
            
            # 2KB 제한 (성공해야 함)
            is_valid, error = validate_file_size(tmp_file.name, max_size=2048)
            assert is_valid is True
            assert error is None
        
        Path(tmp_file.name).unlink()

    def test_validate_file_size_not_found(self):
        """존재하지 않는 파일 테스트"""
        is_valid, error = validate_file_size("non_existent_file.txt")
        assert is_valid is False
        assert "파일이 존재하지 않습니다" in error

    def test_validate_file_size_large_file(self):
        """큰 파일 크기 테스트"""
        # 기본 제한보다 큰 파일 시뮬레이션
        large_size = MAX_FILE_SIZE + 1000
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            # 실제로 큰 파일을 만들지 않고 seek로 크기 설정
            tmp_file.seek(large_size - 1)
            tmp_file.write(b'\0')
            tmp_file.flush()
            
            is_valid, error = validate_file_size(tmp_file.name)
            assert is_valid is False
            assert "파일 크기가 너무 큽니다" in error
        
        Path(tmp_file.name).unlink()


class TestValidateFile:
    """종합 파일 검증 테스트"""

    def test_validate_file_valid(self):
        """유효한 파일 종합 검증 테스트"""
        content = b"Valid file content"
        
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            is_valid, errors = validate_file(tmp_file.name)
            assert is_valid is True
            assert len(errors) == 0
        
        Path(tmp_file.name).unlink()

    def test_validate_file_multiple_errors(self):
        """여러 오류가 있는 파일 테스트"""
        # 존재하지 않는 파일
        is_valid, errors = validate_file("non_existent.exe")
        assert is_valid is False
        assert len(errors) == 1
        assert "파일이 존재하지 않습니다" in errors[0]

    def test_validate_file_custom_constraints(self):
        """커스텀 제약 조건 테스트"""
        content = b"Custom constraint test"
        
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            # 허용되지 않는 확장자와 작은 크기 제한
            is_valid, errors = validate_file(
                tmp_file.name,
                allowed_extensions=[".pdf", ".docx"],
                max_size=10  # 매우 작은 크기
            )
            assert is_valid is False
            assert len(errors) == 2  # 확장자와 크기 오류
        
        Path(tmp_file.name).unlink()


class TestValidateTextContent:
    """텍스트 내용 검증 테스트"""

    def test_validate_text_content_valid(self):
        """유효한 텍스트 내용 테스트"""
        valid_texts = [
            "Hello, World!",
            "한글 텍스트도 가능합니다.",
            "A" * 1000,  # 긴 텍스트
            "Short",
        ]
        
        for text in valid_texts:
            is_valid, error = validate_text_content(text)
            assert is_valid is True
            assert error is None

    def test_validate_text_content_too_short(self):
        """너무 짧은 텍스트 테스트"""
        is_valid, error = validate_text_content("", min_length=5)
        assert is_valid is False
        assert "텍스트가 너무 짧습니다" in error

    def test_validate_text_content_too_long(self):
        """너무 긴 텍스트 테스트"""
        long_text = "A" * 1000
        is_valid, error = validate_text_content(long_text, max_length=500)
        assert is_valid is False
        assert "텍스트가 너무 깁니다" in error

    def test_validate_text_content_not_string(self):
        """문자열이 아닌 입력 테스트"""
        invalid_inputs = [123, [], {}, None]
        
        for invalid_input in invalid_inputs:
            is_valid, error = validate_text_content(invalid_input)
            assert is_valid is False
            assert "텍스트가 문자열이 아닙니다" in error

    def test_validate_text_content_whitespace_handling(self):
        """공백 처리 테스트"""
        # 공백만 있는 텍스트
        is_valid, error = validate_text_content("   ", min_length=1)
        assert is_valid is False
        assert "텍스트가 너무 짧습니다" in error


class TestValidateChunkSize:
    """청크 크기 검증 테스트"""

    def test_validate_chunk_size_valid(self):
        """유효한 청크 크기 테스트"""
        valid_sizes = [100, 500, 1000, 4000, 8000]
        
        for size in valid_sizes:
            is_valid, error = validate_chunk_size(size)
            assert is_valid is True
            assert error is None

    def test_validate_chunk_size_too_small(self):
        """너무 작은 청크 크기 테스트"""
        is_valid, error = validate_chunk_size(50)
        assert is_valid is False
        assert "청크 크기가 너무 작습니다" in error

    def test_validate_chunk_size_too_large(self):
        """너무 큰 청크 크기 테스트"""
        is_valid, error = validate_chunk_size(10000)
        assert is_valid is False
        assert "청크 크기가 너무 큽니다" in error

    def test_validate_chunk_size_invalid_type(self):
        """유효하지 않은 타입 테스트"""
        invalid_inputs = ["100", 100.5, -100, 0]
        
        for invalid_input in invalid_inputs:
            is_valid, error = validate_chunk_size(invalid_input)
            assert is_valid is False
            assert "청크 크기는 양의 정수여야 합니다" in error


class TestValidateSearchQuery:
    """검색 쿼리 검증 테스트"""

    def test_validate_search_query_valid(self):
        """유효한 검색 쿼리 테스트"""
        valid_queries = [
            "search term",
            "한글 검색어",
            "complex search with multiple words",
            "123 numbers",
        ]
        
        for query in valid_queries:
            is_valid, error = validate_search_query(query)
            assert is_valid is True
            assert error is None

    def test_validate_search_query_too_short(self):
        """너무 짧은 검색 쿼리 테스트"""
        is_valid, error = validate_search_query("a")
        assert is_valid is False
        assert "검색 쿼리가 너무 짧습니다" in error

    def test_validate_search_query_too_long(self):
        """너무 긴 검색 쿼리 테스트"""
        long_query = "A" * 1500
        is_valid, error = validate_search_query(long_query)
        assert is_valid is False
        assert "검색 쿼리가 너무 깁니다" in error

    def test_validate_search_query_special_characters_only(self):
        """특수 문자만으로 구성된 쿼리 테스트"""
        is_valid, error = validate_search_query("!@#$%")
        assert is_valid is False
        assert "검색 쿼리에 유효한 문자가 포함되어야 합니다" in error

    def test_validate_search_query_not_string(self):
        """문자열이 아닌 검색 쿼리 테스트"""
        is_valid, error = validate_search_query(123)
        assert is_valid is False
        assert "검색 쿼리가 문자열이 아닙니다" in error

    def test_validate_search_query_whitespace_trimming(self):
        """공백 제거 테스트"""
        is_valid, error = validate_search_query("  valid query  ")
        assert is_valid is True
        assert error is None


class TestValidatePagination:
    """페이지네이션 검증 테스트"""

    def test_validate_pagination_valid(self):
        """유효한 페이지네이션 테스트"""
        valid_cases = [
            (1, 10),
            (5, 20),
            (100, 50),
        ]
        
        for page, size in valid_cases:
            is_valid, error = validate_pagination(page, size)
            assert is_valid is True
            assert error is None

    def test_validate_pagination_invalid_page(self):
        """유효하지 않은 페이지 번호 테스트"""
        invalid_pages = [0, -1, "1", 1.5]
        
        for page in invalid_pages:
            is_valid, error = validate_pagination(page, 10)
            assert is_valid is False
            assert "페이지 번호는 1 이상의 정수여야 합니다" in error

    def test_validate_pagination_invalid_size(self):
        """유효하지 않은 페이지 크기 테스트"""
        invalid_sizes = [0, -1, "10", 10.5]
        
        for size in invalid_sizes:
            is_valid, error = validate_pagination(1, size)
            assert is_valid is False
            assert "페이지 크기는 1 이상의 정수여야 합니다" in error

    def test_validate_pagination_size_too_large(self):
        """너무 큰 페이지 크기 테스트"""
        is_valid, error = validate_pagination(1, 200)
        assert is_valid is False
        assert "페이지 크기가 너무 큽니다" in error

    def test_validate_pagination_custom_max_size(self):
        """커스텀 최대 페이지 크기 테스트"""
        is_valid, error = validate_pagination(1, 50, max_size=30)
        assert is_valid is False
        assert "페이지 크기가 너무 큽니다" in error


class TestIsSafeFilename:
    """안전한 파일명 검증 테스트"""

    def test_is_safe_filename_valid(self):
        """안전한 파일명 테스트"""
        safe_filenames = [
            "document.pdf",
            "my_file.txt",
            "report-2024.docx",
            "한글파일명.pdf",
            "file123.txt",
        ]
        
        for filename in safe_filenames:
            assert is_safe_filename(filename) is True

    def test_is_safe_filename_dangerous_characters(self):
        """위험한 문자가 포함된 파일명 테스트"""
        dangerous_filenames = [
            "file<script>.txt",
            "document>.pdf",
            'file"name.txt',
            "file|name.txt",
            "file?name.txt",
            "file*name.txt",
        ]
        
        for filename in dangerous_filenames:
            assert is_safe_filename(filename) is False

    def test_is_safe_filename_path_traversal(self):
        """경로 순회 공격 파일명 테스트"""
        dangerous_filenames = [
            "../../../etc/passwd",
            "..\\windows\\system32",
            "file/../../../secret.txt",
        ]
        
        for filename in dangerous_filenames:
            assert is_safe_filename(filename) is False

    def test_is_safe_filename_windows_reserved(self):
        """Windows 예약어 파일명 테스트"""
        reserved_names = [
            "CON.txt",
            "PRN.pdf",
            "AUX.docx",
            "NUL.txt",
            "COM1.txt",
            "LPT1.txt",
        ]
        
        for filename in reserved_names:
            assert is_safe_filename(filename) is False

    def test_is_safe_filename_too_long(self):
        """너무 긴 파일명 테스트"""
        long_filename = "a" * 300 + ".txt"
        assert is_safe_filename(long_filename) is False


class TestGetFileType:
    """파일 타입 확인 테스트"""

    def test_get_file_type_document(self):
        """문서 파일 타입 테스트"""
        document_files = [
            "document.pdf",
            "text.txt",
            "markdown.md",
            "word.docx",
            "web.html",
        ]
        
        for file_path in document_files:
            assert get_file_type(file_path) == 'document'

    def test_get_file_type_image(self):
        """이미지 파일 타입 테스트"""
        image_files = [
            "photo.jpg",
            "image.png",
            "animation.gif",
            "bitmap.bmp",
        ]
        
        for file_path in image_files:
            assert get_file_type(file_path) == 'image'

    def test_get_file_type_archive(self):
        """압축 파일 타입 테스트"""
        archive_files = [
            "archive.zip",
            "backup.tar",
            "compressed.gz",
        ]
        
        for file_path in archive_files:
            assert get_file_type(file_path) == 'archive'

    def test_get_file_type_unknown(self):
        """알 수 없는 파일 타입 테스트"""
        unknown_files = [
            "executable.exe",
            "script.bat",
            "unknown.xyz",
            "no_extension",
        ]
        
        for file_path in unknown_files:
            assert get_file_type(file_path) == 'unknown'

    def test_get_file_type_case_insensitive(self):
        """대소문자 구분 없는 파일 타입 테스트"""
        mixed_case_files = [
            ("Document.PDF", 'document'),
            ("Image.JPG", 'image'),
            ("Archive.ZIP", 'archive'),
        ]
        
        for file_path, expected_type in mixed_case_files:
            assert get_file_type(file_path) == expected_type


class TestConstants:
    """상수 테스트"""

    def test_supported_extensions_not_empty(self):
        """지원되는 확장자 목록이 비어있지 않은지 테스트"""
        assert len(SUPPORTED_DOCUMENT_EXTENSIONS) > 0
        assert len(SUPPORTED_IMAGE_EXTENSIONS) > 0
        assert len(SUPPORTED_ARCHIVE_EXTENSIONS) > 0

    def test_max_file_size_reasonable(self):
        """최대 파일 크기가 합리적인지 테스트"""
        assert MAX_FILE_SIZE > 0
        assert MAX_FILE_SIZE == 100 * 1024 * 1024  # 100MB

    def test_extensions_are_lowercase(self):
        """확장자가 소문자로 정의되어 있는지 테스트"""
        all_extensions = (
            SUPPORTED_DOCUMENT_EXTENSIONS |
            SUPPORTED_IMAGE_EXTENSIONS |
            SUPPORTED_ARCHIVE_EXTENSIONS
        )
        
        for ext in all_extensions:
            assert ext == ext.lower()
            assert ext.startswith('.')


class TestIntegration:
    """통합 테스트"""

    def test_file_validation_workflow(self):
        """파일 검증 워크플로우 테스트"""
        content = b"Test file content for validation workflow"
        
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            # 1. 확장자 검증
            ext_valid, ext_error = validate_file_extension(tmp_file.name)
            assert ext_valid is True
            
            # 2. 크기 검증
            size_valid, size_error = validate_file_size(tmp_file.name)
            assert size_valid is True
            
            # 3. 종합 검증
            file_valid, file_errors = validate_file(tmp_file.name)
            assert file_valid is True
            assert len(file_errors) == 0
            
            # 4. 파일 타입 확인
            file_type = get_file_type(tmp_file.name)
            assert file_type == 'document'
            
            # 5. 안전한 파일명 확인
            filename = Path(tmp_file.name).name
            assert is_safe_filename(filename) is True
        
        Path(tmp_file.name).unlink()

    def test_search_and_pagination_workflow(self):
        """검색 및 페이지네이션 워크플로우 테스트"""
        # 1. 검색 쿼리 검증
        query = "test search query"
        query_valid, query_error = validate_search_query(query)
        assert query_valid is True
        
        # 2. 페이지네이션 검증
        page, size = 1, 20
        pagination_valid, pagination_error = validate_pagination(page, size)
        assert pagination_valid is True
        
        # 3. 텍스트 내용 검증 (검색 결과)
        content = "Search result content"
        content_valid, content_error = validate_text_content(content)
        assert content_valid is True
