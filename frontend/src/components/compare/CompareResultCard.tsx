/**
 * Single strategy result panel for A/B comparison.
 */

import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import SourceChip from '@/components/chat/SourceChip';
import { STRATEGY_MAP } from '@/lib/constants';
import { withAlpha, formatDuration } from '@/lib/utils';
import type { CompareResult, RAGStrategy } from '@/types/api';

interface CompareResultCardProps {
  result: CompareResult;
  index: number;
}

export default function CompareResultCard({
  result,
  index,
}: CompareResultCardProps) {
  const navigate = useNavigate();
  const meta = STRATEGY_MAP[result.strategy];
  const color = meta?.color ?? '#888';

  return (
    <div
      className="rounded-[14px] overflow-hidden flex flex-col"
      style={{
        background: '#0b0b0b',
        border: `1px solid ${withAlpha(color, 0.15)}`,
        animation: `fadeSlideUp 0.4s ease-out ${index * 0.1}s both`,
      }}
    >
      {/* Color accent top */}
      <div
        className="h-[2px]"
        style={{
          background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
        }}
      />

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#151515]">
        <div className="flex items-center gap-2">
          <span className="text-lg">{meta?.icon}</span>
          <span
            className="text-[13px] font-semibold font-outfit"
            style={{ color }}
          >
            {meta?.name}
          </span>
        </div>
        <span className="text-[10px] font-mono text-serpent-text-dim">
          {formatDuration(result.latency_ms)}
        </span>
      </div>

      {/* Answer */}
      <div className="flex-1 p-4 overflow-y-auto">
        {/* Sources */}
        {result.sources.length > 0 && (
          <div className="flex gap-1 mb-3 flex-wrap">
            {result.sources.map((s, i) => (
              <SourceChip
                key={i}
                filename={
                  (s.metadata?.filename as string) ??
                  (s.metadata?.source as string) ??
                  `source-${i + 1}`
                }
                score={s.score}
                index={i}
              />
            ))}
          </div>
        )}

        <div className="text-[12px] text-serpent-text-tertiary leading-[1.65] font-dm-sans prose prose-invert prose-sm max-w-none [&_pre]:bg-[#060606] [&_pre]:border [&_pre]:border-[#131313] [&_pre]:rounded-lg [&_pre]:p-3 [&_pre]:font-mono [&_pre]:text-[10px] [&_code]:font-mono [&_code]:text-[10px] [&_code]:bg-[#111] [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded">
          <ReactMarkdown>{result.answer}</ReactMarkdown>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-2.5 border-t border-[#151515]">
        {result.quality_scores && (
          <div className="flex gap-3">
            {Object.entries(result.quality_scores).map(([key, val]) => (
              <div key={key} className="text-center">
                <div className="text-[8px] text-serpent-text-dark uppercase font-mono">
                  {key.replace(/_/g, ' ')}
                </div>
                <div
                  className="text-[11px] font-mono font-semibold"
                  style={{ color }}
                >
                  {(val as number).toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        )}
        <button
          onClick={() => navigate(`/debugger/${result.trace_id}`)}
          className="text-[10px] font-mono cursor-pointer bg-transparent border-none p-0 transition-colors"
          style={{ color: withAlpha(color, 0.6) }}
          onMouseEnter={(e) => (e.currentTarget.style.color = color)}
          onMouseLeave={(e) =>
            (e.currentTarget.style.color = withAlpha(color, 0.6))
          }
        >
          Trace {'\u2192'}
        </button>
      </div>
    </div>
  );
}
