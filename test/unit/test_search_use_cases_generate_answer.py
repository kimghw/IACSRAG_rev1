"""
Generate Answer Use Case 테스트
"""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import UUID, uuid4
from datetime import datetime

from src.modules.search.application.use_cases.generate_answer import (
    GenerateAnswerUseCase,
    GenerateAnswerCommand,
    GenerateAnswerResult
)
from src.modules.search.domain.entities import (
    SearchResult, Answer, AnswerRequest
)
from src.core.exceptions import ValidationError, SearchError


class TestGenerateAnswerUseCase:
    """Generate Answer Use Case 테스트"""
    
    @pytest.fixture
    def mock_llm_port(self):
        """Mock LLM Port"""
        return Mock()
    
    @pytest.fixture
    def use_case(self, mock_llm_port):
        """Use Case 인스턴스"""
        return GenerateAnswerUseCase(mock_llm_port)
    
    @pytest.fixture
    def sample_context_chunks(self):
        """샘플 컨텍스트 청크"""
        return [
            SearchResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                content="Python은 프로그래밍 언어입니다.",
                score=0.9,
                metadata={"source": "python_guide.pdf", "page": 1}
            ),
            SearchResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                content="Python은 간단하고 읽기 쉬운 문법을 가지고 있습니다.",
                score=0.8,
                metadata={"source": "python_guide.pdf", "page": 2}
            )
        ]
    
    @pytest.fixture
    def sample_command(self, sample_context_chunks):
        """샘플 명령"""
        return GenerateAnswerCommand(
            user_id=uuid4(),
            query_text="Python이 무엇인가요?",
            context_chunks=sample_context_chunks,
            model_name="gpt-3.5-turbo",
            max_tokens=1000,
            temperature=0.7,
            include_sources=True,
            language="ko"
        )
    
    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, mock_llm_port, sample_command):
        """정상적인 답변 생성 테스트"""
        # Given
        mock_answer = Answer(
            id=uuid4(),
            request_id=uuid4(),
            user_id=sample_command.user_id,
            query_text=sample_command.query_text,
            answer_text="Python은 프로그래밍 언어입니다. 간단하고 읽기 쉬운 문법을 가지고 있습니다.",
            confidence_score=0.85,
            tokens_used=150,
            generation_time_ms=1200.0,
            created_at=datetime.now(),
            metadata={"model_name": "gpt-3.5-turbo"}
        )
        
        mock_llm_port.generate_answer = AsyncMock(return_value=mock_answer)
        
        # When
        result = await use_case.execute(sample_command)
        
        # Then
        assert isinstance(result, GenerateAnswerResult)
        assert result.answer == mock_answer
        assert result.tokens_used == 150
        assert result.confidence_score == 0.85
        assert result.source_chunks_count == 2
        assert result.execution_time_ms > 0
        
        # LLM 포트가 올바른 요청으로 호출되었는지 확인
        mock_llm_port.generate_answer.assert_called_once()
        call_args = mock_llm_port.generate_answer.call_args[0][0]
        assert isinstance(call_args, AnswerRequest)
        assert call_args.user_id == sample_command.user_id
        assert call_args.query_text == sample_command.query_text
    
    @pytest.mark.asyncio
    async def test_execute_with_custom_system_prompt(self, use_case, mock_llm_port, sample_command):
        """커스텀 시스템 프롬프트 테스트"""
        # Given
        sample_command.system_prompt = "당신은 Python 전문가입니다."
        
        mock_answer = Answer(
            id=uuid4(),
            request_id=uuid4(),
            user_id=sample_command.user_id,
            query_text=sample_command.query_text,
            answer_text="전문가 답변입니다.",
            confidence_score=0.9,
            tokens_used=100,
            generation_time_ms=1000.0,
            created_at=datetime.now(),
            metadata={}
        )
        
        mock_llm_port.generate_answer = AsyncMock(return_value=mock_answer)
        
        # When
        result = await use_case.execute(sample_command)
        
        # Then
        assert result.answer.answer_text == "전문가 답변입니다."
        
        # 요청에 커스텀 프롬프트가 포함되었는지 확인
        call_args = mock_llm_port.generate_answer.call_args[0][0]
        assert call_args.system_prompt == "당신은 Python 전문가입니다."
    
    @pytest.mark.asyncio
    async def test_execute_with_invalid_user_id(self, use_case, sample_command):
        """잘못된 사용자 ID 테스트"""
        # Given
        sample_command.user_id = None
        
        # When & Then
        with pytest.raises(SearchError) as exc_info:
            await use_case.execute(sample_command)
        
        assert "User ID is required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_with_empty_query(self, use_case, sample_command):
        """빈 쿼리 테스트"""
        # Given
        sample_command.query_text = ""
        
        # When & Then
        with pytest.raises(SearchError) as exc_info:
            await use_case.execute(sample_command)
        
        assert "Query text is required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_with_too_long_query(self, use_case, sample_command):
        """너무 긴 쿼리 테스트"""
        # Given
        sample_command.query_text = "a" * 1001
        
        # When & Then
        with pytest.raises(SearchError) as exc_info:
            await use_case.execute(sample_command)
        
        assert "Query text is too long" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_with_empty_context_chunks(self, use_case, sample_command):
        """빈 컨텍스트 청크 테스트"""
        # Given
        sample_command.context_chunks = []
        
        # When & Then
        with pytest.raises(SearchError) as exc_info:
            await use_case.execute(sample_command)
        
        assert "Context chunks are required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_with_too_many_context_chunks(self, use_case, sample_command):
        """너무 많은 컨텍스트 청크 테스트"""
        # Given
        sample_command.context_chunks = [
            SearchResult(
                chunk_id=uuid4(),
                document_id=uuid4(),
                content=f"Content {i}",
                score=0.8,
                metadata={}
            ) for i in range(21)
        ]
        
        # When & Then
        with pytest.raises(SearchError) as exc_info:
            await use_case.execute(sample_command)
        
        assert "Too many context chunks" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_with_invalid_max_tokens(self, use_case, sample_command):
        """잘못된 최대 토큰 수 테스트"""
        # Given
        sample_command.max_tokens = 5000
        
        # When & Then
        with pytest.raises(SearchError) as exc_info:
            await use_case.execute(sample_command)
        
        assert "Max tokens must be between 1 and 4000" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_with_invalid_temperature(self, use_case, sample_command):
        """잘못된 온도 값 테스트"""
        # Given
        sample_command.temperature = 3.0
        
        # When & Then
        with pytest.raises(SearchError) as exc_info:
            await use_case.execute(sample_command)
        
        assert "Temperature must be between 0.0 and 2.0" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_with_llm_error(self, use_case, mock_llm_port, sample_command):
        """LLM 오류 테스트"""
        # Given
        mock_llm_port.generate_answer = AsyncMock(side_effect=Exception("LLM service error"))
        
        # When & Then
        with pytest.raises(SearchError) as exc_info:
            await use_case.execute(sample_command)
        
        assert "Answer generation failed" in str(exc_info.value)
    
    def test_calculate_confidence_score(self, use_case, sample_context_chunks):
        """신뢰도 점수 계산 테스트"""
        # When
        score = use_case._calculate_confidence_score(sample_context_chunks)
        
        # Then
        assert 0.0 <= score <= 1.0
        assert score > 0.7  # 높은 점수의 청크들이므로 높은 신뢰도 예상
    
    def test_calculate_confidence_score_with_empty_chunks(self, use_case):
        """빈 청크로 신뢰도 점수 계산 테스트"""
        # When
        score = use_case._calculate_confidence_score([])
        
        # Then
        assert score == 0.0
    
    def test_format_context_chunks(self, use_case, sample_context_chunks):
        """컨텍스트 청크 포맷팅 테스트"""
        # When
        formatted = use_case._format_context_chunks(sample_context_chunks)
        
        # Then
        assert "[문서 1]" in formatted
        assert "[문서 2]" in formatted
        assert "Python은 프로그래밍 언어입니다." in formatted
        assert "python_guide.pdf" in formatted
        assert "페이지: 1" in formatted
    
    def test_build_system_prompt_default(self, use_case, sample_command):
        """기본 시스템 프롬프트 생성 테스트"""
        # When
        prompt = use_case._build_system_prompt(sample_command)
        
        # Then
        assert "AI 어시스턴트" in prompt
        assert "한국어" in prompt
        assert "참고한 문서 출처를 명시하세요" in prompt
    
    def test_build_user_prompt(self, use_case, sample_command):
        """사용자 프롬프트 생성 테스트"""
        # When
        prompt = use_case._build_user_prompt(sample_command)
        
        # Then
        assert "=== 참고 문서 ===" in prompt
        assert "=== 질문 ===" in prompt
        assert "=== 답변 ===" in prompt
        assert sample_command.query_text in prompt
    
    @pytest.mark.asyncio
    async def test_get_answer_suggestions_how_question(self, use_case):
        """'어떻게' 질문에 대한 제안 테스트"""
        # When
        suggestions = await use_case.get_answer_suggestions(
            uuid4(), "Python을 어떻게 설치하나요?"
        )
        
        # Then
        assert len(suggestions) <= 3
        assert any("단계별 가이드" in s for s in suggestions)
        assert any("모범 사례" in s for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_get_answer_suggestions_what_question(self, use_case):
        """'무엇' 질문에 대한 제안 테스트"""
        # When
        suggestions = await use_case.get_answer_suggestions(
            uuid4(), "Python이 무엇인가요?"
        )
        
        # Then
        assert len(suggestions) <= 3
        assert any("정의와 개념" in s for s in suggestions)
        assert any("종류와 특징" in s for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_get_answer_suggestions_why_question(self, use_case):
        """'왜' 질문에 대한 제안 테스트"""
        # When
        suggestions = await use_case.get_answer_suggestions(
            uuid4(), "Python을 왜 사용하나요?"
        )
        
        # Then
        assert len(suggestions) <= 3
        assert any("배경과 원인" in s for s in suggestions)
        assert any("장단점" in s for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_regenerate_answer(self, use_case, mock_llm_port, sample_command):
        """답변 재생성 테스트"""
        # Given
        feedback = "더 자세한 설명이 필요합니다."
        
        mock_answer = Answer(
            id=uuid4(),
            request_id=uuid4(),
            user_id=sample_command.user_id,
            query_text=sample_command.query_text,
            answer_text="재생성된 더 자세한 답변입니다.",
            confidence_score=0.9,
            tokens_used=200,
            generation_time_ms=1500.0,
            created_at=datetime.now(),
            metadata={}
        )
        
        mock_llm_port.generate_answer = AsyncMock(return_value=mock_answer)
        
        # When
        result = await use_case.regenerate_answer(sample_command, feedback, 0.8)
        
        # Then
        assert result.answer.answer_text == "재생성된 더 자세한 답변입니다."
        
        # 새로운 온도 값이 적용되었는지 확인
        call_args = mock_llm_port.generate_answer.call_args[0][0]
        assert call_args.temperature == 0.8
    
    @pytest.mark.asyncio
    async def test_evaluate_answer_quality(self, use_case):
        """답변 품질 평가 테스트"""
        # Given
        answer = Answer(
            id=uuid4(),
            request_id=uuid4(),
            user_id=uuid4(),
            query_text="Python이 무엇인가요?",
            answer_text="Python은 프로그래밍 언어입니다. 간단하고 읽기 쉬운 문법을 가지고 있어서 초보자도 쉽게 배울 수 있습니다. 데이터 분석, 웹 개발, 인공지능 등 다양한 분야에서 사용됩니다.",
            confidence_score=0.85,
            tokens_used=150,
            generation_time_ms=1200.0,
            created_at=datetime.now(),
            metadata={}
        )
        
        expected_keywords = ["Python", "프로그래밍", "언어", "문법"]
        
        # When
        evaluation = await use_case.evaluate_answer_quality(answer, expected_keywords)
        
        # Then
        assert "confidence_score" in evaluation
        assert "completeness" in evaluation
        assert "relevance" in evaluation
        assert "clarity" in evaluation
        assert "overall_quality" in evaluation
        
        assert evaluation["confidence_score"] == 0.85
        assert 0.0 <= evaluation["overall_quality"] <= 1.0
        assert evaluation["relevance"] > 0.5  # 키워드가 많이 매칭되므로
    
    @pytest.mark.asyncio
    async def test_evaluate_answer_quality_without_keywords(self, use_case):
        """키워드 없이 답변 품질 평가 테스트"""
        # Given
        answer = Answer(
            id=uuid4(),
            request_id=uuid4(),
            user_id=uuid4(),
            query_text="Python이 무엇인가요?",
            answer_text="짧은 답변입니다.",
            confidence_score=0.7,
            tokens_used=50,
            generation_time_ms=800.0,
            created_at=datetime.now(),
            metadata={}
        )
        
        # When
        evaluation = await use_case.evaluate_answer_quality(answer)
        
        # Then
        assert evaluation["relevance"] == 0.7  # confidence_score와 동일해야 함
        assert 0.0 <= evaluation["overall_quality"] <= 1.0
