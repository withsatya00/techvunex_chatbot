import json
import os
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

from app.rag.embeddings import embedding_service
from app.rag.chunker import StructureAwareChunker
from app.rag.vector_store import VectorStore
from app.rag.bm25 import BM25Searcher
from app.rag.reranker import reranker

data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "knowledge_base")
raw_docs_file = os.path.join(data_dir, "crawled_docs.json")
indexed_kb_file = os.path.join(data_dir, "indexed_kb.json")

print(f"Reading raw docs from: {raw_docs_file}")
with open(raw_docs_file, "r", encoding="utf-8") as f:
    raw_docs = json.load(f)

chunker = StructureAwareChunker()
indexed_chunks = []

for doc in raw_docs:
    url = doc["url"]
    title = doc["title"]
    content = doc["content"]
    metadata = doc.get("metadata", {})
    
    chunks = chunker.chunk_document(url, title, content, metadata)
    for idx, c in enumerate(chunks):
        # Generate deterministic 384-dim normalized embedding
        emb = embedding_service._fallback_embed(c["content"])
        chunk_record = {
            "id": f"{url}#chunk_{idx}",
            "document_id": url,
            "chunk_index": idx,
            "content": c["content"],
            "embedding": emb,
            "metadata": c["metadata"]
        }
        indexed_chunks.append(chunk_record)

print(f"Total chunks indexed: {len(indexed_chunks)}")

# Save to indexed_kb.json
with open(indexed_kb_file, "w", encoding="utf-8") as f:
    json.dump(indexed_chunks, f, ensure_ascii=False, indent=2)

print(f"Saved {len(indexed_chunks)} chunks to {indexed_kb_file}")

# Verify retrieval test
vs = VectorStore()
vs.add_chunks(indexed_chunks)
bm = BM25Searcher()
bm.index(indexed_chunks)

test_queries = [
    ("Free Website offer", "Do you offer free website?"),
    ("EMI Payment Terms", "What is the 12 month zero cost EMI?"),
    ("Mobile App Development", "Do you develop Android and iOS apps in Flutter?"),
    ("CRM ERP", "What CRM and ERP solutions do you build?"),
    ("SEO SMO", "Do you provide SEO and Digital Marketing?")
]

print("\n--- RETRIEVAL TEST RESULTS ---")
for cat, q in test_queries:
    q_vec = embedding_service._fallback_embed(q)
    v_matches = vs.search(q_vec, top_k=2)
    b_matches = bm.search(q, top_k=2)
    print(f"\n[Category: {cat}] Query: '{q}'")
    print(f"  > Vector top match: {v_matches[0][0]['content'][:100]}... (sim: {v_matches[0][1]:.3f})")
    print(f"  > BM25 top match:   {b_matches[0][0]['content'][:100]}... (score: {b_matches[0][1]:.2f})")
