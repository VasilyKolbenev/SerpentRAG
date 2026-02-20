/**
 * Strategies page — strategy grid + advisor wizard + pipeline architecture.
 */

import { useState } from 'react';
import StrategyCard from '@/components/strategies/StrategyCard';
import AdvisorPanel from '@/components/strategies/AdvisorPanel';
import { STRATEGIES } from '@/lib/constants';
import { useAppStore } from '@/stores/appStore';
import type { RAGStrategy } from '@/types/api';

const PIPELINE_STEPS = [
  { label: 'Ingest', desc: 'PDF \u00B7 DOCX \u00B7 CSV \u00B7 API', icon: '\uD83D\uDCE5', color: '#38BDF8' },
  { label: 'Process', desc: 'Chunk \u00B7 Embed \u00B7 Extract', icon: '\u2699\uFE0F', color: '#C8F547' },
  { label: 'Index', desc: 'Vector + Graph + BM25', icon: '\uD83D\uDDC4\uFE0F', color: '#8B5CF6' },
  { label: 'Retrieve', desc: 'Strategy-based RAG', icon: '\uD83D\uDD0D', color: '#2DD4A8' },
  { label: 'Generate', desc: 'LLM + Citations', icon: '\uD83D\uDCAC', color: '#F472B6' },
];

export default function StrategiesPage() {
  const selectedStrategy = useAppStore((s) => s.selectedStrategy);
  const setSelectedStrategy = useAppStore((s) => s.setSelectedStrategy);
  const [showAdvisor, setShowAdvisor] = useState(false);

  return (
    <div className="animate-fade-slide-up">
      {/* Title + Advisor toggle */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-[26px] font-semibold tracking-tight font-outfit mb-[5px]">
            Choose Your Strategy
          </h1>
          <p className="text-[13px] text-serpent-text-muted font-dm-sans">
            Select the retrieval approach that best fits your domain
          </p>
        </div>
        <button
          onClick={() => setShowAdvisor(!showAdvisor)}
          className="px-[18px] py-2 text-[11px] rounded-lg cursor-pointer font-medium font-dm-sans transition-all duration-200"
          style={{
            background: showAdvisor ? '#C8F54708' : '#0e0e0e',
            border: `1px solid ${showAdvisor ? '#C8F54730' : '#1e1e1e'}`,
            color: showAdvisor ? '#C8F547' : '#777',
          }}
        >
          {'\uD83D\uDC0D'} Strategy Advisor
        </button>
      </div>

      {/* Advisor panel */}
      {showAdvisor && (
        <div className="bg-serpent-surface border border-serpent-border-light rounded-[14px] p-6 mb-5 animate-fade-slide-up">
          <AdvisorPanel
            onComplete={(id: RAGStrategy) => {
              setSelectedStrategy(id);
              setShowAdvisor(false);
            }}
          />
        </div>
      )}

      {/* Strategy grid */}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(290px,1fr))] gap-3">
        {STRATEGIES.map((s, i) => (
          <StrategyCard
            key={s.id}
            strategy={s}
            selected={selectedStrategy === s.id}
            onSelect={(id) => setSelectedStrategy(id as RAGStrategy)}
            index={i}
          />
        ))}
      </div>

      {/* Pipeline architecture */}
      <div className="mt-7 p-6 bg-serpent-surface border border-serpent-border-light rounded-[14px]">
        <h3 className="text-[14px] font-semibold mb-[18px] font-outfit tracking-tight text-serpent-text-secondary">
          {'\uD83D\uDC0D'} Serpent Pipeline Architecture
        </h3>
        <div className="grid grid-cols-5 gap-[6px] text-center">
          {PIPELINE_STEPS.map((step, i) => (
            <div
              key={step.label}
              className="relative py-[18px] px-2.5 bg-serpent-bg border border-[#141414] rounded-[10px]"
            >
              <div className="text-[22px] mb-[6px]">{step.icon}</div>
              <div
                className="text-[11px] font-semibold mb-[3px] font-mono"
                style={{ color: step.color }}
              >
                {step.label}
              </div>
              <div className="text-[9.5px] text-serpent-text-dark font-dm-sans">
                {step.desc}
              </div>
              {i < PIPELINE_STEPS.length - 1 && (
                <div className="absolute -right-[10px] top-1/2 -translate-y-1/2 text-[#252525] text-xs z-[1]">
                  {'\u2192'}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
