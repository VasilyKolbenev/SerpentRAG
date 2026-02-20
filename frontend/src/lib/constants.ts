/**
 * Design tokens, strategy data, and advisor questions.
 * Ported from serpent-rag-ui.jsx.
 */

import type { StrategyMeta, AdvisorQuestion, TabInfo, PipelineConfigItem } from '@/types/ui';
import type { RAGStrategy } from '@/types/api';

// ── Strategy Data ──────────────────────────────────

export const STRATEGIES: StrategyMeta[] = [
  {
    id: 'agentic',
    name: 'Agentic RAG',
    icon: '\u26A1',
    color: '#C8F547',
    desc: 'Autonomous multi-step reasoning with tool use. Best for complex queries requiring planning, decomposition, and iterative retrieval.',
    tags: ['Multi-hop QA', 'Research', 'Analysis', 'Complex Reasoning'],
    strengths: [
      'Dynamic query planning',
      'Self-correcting retrieval',
      'Tool orchestration',
      'Chain-of-thought',
    ],
    useCases: [
      'Research across multiple documents',
      'Questions requiring synthesis from diverse sources',
      'Tasks needing iterative refinement',
      'Complex analytical workflows',
    ],
    complexity: 5,
    latency: 'Medium-High',
    accuracy: 'Very High',
  },
  {
    id: 'graph',
    name: 'Graph RAG',
    icon: '\uD83D\uDD78\uFE0F',
    color: '#8B5CF6',
    desc: 'Knowledge graph-enhanced retrieval. Best for entity-rich domains with complex relationships between concepts.',
    tags: ['Entity Relations', 'Knowledge Graphs', 'Ontologies', 'Structured Data'],
    strengths: [
      'Relationship traversal',
      'Entity disambiguation',
      'Hierarchical reasoning',
      'Context preservation',
    ],
    useCases: [
      'Legal document analysis',
      'Medical knowledge bases',
      'Organizational knowledge mapping',
      'Supply chain / dependency analysis',
    ],
    complexity: 4,
    latency: 'Medium',
    accuracy: 'High',
  },
  {
    id: 'hybrid',
    name: 'Hybrid RAG',
    icon: '\uD83D\uDD00',
    color: '#2DD4A8',
    desc: 'Combines dense + sparse retrieval with re-ranking. Balanced approach for general-purpose use cases.',
    tags: ['Dense + Sparse', 'Re-ranking', 'Fusion', 'General Purpose'],
    strengths: [
      'BM25 + Vector fusion',
      'Cross-encoder re-ranking',
      'Adaptive chunking',
      'Broad coverage',
    ],
    useCases: [
      'Enterprise search',
      'Customer support knowledge bases',
      'Documentation Q&A',
      'General-purpose retrieval',
    ],
    complexity: 3,
    latency: 'Low-Medium',
    accuracy: 'High',
  },
  {
    id: 'naive',
    name: 'Simple RAG',
    icon: '\uD83D\uDCC4',
    color: '#38BDF8',
    desc: 'Straightforward vector similarity search. Fast, simple, and effective for well-structured single-source documents.',
    tags: ['Vector Search', 'Fast', 'Simple', 'Lightweight'],
    strengths: [
      'Low latency',
      'Easy to debug',
      'Minimal compute',
      'Predictable behavior',
    ],
    useCases: [
      'FAQ systems',
      'Single-document Q&A',
      'Prototyping & testing',
      'Low-latency requirements',
    ],
    complexity: 1,
    latency: 'Low',
    accuracy: 'Medium',
  },
  {
    id: 'memo',
    name: 'MemoRAG',
    icon: '\uD83E\uDDE0',
    color: '#FF6B9D',
    desc: 'Dual-system RAG with global memory. Light LLM builds collection-level memory, generates retrieval clues, then heavy LLM answers.',
    tags: ['Global Memory', 'Dual-System', 'Clue-Guided', 'Holistic'],
    strengths: [
      'Collection-level understanding',
      'Clue-guided retrieval',
      'Better for vague queries',
      'Memory caching (24h)',
    ],
    useCases: [
      'Large knowledge bases needing holistic understanding',
      'Vague or broad queries',
      'Enterprise document collections',
      'Cross-document synthesis',
    ],
    complexity: 4,
    latency: 'Medium',
    accuracy: 'High',
  },
  {
    id: 'corrective',
    name: 'Corrective RAG',
    icon: '\u2705',
    color: '#F97316',
    desc: 'Self-correcting retrieval with LLM relevance grading. Grades each document, supplements or falls back to web search when needed.',
    tags: ['Self-Correcting', 'Relevance Grading', 'Web Fallback', 'High Accuracy'],
    strengths: [
      'Relevance grading per document',
      'Automatic quality control',
      'Web search fallback',
      'Document refinement',
    ],
    useCases: [
      'High-stakes domains (legal, medical)',
      'When retrieval quality varies',
      'Domains requiring factual accuracy',
      'Compliance-sensitive applications',
    ],
    complexity: 3,
    latency: 'Medium',
    accuracy: 'High',
  },
];

