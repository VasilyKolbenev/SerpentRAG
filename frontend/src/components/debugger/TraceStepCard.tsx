/**
 * Individual trace step detail card for RAG Debugger.
 */

import { useState } from 'react';
import { formatDuration } from '@/lib/utils';
import type { TraceStep } from '@/types/api';

interface TraceStepCardProps {
  step: TraceStep;
  totalLatency: number;
  color: string;
  index: number;
}

const STEP_ICONS: Record<string, string> = {
  embedding: '\uD83E\uDDE0',
  vector_search: '\uD83D\uDD0D',
  bm25_search: '\uD83D\uDCC4',
  fusion: '\uD83D\uDD00',
  reranking: '\u2B06\uFE0F',
  generation: '\uD83D\uDCAC',
  entity_extraction: '\uD83C\uDFF7\uFE0F',
  graph_traversal: '\uD83D\uDD78\uFE0F',
  planning: '\uD83D\uDCCB',
  tool_execution: '\u26A1',
  reflection: '\uD83E\uDD14',
};

export default function TraceStepCard({
  step,
  totalLatency,
  color,
  index,
}: TraceStepCardProps) {
  const [expanded, setExpanded] = useState(false);
  const widthPct = totalLatency > 0 ? (step.duration_ms / totalLatency) * 100 : 0;
  const icon = STEP_ICONS[step.name] ?? '\u2699\uFE0F';

  return (
    <div
      className="rounded-[10px] overflow-hidden transition-all duration-300 cursor-pointer"
      style={{
        background: expanded ? '#0f0f0f' : '#0b0b0b',
        border: `1px solid ${expanded ? '#252525' : '#181818'}`,
        animation: `fadeSlideUp 0.4s ease-out ${index * 0.08}s both`,
      }}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Header */}
      <div className="flex items-center gap-3 p-3.5">
        <span className="text-lg">{icon}</span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[13px] font-medium text-serpent-text font-outfit">
              {step.name.replace(/_/g, ' ')}
            </span>
            {step.result_count > 0 && (
              <span className="text-[9px] px-1.5 py-[1px] rounded bg-[#111] text-serpent-text-muted font-mono border border-[#1a1a1a]">
                {step.result_count} results
              </span>
            )}
          </div>

          {/* Duration bar */}
          <div className="flex items-center gap-2">
            <div className="flex-1 h-[3px] bg-[#1a1a1a] rounded-sm overflow-hidden">
              <div
                className="h-full rounded-sm transition-[width] duration-700 ease-[cubic-bezier(0.4,0,0.2,1)]"
                style={{
                  width: `${widthPct}%`,
                  background: `linear-gradient(90deg, ${color}60, ${color})`,
                }}
              />
            </div>
            <span
              className="text-[10px] font-mono font-semibold shrink-0"
              style={{ color }}
            >
              {formatDuration(step.duration_ms)}
            </span>
          </div>
        </div>

        {/* Expand indicator */}
        <span
          className="text-serpent-text-dim text-xs transition-transform duration-200"
          style={{ transform: expanded ? 'rotate(180deg)' : 'none' }}
        >
          {'\u25BC'}
        </span>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-3.5 pb-3.5 border-t border-[#1a1a1a] pt-3 animate-fade-slide-up">
          {step.input_summary && (
            <div className="mb-2.5">
              <span className="text-[9px] text-serpent-text-dark uppercase tracking-wider font-mono">
                Input
              </span>
              <p className="text-[11px] text-serpent-text-muted mt-1 font-dm-sans leading-relaxed">
                {step.input_summary}
              </p>
            </div>
          )}

          {step.output_summary && (
            <div className="mb-2.5">
              <span className="text-[9px] text-serpent-text-dark uppercase tracking-wider font-mono">
                Output
              </span>
              <p className="text-[11px] text-serpent-text-muted mt-1 font-dm-sans leading-relaxed">
                {step.output_summary}
              </p>
            </div>
          )}

          {Object.keys(step.details).length > 0 && (
            <div>
              <span className="text-[9px] text-serpent-text-dark uppercase tracking-wider font-mono">
                Details
              </span>
              <pre className="mt-1 text-[10px] text-serpent-text-dim font-mono bg-[#080808] border border-[#131313] rounded-lg p-3 overflow-x-auto">
                {JSON.stringify(step.details, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
