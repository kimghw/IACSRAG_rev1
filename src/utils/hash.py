"""
해싱 유틸리티

텍스트 및 파일 해싱을 위한 함수들을 제공합니다.
"""

import hashlib
import hmac
from pathlib import Path
from typing import Union, BinaryIO


def hash_text(text: str, algorithm: str = "sha256") -> str:
    """
    텍스트를 해싱합니다.
    
    Args:
        text: 해싱할 텍스트
        algorithm: 해싱 알고리즘 (기본값: sha256)
        
    Returns:
        str: 16진수 해시값
        
    Raises:
        ValueError: 지원하지 않는 알고리즘인 경우
    """
    try:
        hasher = hashlib.new(algorithm)
        hasher.update(text.encode('utf-8'))
        return hasher.hexdigest()
    except ValueError as e:
        raise ValueError(f"지원하지 않는 해싱 알고리즘: {algorithm}") from e


def hash_file(file_path: Union[str, Path], algorithm: str = "sha256") -> str:
    """
    파일을 해싱합니다.
    
    Args:
        file_path: 파일 경로
        algorithm: 해싱 알고리즘 (기본값: sha256)
        
    Returns:
        str: 16진수 해시값
        
    Raises:
        FileNotFoundError: 파일이 존재하지 않는 경우
        ValueError: 지원하지 않는 알고리즘인 경우
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    
    try:
        hasher = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            # 큰 파일을 위해 청크 단위로 읽기
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
                
        return hasher.hexdigest()
    except ValueError as e:
        raise ValueError(f"지원하지 않는 해싱 알고리즘: {algorithm}") from e


def hash_file_stream(file_stream: BinaryIO, algorithm: str = "sha256") -> str:
    """
    파일 스트림을 해싱합니다.
    
    Args:
        file_stream: 파일 스트림 객체
        algorithm: 해싱 알고리즘 (기본값: sha256)
        
    Returns:
        str: 16진수 해시값
        
    Raises:
        ValueError: 지원하지 않는 알고리즘인 경우
    """
    try:
        hasher = hashlib.new(algorithm)
        
        # 현재 위치 저장
        current_position = file_stream.tell()
        
        # 파일 시작으로 이동
        file_stream.seek(0)
        
        # 청크 단위로 읽어서 해싱
        for chunk in iter(lambda: file_stream.read(8192), b""):
            hasher.update(chunk)
        
        # 원래 위치로 복원
        file_stream.seek(current_position)
        
        return hasher.hexdigest()
    except ValueError as e:
        raise ValueError(f"지원하지 않는 해싱 알고리즘: {algorithm}") from e


def verify_hash(text: str, expected_hash: str, algorithm: str = "sha256") -> bool:
    """
    텍스트의 해시값을 검증합니다.
    
    Args:
        text: 검증할 텍스트
        expected_hash: 예상 해시값
        algorithm: 해싱 알고리즘 (기본값: sha256)
        
    Returns:
        bool: 해시값이 일치하는 경우 True
    """
    actual_hash = hash_text(text, algorithm)
    return hmac.compare_digest(actual_hash, expected_hash)


def verify_file_hash(file_path: Union[str, Path], expected_hash: str, algorithm: str = "sha256") -> bool:
    """
    파일의 해시값을 검증합니다.
    
    Args:
        file_path: 파일 경로
        expected_hash: 예상 해시값
        algorithm: 해싱 알고리즘 (기본값: sha256)
        
    Returns:
        bool: 해시값이 일치하는 경우 True
    """
    actual_hash = hash_file(file_path, algorithm)
    return hmac.compare_digest(actual_hash, expected_hash)


def generate_content_hash(content: str) -> str:
    """
    콘텐츠의 고유 해시를 생성합니다.
    중복 제거에 사용됩니다.
    
    Args:
        content: 해싱할 콘텐츠
        
    Returns:
        str: SHA-256 해시값
    """
    # 공백 정규화 후 해싱
    normalized_content = ' '.join(content.split())
    return hash_text(normalized_content, "sha256")


def generate_chunk_hash(text: str, metadata: dict = None) -> str:
    """
    텍스트 청크의 해시를 생성합니다.
    
    Args:
        text: 청크 텍스트
        metadata: 메타데이터 (선택사항)
        
    Returns:
        str: 청크 해시값
    """
    # 텍스트와 메타데이터를 결합하여 해싱
    content = text
    if metadata:
        # 메타데이터를 정렬된 문자열로 변환
        metadata_str = str(sorted(metadata.items()))
        content = f"{text}|{metadata_str}"
    
    return generate_content_hash(content)


def get_supported_algorithms() -> list[str]:
    """
    지원되는 해싱 알고리즘 목록을 반환합니다.
    
    Returns:
        list[str]: 지원되는 알고리즘 목록
    """
    return list(hashlib.algorithms_available)
