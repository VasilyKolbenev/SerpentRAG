/**
 * API types — mirrors backend Pydantic schemas 1:1.
 */

// ── Enums ──────────────────────────────────────────

export type RAGStrategy = 'agentic' | 'corrective' | 'graph' | 'hybrid' | 'memo' | 'naive';

export type DocumentStatus = 'pending' | 'processing' | 'indexed' | 'failed';

// ── Query ──────────────────────────────────────────

export interface QueryRequest {
  query: string;
  strategy: RAGStrategy;
  collection: string;
  top_k: number;
  temperature: number;
  model: string;
  filters?: Record<string, unknown>;
  // Agentic-specific
  max_iterations?: number;
  enable_planning?: boolean;
  enable_reflection?: boolean;
  // Graph-specific
  max_hops?: number;
  entity_types?: string[];
  // Hybrid-specific
  sparse_weight?: number;
  enable_reranking?: boolean;
  reranker_type?: 'cross-encoder' | 'colbert';
  // MemoRAG-specific
  light_model?: string;
  // CRAG-specific
  relevance_threshold?: number;
  web_search_enabled?: boolean;
  // Sufficient Context Check
  check_sufficiency?: boolean;
  sufficiency_threshold?: number;
  sufficiency_action?: 'abstain' | 'retry';
}

// ── Advisor Chatbot ─────────────────────────────────

export interface AdvisorChatRequest {
  session_id?: string;
  message: string;
}

export interface AdvisorRecommendation {
  recommended: string;
  scores: Record<string, number>;
  reasoning: string;
  settings: Record<string, unknown>;
}

export interface AdvisorChatResponse {
  session_id: string;
  reply: string;
  recommendation: AdvisorRecommendation | null;
  is_complete: boolean;
}

export interface SourceInfo {
  content: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface QueryResponse {
  answer: string;
  sources: SourceInfo[];
  strategy_used: RAGStrategy;
  metadata: Record<string, unknown>;
  latency_ms: number;
  trace_id: string;
}

// ── SSE Streaming ──────────────────────────────────

export interface SSEStatusEvent {
  event: 'status';
  data: { phase: 'retrieving' | 'generating' | 'planning' | 'reflecting' };
}

export interface SSESourcesEvent {
  event: 'sources';
  data: { sources: SourceInfo[] };
}

export interface SSETokenEvent {
  event: 'token';
  data: { text: string };
}

export interface SSEDoneEvent {
  event: 'done';
  data: {
    metadata: Record<string, unknown>;
    trace_id: string;
    latency_ms: number;
    strategy_used: RAGStrategy;
  };
}

export type SSEEvent = SSEStatusEvent | SSESourcesEvent | SSETokenEvent | SSEDoneEvent;

// ── Compare ────────────────────────────────────────

export interface CompareRequest {
  query: string;
  strategies: RAGStrategy[];
  collection: string;
  top_k: number;
  temperature: number;
  model: string;
}

export interface CompareResult {
  strategy: RAGStrategy;
  answer: string;
  sources: SourceInfo[];
  latency_ms: number;
  trace_id: string;
  quality_scores?: Record<string, number>;
}

export interface CompareResponse {
  query: string;
  results: CompareResult[];
}

// ── Documents ──────────────────────────────────────

export interface DocumentResponse {
  id: string;
  filename: string;
  status: DocumentStatus;
  chunks: number;
  collection: string;
  file_size: number;
  created_at: string;
}

export interface DocumentDetail extends DocumentResponse {
  content_type: string;
  error_message?: string;
  metadata: Record<string, unknown>;
}

export interface CollectionInfo {
  name: string;
  documents: number;
  chunks: number;
}

export interface CollectionListResponse {
  collections: CollectionInfo[];
}

// ── Strategy ───────────────────────────────────────

export interface RecommendationRequest {
  domain: string;
  query_complexity: string;
  data_structure: string;
  priority: string;
  description?: string;
}

export interface RecommendationResponse {
  recommended: RAGStrategy;
  scores: Record<string, number>;
  reasoning: string;
}

export interface StrategyInfo {
  id: string;
  name: string;
  description: string;
  complexity: number;
  latency: string;
  accuracy: string;
}

export interface StrategyListResponse {
  strategies: StrategyInfo[];
}

// ── Trace (RAG Debugger) ───────────────────────────

export interface TraceStep {
  name: string;
  duration_ms: number;
  input_summary: string;
  output_summary: string;
  result_count: number;
  details: Record<string, unknown>;
}

export interface PipelineTrace {
  trace_id: string;
  query: string;
  strategy: string;
  collection: string;
  total_latency_ms: number;
  steps: TraceStep[];
  chunks_retrieved: number;
  answer_length: number;
  model: string;
}

// ── Graph Explorer ─────────────────────────────────

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ── Quality Dashboard ──────────────────────────────

export interface QualityScores {
  faithfulness: number | null;
  context_precision: number | null;
  context_recall: number | null;
  answer_relevancy: number | null;
}

export interface QualityMetrics {
  strategy: string;
  period: string;
  total_queries: number;
  avg_scores: QualityScores;
  avg_latency_ms: number;
}

// ── Health ──────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  services: Record<string, string>;
  timestamp: string;
}
