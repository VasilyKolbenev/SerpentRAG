# SerpentRAG API Reference

Base URL: `http://localhost:8000`

Interactive docs (development only): `http://localhost:8000/docs`

## Authentication

All endpoints except `/health` require a JWT bearer token:

```
Authorization: Bearer <token>
```

## Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check (PostgreSQL, Redis, Qdrant, Neo4j status) |

### Query

| Method | Path | Description |
|--------|------|-------------|
| POST | `/query` | Execute RAG query with selected strategy |
| POST | `/query/stream` | SSE streaming RAG query (real-time token output) |

**POST /query** request body:
```json
{
  "query": "What is retrieval augmented generation?",
  "strategy": "hybrid",
  "collection": "my-docs",
  "model": "gpt-4o",
  "top_k": 5,
  "temperature": 0.1,
  "check_sufficiency": false
}
```

**POST /query/stream** — Same body, returns `text/event-stream` (SSE):
```
data: {"token": "Retrieval"}
data: {"token": " augmented"}
data: {"token": " generation"}
data: {"done": true, "sources": [...], "trace_id": "abc-123"}
```

### Compare (A/B Testing)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/compare` | Run query through multiple strategies simultaneously |

**Request body:**
```json
{
  "query": "Explain vector search",
  "strategies": ["naive", "hybrid", "graph"],
  "collection": "my-docs"
}
```

### Documents

| Method | Path | Description |
|--------|------|-------------|
| POST | `/documents/upload` | Upload document for processing (PDF, DOCX, TXT, MD) |
| GET | `/documents` | List all documents |
| GET | `/documents/{id}` | Get document details |
| DELETE | `/documents/{id}` | Delete document and its chunks |

### Collections

| Method | Path | Description |
|--------|------|-------------|
| GET | `/collections` | List all vector collections |
| POST | `/collections` | Create new collection |
| DELETE | `/collections/{name}` | Delete collection |

### Strategies

| Method | Path | Description |
|--------|------|-------------|
| GET | `/strategies` | List available RAG strategies with metadata |

### Pipeline Traces (RAG Debugger)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/traces/{trace_id}` | Get full pipeline trace for debugging |
| GET | `/traces` | List recent traces |

### Graph Explorer

| Method | Path | Description |
|--------|------|-------------|
| GET | `/graph/explore` | Get entity-relationship graph data for visualization |
| GET | `/graph/entities` | Search entities in knowledge graph |

### Quality Metrics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/metrics/quality` | RAGAS evaluation metrics (context relevance, faithfulness, answer relevance) |

### AI Advisor

| Method | Path | Description |
|--------|------|-------------|
| POST | `/advisor/chat` | Chat with AI advisor for strategy recommendations |

**Request body:**
```json
{
  "message": "I have technical documentation, ~500 pages",
  "session_id": "optional-session-id"
}
```

## RAG Strategies

| ID | Name | Use Case |
|----|------|----------|
| `naive` | Simple RAG | Quick prototyping, small collections |
| `hybrid` | Hybrid RAG | General purpose, best balance of speed/quality |
| `graph` | Graph RAG | Entity-rich documents, knowledge bases |
| `agentic` | Agentic RAG | Complex multi-hop questions |
| `memo` | MemoRAG | Large collections, recurring query patterns |
| `corrective` | Corrective RAG | High-stakes queries requiring source validation |

## Error Responses

```json
{
  "detail": "Error description",
  "status_code": 400
}
```

| Code | Meaning |
|------|---------|
| 400 | Bad request (invalid parameters) |
| 401 | Unauthorized (missing/invalid JWT) |
| 404 | Resource not found |
| 422 | Validation error (Pydantic) |
| 500 | Internal server error |
| 503 | Service unavailable (dependency down) |
