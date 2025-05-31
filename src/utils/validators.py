"""
검증 유틸리티

입력값 검증을 위한 함수들을 제공합니다.
"""

import re
from pathlib import Path
from typing import Union, List, Optional
from email_validator import validate_email as _validate_email, EmailNotValidError


# 지원되는 파일 확장자
SUPPORTED_DOCUMENT_EXTENSIONS = {
    '.pdf', '.docx', '.doc', '.txt', '.md', '.rtf',
    '.odt', '.html', '.htm', '.xml', '.json'
}

SUPPORTED_IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'
}

SUPPORTED_ARCHIVE_EXTENSIONS = {
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'
}

# 파일 크기 제한 (바이트)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_BATCH_SIZE = 500 * 1024 * 1024  # 500MB (배치 처리용)


def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    이메일 주소를 검증합니다.
    
    Args:
        email: 검증할 이메일 주소
        
    Returns:
        tuple[bool, Optional[str]]: (유효성, 오류 메시지)
    """
    try:
        # email-validator 라이브러리 사용 (DNS 검증 비활성화)
        validated_email = _validate_email(email, check_deliverability=False)
        return True, None
    except EmailNotValidError as e:
        return False, str(e)
    except Exception as e:
        return False, f"이메일 검증 중 오류가 발생했습니다: {str(e)}"


def validate_file_extension(
    file_path: Union[str, Path], 
    allowed_extensions: Optional[List[str]] = None
) -> tuple[bool, Optional[str]]:
    """
    파일 확장자를 검증합니다.
    
    Args:
        file_path: 파일 경로
        allowed_extensions: 허용된 확장자 목록 (None인 경우 기본 문서 확장자 사용)
        
    Returns:
        tuple[bool, Optional[str]]: (유효성, 오류 메시지)
    """
    file_path = Path(file_path)
    extension = file_path.suffix.lower()
    
    if not extension:
        return False, "파일 확장자가 없습니다"
    
    if allowed_extensions is None:
        allowed_extensions = SUPPORTED_DOCUMENT_EXTENSIONS
    else:
        # 소문자로 변환
        allowed_extensions = {ext.lower() for ext in allowed_extensions}
    
    if extension not in allowed_extensions:
        return False, f"지원하지 않는 파일 형식입니다: {extension}"
    
    return True, None


def validate_file_size(
    file_path: Union[str, Path], 
    max_size: Optional[int] = None
) -> tuple[bool, Optional[str]]:
    """
    파일 크기를 검증합니다.
    
    Args:
        file_path: 파일 경로
        max_size: 최대 파일 크기 (바이트, None인 경우 기본값 사용)
        
    Returns:
        tuple[bool, Optional[str]]: (유효성, 오류 메시지)
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return False, "파일이 존재하지 않습니다"
    
    if max_size is None:
        max_size = MAX_FILE_SIZE
    
    file_size = file_path.stat().st_size
    
    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        file_size_mb = file_size / (1024 * 1024)
        return False, f"파일 크기가 너무 큽니다: {file_size_mb:.1f}MB (최대: {max_size_mb:.1f}MB)"
    
    return True, None


def validate_file(
    file_path: Union[str, Path],
    allowed_extensions: Optional[List[str]] = None,
    max_size: Optional[int] = None
) -> tuple[bool, List[str]]:
    """
    파일을 종합적으로 검증합니다.
    
    Args:
        file_path: 파일 경로
        allowed_extensions: 허용된 확장자 목록
        max_size: 최대 파일 크기 (바이트)
        
    Returns:
        tuple[bool, List[str]]: (유효성, 오류 메시지 목록)
    """
    errors = []
    
    # 파일 존재 여부 확인
    file_path = Path(file_path)
    if not file_path.exists():
        return False, ["파일이 존재하지 않습니다"]
    
    # 확장자 검증
    ext_valid, ext_error = validate_file_extension(file_path, allowed_extensions)
    if not ext_valid:
        errors.append(ext_error)
    
    # 크기 검증
    size_valid, size_error = validate_file_size(file_path, max_size)
    if not size_valid:
        errors.append(size_error)
    
    return len(errors) == 0, errors


