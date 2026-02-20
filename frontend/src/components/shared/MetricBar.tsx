/**
 * Progress bar for strategy metrics — ported from JSX.
 */

interface MetricBarProps {
  label: string;
  value: number;
  max?: number;
  color: string;
}

export default function MetricBar({ label, value, max = 5, color }: MetricBarProps) {
  const pct = (value / max) * 100;

  return (
    <div className="flex items-center gap-2.5 mb-[6px]">
      <span className="text-[11px] text-serpent-text-dim w-[70px] shrink-0 font-mono">
        {label}
      </span>
      <div className="flex-1 h-[3px] bg-serpent-border rounded-sm overflow-hidden">
        <div
          className="h-full rounded-sm transition-[width] duration-700 ease-[cubic-bezier(0.4,0,0.2,1)]"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${color}40, ${color})`,
          }}
        />
      </div>
    </div>
  );
}
