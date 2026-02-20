/**
 * A/B Compare — query input + strategy checkboxes + results grid.
 * Killer Feature #2.
 */

import { useState, useCallback } from 'react';
import CompareResultCard from './CompareResultCard';
import { api } from '@/lib/api';
import { STRATEGIES, DEFAULT_QUERY_PARAMS } from '@/lib/constants';
import { withAlpha } from '@/lib/utils';
import type { RAGStrategy, CompareResult } from '@/types/api';

export default function CompareView() {
  const [query, setQuery] = useState('');
  const [selectedStrategies, setSelectedStrategies] = useState<RAGStrategy[]>([
    'hybrid',
    'naive',
  ]);
  const [results, setResults] = useState<CompareResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleStrategy = useCallback((id: RAGStrategy) => {
    setSelectedStrategies((prev) => {
      if (prev.includes(id)) {
        if (prev.length <= 2) return prev; // Min 2
        return prev.filter((s) => s !== id);
      }
      if (prev.length >= 4) return prev; // Max 4
      return [...prev, id];
    });
  }, []);

  const handleCompare = useCallback(async () => {
    const trimmed = query.trim();
    if (!trimmed || selectedStrategies.length < 2) return;

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const res = await api.compare({
        query: trimmed,
        strategies: selectedStrategies,
        ...DEFAULT_QUERY_PARAMS,
      });
      setResults(res.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Comparison failed');
    } finally {
      setLoading(false);
    }
  }, [query, selectedStrategies]);

  return (
    <div>
      {/* Input section */}
      <div className="bg-serpent-surface border border-serpent-border-light rounded-[14px] p-5 mb-5">
        {/* Strategy checkboxes */}
        <div className="flex gap-2 mb-4">
          {STRATEGIES.map((s) => {
            const isSelected = selectedStrategies.includes(s.id);
            return (
              <button
                key={s.id}
                onClick={() => toggleStrategy(s.id)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-[11px] font-dm-sans cursor-pointer transition-all duration-200"
                style={{
                  background: isSelected
                    ? withAlpha(s.color, 0.05)
                    : '#0e0e0e',
                  border: `1px solid ${
                    isSelected ? withAlpha(s.color, 0.25) : '#181818'
                  }`,
                  color: isSelected ? s.color : '#666',
                }}
              >
                {/* Checkbox */}
                <div
                  className="w-3.5 h-3.5 rounded-[3px] flex items-center justify-center transition-all duration-200"
                  style={{
                    border: `1.5px solid ${isSelected ? s.color : '#333'}`,
                    background: isSelected ? s.color : 'transparent',
                  }}
                >
                  {isSelected && (
                    <span className="text-[8px] font-bold text-[#0a0a0a]">
                      {'\u2713'}
                    </span>
                  )}
                </div>
                <span>{s.icon}</span>
                <span className="font-medium">{s.name}</span>
              </button>
            );
          })}
        </div>

        {/* Query input + compare button */}
        <div className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCompare()}
            placeholder="Enter a query to compare strategies..."
            className="flex-1 px-3.5 py-2.5 text-[12.5px] bg-serpent-bg border border-serpent-border rounded-lg text-serpent-text-secondary font-dm-sans placeholder:text-serpent-text-dark"
          />
          <button
            onClick={handleCompare}
            disabled={
              !query.trim() || selectedStrategies.length < 2 || loading
            }
            className="px-6 py-2.5 text-[11px] bg-gradient-to-br from-strategy-agentic to-strategy-hybrid text-[#0a0a0a] border-none rounded-lg font-semibold cursor-pointer font-outfit transition-opacity duration-200 hover:opacity-85 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? 'Comparing...' : 'Compare'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/5 border border-red-500/20 rounded-[14px] p-4 mb-5">
          <p className="text-[12px] text-red-400 font-dm-sans">{error}</p>
        </div>
      )}

      {/* Loading skeletons */}
      {loading && (
        <div
          className="grid gap-3"
          style={{
            gridTemplateColumns: `repeat(${selectedStrategies.length}, 1fr)`,
          }}
        >
          {selectedStrategies.map((stratId) => {
            const meta = STRATEGIES.find((s) => s.id === stratId);
            return (
              <div
                key={stratId}
                className="rounded-[14px] h-[300px] animate-pulse"
                style={{
                  background: '#0b0b0b',
                  border: `1px solid ${withAlpha(meta?.color ?? '#888', 0.1)}`,
                }}
              >
                <div
                  className="h-[2px]"
                  style={{
                    background: `linear-gradient(90deg, transparent, ${meta?.color ?? '#888'}40, transparent)`,
                  }}
                />
              </div>
            );
          })}
        </div>
      )}

      {/* Results grid */}
      {results && !loading && (
        <div
          className="grid gap-3"
          style={{
            gridTemplateColumns: `repeat(${results.length}, 1fr)`,
          }}
        >
          {results.map((r, i) => (
            <CompareResultCard key={r.strategy} result={r} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
