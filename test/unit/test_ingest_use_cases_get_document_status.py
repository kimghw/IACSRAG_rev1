"""
UC-03: 문서 상태 조회 유즈케이스 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from src.modules.ingest.application.use_cases.get_document_status import (
    GetDocumentStatusUseCase,
    DocumentStatusSummaryUseCase,
    DocumentProgressTracker,
    DocumentStatusQuery,
    DocumentStatusInfo,
    DocumentStatusResult
)
from src.modules.ingest.domain.entities import Document, DocumentMetadata, DocumentType, DocumentStatus
from src.core.exceptions import ValidationError, NotFoundError, UnauthorizedError


@pytest.fixture
def mock_document_service():
    """Mock Document Service"""
    return AsyncMock()


@pytest.fixture
def get_document_status_use_case(mock_document_service):
    """GetDocumentStatusUseCase 인스턴스"""
    return GetDocumentStatusUseCase(document_service=mock_document_service)


@pytest.fixture
def document_status_summary_use_case(mock_document_service):
    """DocumentStatusSummaryUseCase 인스턴스"""
    return DocumentStatusSummaryUseCase(document_service=mock_document_service)


@pytest.fixture
def document_progress_tracker(mock_document_service):
    """DocumentProgressTracker 인스턴스"""
    return DocumentProgressTracker(document_service=mock_document_service)


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


@pytest.fixture
def sample_documents():
    """테스트용 문서 목록"""
    user_id = uuid4()
    documents = []
    
    for i in range(5):
        metadata = DocumentMetadata(file_size=1024 * (i + 1), mime_type="application/pdf")
        doc = Document.create(
            user_id=user_id,
            filename=f"test_{i}.pdf",
            original_filename=f"test_{i}.pdf",
            file_path=f"/uploads/test_{i}.pdf",
            document_type=DocumentType.PDF,
            metadata=metadata,
            tags=[f"tag_{i}"]
        )
        # 다양한 상태 설정
        statuses = [
            DocumentStatus.UPLOADED,
            DocumentStatus.PARSING,
            DocumentStatus.PROCESSED,
            DocumentStatus.PROCESSING,
            DocumentStatus.FAILED
        ]
        doc.update_status(statuses[i])
        documents.append(doc)
    
    return documents, user_id


class TestGetDocumentStatusUseCase:
    """문서 상태 조회 유즈케이스 테스트"""

    @pytest.mark.asyncio
    async def test_execute_single_document_success(
        self,
        get_document_status_use_case,
        mock_document_service,
        sample_document
    ):
        """단일 문서 상태 조회 성공 테스트"""
        # Given
        query = DocumentStatusQuery(
            user_id=sample_document.user_id,
            document_id=sample_document.id,
            include_metadata=True
        )
        
        mock_document_service.get_document_by_id.return_value = sample_document
        
        # When
        result = await get_document_status_use_case.execute(query)
        
        # Then
        assert isinstance(result, DocumentStatusResult)
        assert len(result.documents) == 1
        assert result.total_count == 1
        assert result.has_more is False
        
        doc_info = result.documents[0]
        assert isinstance(doc_info, DocumentStatusInfo)
        assert doc_info.id == sample_document.id
        assert doc_info.filename == sample_document.filename
        assert doc_info.status == sample_document.status.value
        assert doc_info.metadata is not None
        
        mock_document_service.get_document_by_id.assert_called_once_with(sample_document.id)

    @pytest.mark.asyncio
    async def test_execute_single_document_not_found(
        self,
        get_document_status_use_case,
        mock_document_service
    ):
        """단일 문서 조회 - 문서 없음 테스트"""
        # Given
        user_id = uuid4()
        document_id = uuid4()
        query = DocumentStatusQuery(
            user_id=user_id,
            document_id=document_id
        )
        
        mock_document_service.get_document_by_id.return_value = None
        
        # When & Then
        with pytest.raises(NotFoundError) as exc_info:
            await get_document_status_use_case.execute(query)
        
        assert f"Document not found: {document_id}" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_single_document_unauthorized(
        self,
        get_document_status_use_case,
        mock_document_service,
        sample_document
    ):
        """단일 문서 조회 - 권한 없음 테스트"""
        # Given
        other_user_id = uuid4()
        query = DocumentStatusQuery(
            user_id=other_user_id,
            document_id=sample_document.id
        )
        
        mock_document_service.get_document_by_id.return_value = sample_document
        
        # When & Then
        with pytest.raises(UnauthorizedError) as exc_info:
            await get_document_status_use_case.execute(query)
        
        assert "Access denied to document" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_document_list_success(
        self,
        get_document_status_use_case,
        mock_document_service,
        sample_documents
    ):
        """문서 목록 조회 성공 테스트"""
        # Given
        documents, user_id = sample_documents
        query = DocumentStatusQuery(
            user_id=user_id,
            limit=10,
            offset=0
        )
        
        mock_document_service.list_documents.return_value = (documents, len(documents))
        
        # When
        result = await get_document_status_use_case.execute(query)
        
        # Then
        assert isinstance(result, DocumentStatusResult)
        assert len(result.documents) == len(documents)
        assert result.total_count == len(documents)
        assert result.has_more is False
        
        # 문서 정보 확인
        for i, doc_info in enumerate(result.documents):
            assert doc_info.id == documents[i].id
            assert doc_info.filename == documents[i].filename
            assert doc_info.status == documents[i].status.value

    @pytest.mark.asyncio
    async def test_execute_document_list_with_status_filter(
        self,
        get_document_status_use_case,
        mock_document_service,
        sample_documents
    ):
        """문서 목록 조회 - 상태 필터 테스트"""
        # Given
        documents, user_id = sample_documents
        processed_docs = [doc for doc in documents if doc.status == DocumentStatus.PROCESSED]
        
        query = DocumentStatusQuery(
            user_id=user_id,
            status_filter=DocumentStatus.PROCESSED,
            limit=10,
            offset=0
        )
        
        mock_document_service.list_documents.return_value = (processed_docs, len(processed_docs))
        
        # When
        result = await get_document_status_use_case.execute(query)
        
        # Then
        assert len(result.documents) == len(processed_docs)
        for doc_info in result.documents:
            assert doc_info.status == DocumentStatus.PROCESSED.value
        
        # 서비스 호출 확인
        call_args = mock_document_service.list_documents.call_args
        assert call_args[1]["filters"]["status"] == DocumentStatus.PROCESSED

    @pytest.mark.asyncio
    async def test_execute_document_list_pagination(
        self,
        get_document_status_use_case,
        mock_document_service,
        sample_documents
    ):
        """문서 목록 조회 - 페이지네이션 테스트"""
        # Given
        documents, user_id = sample_documents
        page_size = 2
        total_count = len(documents)
        
        query = DocumentStatusQuery(
            user_id=user_id,
            limit=page_size,
            offset=0
        )
        
        # 첫 페이지 문서들
        first_page_docs = documents[:page_size]
        mock_document_service.list_documents.return_value = (first_page_docs, total_count)
        
        # When
        result = await get_document_status_use_case.execute(query)
        
        # Then
        assert len(result.documents) == page_size
        assert result.total_count == total_count
        assert result.has_more is True  # 더 많은 문서가 있음

    @pytest.mark.asyncio
    async def test_execute_invalid_limit(
        self,
        get_document_status_use_case
    ):
        """잘못된 limit 값 테스트"""
        # Given
        user_id = uuid4()
        query = DocumentStatusQuery(
            user_id=user_id,
            limit=0  # 잘못된 값
        )
        
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            await get_document_status_use_case.execute(query)
        
        assert "Limit must be between 1 and 1000" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_invalid_offset(
        self,
        get_document_status_use_case
    ):
        """잘못된 offset 값 테스트"""
        # Given
        user_id = uuid4()
        query = DocumentStatusQuery(
            user_id=user_id,
            offset=-1  # 잘못된 값
        )
        
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            await get_document_status_use_case.execute(query)
        
        assert "Offset must be non-negative" in str(exc_info.value)

    def test_convert_to_status_info_with_metadata(
        self,
        get_document_status_use_case,
        sample_document
    ):
        """문서 상태 정보 변환 - 메타데이터 포함 테스트"""
        # When
        status_info = get_document_status_use_case._convert_to_status_info(
            sample_document,
            include_metadata=True
        )
        
        # Then
        assert isinstance(status_info, DocumentStatusInfo)
        assert status_info.id == sample_document.id
        assert status_info.filename == sample_document.filename
        assert status_info.metadata is not None
        assert isinstance(status_info.metadata, dict)

    def test_convert_to_status_info_without_metadata(
        self,
        get_document_status_use_case,
        sample_document
    ):
        """문서 상태 정보 변환 - 메타데이터 제외 테스트"""
        # When
        status_info = get_document_status_use_case._convert_to_status_info(
            sample_document,
            include_metadata=False
        )
        
        # Then
        assert status_info.metadata is None


class TestDocumentStatusSummaryUseCase:
    """문서 상태 요약 조회 유즈케이스 테스트"""

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        document_status_summary_use_case,
        mock_document_service,
        sample_documents
    ):
        """문서 상태 요약 조회 성공 테스트"""
        # Given
        documents, user_id = sample_documents
        
        # Mock 설정
        status_counts = {
            "uploaded": 1,
            "parsing": 1,
            "processed": 1,
            "processing": 1,
            "failed": 1
        }
        
        mock_document_service.get_document_counts_by_status.return_value = status_counts
        mock_document_service.list_documents.side_effect = [
            (documents[:3], 3),  # recent_documents
            (documents[1:2], 1),  # processing_documents
            (documents[4:5], 1)   # failed_documents
        ]
        
        # When
        result = await document_status_summary_use_case.execute(user_id)
        
        # Then
        assert isinstance(result, dict)
        assert "total_documents" in result
        assert "status_counts" in result
        assert "recent_documents" in result
        assert "processing_documents" in result
        assert "failed_documents" in result
        
        assert result["total_documents"] == sum(status_counts.values())
        assert result["status_counts"] == status_counts
        assert len(result["recent_documents"]) == 3
        assert len(result["processing_documents"]) == 1
        assert len(result["failed_documents"]) == 1

    @pytest.mark.asyncio
    async def test_execute_empty_result(
        self,
        document_status_summary_use_case,
        mock_document_service
    ):
        """빈 결과 테스트"""
        # Given
        user_id = uuid4()
        
        mock_document_service.get_document_counts_by_status.return_value = {}
        mock_document_service.list_documents.return_value = ([], 0)
        
        # When
        result = await document_status_summary_use_case.execute(user_id)
        
        # Then
        assert result["total_documents"] == 0
        assert len(result["recent_documents"]) == 0
        assert len(result["processing_documents"]) == 0
        assert len(result["failed_documents"]) == 0


class TestDocumentProgressTracker:
    """문서 처리 진행률 추적기 테스트"""

    @pytest.mark.asyncio
    async def test_get_processing_progress_success(
        self,
        document_progress_tracker,
        mock_document_service,
        sample_document
    ):
        """문서 처리 진행률 조회 성공 테스트"""
        # Given
        sample_document.update_status(DocumentStatus.PROCESSING)
        mock_document_service.get_document_by_id.return_value = sample_document
        
        # When
        result = await document_progress_tracker.get_processing_progress(
            sample_document.id,
            sample_document.user_id
        )
        
        # Then
        assert isinstance(result, dict)
        assert result["document_id"] == str(sample_document.id)
        assert result["filename"] == sample_document.filename
        assert result["status"] == DocumentStatus.PROCESSING.value
        assert result["progress_percentage"] == 80  # PROCESSING 상태의 진행률
        assert "status_message" in result
        assert result["is_completed"] is False
        assert result["is_failed"] is False

    @pytest.mark.asyncio
    async def test_get_processing_progress_completed(
        self,
        document_progress_tracker,
        mock_document_service,
        sample_document
    ):
        """완료된 문서 진행률 조회 테스트"""
        # Given
        sample_document.update_status(DocumentStatus.PROCESSED)
        mock_document_service.get_document_by_id.return_value = sample_document
        
        # When
        result = await document_progress_tracker.get_processing_progress(
            sample_document.id,
            sample_document.user_id
        )
        
        # Then
        assert result["status"] == DocumentStatus.PROCESSED.value
        assert result["progress_percentage"] == 100
        assert result["is_completed"] is True
        assert result["is_failed"] is False

    @pytest.mark.asyncio
    async def test_get_processing_progress_failed(
        self,
        document_progress_tracker,
        mock_document_service,
        sample_document
    ):
        """실패한 문서 진행률 조회 테스트"""
        # Given
        error_message = "Processing failed"
        sample_document.update_status(DocumentStatus.FAILED, error_message)
        mock_document_service.get_document_by_id.return_value = sample_document
        
        # When
        result = await document_progress_tracker.get_processing_progress(
            sample_document.id,
            sample_document.user_id
        )
        
        # Then
        assert result["status"] == DocumentStatus.FAILED.value
        assert result["progress_percentage"] == 0
        assert result["is_completed"] is False
        assert result["is_failed"] is True
        assert result["error_message"] == error_message

    @pytest.mark.asyncio
    async def test_get_processing_progress_not_found(
        self,
        document_progress_tracker,
        mock_document_service
    ):
        """문서 없음 테스트"""
        # Given
        document_id = uuid4()
        user_id = uuid4()
        
        mock_document_service.get_document_by_id.return_value = None
        
        # When & Then
        with pytest.raises(NotFoundError):
            await document_progress_tracker.get_processing_progress(document_id, user_id)

    @pytest.mark.asyncio
    async def test_get_processing_progress_unauthorized(
        self,
        document_progress_tracker,
        mock_document_service,
        sample_document
    ):
        """권한 없음 테스트"""
        # Given
        other_user_id = uuid4()
        mock_document_service.get_document_by_id.return_value = sample_document
        
        # When & Then
        with pytest.raises(UnauthorizedError):
            await document_progress_tracker.get_processing_progress(
                sample_document.id,
                other_user_id
            )


class TestDocumentStatusInfo:
    """문서 상태 정보 데이터클래스 테스트"""

    def test_document_status_info_creation(self):
        """DocumentStatusInfo 생성 테스트"""
        # Given
        doc_id = uuid4()
        now = datetime.utcnow()
        
        # When
        status_info = DocumentStatusInfo(
            id=doc_id,
            filename="test.pdf",
            original_filename="test.pdf",
            document_type="pdf",
            status="uploaded",
            created_at=now,
            updated_at=now
        )
        
        # Then
        assert status_info.id == doc_id
        assert status_info.filename == "test.pdf"
        assert status_info.tags == []  # __post_init__에서 초기화

    def test_document_status_info_with_tags(self):
        """태그가 있는 DocumentStatusInfo 테스트"""
        # Given
        doc_id = uuid4()
        now = datetime.utcnow()
        tags = ["tag1", "tag2"]
        
        # When
        status_info = DocumentStatusInfo(
            id=doc_id,
            filename="test.pdf",
            original_filename="test.pdf",
            document_type="pdf",
            status="uploaded",
            created_at=now,
            updated_at=now,
            tags=tags
        )
        
        # Then
        assert status_info.tags == tags


class TestDocumentStatusQuery:
    """문서 상태 조회 쿼리 테스트"""

    def test_document_status_query_defaults(self):
        """기본값 테스트"""
        # Given
        user_id = uuid4()
        
        # When
        query = DocumentStatusQuery(user_id=user_id)
        
        # Then
        assert query.user_id == user_id
        assert query.document_id is None
        assert query.status_filter is None
        assert query.limit == 50
        assert query.offset == 0
        assert query.include_metadata is False

    def test_document_status_query_with_values(self):
        """값 설정 테스트"""
        # Given
        user_id = uuid4()
        document_id = uuid4()
        
        # When
        query = DocumentStatusQuery(
            user_id=user_id,
            document_id=document_id,
            status_filter=DocumentStatus.PROCESSED,
            limit=100,
            offset=10,
            include_metadata=True
        )
        
        # Then
        assert query.user_id == user_id
        assert query.document_id == document_id
        assert query.status_filter == DocumentStatus.PROCESSED
        assert query.limit == 100
        assert query.offset == 10
        assert query.include_metadata is True
