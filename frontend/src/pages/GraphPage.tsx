/**
 * Knowledge Graph Explorer page.
 * Killer Feature #3.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import GraphExplorer from '@/components/graph/GraphExplorer';
import GraphControls from '@/components/graph/GraphControls';
import { api } from '@/lib/api';
import type { GraphData, GraphNode } from '@/types/api';
import type { GraphSettings } from '@/types/ui';

const INITIAL_SETTINGS: GraphSettings = {
  entity: '',
  depth: 2,
  collection: 'default',
  limit: 50,
};

export default function GraphPage() {
  const [settings, setSettings] = useState<GraphSettings>(INITIAL_SETTINGS);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState<number>(0);

  // Track container width for graph sizing
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });

    observer.observe(el);
    setContainerWidth(el.clientWidth);

    return () => observer.disconnect();
  }, []);

  const handleSearch = useCallback(async (newSettings: GraphSettings) => {
    setSettings(newSettings);
    setLoading(true);
    setError(null);

    try {
      const data = await api.getGraph({
        collection: newSettings.collection || undefined,
        entity: newSettings.entity || undefined,
        depth: newSettings.depth,
        limit: newSettings.limit,
      });
      setGraphData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load graph');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleNodeClick = useCallback(
    (node: GraphNode) => {
      // Re-fetch graph centered on clicked node
      handleSearch({
        ...settings,
        entity: node.label,
      });
    },
    [settings, handleSearch],
  );

  // Initial load
  useEffect(() => {
    handleSearch(INITIAL_SETTINGS);
  }, [handleSearch]);

  const graphHeight = Math.max(400, window.innerHeight - 320);

  return (
    <div className="animate-fade-slide-up" ref={containerRef}>
      <div className="mb-6">
        <h1 className="text-[26px] font-semibold tracking-tight font-outfit mb-[5px]">
          Knowledge Graph
        </h1>
        <p className="text-[13px] text-serpent-text-muted font-dm-sans">
          Explore entity relationships in your knowledge base
        </p>
      </div>

      <GraphControls
        settings={settings}
        onSearch={handleSearch}
        loading={loading}
      />

      {/* Error */}
      {error && (
        <div className="bg-red-500/5 border border-red-500/20 rounded-[14px] p-4 mb-4">
          <p className="text-[12px] text-red-400 font-dm-sans">{error}</p>
        </div>
      )}

      {/* Graph */}
      {graphData && !loading && (
        <div>
          <GraphExplorer
            data={graphData}
            onNodeClick={handleNodeClick}
            width={containerWidth || undefined}
            height={graphHeight}
          />
          {/* Stats */}
          <div className="flex gap-4 mt-3">
            <span className="text-[10px] text-serpent-text-dim font-mono">
              {graphData.nodes.length} nodes
            </span>
            <span className="text-[10px] text-serpent-text-dim font-mono">
              {graphData.edges.length} edges
            </span>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="rounded-[14px] border border-serpent-border-light bg-[#060606] flex items-center justify-center"
          style={{ height: graphHeight }}
        >
          <span className="text-sm text-serpent-text-muted font-dm-sans animate-pulse">
            Loading graph...
          </span>
        </div>
      )}

      {/* Empty state */}
      {!graphData && !loading && !error && (
        <div className="rounded-[14px] border border-serpent-border-light bg-[#060606] flex items-center justify-center flex-col gap-3"
          style={{ height: graphHeight }}
        >
          <span className="text-3xl opacity-30">{'\uD83D\uDD78\uFE0F'}</span>
          <span className="text-sm text-serpent-text-dim font-dm-sans">
            No graph data available. Upload documents first.
          </span>
        </div>
      )}
    </div>
  );
}
