"""
문서 저장소 구현

MongoDB를 사용한 문서 엔티티 영속성 관리를 담당합니다.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from src.modules.ingest.domain.entities import Document, DocumentStatus, DocumentType
from src.core.exceptions import (
    EntityNotFoundError,
    DuplicateEntityError,
    DatabaseError
)
from src.core.logging import get_logger

logger = get_logger(__name__)


class DocumentRepository:
    """문서 저장소"""

    def __init__(self, database: AsyncIOMotorDatabase):
        """
        Args:
            database: MongoDB 데이터베이스 인스턴스
        """
        self.database = database
        self.collection: AsyncIOMotorCollection = database.documents

    async def create_indexes(self) -> None:
        """인덱스 생성"""
        try:
            # 복합 인덱스 생성
            await self.collection.create_index([
                ("user_id", ASCENDING),
                ("created_at", DESCENDING)
            ])
            
            # 단일 필드 인덱스
            await self.collection.create_index("status")
            await self.collection.create_index("document_type")
            await self.collection.create_index("filename")
            await self.collection.create_index("parent_id")
            
            # 텍스트 검색 인덱스
            await self.collection.create_index([
                ("filename", "text"),
                ("original_filename", "text"),
                ("tags", "text")
            ])
            
            logger.info("Document collection indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise DatabaseError(f"Failed to create indexes: {e}")

    async def save(self, document: Document) -> Document:
        """
        문서 저장
        
        Args:
            document: 저장할 문서 엔티티
            
        Returns:
            Document: 저장된 문서 엔티티
            
        Raises:
            DuplicateEntityError: 중복된 문서 ID인 경우
            DatabaseError: 데이터베이스 오류
        """
        try:
            document_dict = document.to_dict()
            
            # MongoDB에서 _id 필드로 사용하기 위해 id를 _id로 변경
            document_dict["_id"] = document_dict.pop("id")
            
            await self.collection.insert_one(document_dict)
            
            logger.info(f"Document saved successfully: {document.id}")
            return document
            
        except DuplicateKeyError:
            logger.warning(f"Duplicate document ID: {document.id}")
            raise DuplicateEntityError(f"Document with ID {document.id} already exists")
        except Exception as e:
            logger.error(f"Failed to save document {document.id}: {e}")
            raise DatabaseError(f"Failed to save document: {e}")

    async def update(self, document: Document) -> Document:
        """
        문서 업데이트
        
        Args:
            document: 업데이트할 문서 엔티티
            
        Returns:
            Document: 업데이트된 문서 엔티티
            
        Raises:
            EntityNotFoundError: 문서를 찾을 수 없는 경우
            DatabaseError: 데이터베이스 오류
        """
        try:
            document_dict = document.to_dict()
            document_dict["_id"] = document_dict.pop("id")
            
            result = await self.collection.replace_one(
                {"_id": str(document.id)},
                document_dict
            )
            
            if result.matched_count == 0:
                raise EntityNotFoundError(f"Document with ID {document.id} not found")
            
            logger.info(f"Document updated successfully: {document.id}")
            return document
            
        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update document {document.id}: {e}")
            raise DatabaseError(f"Failed to update document: {e}")

    async def find_by_id(self, document_id: UUID) -> Optional[Document]:
        """
        ID로 문서 조회
        
        Args:
            document_id: 문서 ID
            
        Returns:
            Optional[Document]: 문서 엔티티 또는 None
            
        Raises:
            DatabaseError: 데이터베이스 오류
        """
        try:
            document_dict = await self.collection.find_one({"_id": str(document_id)})
            
            if document_dict is None:
                return None
            
            # _id를 id로 변경
            document_dict["id"] = document_dict.pop("_id")
            
            return Document.from_dict(document_dict)
            
        except Exception as e:
            logger.error(f"Failed to find document {document_id}: {e}")
            raise DatabaseError(f"Failed to find document: {e}")

    async def find_by_user_id(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
        status: Optional[DocumentStatus] = None,
        document_type: Optional[DocumentType] = None
    ) -> List[Document]:
        """
        사용자 ID로 문서 목록 조회
        
        Args:
            user_id: 사용자 ID
            limit: 조회 제한 수
            offset: 조회 시작 위치
            status: 문서 상태 필터 (선택사항)
            document_type: 문서 유형 필터 (선택사항)
            
        Returns:
            List[Document]: 문서 목록
            
        Raises:
            DatabaseError: 데이터베이스 오류
        """
        try:
            # 쿼리 조건 구성
            query = {"user_id": str(user_id)}
            
            if status:
                query["status"] = status.value
            
            if document_type:
                query["document_type"] = document_type.value
            
            # 쿼리 실행
            cursor = self.collection.find(query).sort("created_at", DESCENDING)
            cursor = cursor.skip(offset).limit(limit)
            
            documents = []
            async for document_dict in cursor:
                document_dict["id"] = document_dict.pop("_id")
                documents.append(Document.from_dict(document_dict))
            
            logger.info(f"Found {len(documents)} documents for user {user_id}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to find documents for user {user_id}: {e}")
            raise DatabaseError(f"Failed to find documents: {e}")

    async def find_by_status(
        self,
        status: DocumentStatus,
        limit: int = 100,
        offset: int = 0
    ) -> List[Document]:
        """
        상태로 문서 목록 조회
        
        Args:
            status: 문서 상태
            limit: 조회 제한 수
            offset: 조회 시작 위치
            
        Returns:
            List[Document]: 문서 목록
            
        Raises:
            DatabaseError: 데이터베이스 오류
        """
        try:
            cursor = self.collection.find({"status": status.value})
            cursor = cursor.sort("created_at", ASCENDING).skip(offset).limit(limit)
            
            documents = []
            async for document_dict in cursor:
                document_dict["id"] = document_dict.pop("_id")
                documents.append(Document.from_dict(document_dict))
            
            logger.info(f"Found {len(documents)} documents with status {status.value}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to find documents with status {status.value}: {e}")
            raise DatabaseError(f"Failed to find documents: {e}")

    async def find_by_parent_id(self, parent_id: UUID) -> List[Document]:
        """
        부모 ID로 문서 목록 조회 (첨부파일 등)
        
        Args:
            parent_id: 부모 문서 ID
            
        Returns:
            List[Document]: 자식 문서 목록
            
        Raises:
            DatabaseError: 데이터베이스 오류
        """
        try:
            cursor = self.collection.find({"parent_id": str(parent_id)})
            cursor = cursor.sort("created_at", ASCENDING)
            
            documents = []
            async for document_dict in cursor:
                document_dict["id"] = document_dict.pop("_id")
                documents.append(Document.from_dict(document_dict))
            
            logger.info(f"Found {len(documents)} child documents for parent {parent_id}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to find child documents for parent {parent_id}: {e}")
            raise DatabaseError(f"Failed to find child documents: {e}")

    async def search_by_filename(
        self,
        user_id: UUID,
        filename_pattern: str,
        limit: int = 50
    ) -> List[Document]:
        """
        파일명으로 문서 검색
        
        Args:
            user_id: 사용자 ID
            filename_pattern: 파일명 패턴
            limit: 조회 제한 수
            
        Returns:
            List[Document]: 검색된 문서 목록
            
        Raises:
            DatabaseError: 데이터베이스 오류
        """
        try:
            query = {
                "user_id": str(user_id),
                "$text": {"$search": filename_pattern}
            }
            
            cursor = self.collection.find(query).limit(limit)
            
            documents = []
            async for document_dict in cursor:
                document_dict["id"] = document_dict.pop("_id")
                documents.append(Document.from_dict(document_dict))
            
            logger.info(f"Found {len(documents)} documents matching '{filename_pattern}'")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to search documents with pattern '{filename_pattern}': {e}")
            raise DatabaseError(f"Failed to search documents: {e}")

    async def count_by_user_id(
        self,
        user_id: UUID,
        status: Optional[DocumentStatus] = None
    ) -> int:
        """
        사용자의 문서 수 조회
        
        Args:
            user_id: 사용자 ID
            status: 문서 상태 필터 (선택사항)
            
        Returns:
            int: 문서 수
            
        Raises:
            DatabaseError: 데이터베이스 오류
        """
        try:
            query = {"user_id": str(user_id)}
            
            if status:
                query["status"] = status.value
            
            count = await self.collection.count_documents(query)
            
            logger.info(f"User {user_id} has {count} documents")
            return count
            
        except Exception as e:
            logger.error(f"Failed to count documents for user {user_id}: {e}")
            raise DatabaseError(f"Failed to count documents: {e}")

    async def delete_by_id(self, document_id: UUID) -> bool:
        """
        ID로 문서 삭제
        
        Args:
            document_id: 문서 ID
            
        Returns:
            bool: 삭제 성공 여부
            
        Raises:
            DatabaseError: 데이터베이스 오류
        """
        try:
            result = await self.collection.delete_one({"_id": str(document_id)})
            
            if result.deleted_count > 0:
                logger.info(f"Document deleted successfully: {document_id}")
                return True
            else:
                logger.warning(f"Document not found for deletion: {document_id}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise DatabaseError(f"Failed to delete document: {e}")

    async def update_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """
        문서 상태 업데이트
        
        Args:
            document_id: 문서 ID
            status: 새로운 상태
            error_message: 에러 메시지 (선택사항)
            
        Returns:
            bool: 업데이트 성공 여부
            
        Raises:
            DatabaseError: 데이터베이스 오류
        """
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if status == DocumentStatus.PROCESSED:
                update_data["processed_at"] = datetime.utcnow().isoformat()
            
            if error_message:
                update_data["error_message"] = error_message
            elif status != DocumentStatus.FAILED:
                update_data["error_message"] = None
            
            result = await self.collection.update_one(
                {"_id": str(document_id)},
                {"$set": update_data}
            )
            
            if result.matched_count > 0:
                logger.info(f"Document status updated: {document_id} -> {status.value}")
                return True
            else:
                logger.warning(f"Document not found for status update: {document_id}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to update document status {document_id}: {e}")
            raise DatabaseError(f"Failed to update document status: {e}")

    async def get_processing_statistics(self, user_id: Optional[UUID] = None) -> Dict[str, int]:
        """
        처리 통계 조회
        
        Args:
            user_id: 사용자 ID (선택사항, None이면 전체 통계)
            
        Returns:
            Dict[str, int]: 상태별 문서 수
            
        Raises:
            DatabaseError: 데이터베이스 오류
        """
        try:
            match_stage = {}
            if user_id:
                match_stage["user_id"] = str(user_id)
            
            pipeline = [
                {"$match": match_stage},
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }}
            ]
            
            result = {}
            async for doc in self.collection.aggregate(pipeline):
                result[doc["_id"]] = doc["count"]
            
            # 모든 상태에 대해 0으로 초기화
            for status in DocumentStatus:
                if status.value not in result:
                    result[status.value] = 0
            
            logger.info(f"Processing statistics retrieved for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get processing statistics: {e}")
            raise DatabaseError(f"Failed to get processing statistics: {e}")
    
    async def find_with_filters(
        self,
        filters: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> tuple[List[Document], int]:
        """
        필터 조건으로 문서 목록 조회
        
        Args:
            filters: 필터 조건
            limit: 조회 제한 수
            offset: 조회 시작 위치
            sort_by: 정렬 기준 필드
            sort_order: 정렬 순서 (asc/desc)
            
        Returns:
            tuple[List[Document], int]: (문서 목록, 전체 개수)
            
        Raises:
            DatabaseError: 데이터베이스 오류
        """
        try:
            # MongoDB 쿼리 조건 구성
            query = {}
            for key, value in filters.items():
                if key == "user_id":
                    query["user_id"] = str(value)
                elif key == "status":
                    if isinstance(value, dict) and "$in" in value:
                        # 다중 상태 필터
                        query["status"] = value
                    else:
                        # 단일 상태 필터
                        query["status"] = value.value if hasattr(value, 'value') else value
                elif key == "document_type":
                    query["document_type"] = value.value if hasattr(value, 'value') else value
                else:
                    query[key] = value
            
            # 전체 개수 조회
            total_count = await self.collection.count_documents(query)
            
            # 정렬 조건 설정
            sort_direction = ASCENDING if sort_order == "asc" else DESCENDING
            
            # 문서 목록 조회
            cursor = self.collection.find(query).sort(sort_by, sort_direction).skip(offset).limit(limit)
            
            documents = []
            async for doc_data in cursor:
                doc_data["id"] = doc_data.pop("_id")
                document = Document.from_dict(doc_data)
                documents.append(document)
            
            logger.info(f"Found {len(documents)} documents with filters, total: {total_count}")
            return documents, total_count
            
        except Exception as e:
            logger.error(f"Failed to find documents with filters: {e}")
            raise DatabaseError(f"Failed to find documents with filters: {e}")
    
    async def count_by_status(self, user_id: UUID) -> Dict[str, int]:
        """
        사용자의 문서 상태별 개수 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            Dict[str, int]: 상태별 문서 개수
            
        Raises:
            DatabaseError: 데이터베이스 오류
        """
        try:
            pipeline = [
                {"$match": {"user_id": str(user_id)}},
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            result = {}
            async for doc in self.collection.aggregate(pipeline):
                result[doc["_id"]] = doc["count"]
            
            # 모든 상태에 대해 0으로 초기화
            for status in DocumentStatus:
                if status.value not in result:
                    result[status.value] = 0
            
            logger.info(f"Status counts retrieved for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to count documents by status for user {user_id}: {e}")
            raise DatabaseError(f"Failed to count documents by status: {e}")
