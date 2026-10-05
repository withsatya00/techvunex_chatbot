import pytest
from app.rag.bm25 import BM25Searcher
from app.rag.vector_store import VectorStore
from app.rag.reranker import CrossScoringReranker

def test_bm25_search():
    bm25 = BM25Searcher()
    docs = [
        {"id": "doc1", "content": "Techvunex provides custom CRM and ERP development solutions for sales teams."},
        {"id": "doc2", "content": "Techvunex provides mobile app development using Flutter and React Native."},
        {"id": "doc3", "content": "Our cloud solutions team works with AWS, Azure and GCP."}
    ]
    bm25.index(docs)

    results = bm25.search("CRM sales", top_k=2)
    assert len(results) > 0
    assert results[0][0]["id"] == "doc1"

def test_vector_store():
    store = VectorStore()
    chunks = [
        {"id": "c1", "content": "Artificial Intelligence and Chatbots", "embedding": [0.9, 0.1, 0.0], "metadata": {"type": "ai"}},
        {"id": "c2", "content": "Cloud Migration on AWS", "embedding": [0.0, 0.9, 0.1], "metadata": {"type": "cloud"}},
        {"id": "c3", "content": "Website Development React", "embedding": [0.1, 0.0, 0.9], "metadata": {"type": "web"}}
    ]
    store.add_chunks(chunks)

    # Search with embedding close to c1
    hits = store.search([0.85, 0.15, 0.0], top_k=1)
    assert len(hits) == 1
    assert hits[0][0]["id"] == "c1"

    # Search with metadata filter
    hits_filter = store.search([0.0, 0.9, 0.1], top_k=1, metadata_filter={"type": "cloud"})
    assert hits_filter[0][0]["id"] == "c2"

def test_reranker():
    reranker = CrossScoringReranker()
    candidates = [
        {
            "chunk": {
                "id": "c1",
                "content": "Techvunex develops custom CRM software for lead pipelines.",
                "metadata": {"page_title": "CRM Solutions", "section": "CRM"}
            },
            "rrf_score": 0.016,
            "vector_score": 0.8,
            "bm25_score": 4.5
        },
        {
            "chunk": {
                "id": "c2",
                "content": "Techvunex privacy policy details and cookies.",
                "metadata": {"page_title": "Privacy", "section": "Legal"}
            },
            "rrf_score": 0.010,
            "vector_score": 0.4,
            "bm25_score": 0.5
        }
    ]

    reranked = reranker.rerank("custom CRM software", candidates, top_k=2)
    assert len(reranked) == 2
    assert reranked[0]["chunk"]["id"] == "c1"
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]

def test_reranker_pricing_priority_over_generic():
    reranker = CrossScoringReranker()
    candidates = [
        {
            "chunk": {
                "id": "generic_chunk",
                "content": "Techvunex Innovation is a premier software development company in India with modern engineers.",
                "metadata": {"page_title": "About Techvunex", "section": "About Techvunex", "content_type": "about"}
            },
            "rrf_score": 0.025,
            "vector_score": 0.85,
            "bm25_score": 3.0
        },
        {
            "chunk": {
                "id": "pricing_chunk",
                "content": "100% Free Website Offer: modern 4-5 page business website with ₹0 development cost and WhatsApp integration.",
                "metadata": {"page_title": "Free Website Offer", "section": "Deliverables", "content_type": "pricing", "pricing_type": "free_offer"}
            },
            "rrf_score": 0.015,
            "vector_score": 0.70,
            "bm25_score": 2.5
        }
    ]

    # When user asks about price, pricing chunk MUST outrank generic chunk despite lower initial RRF
    reranked = reranker.rerank("How much does a normal website cost?", candidates, top_k=2, intent="pricing_website")
    assert reranked[0]["chunk"]["id"] == "pricing_chunk"
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]

