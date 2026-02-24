# SerpentRAG — Manual UI Testing Checklist

**URL:** http://localhost:3000
**API:** http://localhost:8000

---

## Pre-requisites

- [x] Docker stack running: `docker compose ps` — all 7 services up
- [x] API healthy: `curl http://localhost:8000/health` returns `"status": "healthy"`
- [x] Frontend loads: http://localhost:3000 shows SerpentRAG UI
- [x] API keys configured in `.env` (OPENAI_API_KEY and/or ANTHROPIC_API_KEY)

---

## 1. Strategies Page (`/strategies`)

### 1.1 Strategy Grid
- [x] All 6 strategy cards displayed (Simple, Hybrid, Graph, Agentic, MemoRAG, Corrective)
- [x] Each card shows: name, description, tags, complexity/latency/accuracy ratings
- [x] Click on strategy card — card visually highlights as selected
- [x] Selected strategy persists when navigating to Chat page

### 1.2 Strategy Advisor (wizard)
- [x] Click "Strategy Advisor" toggle — advisor panel opens
- [x] Step 1: Select domain (7 options) — click one, advances to step 2
- [x] Step 2: Select query complexity (4 options)
- [x] Step 3: Select data structure (4 options)
- [x] Step 4: Select priority (4 options)
- [x] After step 4: recommendation appears with strategy name + percentage scores
- [x] Click recommended strategy — applies to selected strategy
- [x] Click "Start Over" — wizard resets to step 1

### 1.3 Pipeline Architecture
- [x] 5-step pipeline visualization displayed (Ingest → Process → Index → Retrieve → Generate)

---

## 2. Chat Page (`/chat`)

### 2.1 Document Upload
- [x] Upload zone visible in sidebar
- [x] **Drag & drop** a PDF file — upload starts, status shows ⏳
- [x] **Click zone** to open file picker — select file, upload starts
- [x] File status changes: ⏳ uploading → ⚙️ processing → ✅ indexed
- [ ] Upload a DOCX file — same flow
- [x] Upload a TXT file — same flow
- [ ] Upload invalid file (e.g., .exe) — rejected or error shown
- [ ] Upload multiple files at once — all show in file list

### 2.2 Query (Streaming)
- [x] Type query in input box, press Enter
- [x] **Tokens stream** in real-time (word by word, not all at once)
- [ ] Streaming cursor visible during generation
- [x] After completion: full answer displayed with markdown formatting
- [x] **Source chips** appear below answer (filename + relevance score)
- [x] **Strategy badge** shows which strategy was used
- [x] **Latency** (ms) displayed
- [x] **"View trace →"** link appears — click opens Debugger page

### 2.3 Strategy Selection
- [x] Current strategy shown as badge in chat input
- [x] Change strategy on Strategies page → badge updates on Chat page
- [x] Query uses the selected strategy (check strategy badge in response)

### 2.4 Error Handling
- [ ] Send query with no uploaded documents — appropriate message returned
- [ ] Stop Docker API container → send query → error message displayed
- [ ] Restart API → retry query → works again

---

## 3. Debugger Page (`/debugger`)

### 3.1 Manual Trace Load
- [ ] Enter trace ID in input box, click "Load"
- [ ] Trace loads: summary bar + timeline + step cards
- [ ] Enter invalid trace ID → red error message shown
- [ ] Empty input → "Load" button disabled

### 3.2 Trace from Chat
- [ ] Send query on Chat page → click "View trace →" link
- [ ] Debugger page opens with trace pre-loaded
- [ ] Correct trace displayed (matching the query)

### 3.3 Trace Visualization
- [ ] **Summary bar:** query text, strategy badge, total latency, steps count, chunks retrieved, model name
- [ ] **Timeline:** horizontal bar with proportional segments for each step
- [ ] Hover timeline segments → tooltip shows step name + duration
- [ ] **Step cards:** click to expand/collapse
- [ ] Expanded card shows: inputs, outputs, metadata, duration

