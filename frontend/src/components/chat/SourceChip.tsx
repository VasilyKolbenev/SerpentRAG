/**
 * Clickable source citation chip [1].
 */

import { withAlpha } from '@/lib/utils';

interface SourceChipProps {
  filename: string;
  score?: number;
  index: number;
}

export default function SourceChip({ filename, score, index }: SourceChipProps) {
  return (
    <span
      className="inline-flex items-center gap-1 text-[9px] px-[5px] py-[2px] rounded-[3px] font-mono cursor-default"
      style={{
        background: withAlpha('#8B5CF6', 0.03),
        color: withAlpha('#8B5CF6', 0.67),
        border: `1px solid ${withAlpha('#8B5CF6', 0.08)}`,
      }}
      title={score !== undefined ? `Score: ${score.toFixed(3)}` : undefined}
    >
      <span className="opacity-60">[{index + 1}]</span> {filename}
    </span>
  );
}
