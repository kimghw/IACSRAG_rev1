"""
OpenAI 임베딩 서비스 구현체
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
import openai
from openai import AsyncOpenAI

from src.core.config import Settings
from src.core.exceptions import EmbeddingServiceError, ConfigurationError
from src.modules.process.application.ports.services import EmbeddingService
from src.modules.process.domain.entities import EmbeddingResult


logger = logging.getLogger(__name__)


class OpenAIEmbeddingService(EmbeddingService):
    """OpenAI 임베딩 서비스 구현체"""
    
    def __init__(self, settings: Settings):
        """
        OpenAI 임베딩 서비스 초기화
        
        Args:
            settings: 애플리케이션 설정
        """
        self.settings = settings
        self._validate_config()
        
        # OpenAI 클라이언트 초기화
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=30.0,
            max_retries=3
        )
        
        self.model = settings.openai_embedding_model
        self.max_batch_size = 100  # OpenAI API 제한
        self.max_tokens_per_request = 8191  # text-embedding-3-small 제한
        
    def _validate_config(self) -> None:
        """설정 검증"""
        if not self.settings.openai_api_key:
            raise ConfigurationError("OpenAI API key is required")
        
        if not self.settings.openai_embedding_model:
            raise ConfigurationError("OpenAI embedding model is required")
    
    async def generate_embedding(
        self,
        text: str,
        model_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        단일 텍스트 임베딩 생성
        
        Args:
            text: 임베딩할 텍스트
            model_name: 사용할 모델명
            parameters: 임베딩 파라미터
            
        Returns:
            Dict[str, Any]: 임베딩 정보
        """
        results = await self.generate_embeddings([text], model_name)
        if not results:
            raise EmbeddingServiceError("Failed to generate embedding")
        
        result = results[0]
        return {
            "embedding": result.vector,
            "model_name": result.model,
            "model_version": "1.0",  # OpenAI doesn't provide version info
            "dimension": result.dimensions,
            "metadata": result.metadata
        }
    
    async def generate_batch_embeddings(
        self,
        texts: List[str],
        model_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        배치 텍스트 임베딩 생성
        
        Args:
            texts: 임베딩할 텍스트 목록
            model_name: 사용할 모델명
            parameters: 임베딩 파라미터
            
        Returns:
            List[Dict[str, Any]]: 임베딩 정보 목록
        """
        results = await self.generate_embeddings(texts, model_name)
        return [
            {
                "embedding": result.vector,
                "model_name": result.model,
                "model_version": "1.0",
                "dimension": result.dimensions,
                "metadata": result.metadata
            }
            for result in results
        ]
    
    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        모델 정보 조회
        
        Args:
            model_name: 모델명
            
        Returns:
            Dict[str, Any]: 모델 정보
        """
        model_info = {
            "text-embedding-3-small": {
                "name": "text-embedding-3-small",
                "version": "1.0",
                "dimension": 1536,
                "max_tokens": 8191,
                "description": "OpenAI's small embedding model with 1536 dimensions"
            },
            "text-embedding-3-large": {
                "name": "text-embedding-3-large",
                "version": "1.0",
                "dimension": 3072,
                "max_tokens": 8191,
                "description": "OpenAI's large embedding model with 3072 dimensions"
            },
            "text-embedding-ada-002": {
                "name": "text-embedding-ada-002",
                "version": "1.0",
                "dimension": 1536,
                "max_tokens": 8191,
                "description": "OpenAI's Ada-002 embedding model"
            }
        }
        
        if model_name not in model_info:
            raise EmbeddingServiceError(f"Unsupported model: {model_name}")
        
        return model_info[model_name]

    async def generate_embeddings(
        self,
        texts: List[str],
        model_name: Optional[str] = None,
        batch_size: Optional[int] = None
    ) -> List[EmbeddingResult]:
        """
        텍스트 리스트에 대한 임베딩 생성
        
        Args:
            texts: 임베딩을 생성할 텍스트 리스트
            model_name: 사용할 모델명 (기본값: 설정의 모델)
            batch_size: 배치 크기 (기본값: 50)
            
        Returns:
            임베딩 결과 리스트
            
        Raises:
            EmbeddingServiceError: 임베딩 생성 실패 시
        """
        if not texts:
            return []
        
        model = model_name or self.model
        batch_size = min(batch_size or 50, self.max_batch_size)
        
        logger.info(f"Generating embeddings for {len(texts)} texts using model {model}")
        
        try:
            # 텍스트를 배치로 분할
            batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
            all_results = []
            
            for batch_idx, batch in enumerate(batches):
                logger.debug(f"Processing batch {batch_idx + 1}/{len(batches)}")
                
                # 토큰 수 검증
                validated_batch = self._validate_token_limits(batch)
                
                # OpenAI API 호출
                batch_results = await self._generate_batch_embeddings(
                    validated_batch, model
                )
                all_results.extend(batch_results)
                
                # API 레이트 리미트 고려한 지연
                if batch_idx < len(batches) - 1:
                    await asyncio.sleep(0.1)
            
            logger.info(f"Successfully generated {len(all_results)} embeddings")
            return all_results
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            raise EmbeddingServiceError(f"Embedding generation failed: {str(e)}")
    
    async def _generate_batch_embeddings(
        self,
        texts: List[str],
        model: str
    ) -> List[EmbeddingResult]:
        """
        배치 단위로 임베딩 생성
        
        Args:
            texts: 텍스트 리스트
            model: 모델명
            
        Returns:
            임베딩 결과 리스트
        """
        try:
            response = await self.client.embeddings.create(
                input=texts,
                model=model,
                encoding_format="float"
            )
            
            results = []
            for i, embedding_data in enumerate(response.data):
                result = EmbeddingResult(
                    text=texts[i],
                    vector=embedding_data.embedding,
                    model=model,
                    dimensions=len(embedding_data.embedding),
                    metadata={
                        "index": embedding_data.index,
                        "usage": {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "total_tokens": response.usage.total_tokens
                        }
                    }
                )
                results.append(result)
            
            return results
            
        except openai.RateLimitError as e:
            logger.warning(f"Rate limit exceeded, retrying after delay: {str(e)}")
            await asyncio.sleep(1.0)
            return await self._generate_batch_embeddings(texts, model)
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise EmbeddingServiceError(f"OpenAI API error: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error in batch embedding generation: {str(e)}")
            raise EmbeddingServiceError(f"Batch embedding generation failed: {str(e)}")
    
    def _validate_token_limits(self, texts: List[str]) -> List[str]:
        """
        토큰 수 제한 검증 및 텍스트 자르기
        
        Args:
            texts: 검증할 텍스트 리스트
            
        Returns:
            검증된 텍스트 리스트
        """
        validated_texts = []
        
        for text in texts:
            # 간단한 토큰 수 추정 (실제로는 tiktoken 사용 권장)
            estimated_tokens = len(text.split()) * 1.3  # 대략적인 추정
            
            if estimated_tokens > self.max_tokens_per_request:
                # 토큰 수가 초과하면 텍스트를 자름
                words = text.split()
                max_words = int(self.max_tokens_per_request / 1.3)
                truncated_text = " ".join(words[:max_words])
                validated_texts.append(truncated_text)
                logger.warning(f"Text truncated due to token limit: {len(words)} -> {max_words} words")
            else:
                validated_texts.append(text)
        
        return validated_texts
    
    async def get_embedding_dimensions(self, model_name: Optional[str] = None) -> int:
        """
        모델의 임베딩 차원 수 반환
        
        Args:
            model_name: 모델명
            
        Returns:
            임베딩 차원 수
        """
        model = model_name or self.model
        
        # OpenAI 모델별 차원 수 매핑
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }
        
        return model_dimensions.get(model, 1536)  # 기본값
    
    async def health_check(self) -> Dict[str, Any]:
        """
        서비스 상태 확인
        
        Returns:
            상태 정보
        """
        try:
            # 간단한 테스트 임베딩 생성
            test_result = await self.generate_embeddings(["health check test"])
            
            return {
                "status": "healthy",
                "model": self.model,
                "dimensions": await self.get_embedding_dimensions(),
                "test_embedding_generated": len(test_result) > 0
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": self.model
            }
    
    async def get_supported_models(self) -> List[str]:
        """
        지원되는 모델 목록 반환
        
        Returns:
            지원되는 모델 목록
        """
        return [
            "text-embedding-3-small",
            "text-embedding-3-large", 
            "text-embedding-ada-002"
        ]
    
    async def close(self) -> None:
        """리소스 정리"""
        if hasattr(self.client, 'close'):
            await self.client.close()
        logger.info("OpenAI embedding service closed")
