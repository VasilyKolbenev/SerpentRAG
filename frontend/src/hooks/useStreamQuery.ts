/**
 * SSE streaming hook for POST /query/stream.
 * Uses fetch + ReadableStream (not EventSource, because we need POST).
 *
 * SSE protocol from backend:
 *   event: status  -> { phase: "retrieving" | "generating" | "planning" | "reflecting" }
 *   event: sources -> { sources: SourceInfo[] }
 *   event: token   -> { text: "..." }
 *   event: done    -> { metadata, trace_id, latency_ms, strategy_used }
 */

import { useCallback, useRef, useState } from 'react';
import type { QueryRequest, SourceInfo, RAGStrategy } from '@/types/api';
import type { StreamPhase, StreamState } from '@/types/ui';

const INITIAL_STATE: StreamState = {
  phase: 'idle',
  tokens: '',
  sources: [],
  traceId: null,
  latencyMs: null,
  strategyUsed: null,
  sessionId: null,
  error: null,
};

interface UseStreamQueryReturn {
  state: StreamState;
  start: (params: QueryRequest) => void;
  abort: () => void;
  isStreaming: boolean;
}

export function useStreamQuery(): UseStreamQueryReturn {
  const [state, setState] = useState<StreamState>(INITIAL_STATE);
  const abortRef = useRef<AbortController | null>(null);

  const abort = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setState((prev) => ({
      ...prev,
      phase: prev.phase === 'done' ? 'done' : 'idle',
    }));
  }, []);

  const start = useCallback(
    async (params: QueryRequest) => {
      // Abort previous stream if any
      abortRef.current?.abort();

      const controller = new AbortController();
      abortRef.current = controller;

      setState({
        ...INITIAL_STATE,
        phase: 'retrieving',
      });

      try {
        const res = await fetch('/api/query/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(params),
          signal: controller.signal,
        });

        if (!res.ok) {
          const errText = await res.text();
          setState((prev) => ({
            ...prev,
            phase: 'error',
            error: `HTTP ${res.status}: ${errText}`,
          }));
          return;
        }

        if (!res.body) {
          setState((prev) => ({
            ...prev,
            phase: 'error',
            error: 'ReadableStream not supported',
          }));
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            // Process remaining buffer
            if (buffer.trim()) {
              processSSEBuffer(buffer, setState);
            }
            setState((prev) => {
              if (prev.phase !== 'error') {
                return { ...prev, phase: 'done' };
              }
              return prev;
            });
            break;
          }

          buffer += decoder.decode(value, { stream: true });

          // Normalize \r\n to \n (sse-starlette sends \r\n line endings)
          buffer = buffer.replace(/\r\n/g, '\n');

          // Process complete SSE messages (separated by \n\n)
          const parts = buffer.split('\n\n');
          // Keep last (possibly incomplete) part in buffer
          buffer = parts.pop() ?? '';

          for (const part of parts) {
            processSSEMessage(part, setState);
          }
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          return; // User aborted — not an error
        }
        setState((prev) => ({
          ...prev,
          phase: 'error',
          error: err instanceof Error ? err.message : 'Stream failed',
        }));
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
      }
    },
    [],
  );

  const isStreaming =
    state.phase !== 'idle' &&
    state.phase !== 'done' &&
    state.phase !== 'error';

  return { state, start, abort, isStreaming };
}

// ── SSE Parsing ────────────────────────────────────

function processSSEBuffer(
  buffer: string,
  setState: React.Dispatch<React.SetStateAction<StreamState>>,
) {
  // Buffer may contain multiple SSE messages — split and process each
  const normalized = buffer.replace(/\r\n/g, '\n');
  const parts = normalized.split('\n\n');
  for (const part of parts) {
    if (part.trim()) {
      processSSEMessage(part, setState);
    }
  }
}

function processSSEMessage(
  message: string,
  setState: React.Dispatch<React.SetStateAction<StreamState>>,
) {
  // Standard SSE format: "event: <type>\ndata: <json>\n\n"
  const lines = message.split('\n');
  let eventType = '';
  let dataStr = '';

  for (const line of lines) {
    const trimmed = line.replace(/\r$/, '');
    if (trimmed.startsWith('event: ')) {
      eventType = trimmed.slice(7).trim();
    } else if (trimmed.startsWith('data: ')) {
      dataStr = trimmed.slice(6);
    }
  }

  if (!dataStr) return;

  try {
    const data = JSON.parse(dataStr);

    // Fallback: if no event: line, try to get event from data.event
    const event = eventType || (data.event as string) || '';

    switch (event) {
      case 'status':
        setState((prev) => ({
          ...prev,
          phase: (data.phase as StreamPhase) ?? prev.phase,
        }));
        break;

      case 'sources': {
        // Backend sends array directly, or {sources: [...]}
        const sources = Array.isArray(data) ? data : (data.sources ?? []);
        setState((prev) => ({
          ...prev,
          sources: sources as SourceInfo[],
        }));
        break;
      }

      case 'token':
        setState((prev) => ({
          ...prev,
          tokens: prev.tokens + ((data.text as string) ?? ''),
        }));
        break;

      case 'done':
        setState((prev) => ({
          ...prev,
          phase: 'done',
          traceId: (data.trace_id as string) ?? null,
          latencyMs: (data.latency_ms as number) ?? null,
          strategyUsed: (data.strategy as RAGStrategy) ?? (data.strategy_used as RAGStrategy) ?? null,
          sessionId: (data.session_id as string) ?? null,
        }));
        break;

      case 'error':
        setState((prev) => ({
          ...prev,
          phase: 'error',
          error: (data.message as string) ?? 'Unknown error',
        }));
        break;
    }
  } catch {
    // Skip malformed SSE data
  }
}
