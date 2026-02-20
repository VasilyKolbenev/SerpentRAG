/**
 * Streaming phase indicator (retrieving / generating / planning / reflecting).
 */

import type { StreamPhase } from '@/types/ui';

interface StreamingIndicatorProps {
  phase: StreamPhase;
}

const PHASE_LABELS: Record<string, string> = {
  retrieving: 'Retrieving context...',
  generating: 'Generating response...',
  planning: 'Planning approach...',
  reflecting: 'Reflecting on results...',
};

export default function StreamingIndicator({ phase }: StreamingIndicatorProps) {
  const label = PHASE_LABELS[phase];
  if (!label) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-1.5">
      <div className="flex gap-1">
        <span className="w-1 h-1 rounded-full bg-strategy-agentic animate-pulse" />
        <span
          className="w-1 h-1 rounded-full bg-strategy-hybrid animate-pulse"
          style={{ animationDelay: '0.2s' }}
        />
        <span
          className="w-1 h-1 rounded-full bg-strategy-graph animate-pulse"
          style={{ animationDelay: '0.4s' }}
        />
      </div>
      <span className="text-[11px] text-serpent-text-muted font-mono">
        {label}
      </span>
    </div>
  );
}