// ── Strategy Lookup ────────────────────────────────

export const STRATEGY_MAP: Record<RAGStrategy, StrategyMeta> =
  Object.fromEntries(STRATEGIES.map((s) => [s.id, s])) as Record<RAGStrategy, StrategyMeta>;

export const STRATEGY_COLORS: Record<RAGStrategy, string> = {
  agentic: '#C8F547',
  corrective: '#F97316',
  graph: '#8B5CF6',
  hybrid: '#2DD4A8',
  memo: '#FF6B9D',
  naive: '#38BDF8',
};

// ── Advisor Questions ──────────────────────────────

export const ADVISOR_QUESTIONS: AdvisorQuestion[] = [
  {
    id: 'domain',
    question: 'What domain are you working in?',
    options: [
      'Legal / Compliance',
      'Medical / Healthcare',
      'Enterprise / Business',
      'Technical / Engineering',
      'Research / Academic',
      'Customer Support',
      'Other',
    ],
  },
  {
    id: 'complexity',
    question: 'How complex are typical queries?',
    options: [
      'Simple factual lookups',
      'Multi-step reasoning needed',
      'Requires connecting multiple sources',
      'Complex analytical workflows',
    ],
  },
  {
    id: 'data',
    question: "What's your data structure like?",
    options: [
      'Flat documents (PDFs, text)',
      'Structured with entity relationships',
      'Mixed structured & unstructured',
      'Code repositories & technical docs',
    ],
  },
  {
    id: 'priority',
    question: "What's your top priority?",
    options: [
      'Speed / Low latency',
      'Maximum accuracy',
      'Cost efficiency',
      'Explainability / Transparency',
    ],
  },
];

// ── Navigation Tabs ────────────────────────────────

export const TABS: TabInfo[] = [
  { id: 'strategies', label: 'Strategies', icon: '\u25C8' },
  { id: 'chat', label: 'Chat', icon: '\u25C9' },
  { id: 'debugger', label: 'Debugger', icon: '\u25C6' },
  { id: 'compare', label: 'Compare', icon: '\u2261' },
  { id: 'graph', label: 'Graph', icon: '\u25CE' },
  { id: 'quality', label: 'Quality', icon: '\u25A3' },
];

// ── Pipeline Configs per Strategy ──────────────────

export const PIPELINE_CONFIGS: Record<RAGStrategy, PipelineConfigItem[]> = {
  agentic: [
    { label: 'Max Iterations', value: '5', type: 'number' },
    { label: 'Planning Model', value: 'gpt-4o / claude-3.5', type: 'select' },
    { label: 'Tool Use', value: true, type: 'toggle' },
    { label: 'Self-Reflection', value: true, type: 'toggle' },
    { label: 'Max Context', value: '128K', type: 'select' },
  ],
  graph: [
    { label: 'Graph Backend', value: 'Neo4j', type: 'select' },
    { label: 'Entity Extraction', value: 'NER + LLM', type: 'select' },
    { label: 'Max Hop Depth', value: '3', type: 'number' },
    { label: 'Community Detect', value: true, type: 'toggle' },
    { label: 'Relation Scoring', value: true, type: 'toggle' },
  ],
  hybrid: [
    { label: 'Dense Model', value: 'BGE-M3', type: 'select' },
    { label: 'Sparse Weight', value: '0.3', type: 'number' },
    { label: 'Re-ranker', value: 'Cross-Encoder', type: 'select' },
    { label: 'RRF Enabled', value: true, type: 'toggle' },
    { label: 'Chunk Overlap', value: '128', type: 'number' },
  ],
  naive: [
    { label: 'Embedding Model', value: 'BGE-M3', type: 'select' },
    { label: 'Top-K', value: '10', type: 'number' },
    { label: 'Chunk Size', value: '512', type: 'number' },
    { label: 'Sim Threshold', value: '0.5', type: 'number' },
  ],
  memo: [
    { label: 'Light Model', value: 'claude-3-haiku', type: 'select' },
    { label: 'Memory TTL', value: '24h', type: 'select' },
    { label: 'Max Memory Chunks', value: '200', type: 'number' },
    { label: 'Clue Count', value: '3-5', type: 'number' },
  ],
  corrective: [
    { label: 'Relevance Threshold', value: '0.7', type: 'number' },
    { label: 'Web Search', value: false, type: 'toggle' },
    { label: 'Search Provider', value: 'Tavily', type: 'select' },
    { label: 'Grading Batch Size', value: '5', type: 'number' },
  ],
};

// ── Supported Upload Formats ───────────────────────

export const SUPPORTED_FORMATS = ['pdf', 'docx', 'txt', 'md', 'csv', 'json'];

// ── Default Query Params ───────────────────────────

export const DEFAULT_QUERY_PARAMS = {
  collection: 'default',
  top_k: 10,
  temperature: 0.1,
  model: 'gpt-4o',
} as const;

// ── Health Polling ─────────────────────────────────

export const HEALTH_POLL_INTERVAL = 30_000; // 30s
