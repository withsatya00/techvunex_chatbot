import pytest
from app.rag.chunker import StructureAwareChunker

def test_structure_aware_chunking():
    chunker = StructureAwareChunker(chunk_size=300, chunk_overlap=50)

    doc_text = """# Custom Software Development
Techvunex develops tailored software systems for enterprise workflows.

## Our Approach
We conduct deep architectural discovery sprints.
We design scalable cloud-native microservices.

## Technology Stack
Python, FastAPI, React, PostgreSQL, Redis, and Docker.
"""

    chunks = chunker.chunk_document(
        url="https://techvunex.in/services/custom-software",
        page_title="Custom Software Development | Techvunex Innovation",
        text=doc_text
    )

    assert len(chunks) >= 2
    for c in chunks:
        meta = c["metadata"]
        assert meta["source_url"] == "https://techvunex.in/services/custom-software"
        assert meta["content_type"] == "service"
        assert "chunk_index" in meta
        assert "Title:" in c["content"]

def test_content_type_detection():
    chunker = StructureAwareChunker()
    assert chunker.detect_content_type("https://techvunex.in/services/crm-erp") == "service"
    assert chunker.detect_content_type("https://techvunex.in/solutions/ai-integration") == "solution"
    assert chunker.detect_content_type("https://techvunex.in/about") == "about"
    assert chunker.detect_content_type("https://techvunex.in/contact") == "contact"
    assert chunker.detect_content_type("https://techvunex.in/portfolio") == "portfolio"
    assert chunker.detect_content_type("https://techvunex.in/privacy-policy") == "legal"