def validate_text_content(text: str, min_length: int = 1, max_length: int = 1000000) -> tuple[bool, Optional[str]]:
    """
    텍스트 내용을 검증합니다.
    
    Args:
        text: 검증할 텍스트
        min_length: 최소 길이
        max_length: 최대 길이
        
    Returns:
        tuple[bool, Optional[str]]: (유효성, 오류 메시지)
    """
    if not isinstance(text, str):
        return False, "텍스트가 문자열이 아닙니다"
    
    text_length = len(text.strip())
    
    if text_length < min_length:
        return False, f"텍스트가 너무 짧습니다: {text_length}자 (최소: {min_length}자)"
    
    if text_length > max_length:
        return False, f"텍스트가 너무 깁니다: {text_length}자 (최대: {max_length}자)"
    
    return True, None


def validate_chunk_size(chunk_size: int, min_size: int = 100, max_size: int = 8000) -> tuple[bool, Optional[str]]:
    """
    청크 크기를 검증합니다.
    
    Args:
        chunk_size: 청크 크기
        min_size: 최소 크기
        max_size: 최대 크기
        
    Returns:
        tuple[bool, Optional[str]]: (유효성, 오류 메시지)
    """
    if not isinstance(chunk_size, int) or chunk_size <= 0:
        return False, "청크 크기는 양의 정수여야 합니다"
    
    if chunk_size < min_size:
        return False, f"청크 크기가 너무 작습니다: {chunk_size} (최소: {min_size})"
    
    if chunk_size > max_size:
        return False, f"청크 크기가 너무 큽니다: {chunk_size} (최대: {max_size})"
    
    return True, None


def validate_search_query(query: str, min_length: int = 2, max_length: int = 1000) -> tuple[bool, Optional[str]]:
    """
    검색 쿼리를 검증합니다.
    
    Args:
        query: 검색 쿼리
        min_length: 최소 길이
        max_length: 최대 길이
        
    Returns:
        tuple[bool, Optional[str]]: (유효성, 오류 메시지)
    """
    if not isinstance(query, str):
        return False, "검색 쿼리가 문자열이 아닙니다"
    
    query = query.strip()
    
    if len(query) < min_length:
        return False, f"검색 쿼리가 너무 짧습니다: {len(query)}자 (최소: {min_length}자)"
    
    if len(query) > max_length:
        return False, f"검색 쿼리가 너무 깁니다: {len(query)}자 (최대: {max_length}자)"
    
    # 특수 문자만으로 구성된 쿼리 검증
    if re.match(r'^[^\w\s]+$', query):
        return False, "검색 쿼리에 유효한 문자가 포함되어야 합니다"
    
    return True, None


def validate_pagination(page: int, size: int, max_size: int = 100) -> tuple[bool, Optional[str]]:
    """
    페이지네이션 파라미터를 검증합니다.
    
    Args:
        page: 페이지 번호 (1부터 시작)
        size: 페이지 크기
        max_size: 최대 페이지 크기
        
    Returns:
        tuple[bool, Optional[str]]: (유효성, 오류 메시지)
    """
    if not isinstance(page, int) or page < 1:
        return False, "페이지 번호는 1 이상의 정수여야 합니다"
    
    if not isinstance(size, int) or size < 1:
        return False, "페이지 크기는 1 이상의 정수여야 합니다"
    
    if size > max_size:
        return False, f"페이지 크기가 너무 큽니다: {size} (최대: {max_size})"
    
    return True, None


def is_safe_filename(filename: str) -> bool:
    """
    안전한 파일명인지 검증합니다.
    
    Args:
        filename: 파일명
        
    Returns:
        bool: 안전한 파일명인 경우 True
    """
    # 경로 순회 공격 패턴
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    
    # Windows 금지 문자
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
    if any(char in filename for char in dangerous_chars):
        return False
    
    # Windows 예약어 (확장자 제거 후 검사)
    name_without_ext = filename.split('.')[0].upper()
    windows_reserved = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]
    if name_without_ext in windows_reserved:
        return False
    
    # 파일명 길이 검증
    if len(filename) > 255:
        return False
    
    return True


def get_file_type(file_path: Union[str, Path]) -> str:
    """
    파일 타입을 반환합니다.
    
    Args:
        file_path: 파일 경로
        
    Returns:
        str: 파일 타입 ('document', 'image', 'archive', 'unknown')
    """
    extension = Path(file_path).suffix.lower()
    
    if extension in SUPPORTED_DOCUMENT_EXTENSIONS:
        return 'document'
    elif extension in SUPPORTED_IMAGE_EXTENSIONS:
        return 'image'
    elif extension in SUPPORTED_ARCHIVE_EXTENSIONS:
        return 'archive'
    else:
        return 'unknown'
