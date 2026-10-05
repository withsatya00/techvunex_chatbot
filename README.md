# Techvunex AI Website Assistant & Intelligent RAG Chatbot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-25%20passed-success.svg)](#testing--evaluation)
[![RAG Evaluation](https://img.shields.io/badge/Faithfulness-98%25-brightgreen.svg)](#rag-evaluation-benchmarks)

A production-ready AI Website Assistant, RAG Chatbot, Sales Assistant, and Lead Qualification System engineered specifically for **Techvunex Innovation** ([https://techvunex.in/](https://techvunex.in/)).

---

## 1. System Architecture

```
User Query (Widget / API)
        │
        ▼
┌──────────────────────────────────────────────┐
│  Security & Prompt Injection Protection Layer │
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│        Query Understanding Agent             │
│ (Intent, Entities, Urgency, Lang, Lead Intent)│
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│              Hybrid Retrieval                │
│  ┌────────────────────┐ ┌──────────────────┐ │
│  │ Dense Vector Store │ │ Sparse BM25 Store│ │
│  └────────────────────┘ └──────────────────┘ │
│           │                      │           │
│           └──────────┬───────────┘           │
│                      ▼                       │
│        Reciprocal Rank Fusion (RRF)          │
│                      │                       │
│                      ▼                       │
│             Cross-Scoring Reranker           │
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│        Context Construction & Grounding       │
│      (Strict Anti-Hallucination Guardrails)   │
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│            LLM Provider Gateway              │
│ ┌─────────┐ ┌────────┐ ┌──────┐ ┌──────────┐ │
│ │ Gemini  │ │ OpenAI │ │ Groq │ │  Ollama  │ │
│ └─────────┘ └────────┘ └──────┘ └──────────┘ │
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│     Sales Assistant & Lead Qualification     │
│   (Auto-Leads, Contact Extraction, Handoff)  │
└──────────────────────────────────────────────┘
        │
        ▼
Response Streaming (SSE) / JSON + Source Citations
```

---

## 2. Key Capabilities

1. **Intelligent RAG Retrieval**:
   - Hybrid Vector Search (`pgvector` / cosine similarity) + BM25 keyword search.
   - Reciprocal Rank Fusion ($RRF = \sum \frac{1}{60 + rank}$).
   - Cross-scoring reranker boosting query-intent alignment, section matches, and keyword density.
2. **Real Techvunex Website Knowledge Base**:
   - Automated crawler parsing `sitemap.xml` discovering all 23 official canonical URLs (Services, Solutions, Portfolio, Contact, About, Policies).
   - Structure-aware chunking preserving titles, headings (`#`, `##`), service specifications, and contact metadata.
3. **Pluggable LLM Provider Abstraction**:
   - Seamlessly switch between **Gemini**, **OpenAI**, **Groq**, **Ollama**, and built-in local fallback via environment variable `LLM_PROVIDER`.
4. **AI Sales Assistant & Progressive Lead Qualification**:
   - Non-intrusive qualification: gathers Name, Email, Phone, Company, Service, Requirement, Budget, and Timeline progressively without interrogation.
   - Saves qualified leads with real-time statuses (`new`, `contacted`, `qualified`, `converted`, `human_required`).
5. **Strict Anti-Hallucination Controls**:
   - Grounded solely on verified knowledge base data.
   - Explicit fallback: *"I don't have verified information about that. I can connect you with the Techvunex team."*
   - Never fabricates prices, client names, project timelines, or guarantees.
6. **Multilingual & Hinglish Support**:
   - Fluently detects and replies in natural English, Hindi, and Hinglish (e.g. *"bhai mujhe CRM banwana hai"*).
7. **Embeddable Chat Widget**:
   - Lightweight, standalone script bundle (`<script src="https://YOUR-DOMAIN/widget.js"></script>`) matching Techvunex visual identity (Violet `#7c3aed`, deep slate, Poppins font).
8. **Operations Admin Dashboard**:
   - Comprehensive administrative web portal (`/admin`) displaying real-time conversation history, lead pipeline, knowledge base status, and analytics.

---

## 3. Technology Stack

- **Backend**: Python 3.11, FastAPI, Pydantic v2, Uvicorn, AsyncIO
- **Database & Vectors**: PostgreSQL 16 + pgvector, SQLAlchemy 2.0 (async), with automatic SQLite + NumPy cosine fallback for standalone local execution
- **Caching**: Redis 7
- **Information Retrieval**: BM25Okapi (`rank-bm25`), Sentence-Transformers (`all-MiniLM-L6-v2` / `bge-m3`), Reciprocal Rank Fusion (RRF)
- **LLM Integrations**: Google Gemini, OpenAI, Groq, Ollama
- **Frontend Widget & Admin**: Vanilla JavaScript (zero framework runtime dependency), CSS3 Design System, HTML5

---

## 4. Database Schema

- `users`: id, name, email, phone, company, role, password_hash, created_at
- `conversations`: id, session_id, user_id, title, intent, created_at, updated_at
- `messages`: id, conversation_id, role, content, sources (JSON), token_usage (JSON), created_at
- `leads`: id, name, email, phone, company, service, requirement, budget, timeline, status, source, human_required, created_at, updated_at
- `documents`: id, url, title, content, content_hash, metadata_info (JSON), created_at, updated_at
- `document_chunks`: id, document_id, chunk_index, content, embedding (JSON/Vector), metadata_info (JSON), created_at
- `feedbacks`: id, conversation_id, message_id, rating, feedback, created_at

---

## 5. Quick Start & Setup

### Prerequisites
- Python 3.11+
- Git

### Local Installation
```bash
# 1. Clone repository and navigate to directory
cd "Techvunex chatbot"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env and supply GEMINI_API_KEY (or OPENAI_API_KEY / GROQ_API_KEY)

# 4. Crawl & Index Knowledge Base
python -m app.ingestion.crawl
python -m app.ingestion.index

# 5. Start Server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:
- **Interactive Website Demo with Chatbot**: [http://localhost:8000/](http://localhost:8000/)
- **Admin Dashboard**: [http://localhost:8000/admin](http://localhost:8000/admin)
- **Swagger API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 6. Website Integration

To integrate the Techvunex AI chatbot into the production Techvunex website or any external landing page, simply add a single script tag before the closing `</body>` tag:

```html
<!-- Techvunex AI Assistant Widget -->
<script src="https://YOUR-CHATBOT-DOMAIN/widget.js"></script>
```

The widget automatically initializes, injects its responsive stylesheet, attaches the launcher button at the bottom-right corner, and communicates with the backend via Server-Sent Events (SSE).

---

## 7. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Application health and KB status |
| `POST` | `/api/v1/auth/login` | Admin authentication, returns JWT |
| `POST` | `/api/v1/chat` | Standard JSON chat response |
| `POST` | `/api/v1/chat/stream` | Server-Sent Events (SSE) streaming chat |
| `GET` | `/api/v1/conversations` | List conversation sessions |
| `GET` | `/api/v1/conversations/{id}` | Detailed conversation transcript |
| `DELETE` | `/api/v1/conversations/{id}` | Delete conversation session |
| `POST` | `/api/v1/leads` | Create lead record |
| `GET` | `/api/v1/leads` | List qualified leads (filter by status) |
| `PATCH` | `/api/v1/leads/{id}` | Update lead status |
| `POST` | `/api/v1/feedback` | Record user feedback (rating & notes) |
| `GET` | `/api/v1/kb/documents` | List indexed documents |
| `POST` | `/api/v1/kb/ingest` | Trigger crawler and indexing |
| `POST` | `/api/v1/kb/reindex` | Full knowledge base reindexing |

---

## 8. Docker Deployment

Deploy the entire stack with PostgreSQL (`pgvector`), Redis, and FastAPI:

```bash
docker compose up -d --build
```

View running containers:
```bash
docker compose ps
```

---

## 9. Testing & Evaluation

### Running Tests
Execute the automated test suite covering unit tests and integration tests:
```bash
python -m pytest tests/ -v
```

### Running RAG Evaluation (50 Realistic Questions)
Execute the comprehensive benchmark evaluating Recall@K, Answer Relevance, and Faithfulness:
```bash
python -m app.evaluation.run
```

**Evaluation Benchmark Results:**
- **Retrieval Recall**: 90%
- **Mean Reciprocal Rank (MRR)**: 0.86
- **Answer Relevance**: 74%
- **Faithfulness (Anti-Hallucination)**: 98%
- **Prompt Injection Defense**: 100% blocked
