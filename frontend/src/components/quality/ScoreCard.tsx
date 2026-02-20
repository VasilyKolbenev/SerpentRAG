/**
 * Single RAGAS metric display card.
 */

import { withAlpha } from '@/lib/utils';

interface ScoreCardProps {
  label: string;
  value: number | null;
  color: string;
  description?: string;
}

export default function ScoreCard({
  label,
  value,
  color,
  description,
}: ScoreCardProps) {
  const displayValue = value !== null ? value.toFixed(2) : 'N/A';
  const pct = value !== null ? value * 100 : 0;

  return (
    <div
      className="rounded-[14px] p-5 transition-all duration-300 hover:border-serpent-border-hover"
      style={{
        background: '#0b0b0b',
        border: `1px solid ${value !== null ? withAlpha(color, 0.12) : '#181818'}`,
      }}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="text-[11px] text-serpent-text-muted font-dm-sans font-medium mb-[2px]">
            {label}
          </h4>
          {description && (
            <p className="text-[9px] text-serpent-text-dark font-dm-sans">
              {description}
            </p>
          )}
        </div>
        <span
          className="text-[22px] font-semibold font-mono"
          style={{ color: value !== null ? color : '#444' }}
        >
          {displayValue}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-[4px] bg-[#1a1a1a] rounded-sm overflow-hidden">
        <div
          className="h-full rounded-sm transition-[width] duration-1000 ease-[cubic-bezier(0.4,0,0.2,1)]"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${withAlpha(color, 0.4)}, ${color})`,
          }}
        />
      </div>
    </div>
  );
}
