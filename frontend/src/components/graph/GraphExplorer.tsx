/**
 * Interactive knowledge graph explorer using react-force-graph-2d.
 * Killer Feature #3.
 */

import { useRef, useCallback, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { GraphData, GraphNode } from '@/types/api';

// Node type → color mapping
const NODE_TYPE_COLORS: Record<string, string> = {
  Person: '#C8F547',
  Organization: '#8B5CF6',
  Concept: '#2DD4A8',
  Location: '#38BDF8',
  Event: '#F472B6',
  Document: '#FB923C',
  Technology: '#60A5FA',
};

const DEFAULT_NODE_COLOR = '#666';

interface GraphExplorerProps {
  data: GraphData;
  onNodeClick?: (node: GraphNode) => void;
  width?: number;
  height?: number;
}

interface ForceNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
  x?: number;
  y?: number;
}

interface ForceLink {
  source: string | ForceNode;
  target: string | ForceNode;
  type: string;
  weight: number;
}

export default function GraphExplorer({
  data,
  onNodeClick,
  width,
  height = 500,
}: GraphExplorerProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null);

  // Transform edges → links (react-force-graph expects source/target)
  const graphData = useMemo(() => {
    const nodes: ForceNode[] = data.nodes.map((n) => ({
      id: n.id,
      label: n.label,
      type: n.type,
      properties: n.properties,
    }));

    const links: ForceLink[] = data.edges.map((e) => ({
      source: e.source,
      target: e.target,
      type: e.type,
      weight: e.weight,
    }));

    return { nodes, links };
  }, [data]);

  const handleNodeClick = useCallback(
    (node: ForceNode) => {
      if (onNodeClick) {
        onNodeClick({
          id: node.id,
          label: node.label,
          type: node.type,
          properties: node.properties,
        });
      }
    },
    [onNodeClick],
  );

  const nodeCanvasObject = useCallback(
    (node: ForceNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.label;
      const color = NODE_TYPE_COLORS[node.type] ?? DEFAULT_NODE_COLOR;
      const fontSize = 11 / globalScale;
      const radius = 5;

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x ?? 0, node.y ?? 0, radius, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      // Glow effect
      ctx.beginPath();
      ctx.arc(node.x ?? 0, node.y ?? 0, radius + 2, 0, 2 * Math.PI);
      ctx.fillStyle = `${color}15`;
      ctx.fill();

      // Label
      if (globalScale > 0.6) {
        ctx.font = `${fontSize}px "DM Sans", sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillStyle = '#b0b0b0';
        ctx.fillText(label, node.x ?? 0, (node.y ?? 0) + radius + 3);
      }
    },
    [],
  );

  const linkCanvasObject = useCallback(
    (link: ForceLink, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const source = link.source as ForceNode;
      const target = link.target as ForceNode;
      if (!source.x || !source.y || !target.x || !target.y) return;

      // Draw line
      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);
      ctx.strokeStyle = '#252525';
      ctx.lineWidth = 0.5;
      ctx.stroke();

      // Draw label at midpoint
      if (globalScale > 1.2 && link.type) {
        const mx = (source.x + target.x) / 2;
        const my = (source.y + target.y) / 2;
        const fontSize = 8 / globalScale;

        ctx.font = `${fontSize}px "DM Mono", monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#444';
        ctx.fillText(link.type, mx, my);
      }
    },
    [],
  );

  return (
    <div className="rounded-[14px] overflow-hidden border border-serpent-border-light bg-[#060606]">
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        width={width}
        height={height}
        backgroundColor="#060606"
        nodeCanvasObject={nodeCanvasObject}
        linkCanvasObject={linkCanvasObject}
        onNodeClick={handleNodeClick}
        nodePointerAreaPaint={(node: ForceNode, color: string, ctx: CanvasRenderingContext2D) => {
          ctx.beginPath();
          ctx.arc(node.x ?? 0, node.y ?? 0, 8, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={0.8}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        warmupTicks={50}
        cooldownTicks={200}
      />

      {/* Legend */}
      <div className="flex gap-3 px-4 py-2.5 border-t border-[#141414] bg-[#080808]">
        {Object.entries(NODE_TYPE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div
              className="w-2 h-2 rounded-full"
              style={{ background: color }}
            />
            <span className="text-[9px] text-serpent-text-dim font-mono">
              {type}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
