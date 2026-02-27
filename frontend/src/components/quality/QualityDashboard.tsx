/**
 * Quality Dashboard — RAGAS metrics with Recharts bar chart.
 * Killer Feature #4.
 */

import { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import ScoreCard from './ScoreCard';
import { api } from '@/lib/api';
import { STRATEGIES, STRATEGY_COLORS } from '@/lib/constants';
import { formatDuration } from '@/lib/utils';
import type { QualityMetrics, RAGStrategy } from '@/types/api';

const METRIC_DESCRIPTIONS: Record<string, string> = {
  faithfulness: 'How factually accurate are the generated answers',
  context_precision: 'Relevance of retrieved context to the question',
  context_recall: 'Coverage of relevant information in retrieved context',
  answer_relevancy: 'How relevant the answer is to the question',
};

const METRIC_COLORS: Record<string, string> = {
  faithfulness: '#C8F547',
  context_precision: '#8B5CF6',
  context_recall: '#2DD4A8',
  answer_relevancy: '#38BDF8',
};

const PERIODS = ['24h', '7d', '30d'] as const;

export default function QualityDashboard() {
  const [selectedStrategy, setSelectedStrategy] = useState<string>('hybrid');
  const [selectedPeriod, setSelectedPeriod] = useState<string>('7d');
  const [metrics, setMetrics] = useState<QualityMetrics | null>(null);
  const [allMetrics, setAllMetrics] = useState<
    Record<string, QualityMetrics>
  >({});
  const [loading, setLoading] = useState(false);

  // C24: Fetch with isMounted guard to prevent stale state updates
  useEffect(() => {
    let cancelled = false;

    const fetchMetrics = async () => {
      setLoading(true);
      try {
        const data = await api.getQualityMetrics({
          strategy: selectedStrategy,
          period: selectedPeriod,
        });
        if (!cancelled) setMetrics(data);
      } catch {
        if (!cancelled) setMetrics(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchMetrics();
    return () => { cancelled = true; };
  }, [selectedStrategy, selectedPeriod]);

  // Fetch all strategies for comparison chart
  useEffect(() => {
    let cancelled = false;

    const fetchAllMetrics = async () => {
      const results: Record<string, QualityMetrics> = {};
      for (const s of STRATEGIES) {
        if (cancelled) break;
        try {
          const data = await api.getQualityMetrics({
            strategy: s.id,
            period: selectedPeriod,
          });
          results[s.id] = data;
        } catch {
          // Skip unavailable strategies
        }
      }
      if (!cancelled) setAllMetrics(results);
    };

    fetchAllMetrics();
    return () => { cancelled = true; };
  }, [selectedPeriod]);

  // Build chart data
  const chartData = Object.keys(METRIC_COLORS).map((metric) => {
    const row: Record<string, string | number> = { metric: metric.replace(/_/g, ' ') };
    for (const s of STRATEGIES) {
      const m = allMetrics[s.id];
      if (m?.avg_scores) {
        const val = m.avg_scores[metric as keyof typeof m.avg_scores];
        row[s.name] = val ?? 0;
      }
    }
    return row;
  });

  return (
    <div>
      {/* Controls */}
      <div className="flex gap-3 mb-5">
        {/* Strategy filter */}
        <div className="flex gap-1">
          {STRATEGIES.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelectedStrategy(s.id)}
              className="px-3 py-1.5 text-[10px] rounded-lg font-dm-sans cursor-pointer transition-all duration-200"
              style={{
                background:
                  selectedStrategy === s.id ? `${s.color}0a` : '#0e0e0e',
                border: `1px solid ${selectedStrategy === s.id ? `${s.color}30` : '#181818'}`,
                color: selectedStrategy === s.id ? s.color : '#666',
              }}
            >
              {s.icon} {s.name}
            </button>
          ))}
        </div>

        {/* Period filter */}
        <div className="flex gap-1 ml-auto">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setSelectedPeriod(p)}
              className="px-3 py-1.5 text-[10px] rounded-lg font-mono cursor-pointer transition-all duration-200"
              style={{
                background:
                  selectedPeriod === p ? '#151515' : '#0e0e0e',
                border: `1px solid ${selectedPeriod === p ? '#252525' : '#181818'}`,
                color: selectedPeriod === p ? '#ccc' : '#555',
              }}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Score cards */}
      {metrics && (
        <div className="grid grid-cols-4 gap-3 mb-5">
          {Object.entries(METRIC_COLORS).map(([key, color]) => (
            <ScoreCard
              key={key}
              label={key.replace(/_/g, ' ')}
              value={metrics.avg_scores[key as keyof typeof metrics.avg_scores]}
              color={color}
              description={METRIC_DESCRIPTIONS[key]}
            />
          ))}
        </div>
      )}

      {/* Summary stats */}
      {metrics && (
        <div className="flex gap-5 mb-5 px-1">
          <div>
            <span className="text-[9px] text-serpent-text-dark uppercase font-mono">
              Total Queries
            </span>
            <div className="text-[14px] text-serpent-text-secondary font-mono">
              {metrics.total_queries}
            </div>
          </div>
          <div>
            <span className="text-[9px] text-serpent-text-dark uppercase font-mono">
              Avg Latency
            </span>
            <div className="text-[14px] text-serpent-text-secondary font-mono">
              {formatDuration(metrics.avg_latency_ms)}
            </div>
          </div>
        </div>
      )}

      {/* Comparison chart */}
      {chartData.length > 0 && Object.keys(allMetrics).length > 0 && (
        <div className="bg-serpent-surface border border-serpent-border-light rounded-[14px] p-5">
          <h3 className="text-[12px] font-semibold font-outfit text-serpent-text-secondary mb-4">
            Strategy Comparison
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} barCategoryGap="20%">
              <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
              <XAxis
                dataKey="metric"
                tick={{ fill: '#666', fontSize: 10, fontFamily: 'DM Mono' }}
                tickLine={false}
                axisLine={{ stroke: '#1a1a1a' }}
              />
              <YAxis
                domain={[0, 1]}
                tick={{ fill: '#555', fontSize: 10, fontFamily: 'DM Mono' }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: '#0f0f0f',
                  border: '1px solid #252525',
                  borderRadius: '8px',
                  fontSize: '11px',
                  fontFamily: 'DM Sans',
                }}
                itemStyle={{ color: '#b0b0b0' }}
              />
              <Legend
                wrapperStyle={{ fontSize: '10px', fontFamily: 'DM Sans' }}
              />
              {STRATEGIES.filter((s) => allMetrics[s.id]).map((s) => (
                <Bar
                  key={s.id}
                  dataKey={s.name}
                  fill={STRATEGY_COLORS[s.id as RAGStrategy]}
                  radius={[3, 3, 0, 0]}
                  opacity={0.8}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <span className="text-sm text-serpent-text-muted font-dm-sans animate-pulse">
            Loading metrics...
          </span>
        </div>
      )}
    </div>
  );
}