---

## 4. Compare Page (`/compare`)

### 4.1 Strategy Selection
- [ ] Click strategy buttons to toggle selection (checkmark appears)
- [ ] Select 2 strategies — "Compare" button becomes active
- [ ] Select 3-4 strategies — button still active
- [ ] Try to select 5+ — not allowed (max 4)
- [ ] Deselect to <2 — "Compare" button disabled

### 4.2 Comparison
- [ ] Type query, click "Compare" with 2 strategies selected
- [ ] Loading state: skeleton cards with gradient animation
- [ ] Results appear: 2 side-by-side cards
- [ ] Each card shows: strategy name, answer (markdown), sources, latency
- [ ] Compare with 3 strategies — 3 cards displayed
- [ ] Compare with 4 strategies — 4 cards displayed (grid)

### 4.3 Result Analysis
- [ ] Compare Naive vs Hybrid — Hybrid should have better sources
- [ ] Compare latencies — Naive should be fastest
- [ ] Answers differ between strategies (not identical)

---

## 5. Graph Page (`/graph`)

### 5.1 Graph Controls
- [ ] Enter entity name in search box
- [ ] Adjust depth slider (1-5)
- [ ] Adjust limit slider (10-200)
- [ ] Click "Explore" — graph loads

### 5.2 Graph Visualization
- [ ] Nodes displayed as colored circles with labels
- [ ] Edges displayed as lines connecting nodes
- [ ] **Node colors** differ by type (Person, Organization, Concept, etc.)
- [ ] Legend shows color mapping
- [ ] Graph stats: node count + edge count displayed
- [ ] **Click node** → graph re-centers on that node
- [ ] **Zoom** in/out with scroll wheel
- [ ] **Pan** by dragging background
- [ ] Hover node → tooltip appears

### 5.3 Empty State
- [ ] If no graph data (Neo4j empty) → empty state message with spider emoji

---

## 6. Quality Page (`/quality`)

### 6.1 Filters
- [ ] Click strategy buttons — selected strategy highlighted
- [ ] Click time period buttons (24h, 7d, 30d) — period changes
- [ ] Metrics update when filters change

### 6.2 Metrics Display
- [ ] 4 ScoreCards visible:
  - Faithfulness (0-1)
  - Context Precision (0-1)
  - Context Recall (0-1)
  - Answer Relevancy (0-1)
- [ ] Summary stats: Total Queries + Avg Latency
- [ ] Comparison BarChart renders with bars per strategy

### 6.3 Edge Cases
- [ ] No queries executed yet → metrics show 0 or empty state
- [ ] Switch between strategies → chart updates

---

## 7. Advisor Chatbot (Floating Widget)

### 7.1 Basic Interaction
- [ ] Floating 🐍 button visible in bottom-right corner
- [ ] Click button → chat window opens (400x500px)
- [ ] Click X (or button again) → chat window closes
- [ ] Type message, press Enter → message sent
- [ ] Advisor replies (Claude 3 Haiku)
- [ ] "Thinking..." indicator during response

### 7.2 Conversation
- [ ] Send: "Hello" → get greeting response
- [ ] Send: "I have technical docs, 500 pages" → get strategy advice
- [ ] Continue conversation — session persists (session_id)
- [ ] Click "Reset" → new session starts, messages cleared

### 7.3 Recommendation
- [ ] After describing use case, advisor returns recommendation card
- [ ] Card shows: recommended strategy, reasoning, top scores
- [ ] Recommendation card styled with strategy color

---

## 8. Global / Cross-Page

### 8.1 Navigation
- [x] Header shows all nav links: Strategies, Chat, Debugger, Compare, Graph, Quality
- [x] Click each nav link — correct page loads
- [x] Active page highlighted in nav

