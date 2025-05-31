"""
이벤트 발행 포트 인터페이스
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from uuid import UUID


class EventPublisherPort(ABC):
    """
    이벤트 발행을 위한 포트 인터페이스
    
    외부 메시징 시스템(Kafka 등)과의 결합도를 낮추기 위한 추상화 계층
    """
    
    @abstractmethod
    async def publish_document_uploaded(
        self,
        document_id: UUID,
        user_id: UUID,
        filename: str,
        document_type: str,
        file_path: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        문서 업로드 이벤트 발행
        
        Args:
            document_id: 문서 ID
            user_id: 사용자 ID
            filename: 파일명
            document_type: 문서 유형
            file_path: 파일 경로
            metadata: 메타데이터
        """
        pass
    
    @abstractmethod
    async def publish_document_processing_failed(
        self,
        document_id: UUID,
        user_id: UUID,
        error_message: str,
        error_code: str = None
    ) -> None:
        """
        문서 처리 실패 이벤트 발행
        
        Args:
            document_id: 문서 ID
            user_id: 사용자 ID
            error_message: 에러 메시지
            error_code: 에러 코드 (선택사항)
        """
        pass
    
    @abstractmethod
    async def publish_email_parsed(
        self,
        user_id: UUID,
        main_document_id: UUID,
        attachment_document_ids: List[UUID],
        email_metadata: Dict[str, Any]
    ) -> None:
        """
        이메일 파싱 완료 이벤트 발행
        
        Args:
            user_id: 사용자 ID
            main_document_id: 메인 문서 ID (이메일 본문)
            attachment_document_ids: 첨부파일 문서 ID 목록
            email_metadata: 이메일 메타데이터
        """
        pass


class FileStoragePort(ABC):
    """
    파일 저장소 포트 인터페이스
    
    파일 시스템, S3 등 다양한 저장소와의 결합도를 낮추기 위한 추상화 계층
    """
    
    @abstractmethod
    async def save_file(
        self,
        file_content: bytes,
        filename: str,
        user_id: UUID,
        content_type: str = None
    ) -> str:
        """
        파일 저장
        
        Args:
            file_content: 파일 내용
            filename: 파일명
            user_id: 사용자 ID
            content_type: 콘텐츠 타입 (선택사항)
            
        Returns:
            str: 저장된 파일 경로
        """
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """
        파일 삭제
        
        Args:
            file_path: 파일 경로
            
        Returns:
            bool: 삭제 성공 여부
        """
        pass
    
    @abstractmethod
    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        파일 정보 조회
        
        Args:
            file_path: 파일 경로
            
        Returns:
            Dict[str, Any]: 파일 정보 (크기, 수정일 등)
        """
        pass
