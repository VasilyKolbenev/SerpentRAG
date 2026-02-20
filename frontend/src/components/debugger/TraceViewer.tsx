/**
 * Pipeline trace viewer — horizontal timeline + step cards.
 * Killer Feature #1: RAG Debugger.
 */

import TraceStepCard from './TraceStepCard';
import StrategyBadge from '@/components/shared/StrategyBadge';
import { formatDuration } from '@/lib/utils';
import { STRATEGY_COLORS } from '@/lib/constants';
import type { PipelineTrace, RAGStrategy } from '@/types/api';

interface TraceViewerProps {
  trace: PipelineTrace;
}

export default function TraceViewer({ trace }: TraceViewerProps) {
  const strategyColor =
    STRATEGY_COLORS[trace.strategy as RAGStrategy] ?? '#888';

  return (
    <div className="animate-fade-slide-up">
      {/* Summary bar */}
      <div className="bg-serpent-surface border border-serpent-border-light rounded-[14px] p-5 mb-4">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-[15px] font-semibold font-outfit text-serpent-text mb-1">
              Pipeline Trace
            </h3>
            <p className="text-[12px] text-serpent-text-muted font-dm-sans leading-relaxed max-w-[600px]">
              {trace.query}
            </p>
          </div>
          <StrategyBadge strategy={trace.strategy as RAGStrategy} />
        </div>

        {/* Metrics row */}
        <div className="flex gap-5">
          {[
            { label: 'Total Latency', value: formatDuration(trace.total_latency_ms) },
            { label: 'Steps', value: String(trace.steps.length) },
            { label: 'Chunks', value: String(trace.chunks_retrieved) },
            { label: 'Answer', value: `${trace.answer_length} chars` },
            { label: 'Model', value: trace.model },
          ].map((metric) => (
            <div key={metric.label}>
              <div className="text-[9px] text-serpent-text-dark uppercase tracking-wider font-mono mb-[2px]">
                {metric.label}
              </div>
              <div className="text-[12px] text-serpent-text-tertiary font-mono">
                {metric.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Horizontal timeline overview */}
      <div className="bg-serpent-surface border border-serpent-border-light rounded-[14px] p-5 mb-4">
        <h4 className="text-[10px] text-serpent-text-dark uppercase tracking-[1.5px] font-mono mb-3">
          Timeline
        </h4>
        <div className="flex gap-[2px] h-8 rounded-lg overflow-hidden">
          {trace.steps.map((step, i) => {
            const pct =
              trace.total_latency_ms > 0
                ? (step.duration_ms / trace.total_latency_ms) * 100
                : 100 / trace.steps.length;
            return (
              <div
                key={i}
                className="relative group cursor-pointer transition-opacity hover:opacity-80"
                style={{
                  width: `${Math.max(pct, 2)}%`,
                  background: `linear-gradient(180deg, ${strategyColor}40, ${strategyColor}15)`,
                  borderLeft: i > 0 ? '1px solid #080808' : 'none',
                }}
                title={`${step.name}: ${formatDuration(step.duration_ms)}`}
              >
                {/* Label (only show if wide enough) */}
                {pct > 8 && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-[8px] text-serpent-text-muted font-mono truncate px-1">
                      {step.name.replace(/_/g, ' ')}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
        {/* Step labels below */}
        <div className="flex mt-1.5 gap-[2px]">
          {trace.steps.map((step, i) => {
            const pct =
              trace.total_latency_ms > 0
                ? (step.duration_ms / trace.total_latency_ms) * 100
                : 100 / trace.steps.length;
            return (
              <div
                key={i}
                className="text-[8px] text-serpent-text-darker font-mono text-center truncate"
                style={{ width: `${Math.max(pct, 2)}%` }}
              >
                {formatDuration(step.duration_ms)}
              </div>
            );
          })}
        </div>
      </div>

      {/* Step cards */}
      <div className="flex flex-col gap-2">
        {trace.steps.map((step, i) => (
          <TraceStepCard
            key={i}
            step={step}
            totalLatency={trace.total_latency_ms}
            color={strategyColor}
            index={i}
          />
        ))}
      </div>
    </div>
  );
}
