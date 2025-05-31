"""
Document Repository 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.modules.ingest.infrastructure.repositories.document_repository import DocumentRepository
from src.modules.ingest.domain.entities import Document, DocumentMetadata, DocumentStatus, DocumentType
from src.core.exceptions import EntityNotFoundError, DuplicateEntityError, DatabaseError


@pytest.fixture
def mock_database():
    """Mock MongoDB 데이터베이스"""
    database = MagicMock()
    collection = AsyncMock()
    database.documents = collection
    return database


@pytest.fixture
def document_repository(mock_database):
    """Document Repository 인스턴스"""
    return DocumentRepository(mock_database)


@pytest.fixture
def sample_document():
    """테스트용 문서 엔티티"""
    user_id = uuid4()
    metadata = DocumentMetadata(file_size=1024, mime_type="application/pdf")
    
    return Document.create(
        user_id=user_id,
        filename="test.pdf",
        original_filename="test.pdf",
        file_path="/uploads/test.pdf",
        document_type=DocumentType.PDF,
        metadata=metadata,
        tags=["test"]
    )


class TestDocumentRepositoryBasicOperations:
    """기본 CRUD 연산 테스트"""

    @pytest.mark.asyncio
    async def test_save_document_success(self, document_repository, sample_document):
        """문서 저장 성공 테스트"""
        # Given
        document_repository.collection.insert_one = AsyncMock()
        
        # When
        result = await document_repository.save(sample_document)
        
        # Then
        assert result == sample_document
        document_repository.collection.insert_one.assert_called_once()
        
        # 호출된 인자 확인
        call_args = document_repository.collection.insert_one.call_args[0][0]
        assert call_args["_id"] == str(sample_document.id)
        assert call_args["filename"] == "test.pdf"
        assert "id" not in call_args  # id가 _id로 변경되었는지 확인

    @pytest.mark.asyncio
    async def test_save_document_duplicate_error(self, document_repository, sample_document):
        """중복 문서 저장 에러 테스트"""
        # Given
        from pymongo.errors import DuplicateKeyError
        document_repository.collection.insert_one = AsyncMock(
            side_effect=DuplicateKeyError("Duplicate key")
        )
        
        # When & Then
        with pytest.raises(DuplicateEntityError):
            await document_repository.save(sample_document)

    @pytest.mark.asyncio
    async def test_find_by_id_success(self, document_repository, sample_document):
        """ID로 문서 조회 성공 테스트"""
        # Given
        document_dict = sample_document.to_dict()
        document_dict["_id"] = document_dict.pop("id")
        
        document_repository.collection.find_one = AsyncMock(return_value=document_dict)
        
        # When
        result = await document_repository.find_by_id(sample_document.id)
        
        # Then
        assert result is not None
        assert result.id == sample_document.id
        assert result.filename == sample_document.filename
        document_repository.collection.find_one.assert_called_once_with(
            {"_id": str(sample_document.id)}
        )

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, document_repository):
        """ID로 문서 조회 실패 테스트"""
        # Given
        document_id = uuid4()
        document_repository.collection.find_one = AsyncMock(return_value=None)
        
        # When
        result = await document_repository.find_by_id(document_id)
        
        # Then
        assert result is None

    @pytest.mark.asyncio
    async def test_update_document_success(self, document_repository, sample_document):
        """문서 업데이트 성공 테스트"""
        # Given
        mock_result = MagicMock()
        mock_result.matched_count = 1
        document_repository.collection.replace_one = AsyncMock(return_value=mock_result)
        
        # When
        result = await document_repository.update(sample_document)
        
        # Then
        assert result == sample_document
        document_repository.collection.replace_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_document_not_found(self, document_repository, sample_document):
        """존재하지 않는 문서 업데이트 테스트"""
        # Given
        mock_result = MagicMock()
        mock_result.matched_count = 0
        document_repository.collection.replace_one = AsyncMock(return_value=mock_result)
        
        # When & Then
        with pytest.raises(EntityNotFoundError):
            await document_repository.update(sample_document)

    @pytest.mark.asyncio
    async def test_delete_by_id_success(self, document_repository):
        """문서 삭제 성공 테스트"""
        # Given
        document_id = uuid4()
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        document_repository.collection.delete_one = AsyncMock(return_value=mock_result)
        
        # When
        result = await document_repository.delete_by_id(document_id)
        
        # Then
        assert result is True
        document_repository.collection.delete_one.assert_called_once_with(
            {"_id": str(document_id)}
        )

    @pytest.mark.asyncio
    async def test_delete_by_id_not_found(self, document_repository):
        """존재하지 않는 문서 삭제 테스트"""
        # Given
        document_id = uuid4()
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        document_repository.collection.delete_one = AsyncMock(return_value=mock_result)
        
        # When
        result = await document_repository.delete_by_id(document_id)
        
        # Then
        assert result is False


class TestDocumentRepositoryQueries:
    """쿼리 관련 테스트"""

    @pytest.mark.asyncio
    async def test_find_by_user_id(self, document_repository, sample_document):
        """사용자 ID로 문서 목록 조회 테스트"""
        # Given
        user_id = sample_document.user_id
        document_dict = sample_document.to_dict()
        document_dict["_id"] = document_dict.pop("id")
        
        # Mock cursor 설정
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        
        # async iteration을 위한 설정
        async def mock_aiter(self):
            for doc in [document_dict]:
                yield doc
        mock_cursor.__aiter__ = mock_aiter
        
        document_repository.collection.find = MagicMock(return_value=mock_cursor)
        
        # When
        result = await document_repository.find_by_user_id(user_id, limit=10, offset=0)
        
        # Then
        assert len(result) == 1
        assert result[0].id == sample_document.id
        document_repository.collection.find.assert_called_once_with(
            {"user_id": str(user_id)}
        )

    @pytest.mark.asyncio
    async def test_find_by_user_id_with_filters(self, document_repository):
        """필터가 있는 사용자 문서 조회 테스트"""
        # Given
        user_id = uuid4()
        status = DocumentStatus.PROCESSED
        document_type = DocumentType.PDF
        
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        
        async def mock_aiter(self):
            return
            yield  # unreachable
        mock_cursor.__aiter__ = mock_aiter
        
        document_repository.collection.find = MagicMock(return_value=mock_cursor)
        
        # When
        await document_repository.find_by_user_id(
            user_id, status=status, document_type=document_type
        )
        
        # Then
        expected_query = {
            "user_id": str(user_id),
            "status": status.value,
            "document_type": document_type.value
        }
        document_repository.collection.find.assert_called_once_with(expected_query)

    @pytest.mark.asyncio
    async def test_find_by_status(self, document_repository, sample_document):
        """상태로 문서 조회 테스트"""
        # Given
        status = DocumentStatus.UPLOADED
        document_dict = sample_document.to_dict()
        document_dict["_id"] = document_dict.pop("id")
        
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        
        async def mock_aiter(self):
            for doc in [document_dict]:
                yield doc
        mock_cursor.__aiter__ = mock_aiter
        
        document_repository.collection.find = MagicMock(return_value=mock_cursor)
        
        # When
        result = await document_repository.find_by_status(status)
        
        # Then
        assert len(result) == 1
        document_repository.collection.find.assert_called_once_with(
            {"status": status.value}
        )

    @pytest.mark.asyncio
    async def test_find_by_parent_id(self, document_repository, sample_document):
        """부모 ID로 문서 조회 테스트"""
        # Given
        parent_id = uuid4()
        document_dict = sample_document.to_dict()
        document_dict["_id"] = document_dict.pop("id")
        
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        
        async def mock_aiter(self):
            for doc in [document_dict]:
                yield doc
        mock_cursor.__aiter__ = mock_aiter
        
        document_repository.collection.find = MagicMock(return_value=mock_cursor)
        
        # When
        result = await document_repository.find_by_parent_id(parent_id)
        
        # Then
        assert len(result) == 1
        document_repository.collection.find.assert_called_once_with(
            {"parent_id": str(parent_id)}
        )

    @pytest.mark.asyncio
    async def test_search_by_filename(self, document_repository, sample_document):
        """파일명으로 문서 검색 테스트"""
        # Given
        user_id = sample_document.user_id
        filename_pattern = "test"
        document_dict = sample_document.to_dict()
        document_dict["_id"] = document_dict.pop("id")
        
        mock_cursor = MagicMock()
        mock_cursor.limit.return_value = mock_cursor
        
        async def mock_aiter(self):
            for doc in [document_dict]:
                yield doc
        mock_cursor.__aiter__ = mock_aiter
        
        document_repository.collection.find = MagicMock(return_value=mock_cursor)
        
        # When
        result = await document_repository.search_by_filename(user_id, filename_pattern)
        
        # Then
        assert len(result) == 1
        expected_query = {
            "user_id": str(user_id),
            "$text": {"$search": filename_pattern}
        }
        document_repository.collection.find.assert_called_once_with(expected_query)

    @pytest.mark.asyncio
    async def test_count_by_user_id(self, document_repository):
        """사용자 문서 수 조회 테스트"""
        # Given
        user_id = uuid4()
        expected_count = 5
        document_repository.collection.count_documents = AsyncMock(
            return_value=expected_count
        )
        
        # When
        result = await document_repository.count_by_user_id(user_id)
        
        # Then
        assert result == expected_count
        document_repository.collection.count_documents.assert_called_once_with(
            {"user_id": str(user_id)}
        )

    @pytest.mark.asyncio
    async def test_count_by_user_id_with_status(self, document_repository):
        """상태 필터가 있는 사용자 문서 수 조회 테스트"""
        # Given
        user_id = uuid4()
        status = DocumentStatus.PROCESSED
        expected_count = 3
        document_repository.collection.count_documents = AsyncMock(
            return_value=expected_count
        )
        
        # When
        result = await document_repository.count_by_user_id(user_id, status=status)
        
        # Then
        assert result == expected_count
        expected_query = {
            "user_id": str(user_id),
            "status": status.value
        }
        document_repository.collection.count_documents.assert_called_once_with(
            expected_query
        )


class TestDocumentRepositoryStatusUpdate:
    """상태 업데이트 관련 테스트"""

    @pytest.mark.asyncio
    async def test_update_status_success(self, document_repository):
        """문서 상태 업데이트 성공 테스트"""
        # Given
        document_id = uuid4()
        status = DocumentStatus.PROCESSING
        
        mock_result = MagicMock()
        mock_result.matched_count = 1
        document_repository.collection.update_one = AsyncMock(return_value=mock_result)
        
        # When
        result = await document_repository.update_status(document_id, status)
        
        # Then
        assert result is True
        document_repository.collection.update_one.assert_called_once()
        
        # 호출된 인자 확인
        call_args = document_repository.collection.update_one.call_args
        assert call_args[0][0] == {"_id": str(document_id)}
        update_data = call_args[0][1]["$set"]
        assert update_data["status"] == status.value
        assert "updated_at" in update_data

    @pytest.mark.asyncio
    async def test_update_status_processed(self, document_repository):
        """처리 완료 상태 업데이트 테스트"""
        # Given
        document_id = uuid4()
        status = DocumentStatus.PROCESSED
        
        mock_result = MagicMock()
        mock_result.matched_count = 1
        document_repository.collection.update_one = AsyncMock(return_value=mock_result)
        
        # When
        await document_repository.update_status(document_id, status)
        
        # Then
        call_args = document_repository.collection.update_one.call_args
        update_data = call_args[0][1]["$set"]
        assert update_data["status"] == status.value
        assert "processed_at" in update_data

    @pytest.mark.asyncio
    async def test_update_status_with_error(self, document_repository):
        """에러 메시지와 함께 상태 업데이트 테스트"""
        # Given
        document_id = uuid4()
        status = DocumentStatus.FAILED
        error_message = "Processing failed"
        
        mock_result = MagicMock()
        mock_result.matched_count = 1
        document_repository.collection.update_one = AsyncMock(return_value=mock_result)
        
        # When
        await document_repository.update_status(document_id, status, error_message)
        
        # Then
        call_args = document_repository.collection.update_one.call_args
        update_data = call_args[0][1]["$set"]
        assert update_data["status"] == status.value
        assert update_data["error_message"] == error_message

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, document_repository):
        """존재하지 않는 문서 상태 업데이트 테스트"""
        # Given
        document_id = uuid4()
        status = DocumentStatus.PROCESSING
        
        mock_result = MagicMock()
        mock_result.matched_count = 0
        document_repository.collection.update_one = AsyncMock(return_value=mock_result)
        
        # When
        result = await document_repository.update_status(document_id, status)
        
        # Then
        assert result is False


class TestDocumentRepositoryStatistics:
    """통계 관련 테스트"""

    @pytest.mark.asyncio
    async def test_get_processing_statistics_all_users(self, document_repository):
        """전체 사용자 처리 통계 조회 테스트"""
        # Given
        mock_stats = [
            {"_id": "uploaded", "count": 5},
            {"_id": "processed", "count": 10},
            {"_id": "failed", "count": 2}
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__.return_value = mock_stats
        document_repository.collection.aggregate = MagicMock(return_value=mock_cursor)
        
        # When
        result = await document_repository.get_processing_statistics()
        
        # Then
        assert result["uploaded"] == 5
        assert result["processed"] == 10
        assert result["failed"] == 2
        assert result["parsing"] == 0  # 없는 상태는 0으로 초기화
        
        # 집계 파이프라인 확인
        call_args = document_repository.collection.aggregate.call_args[0][0]
        assert call_args[0]["$match"] == {}  # 전체 사용자

    @pytest.mark.asyncio
    async def test_get_processing_statistics_specific_user(self, document_repository):
        """특정 사용자 처리 통계 조회 테스트"""
        # Given
        user_id = uuid4()
        mock_stats = [
            {"_id": "uploaded", "count": 3},
            {"_id": "processed", "count": 7}
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__.return_value = mock_stats
        document_repository.collection.aggregate = MagicMock(return_value=mock_cursor)
        
        # When
        result = await document_repository.get_processing_statistics(user_id)
        
        # Then
        assert result["uploaded"] == 3
        assert result["processed"] == 7
        
        # 집계 파이프라인 확인
        call_args = document_repository.collection.aggregate.call_args[0][0]
        assert call_args[0]["$match"] == {"user_id": str(user_id)}


class TestDocumentRepositoryIndexes:
    """인덱스 관련 테스트"""

    @pytest.mark.asyncio
    async def test_create_indexes_success(self, document_repository):
        """인덱스 생성 성공 테스트"""
        # Given
        document_repository.collection.create_index = AsyncMock()
        
        # When
        await document_repository.create_indexes()
        
        # Then
        # create_index가 여러 번 호출되었는지 확인
        assert document_repository.collection.create_index.call_count >= 5

    @pytest.mark.asyncio
    async def test_create_indexes_failure(self, document_repository):
        """인덱스 생성 실패 테스트"""
        # Given
        document_repository.collection.create_index = AsyncMock(
            side_effect=Exception("Index creation failed")
        )
        
        # When & Then
        with pytest.raises(DatabaseError):
            await document_repository.create_indexes()


class TestDocumentRepositoryErrorHandling:
    """에러 처리 테스트"""

    @pytest.mark.asyncio
    async def test_database_error_handling(self, document_repository, sample_document):
        """데이터베이스 에러 처리 테스트"""
        # Given
        document_repository.collection.insert_one = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        
        # When & Then
        with pytest.raises(DatabaseError):
            await document_repository.save(sample_document)

    @pytest.mark.asyncio
    async def test_find_error_handling(self, document_repository):
        """조회 에러 처리 테스트"""
        # Given
        document_id = uuid4()
        document_repository.collection.find_one = AsyncMock(
            side_effect=Exception("Query failed")
        )
        
        # When & Then
        with pytest.raises(DatabaseError):
            await document_repository.find_by_id(document_id)


class TestDocumentRepositoryEdgeCases:
    """엣지 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_empty_query_results(self, document_repository):
        """빈 쿼리 결과 테스트"""
        # Given
        user_id = uuid4()
        
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        
        async def mock_aiter(self):
            return
            yield  # unreachable
        mock_cursor.__aiter__ = mock_aiter
        
        document_repository.collection.find = MagicMock(return_value=mock_cursor)
        
        # When
        result = await document_repository.find_by_user_id(user_id)
        
        # Then
        assert result == []

    @pytest.mark.asyncio
    async def test_large_limit_values(self, document_repository):
        """큰 limit 값 테스트"""
        # Given
        user_id = uuid4()
        large_limit = 10000
        
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        
        async def mock_aiter(self):
            return
            yield  # unreachable
        mock_cursor.__aiter__ = mock_aiter
        
        document_repository.collection.find = MagicMock(return_value=mock_cursor)
        
        # When
        await document_repository.find_by_user_id(user_id, limit=large_limit)
        
        # Then
        mock_cursor.limit.assert_called_with(large_limit)

    @pytest.mark.asyncio
    async def test_zero_count_result(self, document_repository):
        """0개 문서 카운트 테스트"""
        # Given
        user_id = uuid4()
        document_repository.collection.count_documents = AsyncMock(return_value=0)
        
        # When
        result = await document_repository.count_by_user_id(user_id)
        
        # Then
        assert result == 0
