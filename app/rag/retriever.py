from typing import List, Dict, Any, Optional
from app.config import settings
from app.rag.embeddings import embedding_service
from app.rag.vector_store import vector_store
from app.rag.bm25 import bm25_index
from app.rag.reranker import reranker
from app.core.logging import logger

class HybridRetriever:
    """
    Hybrid retriever combining Dense Vector Search + Sparse BM25 Search
    using Reciprocal Rank Fusion (RRF) followed by Reranking.
    """
    def __init__(
        self,
        top_k: int = settings.TOP_K_RETRIEVAL,
        rrf_k: int = settings.RRF_K
    ):
        self.top_k = top_k
        self.rrf_k = rrf_k
        self._retrieval_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._max_cache_size = 1024

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval:
        1. Dense Vector Search (Top 25)
        2. Sparse BM25 Search (Top 25 with intent-aware augmentation)
        3. Reciprocal Rank Fusion (RRF)
        4. Re-ranker with Intent and Pricing Boosts (Top K)
        """
        k = top_k or self.top_k
        cache_key = f"{query.strip().lower()}_{k}_{intent or ''}"
        if metadata_filter is None and cache_key in self._retrieval_cache:
            return self._retrieval_cache[cache_key]

        candidates_pool_size = max(25, k * 4)

        # 1. Vector Search
        query_vec = embedding_service.embed_query(query)
        vec_results = vector_store.search(
            query_vec,
            top_k=candidates_pool_size,
            metadata_filter=metadata_filter
        )

        # 2. BM25 Search with intent-aware augmentation
        bm25_query = query
        if intent == "free_offer" or "free" in query.lower():
            bm25_query += " free website ₹0 zero development cost deliverables"
        elif intent in ("emi", "payment_terms") or "emi" in query.lower() or "upfront" in query.lower():
            bm25_query += " 25% upfront 75% zero-cost 12-month emi payment"
        elif intent and intent.startswith("pricing"):
            bm25_query += " pricing charges cost packages fee"
            if intent == "pricing_crm":
                bm25_query += " crm erp pipeline"
            elif intent == "pricing_app":
                bm25_query += " mobile app flutter react native"
            elif intent == "pricing_website":
                bm25_query += " website ₹0 free scope"
            elif intent == "pricing_ai":
                bm25_query += " ai chatbot automation"
            elif intent in ("pricing_seo", "pricing_digital_marketing"):
                bm25_query += " seo smo marketing"

        bm25_results = bm25_index.search(
            bm25_query,
            top_k=candidates_pool_size
        )

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF Score = 1 / (60 + rank)
        combined: Dict[str, Dict[str, Any]] = {}

        # Process vector ranks
        for rank, (chunk, vec_score) in enumerate(vec_results):
            chunk_id = chunk["id"]
            if chunk_id not in combined:
                combined[chunk_id] = {
                    "chunk": chunk,
                    "rrf_score": 0.0,
                    "vector_score": vec_score,
                    "bm25_score": 0.0
                }
            combined[chunk_id]["rrf_score"] += 1.0 / (self.rrf_k + rank + 1)

        # Process BM25 ranks
        for rank, (chunk, bm25_score) in enumerate(bm25_results):
            chunk_id = chunk["id"]
            if chunk_id not in combined:
                combined[chunk_id] = {
                    "chunk": chunk,
                    "rrf_score": 0.0,
                    "vector_score": 0.0,
                    "bm25_score": bm25_score
                }
            combined[chunk_id]["bm25_score"] = bm25_score
            combined[chunk_id]["rrf_score"] += 1.0 / (self.rrf_k + rank + 1)

        candidates = list(combined.values())

        # If no hybrid matches found (e.g. empty index), return empty list
        if not candidates:
            return []

        # 4. Reranking
        reranked_results = reranker.rerank(query, candidates, top_k=k, intent=intent)

        # 5. Format return structure
        output = []
        for item in reranked_results:
            chunk = item["chunk"]
            meta = chunk.get("metadata", {})
            output.append({
                "chunk_id": chunk["id"],
                "content": chunk["content"],
                "source_url": meta.get("source_url", "https://techvunex.in/"),
                "page_title": meta.get("page_title", "Techvunex"),
                "section": meta.get("section", ""),
                "content_type": meta.get("content_type", "general"),
                "pricing_type": meta.get("pricing_type", ""),
                "service": meta.get("service", ""),
                "relevance_score": item.get("rerank_score", 0.0),
                "vector_score": item.get("vector_score", 0.0),
                "bm25_score": item.get("bm25_score", 0.0),
                "rrf_score": item.get("rrf_score", 0.0)
            })

        if metadata_filter is None:
            if len(self._retrieval_cache) >= self._max_cache_size:
                oldest_keys = list(self._retrieval_cache.keys())[:len(self._retrieval_cache) // 5]
                for ok in oldest_keys:
                    self._retrieval_cache.pop(ok, None)
            self._retrieval_cache[cache_key] = output

        logger.info(f"Hybrid retriever returned {len(output)} chunks for query: '{query[:40]}'")
        return output

hybrid_retriever = HybridRetriever()
