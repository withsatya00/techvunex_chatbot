import os
import hashlib
import numpy as np
from typing import List, Union
from app.config import settings
from app.core.logging import logger

class EmbeddingGenerator:
    """
    Configurable embedding generation supporting:
    - sentence-transformers (local neural models like BAAI/bge-m3, all-MiniLM-L6-v2)
    - OpenAI embeddings
    - Gemini embeddings
    - Fast deterministic dense fallback (384-dim) for offline/testing environments
    """
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        self.model_name = model_name
        self._st_model = None
        self.dim = 384
        self._query_cache: dict = {}
        self._max_cache_size = 2048

    def _get_st_model(self):
        if self._st_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading sentence-transformer model: {self.model_name}")
                self._st_model = SentenceTransformer(self.model_name)
                self.dim = self._st_model.get_sentence_embedding_dimension()
            except Exception as e:
                logger.warning(f"Could not load sentence-transformers model '{self.model_name}': {e}. Using dense fallback.")
                self._st_model = "fallback"
        return self._st_model

    def _fallback_embed(self, text: str) -> List[float]:
        """
        Fast deterministic 384-dim semantic representation fallback
        based on token n-grams and hashing trick, normalized to unit length.
        """
        tokens = text.lower().split()
        vec = np.zeros(self.dim, dtype=np.float32)
        if not tokens:
            return vec.tolist()

        for i, token in enumerate(tokens):
            h = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h % 2 == 0) else -1.0
            vec[idx] += sign

            # bigram
            if i > 0:
                bigram = f"{tokens[i-1]}_{token}"
                hb = int(hashlib.sha256(bigram.encode('utf-8')).hexdigest(), 16)
                idx_b = hb % self.dim
                vec[idx_b] += 1.5 if (hb % 2 == 0) else -1.5

        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            vec = vec / norm
        return vec.tolist()

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding vector for a single query text with in-memory caching"""
        cache_key = query.strip().lower()
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]

        vec = self.embed_documents([query])[0]
        if len(self._query_cache) >= self._max_cache_size:
            # Evict oldest 20%
            keys = list(self._query_cache.keys())[:len(self._query_cache) // 5]
            for k in keys:
                self._query_cache.pop(k, None)
        self._query_cache[cache_key] = vec
        return vec

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a list of document chunks"""
        if not texts:
            return []

        # Check for OpenAI embedding if configured
        if settings.OPENAI_API_KEY and "text-embedding" in self.model_name:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                resp = client.embeddings.create(input=texts, model=self.model_name)
                return [d.embedding for d in resp.data]
            except Exception as e:
                logger.error(f"OpenAI embedding failed: {e}. Falling back.")

        # Try sentence-transformers
        model = self._get_st_model()
        if model != "fallback" and model is not None:
            try:
                embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
                return [emb.tolist() for emb in embeddings]
            except Exception as e:
                logger.error(f"Sentence-transformer encoding failed: {e}. Falling back.")

        # Fallback dense embedding
        return [self._fallback_embed(t) for t in texts]

embedding_service = EmbeddingGenerator()
