/**
 * RAG Debugger page — view pipeline execution traces.
 * Killer Feature #1.
 */

import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import TraceViewer from '@/components/debugger/TraceViewer';
import { api } from '@/lib/api';
import { useTraceStore } from '@/stores/traceStore';
import type { PipelineTrace } from '@/types/api';

export default function DebuggerPage() {
  const { traceId } = useParams<{ traceId?: string }>();
  const cachedTrace = useTraceStore((s) =>
    traceId ? s.getTrace(traceId) : undefined,
  );
  const setTrace = useTraceStore((s) => s.setTrace);

  const [trace, setTraceLocal] = useState<PipelineTrace | null>(
    cachedTrace ?? null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [traceInput, setTraceInput] = useState('');

  // Fetch trace from API if not cached
  useEffect(() => {
    if (!traceId) return;
    if (cachedTrace) {
      setTraceLocal(cachedTrace);
      return;
    }

    setLoading(true);
    setError(null);

    api
      .getTrace(traceId)
      .then((data) => {
        setTraceLocal(data);
        setTrace(data);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load trace');
      })
      .finally(() => setLoading(false));
  }, [traceId, cachedTrace, setTrace]);

  const handleManualLoad = async () => {
    const id = traceInput.trim();
    if (!id) return;

    setLoading(true);
    setError(null);

    try {
      const data = await api.getTrace(id);
      setTraceLocal(data);
      setTrace(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load trace');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-slide-up">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-[26px] font-semibold tracking-tight font-outfit mb-[5px]">
            RAG Debugger
          </h1>
          <p className="text-[13px] text-serpent-text-muted font-dm-sans">
            Inspect pipeline execution traces step by step
          </p>
        </div>
      </div>

      {/* Manual trace ID input */}
      {!traceId && !trace && (
        <div className="bg-serpent-surface border border-serpent-border-light rounded-[14px] p-6 mb-5">
          <h3 className="text-[14px] font-semibold font-outfit text-serpent-text-secondary mb-3">
            Load a Trace
          </h3>
          <p className="text-[12px] text-serpent-text-muted font-dm-sans mb-4">
            Enter a trace ID or click "View trace" from a chat response to inspect the pipeline execution.
          </p>
          <div className="flex gap-2">
            <input
              value={traceInput}
              onChange={(e) => setTraceInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleManualLoad()}
              placeholder="Enter trace ID..."
              className="flex-1 px-3 py-2 text-[12px] bg-serpent-bg border border-serpent-border rounded-lg text-serpent-text-secondary font-mono placeholder:text-serpent-text-dark"
            />
            <button
              onClick={handleManualLoad}
              disabled={!traceInput.trim() || loading}
              className="px-4 py-2 text-[11px] bg-[#111] border border-serpent-border rounded-lg text-serpent-text-muted font-dm-sans font-medium cursor-pointer hover:border-serpent-border-hover transition-colors disabled:opacity-40"
            >
              Load
            </button>
          </div>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <div className="text-sm text-serpent-text-muted font-dm-sans animate-pulse">
            Loading trace...
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-red-500/5 border border-red-500/20 rounded-[14px] p-5 mb-5">
          <p className="text-[12px] text-red-400 font-dm-sans">{error}</p>
        </div>
      )}

      {/* Trace viewer */}
      {trace && !loading && <TraceViewer trace={trace} />}
    </div>
  );
}
