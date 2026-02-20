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
  const lines = buffer.split('\n');
  for (const line of lines) {
    processSSELine(line, setState);
  }
}

function processSSEMessage(
  message: string,
  setState: React.Dispatch<React.SetStateAction<StreamState>>,
) {
  const lines = message.split('\n');
  for (const line of lines) {
    processSSELine(line, setState);
  }
}

function processSSELine(
  line: string,
  setState: React.Dispatch<React.SetStateAction<StreamState>>,
) {
  if (!line.startsWith('data: ')) return;

  try {
    const raw = line.slice(6);
    const parsed = JSON.parse(raw);
    const event = parsed.event as string;
    const data = parsed.data ?? parsed;

    switch (event) {
      case 'status':
        setState((prev) => ({
          ...prev,
          phase: (data.phase as StreamPhase) ?? prev.phase,
        }));
        break;

      case 'sources':
        setState((prev) => ({
          ...prev,
          sources: data.sources as SourceInfo[],
        }));
        break;

      case 'token':
        setState((prev) => ({
          ...prev,
          tokens: prev.tokens + (data.text as string),
        }));
        break;

      case 'done':
        setState((prev) => ({
          ...prev,
          phase: 'done',
          traceId: (data.trace_id as string) ?? null,
          latencyMs: (data.latency_ms as number) ?? null,
          strategyUsed: (data.strategy_used as RAGStrategy) ?? null,
        }));
        break;
    }
  } catch {
    // Skip malformed SSE lines
  }
}
