"""
Vector Database Implementation

Qdrant를 활용한 벡터 검색 구현
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from src.infrastructure.vectordb.qdrant_client import QdrantClient
from src.modules.search.application.ports.vector_search_port import VectorSearchPort
from src.modules.search.domain.entities import SearchResult
from src.core.exceptions import SearchError

logger = logging.getLogger(__name__)


class VectorDatabase(VectorSearchPort):
    """Qdrant 벡터 데이터베이스 구현"""
    
    def __init__(self, qdrant_client: QdrantClient):
        self.client = qdrant_client
        self.collection_name = "document_chunks"
    
    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None
    ) -> List[SearchResult]:
        """유사도 기반 벡터 검색"""
        try:
            logger.info(f"Searching similar vectors with limit: {limit}")
            
            # Qdrant 검색 수행
            search_results = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=threshold,
                query_filter=self._build_filter(filters)
            )
            
            # SearchResult 객체로 변환
            results = []
            for result in search_results:
                search_result = SearchResult(
                    chunk_id=UUID(result.id),
                    document_id=UUID(result.payload.get("document_id")),
                    content=result.payload.get("content", ""),
                    score=float(result.score),
                    metadata={
                        "source": result.payload.get("source", ""),
                        "page": result.payload.get("page"),
                        "chunk_index": result.payload.get("chunk_index"),
                        "created_at": result.payload.get("created_at"),
                        **result.payload.get("metadata", {})
                    }
                )
                results.append(search_result)
            
            logger.info(f"Found {len(results)} similar chunks")
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise SearchError(f"Vector search failed: {str(e)}")
    
    async def search_by_keywords(
        self,
        keywords: List[str],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None
    ) -> List[SearchResult]:
        """키워드 기반 청크 검색"""
        try:
            logger.info(f"Searching by keywords: {keywords}")
            
            # 키워드를 포함하는 청크 검색
            # 실제로는 Elasticsearch나 전문 검색 엔진을 사용하는 것이 좋지만
            # 여기서는 간단한 텍스트 매칭으로 구현
            
            # 모든 청크를 가져와서 키워드 매칭 (비효율적이지만 프로토타입용)
            all_chunks = await self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,  # 제한된 수만 검색
                scroll_filter=self._build_filter(filters),
                with_payload=True,
                with_vectors=False
            )
            
            results = []
            for point in all_chunks[0]:
                content = point.payload.get("content", "").lower()
                
                # 키워드 매칭 점수 계산
                score = 0.0
                for keyword in keywords:
                    if keyword.lower() in content:
                        score += content.count(keyword.lower()) / len(content.split())
                
                if score > 0:
                    search_result = SearchResult(
                        chunk_id=UUID(point.id),
                        document_id=UUID(point.payload.get("document_id")),
                        content=point.payload.get("content", ""),
                        score=score,
                        metadata={
                            "source": point.payload.get("source", ""),
                            "page": point.payload.get("page"),
                            "chunk_index": point.payload.get("chunk_index"),
                            "created_at": point.payload.get("created_at"),
                            **point.payload.get("metadata", {})
                        }
                    )
                    results.append(search_result)
            
            # 점수 순으로 정렬
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Keyword search failed: {str(e)}")
            return []
    
    async def hybrid_search(
        self,
        query_embedding: List[float],
        keywords: List[str],
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        limit: int = 10,
        threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None
    ) -> List[SearchResult]:
        """하이브리드 검색 (벡터 + 키워드)"""
        try:
            logger.info(f"Performing hybrid search with limit: {limit}")
            
            # 벡터 검색 결과
            vector_results = await self.search_similar_chunks(
                query_embedding, limit, threshold, filters, user_id
            )
            
            # 키워드 검색 결과 (텍스트 매칭)
            keyword_results = await self.search_by_keywords(
                keywords, limit, filters, user_id
            )
            
            # 결과 병합 및 재순위화
            merged_results = self._merge_and_rerank(
                vector_results, 
                keyword_results,
                vector_weight=semantic_weight,
                keyword_weight=keyword_weight
            )
            
            # 제한된 수만큼 반환
            return merged_results[:limit]
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            raise SearchError(f"Hybrid search failed: {str(e)}")
    
    async def get_chunk_by_id(
        self, 
        chunk_id: UUID, 
        user_id: Optional[UUID] = None
    ) -> Optional[SearchResult]:
        """ID로 특정 청크 조회"""
        try:
            result = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=[str(chunk_id)],
                with_payload=True,
                with_vectors=False
            )
            
            if not result:
                return None
            
            point = result[0]
            return SearchResult(
                chunk_id=UUID(point.id),
                document_id=UUID(point.payload.get("document_id")),
                content=point.payload.get("content", ""),
                score=1.0,
                metadata={
                    "source": point.payload.get("source", ""),
                    "page": point.payload.get("page"),
                    "chunk_index": point.payload.get("chunk_index"),
                    "created_at": point.payload.get("created_at"),
                    **point.payload.get("metadata", {})
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get chunk by ID {chunk_id}: {str(e)}")
            raise SearchError(f"Failed to get chunk by ID: {str(e)}")
    
    async def get_chunks_by_document(
        self,
        document_id: UUID,
        user_id: Optional[UUID] = None
    ) -> List[SearchResult]:
        """문서별 청크 조회"""
        try:
            logger.info(f"Getting chunks for document: {document_id}")
            
            filters = {"document_id": document_id}
            search_results = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=self._build_filter(filters),
                limit=1000,  # 문서의 모든 청크
                with_payload=True,
                with_vectors=False
            )
            
            results = []
            for result in search_results[0]:  # scroll returns (points, next_page_offset)
                search_result = SearchResult(
                    chunk_id=UUID(result.id),
                    document_id=UUID(result.payload.get("document_id")),
                    content=result.payload.get("content", ""),
                    score=1.0,  # 문서별 조회는 스코어 없음
                    metadata={
                        "source": result.payload.get("source", ""),
                        "page": result.payload.get("page"),
                        "chunk_index": result.payload.get("chunk_index"),
                        "created_at": result.payload.get("created_at"),
                        **result.payload.get("metadata", {})
                    }
                )
                results.append(search_result)
            
            # 청크 인덱스 순으로 정렬
            results.sort(key=lambda x: x.metadata.get("chunk_index", 0))
            
            logger.info(f"Found {len(results)} chunks for document {document_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to get chunks for document {document_id}: {str(e)}")
            raise SearchError(f"Failed to get chunks for document: {str(e)}")
    
    async def check_collection_health(self) -> Dict[str, Any]:
        """벡터 컬렉션 상태 확인"""
        try:
            info = await self.client.get_collection(self.collection_name)
            return {
                "name": info.config.name,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance.name,
                "points_count": info.points_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": info.status.name,
                "health": "healthy" if info.status.name == "GREEN" else "unhealthy"
            }
        except Exception as e:
            logger.error(f"Failed to check collection health: {str(e)}")
            return {
                "health": "unhealthy",
                "error": str(e)
            }
    
    async def search_by_metadata(
        self,
        filters: Dict[str, Any],
        limit: int = 10
    ) -> List[SearchResult]:
        """메타데이터 기반 검색"""
        try:
            logger.info(f"Searching by metadata: {filters}")
            
            search_results = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=self._build_filter(filters),
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            results = []
            for result in search_results[0]:  # scroll returns (points, next_page_offset)
                search_result = SearchResult(
                    chunk_id=UUID(result.id),
                    document_id=UUID(result.payload.get("document_id")),
                    content=result.payload.get("content", ""),
                    score=1.0,  # 메타데이터 검색은 스코어 없음
                    metadata={
                        "source": result.payload.get("source", ""),
                        "page": result.payload.get("page"),
                        "chunk_index": result.payload.get("chunk_index"),
                        "created_at": result.payload.get("created_at"),
                        **result.payload.get("metadata", {})
                    }
                )
                results.append(search_result)
            
            logger.info(f"Found {len(results)} chunks by metadata")
            return results
            
        except Exception as e:
            logger.error(f"Metadata search failed: {str(e)}")
            raise SearchError(f"Metadata search failed: {str(e)}")
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보 조회"""
        try:
            info = await self.client.get_collection(self.collection_name)
            return {
                "name": info.config.name,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance.name,
                "points_count": info.points_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": info.status.name
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {str(e)}")
            raise SearchError(f"Failed to get collection info: {str(e)}")
    
    def _build_filter(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Qdrant 필터 구성"""
        if not filters:
            return None
        
        must_conditions = []
        
        for key, value in filters.items():
            if key == "document_id":
                must_conditions.append({
                    "key": "document_id",
                    "match": {"value": str(value)}
                })
            elif key == "source":
                must_conditions.append({
                    "key": "source",
                    "match": {"value": value}
                })
            elif key == "page":
                if isinstance(value, dict):
                    # 범위 검색 (예: {"gte": 1, "lte": 10})
                    range_filter = {"key": "page", "range": {}}
                    if "gte" in value:
                        range_filter["range"]["gte"] = value["gte"]
                    if "lte" in value:
                        range_filter["range"]["lte"] = value["lte"]
                    if "gt" in value:
                        range_filter["range"]["gt"] = value["gt"]
                    if "lt" in value:
                        range_filter["range"]["lt"] = value["lt"]
                    must_conditions.append(range_filter)
                else:
                    # 정확한 값 매칭
                    must_conditions.append({
                        "key": "page",
                        "match": {"value": value}
                    })
            elif key == "created_after":
                must_conditions.append({
                    "key": "created_at",
                    "range": {"gte": value}
                })
            elif key == "created_before":
                must_conditions.append({
                    "key": "created_at",
                    "range": {"lte": value}
                })
            elif key.startswith("metadata."):
                # 메타데이터 필터
                metadata_key = key[9:]  # "metadata." 제거
                must_conditions.append({
                    "key": f"metadata.{metadata_key}",
                    "match": {"value": value}
                })
        
        if not must_conditions:
            return None
        
        return {"must": must_conditions}
    
    def _merge_and_rerank(
        self,
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult],
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[SearchResult]:
        """벡터 검색과 키워드 검색 결과 병합 및 재순위화"""
        
        # 결과를 chunk_id로 그룹화
        merged_scores = {}
        
        # 벡터 검색 결과 처리
        for result in vector_results:
            chunk_id = result.chunk_id
            merged_scores[chunk_id] = {
                "result": result,
                "vector_score": result.score * vector_weight,
                "keyword_score": 0.0
            }
        
        # 키워드 검색 결과 처리
        for result in keyword_results:
            chunk_id = result.chunk_id
            if chunk_id in merged_scores:
                # 이미 벡터 검색에서 찾은 결과
                merged_scores[chunk_id]["keyword_score"] = result.score * keyword_weight
            else:
                # 키워드 검색에서만 찾은 결과
                merged_scores[chunk_id] = {
                    "result": result,
                    "vector_score": 0.0,
                    "keyword_score": result.score * keyword_weight
                }
        
        # 최종 점수 계산 및 정렬
        final_results = []
        for chunk_data in merged_scores.values():
            final_score = chunk_data["vector_score"] + chunk_data["keyword_score"]
            result = chunk_data["result"]
            result.score = final_score
            final_results.append(result)
        
        # 점수 순으로 정렬
        final_results.sort(key=lambda x: x.score, reverse=True)
        return final_results
