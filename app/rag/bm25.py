import re
from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi

class BM25Searcher:
    """
    BM25 Okapi indexer and retriever for keyword-based search.
    """
    def __init__(self):
        self.bm25: BM25Okapi = None
        self.corpus: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Tokenize text into lowercase alpha-numeric tokens"""
        tokens = re.findall(r'\b[a-zA-Z0-9_\-\.]{2,}\b', text.lower())
        return tokens

    def index(self, documents: List[Dict[str, Any]]):
        """
        Build BM25 index over documents.
        Each doc should have: id, content, metadata
        """
        self.corpus = documents
        self.tokenized_corpus = [self.tokenize(doc["content"]) for doc in documents]
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search documents by BM25 score.
        Returns list of (document, score) sorted by score descending.
        """
        if not self.bm25 or not self.corpus:
            return []

        tokenized_query = self.tokenize(query)
        if not tokenized_query:
            return []

        scores = self.bm25.get_scores(tokenized_query)
        scored_docs = []
        for i, score in enumerate(scores):
            if score > 0.01:
                scored_docs.append((self.corpus[i], float(score)))

        scored_docs.sort(key=lambda x: x[1], reverse=True)
        return scored_docs[:top_k]

bm25_index = BM25Searcher()
