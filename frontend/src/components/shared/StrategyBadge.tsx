/**
 * Small colored badge showing strategy dot + name.
 */

import { STRATEGY_MAP } from '@/lib/constants';
import type { RAGStrategy } from '@/types/api';

interface StrategyBadgeProps {
  strategy: RAGStrategy;
  className?: string;
}

export default function StrategyBadge({ strategy, className = '' }: StrategyBadgeProps) {
  const meta = STRATEGY_MAP[strategy];
  if (!meta) return null;

  return (
    <span className={`inline-flex items-center gap-[5px] text-[10px] font-mono ${className}`}>
      <span
        className="inline-block w-[5px] h-[5px] rounded-full"
        style={{ background: meta.color }}
      />
      <span style={{ color: meta.color }}>{meta.name}</span>
    </span>
  );
}
