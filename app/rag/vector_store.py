import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from app.core.logging import logger

class VectorStore:
    """
    In-memory and persistent vector index with cosine similarity search and metadata filtering.
    """
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.embeddings_matrix: Optional[np.ndarray] = None

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Add chunks with their precomputed embeddings.
        chunk: {"id": str, "content": str, "embedding": List[float], "metadata": dict}
        """
        if not chunks:
            return

        self.chunks.extend(chunks)
        matrix = [c["embedding"] for c in self.chunks]
        self.embeddings_matrix = np.array(matrix, dtype=np.float32)

        # Normalize matrix rows for cosine similarity via dot product
        norms = np.linalg.norm(self.embeddings_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1e-9
        self.embeddings_matrix = self.embeddings_matrix / norms
        logger.info(f"Vector store indexed {len(self.chunks)} chunks.")

    def clear(self):
        self.chunks = []
        self.embeddings_matrix = None

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Cosine similarity search over indexed chunks with optional metadata filter.
        """
        if not self.chunks or self.embeddings_matrix is None:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        scores = np.dot(self.embeddings_matrix, q_vec)
        
        results = []
        for idx, score in enumerate(scores):
            chunk = self.chunks[idx]
            
            # Apply metadata filter if specified
            if metadata_filter:
                match = True
                meta = chunk.get("metadata", {})
                for k, v in metadata_filter.items():
                    if meta.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            results.append((chunk, float(score)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

vector_store = VectorStore()
