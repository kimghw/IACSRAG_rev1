"""
ID 생성 유틸리티

UUID 및 다양한 형태의 고유 ID를 생성하는 함수들을 제공합니다.
"""

import uuid
import secrets
import string
from datetime import datetime
from typing import Optional


def generate_uuid() -> str:
    """
    표준 UUID4를 생성합니다.
    
    Returns:
        str: UUID4 문자열 (하이픈 포함)
    """
    return str(uuid.uuid4())


def generate_uuid_object() -> uuid.UUID:
    """
    표준 UUID4 객체를 생성합니다.
    
    Returns:
        uuid.UUID: UUID4 객체
    """
    return uuid.uuid4()


def generate_short_id(length: int = 8) -> str:
    """
    짧은 랜덤 ID를 생성합니다.
    
    Args:
        length: ID 길이 (기본값: 8)
        
    Returns:
        str: 영숫자로 구성된 랜덤 ID
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_document_id(prefix: Optional[str] = None) -> str:
    """
    문서용 고유 ID를 생성합니다.
    
    Args:
        prefix: ID 접두사 (선택사항)
        
    Returns:
        str: 문서 ID (예: doc_20240531_abc123def)
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    random_suffix = generate_short_id(6)
    
    if prefix:
        return f"{prefix}_{timestamp}_{random_suffix}"
    else:
        return f"doc_{timestamp}_{random_suffix}"


def generate_chunk_id(document_id: str, chunk_index: int) -> str:
    """
    청크용 고유 ID를 생성합니다.
    
    Args:
        document_id: 문서 ID
        chunk_index: 청크 인덱스
        
    Returns:
        str: 청크 ID (예: doc_123_chunk_001)
    """
    return f"{document_id}_chunk_{chunk_index:03d}"


def generate_user_id() -> str:
    """
    사용자용 고유 ID를 생성합니다.
    
    Returns:
        str: 사용자 ID (예: user_abc123def456)
    """
    return f"user_{generate_short_id(12)}"


def generate_session_id() -> str:
    """
    세션용 고유 ID를 생성합니다.
    
    Returns:
        str: 세션 ID (예: sess_abc123def456)
    """
    return f"sess_{generate_short_id(16)}"


def is_valid_uuid(value: str) -> bool:
    """
    유효한 UUID인지 검증합니다.
    
    Args:
        value: 검증할 문자열
        
    Returns:
        bool: 유효한 UUID인 경우 True
    """
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False
