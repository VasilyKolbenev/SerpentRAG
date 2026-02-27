/**
 * UI-specific types (not from backend).
 */

import type { RAGStrategy, SourceInfo } from './api';

// ── Navigation ─────────────────────────────────────

export type TabId =
  | 'strategies'
  | 'chat'
  | 'documents'
  | 'debugger'
  | 'compare'
  | 'graph'
  | 'quality';

export interface TabInfo {
  id: TabId;
  label: string;
  icon: string;
}

// ── Chat ───────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  strategy?: RAGStrategy;
  sources?: SourceInfo[];
  traceId?: string;
  latencyMs?: number;
  timestamp: number;
  isStreaming?: boolean;
}

// ── Streaming ──────────────────────────────────────

export type StreamPhase =
  | 'idle'
  | 'retrieving'
  | 'generating'
  | 'planning'
  | 'reflecting'
  | 'done'
  | 'error';

export interface StreamState {
  phase: StreamPhase;
  tokens: string;
  sources: SourceInfo[];
  traceId: string | null;
  latencyMs: number | null;
  strategyUsed: RAGStrategy | null;
  sessionId: string | null;
  error: string | null;
}

// ── Strategy UI ────────────────────────────────────

export interface StrategyMeta {
  id: RAGStrategy;
  name: string;
  icon: string;
  color: string;
  desc: string;
  tags: string[];
  strengths: string[];
  useCases: string[];
  complexity: number;
  latency: string;
  accuracy: string;
}

export interface AdvisorQuestion {
  id: string;
  question: string;
  options: string[];
}

export interface AdvisorResult {
  strategy: StrategyMeta;
  score: number;
  percentage: number;
}

// ── Pipeline Config ────────────────────────────────

export interface PipelineConfigItem {
  label: string;
  value: string | boolean;
  type: 'number' | 'select' | 'toggle';
}

// ── Graph Explorer ─────────────────────────────────

export interface GraphSettings {
  entity: string;
  depth: number;
  collection: string;
  limit: number;
}
