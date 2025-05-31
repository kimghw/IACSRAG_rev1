"""
Generate Answer Use Case

검색 결과를 기반으로 LLM을 사용하여 답변을 생성하는 유즈케이스
"""

import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from uuid import UUID

from src.core.exceptions import ValidationError, SearchError
from src.modules.search.domain.entities import (
    AnswerRequest, Answer, SearchResult
)
from src.modules.search.application.ports.llm_port import LLMPort


@dataclass
class GenerateAnswerCommand:
    """답변 생성 명령"""
    
    user_id: UUID
    query_text: str
    context_chunks: List[SearchResult]
    model_name: str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.7
    system_prompt: Optional[str] = None
    include_sources: bool = True
    language: str = "ko"


@dataclass
class GenerateAnswerResult:
    """답변 생성 결과"""
    
    answer: Answer
    execution_time_ms: float
    tokens_used: int
    confidence_score: float
    source_chunks_count: int


class GenerateAnswerUseCase:
    """답변 생성 유즈케이스"""
    
    def __init__(self, llm_port: LLMPort):
        self.llm_port = llm_port
    
    async def execute(self, command: GenerateAnswerCommand) -> GenerateAnswerResult:
        """답변 생성 실행"""
        start_time = time.time()
        
        try:
            # 1. 입력 검증
            self._validate_command(command)
            
            # 2. 답변 요청 생성
            answer_request = self._create_answer_request(command)
            
            # 3. LLM을 통한 답변 생성
            answer = await self.llm_port.generate_answer(answer_request)
            
            # 4. 실행 시간 계산
            execution_time_ms = (time.time() - start_time) * 1000
            
            return GenerateAnswerResult(
                answer=answer,
                execution_time_ms=execution_time_ms,
                tokens_used=answer.tokens_used,
                confidence_score=answer.confidence_score,
                source_chunks_count=len(command.context_chunks)
            )
            
        except Exception as e:
            raise SearchError(f"Answer generation failed: {str(e)}") from e
    
    def _validate_command(self, command: GenerateAnswerCommand) -> None:
        """명령 검증"""
        if not command.user_id:
            raise ValidationError("User ID is required")
        
        if not command.query_text or not command.query_text.strip():
            raise ValidationError("Query text is required")
        
        if len(command.query_text) > 1000:
            raise ValidationError("Query text is too long (max 1000 characters)")
        
        if not command.context_chunks:
            raise ValidationError("Context chunks are required")
        
        if len(command.context_chunks) > 20:
            raise ValidationError("Too many context chunks (max 20)")
        
        if command.max_tokens <= 0 or command.max_tokens > 4000:
            raise ValidationError("Max tokens must be between 1 and 4000")
        
        if not 0.0 <= command.temperature <= 2.0:
            raise ValidationError("Temperature must be between 0.0 and 2.0")
    
    def _create_answer_request(self, command: GenerateAnswerCommand) -> AnswerRequest:
        """답변 요청 생성"""
        return AnswerRequest.create(
            user_id=command.user_id,
            query_text=command.query_text,
            context_chunks=command.context_chunks,
            model_name=command.model_name,
            max_tokens=command.max_tokens,
            temperature=command.temperature,
            system_prompt=command.system_prompt
        )
    
    def _build_system_prompt(self, command: GenerateAnswerCommand) -> str:
        """시스템 프롬프트 생성"""
        if command.system_prompt:
            return command.system_prompt
        
        base_prompt = """당신은 문서 검색 시스템의 AI 어시스턴트입니다. 
주어진 문서 내용을 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 제공해야 합니다.

지침:
1. 제공된 문서 내용만을 기반으로 답변하세요
2. 문서에 없는 정보는 추측하지 마세요
3. 답변이 불확실한 경우 그렇다고 명시하세요
4. 가능한 한 구체적이고 상세한 답변을 제공하세요
5. 답변은 한국어로 작성하세요"""
        
        if command.include_sources:
            base_prompt += "\n6. 답변 끝에 참고한 문서 출처를 명시하세요"
        
        if command.language != "ko":
            base_prompt = base_prompt.replace("한국어", command.language)
        
        return base_prompt
    
    def _build_user_prompt(self, command: GenerateAnswerCommand) -> str:
        """사용자 프롬프트 생성"""
        # 컨텍스트 문서 정리
        context_text = self._format_context_chunks(command.context_chunks)
        
        prompt = f"""다음 문서들을 참고하여 질문에 답변해 주세요:

=== 참고 문서 ===
{context_text}

=== 질문 ===
{command.query_text}

=== 답변 ==="""
        
        return prompt
    
    def _format_context_chunks(self, chunks: List[SearchResult]) -> str:
        """컨텍스트 청크 포맷팅"""
        formatted_chunks = []
        
        for i, chunk in enumerate(chunks, 1):
            chunk_text = f"[문서 {i}]\n{chunk.content}"
            
            # 메타데이터가 있으면 추가
            if chunk.metadata:
                metadata_info = []
                if "page" in chunk.metadata:
                    metadata_info.append(f"페이지: {chunk.metadata['page']}")
                if "title" in chunk.metadata:
                    metadata_info.append(f"제목: {chunk.metadata['title']}")
                if "source" in chunk.metadata:
                    metadata_info.append(f"출처: {chunk.metadata['source']}")
                
                if metadata_info:
                    chunk_text += f"\n({', '.join(metadata_info)})"
            
            formatted_chunks.append(chunk_text)
        
        return "\n\n".join(formatted_chunks)
    
    def _calculate_confidence_score(
        self, 
        context_chunks: List[SearchResult]
    ) -> float:
        """신뢰도 점수 계산"""
        # 기본 신뢰도는 컨텍스트 청크들의 평균 점수
        if not context_chunks:
            return 0.0
        
        avg_chunk_score = sum(chunk.score for chunk in context_chunks) / len(context_chunks)
        
        # 컨텍스트 청크 수에 따른 보정
        chunk_count_factor = min(len(context_chunks) / 5, 1.0)  # 5개 기준으로 정규화
        
        # 최종 신뢰도 계산
        confidence = avg_chunk_score * 0.8 + chunk_count_factor * 0.2
        
        return min(confidence, 1.0)
    
    async def get_answer_suggestions(
        self, 
        user_id: UUID, 
        query_text: str
    ) -> List[str]:
        """답변 제안 생성"""
        # 간단한 제안 생성 로직
        suggestions = []
        
        # 질문 유형에 따른 제안
        if "어떻게" in query_text or "방법" in query_text:
            suggestions.append(f"{query_text}에 대한 단계별 가이드")
            suggestions.append(f"{query_text}의 모범 사례")
        
        if "무엇" in query_text or "뭐" in query_text:
            suggestions.append(f"{query_text}의 정의와 개념")
            suggestions.append(f"{query_text}의 종류와 특징")
        
        if "왜" in query_text or "이유" in query_text:
            suggestions.append(f"{query_text}의 배경과 원인")
            suggestions.append(f"{query_text}의 장단점")
        
        return suggestions[:3]  # 최대 3개 제안
    
    async def regenerate_answer(
        self,
        original_command: GenerateAnswerCommand,
        feedback: str,
        new_temperature: Optional[float] = None
    ) -> GenerateAnswerResult:
        """답변 재생성"""
        # 새로운 명령 생성
        new_command = GenerateAnswerCommand(
            user_id=original_command.user_id,
            query_text=original_command.query_text,
            context_chunks=original_command.context_chunks,
            model_name=original_command.model_name,
            max_tokens=original_command.max_tokens,
            temperature=new_temperature or original_command.temperature + 0.1,
            system_prompt=self._build_regeneration_prompt(
                original_command.system_prompt, feedback
            ),
            include_sources=original_command.include_sources,
            language=original_command.language
        )
        
        return await self.execute(new_command)
    
    def _build_regeneration_prompt(
        self, 
        original_prompt: Optional[str], 
        feedback: str
    ) -> str:
        """재생성용 프롬프트 생성"""
        base_prompt = original_prompt or self._build_system_prompt(
            GenerateAnswerCommand(
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                query_text="",
                context_chunks=[]
            )
        )
        
        regeneration_instruction = f"""

추가 지침:
사용자 피드백: {feedback}
위 피드백을 반영하여 이전 답변을 개선해 주세요."""
        
        return base_prompt + regeneration_instruction
    
    async def evaluate_answer_quality(
        self,
        answer: Answer,
        expected_keywords: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """답변 품질 평가"""
        evaluation = {
            "confidence_score": answer.confidence_score,
            "completeness": 0.0,
            "relevance": 0.0,
            "clarity": 0.0,
            "overall_quality": 0.0
        }
        
        # 완성도 평가 (답변 길이 기반)
        answer_length = len(answer.answer_text)
        evaluation["completeness"] = min(answer_length / 300, 1.0)  # 300자 기준
        
        # 관련성 평가 (키워드 매칭)
        if expected_keywords:
            matched_keywords = sum(
                1 for keyword in expected_keywords 
                if keyword.lower() in answer.answer_text.lower()
            )
            evaluation["relevance"] = matched_keywords / len(expected_keywords)
        else:
            evaluation["relevance"] = answer.confidence_score
        
        # 명확성 평가 (문장 구조 기반)
        sentences = answer.answer_text.split('.')
        avg_sentence_length = sum(len(s.strip()) for s in sentences) / max(len(sentences), 1)
        evaluation["clarity"] = min(avg_sentence_length / 100, 1.0)  # 100자 기준
        
        # 전체 품질 점수
        evaluation["overall_quality"] = (
            evaluation["confidence_score"] * 0.3 +
            evaluation["completeness"] * 0.25 +
            evaluation["relevance"] * 0.25 +
            evaluation["clarity"] * 0.2
        )
        
        return evaluation
