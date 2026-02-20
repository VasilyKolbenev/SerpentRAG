# SerpentRAG

**Universal self-hosted RAG platform with 6 retrieval strategies**

![Python](https://img.shields.io/badge/python-3.12-blue)
![React](https://img.shields.io/badge/react-18-61dafb)
![License](https://img.shields.io/badge/license-BSL--1.1-orange)
![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen)
![Tests](https://img.shields.io/badge/tests-139%20passed-brightgreen)
![Docker](https://img.shields.io/badge/docker-compose-2496ED)

---

## What is SerpentRAG?

SerpentRAG is a production-ready RAG (Retrieval Augmented Generation) platform that lets you query your documents using 6 different retrieval strategies. Deploy on your own infrastructure, keep your data private, use any LLM provider.

### Key Features

- **RAG Debugger** — Full pipeline trace visualization (see exactly what happened at each step)
- **A/B Compare** — Run the same query through multiple strategies side-by-side
- **Graph Explorer** — Interactive Neo4j knowledge graph visualization
- **Quality Dashboard** — RAGAS metrics (context relevance, faithfulness, answer relevance)
- **AI Advisor** — Chatbot that recommends the best strategy for your use case
- **SSE Streaming** — Real-time token-by-token response streaming

## RAG Strategies

| Strategy | ID | Best For | Latency | Accuracy |
|----------|-----|----------|---------|----------|
| **Simple RAG** | `naive` | FAQ, single-doc Q&A, prototyping | Low | Medium |
| **Hybrid RAG** | `hybrid` | Enterprise search, general-purpose | Low-Medium | High |
| **Graph RAG** | `graph` | Entity-rich domains (legal, medical, biotech) | Medium | High |
| **Agentic RAG** | `agentic` | Complex research, multi-hop reasoning | Medium-High | Very High |
| **MemoRAG** | `memo` | Large collections, recurring query patterns | Medium | High |
| **Corrective RAG** | `corrective` | High-stakes queries, source validation | Medium | High |

## Architecture

```
                         ┌─────────────────┐
                         │   User Browser   │
                         └────────┬─────────┘
                                  │ HTTPS
                    ┌─────────────▼──────────────┐
                    │   Frontend (React + Nginx)  │
                    │        :3000                │
                    └─────────────┬───────────────┘
                                  │ /api/*
                    ┌─────────────▼───────────────┐
                    │   API Server (FastAPI)       │
                    │   6 RAG Strategies + SSE     │
                    │        :8000                 │
                    └──┬──────┬──────┬──────┬─────┘
                       │      │      │      │
              ┌────────▼┐ ┌──▼───┐ ┌▼─────┐ ┌▼──────┐
              │PostgreSQL│ │Redis │ │Qdrant│ │ Neo4j │
              │ pgvector │ │Cache │ │Vector│ │ Graph │
              │  :5432   │ │:6379 │ │:6333 │ │ :7687 │
              └──────────┘ └──┬───┘ └──────┘ └───────┘
                              │
                    ┌─────────▼───────────────┐
                    │   Celery Worker          │
                    │   Document Processing    │
                    └─────────────────────────┘
```

> C4 architecture diagrams (PlantUML): [`docs/architecture/`](docs/architecture/)

## Quick Start

```bash
# 1. Clone
git clone https://github.com/VasilyKolbenev/SerpentRAG.git
cd SerpentRAG

# 2. Configure
cp .env.example .env
# Edit .env: add your OPENAI_API_KEY and/or ANTHROPIC_API_KEY

# 3. Launch
docker compose up -d

# 4. Verify
curl http://localhost:8000/health
# Open http://localhost:3000 in browser
```

**Requirements:** Docker Engine 24+ with Docker Compose v2

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Tailwind CSS, Zustand, Vite |
| **Backend** | FastAPI, Uvicorn, Python 3.12, Pydantic v2 |
| **LLM** | LiteLLM (OpenAI, Anthropic, Ollama) |
| **Embeddings** | sentence-transformers (BGE-M3, 1024-dim, local) |
| **Vector Store** | Qdrant v1.11 |
| **Graph Store** | Neo4j 5.22 Community (optional) |
| **Database** | PostgreSQL 16 + pgvector |
| **Cache/Queue** | Redis 7 + Celery 5.4 |
| **Observability** | structlog, OpenTelemetry, Prometheus, Grafana |
| **Infrastructure** | Docker Compose, Traefik (production), Alembic migrations |

## Project Structure

```
serpent-rag-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # 9 API routers
│   │   ├── services/        # 8 core services
│   │   ├── strategies/      # 6 RAG strategies + factory
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── middleware/       # Logging, telemetry, tenant
│   │   ├── workers/         # Celery tasks
│   │   ├── main.py          # App factory
│   │   └── config.py        # Settings (pydantic-settings)
│   ├── tests/               # 139 tests, 80%+ coverage
│   ├── alembic/             # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/      # 25+ React components
│   │   ├── pages/           # 6 pages
│   │   ├── stores/          # Zustand stores
│   │   ├── hooks/           # SSE streaming hook
│   │   └── lib/             # API client, utils
│   ├── package.json
│   └── Dockerfile
├── infra/                   # Prometheus, Grafana, OTel configs
├── docs/
│   ├── architecture/        # C4 PlantUML diagrams
│   ├── API.md               # API reference
│   └── ROADMAP.md           # Commercialization roadmap
├── docker-compose.yml       # Development (7 services)
├── docker-compose.prod.yml  # Production (+ Traefik, monitoring)
└── .env.example             # Environment template
```

## API Endpoints

| Group | Endpoint | Description |
|-------|----------|-------------|
| Health | `GET /health` | Service health (PostgreSQL, Redis, Qdrant, Neo4j) |
| Query | `POST /query` | RAG query with selected strategy |
| Streaming | `POST /query/stream` | SSE streaming response |
| Compare | `POST /compare` | A/B test multiple strategies |
| Documents | `POST /documents/upload` | Upload PDF, DOCX, TXT, MD |
| Collections | `GET /collections` | Manage vector collections |
| Strategies | `GET /strategies` | List available strategies |
| Traces | `GET /traces/{id}` | Pipeline trace (RAG Debugger) |
| Graph | `GET /graph/explore` | Knowledge graph data |
| Metrics | `GET /metrics/quality` | RAGAS quality metrics |
| Advisor | `POST /advisor/chat` | AI strategy recommendation |

Full API reference: [`docs/API.md`](docs/API.md)

## Development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v --cov=app

# Frontend
cd frontend
npm ci
npm run dev
```

## License

**Business Source License 1.1 (BSL)**

- Source code is available for reading, modification, and non-production use
- Production use requires a commercial license
- Converts to Apache 2.0 on 2030-02-20

See [LICENSE](LICENSE) for details. For commercial licensing: serpentrag@proton.me
