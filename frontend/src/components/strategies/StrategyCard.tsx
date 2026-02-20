/**
 * Strategy info card — ported from serpent-rag-ui.jsx.
 * Inline styles → Tailwind + dynamic styles for strategy colors.
 */

import { useState } from 'react';
import MetricBar from '@/components/shared/MetricBar';
import { withAlpha, accuracyToValue, latencyToValue } from '@/lib/utils';
import type { StrategyMeta } from '@/types/ui';

interface StrategyCardProps {
  strategy: StrategyMeta;
  selected: boolean;
  onSelect: (id: string) => void;
  index: number;
}

export default function StrategyCard({
  strategy,
  selected,
  onSelect,
  index,
}: StrategyCardProps) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onClick={() => onSelect(strategy.id)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="relative overflow-hidden rounded-[14px] p-[26px] cursor-pointer transition-all duration-[350ms] ease-[cubic-bezier(0.4,0,0.2,1)]"
      style={{
        background: selected ? '#0f0f0f' : hovered ? '#0e0e0e' : '#0b0b0b',
        border: `1px solid ${
          selected
            ? withAlpha(strategy.color, 0.21)
            : hovered
              ? '#252525'
              : '#181818'
        }`,
        transform: hovered && !selected ? 'translateY(-3px)' : 'none',
        animation: `fadeSlideUp 0.5s ease-out ${index * 0.1}s both`,
        boxShadow: selected
          ? `0 0 30px ${withAlpha(strategy.color, 0.03)}`
          : 'none',
      }}
    >
      {/* Active top accent */}
      {selected && (
        <div
          className="absolute top-0 left-0 right-0 h-[2px]"
          style={{
            background: `linear-gradient(90deg, transparent, ${withAlpha(strategy.color, 0.5)}, transparent)`,
          }}
        />
      )}

      {/* Header row */}
      <div className="flex justify-between items-start mb-[14px]">
        <div className="flex items-center gap-2.5">
          <span className="text-2xl">{strategy.icon}</span>
          <span className="text-[17px] font-semibold text-serpent-text font-outfit tracking-tight">
            {strategy.name}
          </span>
        </div>
        {/* Radio indicator */}
        <div
          className="w-[18px] h-[18px] rounded-full flex items-center justify-center shrink-0 transition-all duration-300"
          style={{
            border: `2px solid ${selected ? strategy.color : '#2a2a2a'}`,
            background: selected ? strategy.color : 'transparent',
          }}
        >
          {selected && (
            <span className="text-[10px] font-extrabold text-[#0a0a0a]">
              \u2713
            </span>
          )}
        </div>
      </div>

      {/* Description */}
      <p className="text-[12.5px] text-serpent-text-muted leading-[1.65] mb-4 font-dm-sans">
        {strategy.desc}
      </p>

      {/* Tags */}
      <div className="flex flex-wrap gap-[5px] mb-4">
        {strategy.tags.map((tag) => (
          <span
            key={tag}
            className="text-[10px] px-2 py-[3px] rounded font-medium font-mono"
            style={{
              background: withAlpha(strategy.color, 0.04),
              color: withAlpha(strategy.color, 0.8),
              border: `1px solid ${withAlpha(strategy.color, 0.08)}`,
            }}
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Metric bars */}
      <MetricBar
        label="Complex"
        value={strategy.complexity}
        color={strategy.color}
      />
      <MetricBar
        label="Accuracy"
        value={accuracyToValue(strategy.accuracy)}
        color={strategy.color}
      />
      <MetricBar
        label="Speed"
        value={latencyToValue(strategy.latency)}
        color={strategy.color}
      />
    </div>
  );
}
