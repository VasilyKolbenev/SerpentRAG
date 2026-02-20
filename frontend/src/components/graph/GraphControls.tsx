/**
 * Graph Explorer controls — entity search, depth, collection, limit.
 */

import { useState } from 'react';
import type { GraphSettings } from '@/types/ui';

interface GraphControlsProps {
  settings: GraphSettings;
  onSearch: (settings: GraphSettings) => void;
  loading: boolean;
}

export default function GraphControls({
  settings,
  onSearch,
  loading,
}: GraphControlsProps) {
  const [local, setLocal] = useState<GraphSettings>(settings);

  const handleSearch = () => {
    onSearch(local);
  };

  return (
    <div className="bg-serpent-surface border border-serpent-border-light rounded-[14px] p-5 mb-4">
      <div className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-3 items-end">
        {/* Entity search */}
        <div>
          <label className="text-[9px] text-serpent-text-dark uppercase tracking-wider font-mono block mb-1.5">
            Entity
          </label>
          <input
            value={local.entity}
            onChange={(e) => setLocal({ ...local, entity: e.target.value })}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search entities..."
            className="w-full px-3 py-2 text-[12px] bg-serpent-bg border border-serpent-border rounded-lg text-serpent-text-secondary font-dm-sans placeholder:text-serpent-text-dark"
          />
        </div>

        {/* Depth */}
        <div>
          <label className="text-[9px] text-serpent-text-dark uppercase tracking-wider font-mono block mb-1.5">
            Depth
          </label>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={1}
              max={5}
              value={local.depth}
              onChange={(e) =>
                setLocal({ ...local, depth: Number(e.target.value) })
              }
              className="w-20 accent-strategy-graph"
            />
            <span className="text-[11px] text-serpent-text-muted font-mono w-4 text-center">
              {local.depth}
            </span>
          </div>
        </div>

        {/* Collection */}
        <div>
          <label className="text-[9px] text-serpent-text-dark uppercase tracking-wider font-mono block mb-1.5">
            Collection
          </label>
          <input
            value={local.collection}
            onChange={(e) =>
              setLocal({ ...local, collection: e.target.value })
            }
            placeholder="default"
            className="w-28 px-3 py-2 text-[12px] bg-serpent-bg border border-serpent-border rounded-lg text-serpent-text-secondary font-mono placeholder:text-serpent-text-dark"
          />
        </div>

        {/* Limit */}
        <div>
          <label className="text-[9px] text-serpent-text-dark uppercase tracking-wider font-mono block mb-1.5">
            Limit
          </label>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={10}
              max={200}
              step={10}
              value={local.limit}
              onChange={(e) =>
                setLocal({ ...local, limit: Number(e.target.value) })
              }
              className="w-20 accent-strategy-graph"
            />
            <span className="text-[11px] text-serpent-text-muted font-mono w-8 text-center">
              {local.limit}
            </span>
          </div>
        </div>

        {/* Search button */}
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-5 py-2 text-[11px] bg-strategy-graph/10 border border-strategy-graph/25 text-strategy-graph rounded-lg font-medium cursor-pointer font-dm-sans transition-all duration-200 hover:bg-strategy-graph/15 disabled:opacity-40"
        >
          {loading ? 'Loading...' : 'Explore'}
        </button>
      </div>
    </div>
  );
}