### 8.2 Health Status
- [x] "System: nominal" indicator in header (green when healthy)
- [x] Stop API → indicator changes to "offline" / "degraded"
- [x] Restart API → indicator recovers to "nominal"

### 8.3 Responsive
- [ ] Resize browser window — layout adapts (no horizontal scroll)
- [ ] All pages usable at 1280px width minimum

---

## 9. End-to-End Flow (Happy Path)

**The complete user journey:**

1. [x] Open http://localhost:3000 → Strategies page loads
2. [x] Select "Hybrid" strategy
3. [x] Navigate to Chat page
4. [x] Upload a PDF document → wait for "indexed" status ✅
5. [x] Type query about the document → tokens stream in real-time
6. [x] Answer appears with sources and trace link
7. [ ] Click "View trace →" → Debugger shows pipeline steps
8. [ ] Go to Compare page → select Naive + Hybrid + Graph
9. [ ] Run same query → see 3 results side-by-side
10. [ ] Go to Quality page → check metrics for Hybrid strategy
11. [ ] Open Advisor chatbot → describe use case → get recommendation
12. [ ] Go to Graph page → explore entity from uploaded document

---

## 10. Bugs Found & Fixed (Phase 8)

| # | Bug | Root Cause | Fix | Commit |
|---|-----|-----------|-----|--------|
| 1 | Docker daemon restarting every ~3 min | WSL2 `systemctl poweroff` (vmIdleTimeout) | `.wslconfig` with `vmIdleTimeout=-1` | `ccf6d03` |
| 2 | Qdrant 400: invalid point ID | `f"{doc_id}_{i}"` not valid UUID/uint | `uuid.uuid5()` in `document_processor.py` | `ccf6d03` |
| 3 | Vector dimension mismatch (1024 vs 384) | Worker missing `EMBEDDING_DIMENSIONS` env | Added `EMBEDDING_DIMENSIONS=384` to worker in `docker-compose.yml` | `ccf6d03` |
| 4 | LogRecord `name` key conflict | `extra={"name": ...}` overwrites built-in | Changed to `extra={"collection": ...}` in `vector_store.py` | `ccf6d03` |
| 5 | Collection creation race condition | Two workers create same collection simultaneously | try/except "already exists" in `vector_store.py` | `ccf6d03` |
| 6 | nginx 502 after API restart | Stale DNS cache (IP from startup) | `resolver 127.0.0.11 valid=10s` + variable `proxy_pass` | `ccf6d03` |
| 7 | nginx blocks file uploads >1MB | Default `client_max_body_size 1m` | Added `client_max_body_size 50m` in `nginx.conf` | `ccf6d03` |
| 8 | SSE tokens not displayed | Frontend expected nested JSON, backend sends standard SSE | Rewrote `processSSEMessage` for `event:`/`data:` format | `ccf6d03` |
| 9 | SSE buffer never splits | `\r\n\r\n` ≠ `\n\n` (sse-starlette sends `\r\n`) | `buffer.replace(/\r\n/g, '\n')` before split | `ccf6d03` |
| 10 | Pipeline Config shows "BGE-M3" | Hardcoded in `constants.ts` | Changed to "MiniLM-L6-v2" | `ccf6d03` |
| 11 | Dockerfile HEALTHCHECK restart loop | Docker Compose v5 ignores `start_period` | Removed HEALTHCHECK from Dockerfile | `ccf6d03` |
| 12 | Embedding model too slow (BGE-M3, 5+ min) | 1.7GB model on CPU | Switched to all-MiniLM-L6-v2 (80MB, ~3s load) | `ccf6d03` |

---

## 11. Bug Report Template

When finding issues, record:

```
**Page:** [Chat / Strategies / Debugger / Compare / Graph / Quality / Advisor]
**Steps to Reproduce:**
1. ...
2. ...
3. ...
**Expected:** ...
**Actual:** ...
**Screenshot:** [attach]
**Browser Console Errors:** [if any]
```
