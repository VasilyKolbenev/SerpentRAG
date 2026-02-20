/**
 * Strategy Advisor — 4-step wizard.
 * Ported from JSX but calls POST /recommend instead of local scoring.
 * Falls back to local scoring if API is unavailable.
 */

import { useState } from 'react';
import { ADVISOR_QUESTIONS, STRATEGIES, STRATEGY_MAP } from '@/lib/constants';
import { withAlpha } from '@/lib/utils';
import { api } from '@/lib/api';
import type { RAGStrategy } from '@/types/api';
import type { AdvisorResult } from '@/types/ui';

interface AdvisorPanelProps {
  onComplete: (strategyId: RAGStrategy) => void;
}

export default function AdvisorPanel({ onComplete }: AdvisorPanelProps) {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<AdvisorResult[] | null>(null);
  const [loading, setLoading] = useState(false);

  const handleAnswer = async (questionId: string, answer: string) => {
    const newAnswers = { ...answers, [questionId]: answer };
    setAnswers(newAnswers);

    if (step < ADVISOR_QUESTIONS.length - 1) {
      setTimeout(() => setStep(step + 1), 300);
    } else {
      setLoading(true);
      try {
        const res = await api.recommend({
          domain: newAnswers.domain ?? '',
          query_complexity: newAnswers.complexity ?? '',
          data_structure: newAnswers.data ?? '',
          priority: newAnswers.priority ?? '',
        });

        const sorted = Object.entries(res.scores)
          .sort((a, b) => b[1] - a[1]);
        const maxScore = sorted[0]?.[1] ?? 1;

        setResult(
          sorted.map(([id, score]) => ({
            strategy: STRATEGY_MAP[id as RAGStrategy] ?? STRATEGIES[0],
            score,
            percentage: Math.round((score / Math.max(maxScore, 1)) * 100),
          })),
        );
      } catch {
        // Fallback to local scoring
        setResult(getLocalRecommendation(newAnswers));
      } finally {
        setLoading(false);
      }
    }
  };

  const reset = () => {
    setStep(0);
    setAnswers({});
    setResult(null);
  };

  // ── Result view ──
  if (result) {
    return (
      <div className="animate-fade-slide-up">
        <h3 className="text-[16px] text-serpent-text-secondary mb-5 font-outfit flex items-center gap-2">
          <span className="text-[18px]">{'\uD83D\uDC0D'}</span> Serpent's Recommendation
        </h3>

        {result.map((r, i) => (
          <div
            key={r.strategy.id}
            className="flex items-center gap-[14px] px-4 py-3 mb-[6px] rounded-[10px]"
            style={{
              background: i === 0 ? withAlpha(r.strategy.color, 0.03) : '#0b0b0b',
              border: `1px solid ${i === 0 ? withAlpha(r.strategy.color, 0.15) : '#151515'}`,
              animation: `fadeSlideUp 0.4s ease-out ${i * 0.1}s both`,
            }}
          >
            <span className="text-[20px]">{r.strategy.icon}</span>
            <div className="flex-1">
              <div className="text-[13px] font-semibold text-serpent-text-secondary font-outfit">
                {r.strategy.name}
              </div>
              {i === 0 && (
                <div className="text-[10px] text-serpent-text-dim font-dm-sans">
                  Best match for your needs
                </div>
              )}
            </div>
            <div className="w-[90px] h-1 bg-[#1a1a1a] rounded-sm overflow-hidden">
              <div
                className="h-full rounded-sm transition-[width] duration-1000 ease-[cubic-bezier(0.4,0,0.2,1)]"
                style={{
                  width: `${r.percentage}%`,
                  background: `linear-gradient(90deg, ${withAlpha(r.strategy.color, 0.38)}, ${r.strategy.color})`,
                }}
              />
            </div>
            <span
              className="text-xs font-semibold w-9 text-right font-mono"
              style={{ color: r.strategy.color }}
            >
              {r.percentage}%
            </span>
          </div>
        ))}

        <button
          onClick={() => onComplete(result[0].strategy.id)}
          className="mt-[14px] w-full py-[11px] border-none rounded-lg text-xs font-semibold cursor-pointer font-outfit transition-opacity duration-200 hover:opacity-85 text-[#0a0a0a]"
          style={{
            background: `linear-gradient(135deg, ${result[0].strategy.color}, ${withAlpha(result[0].strategy.color, 0.8)})`,
          }}
        >
          Use {result[0].strategy.name} \u2192
        </button>

        <button
          onClick={reset}
          className="mt-[6px] w-full py-[9px] bg-transparent text-serpent-text-dim border border-[#1a1a1a] rounded-lg text-[11px] cursor-pointer font-dm-sans hover:border-serpent-border"
        >
          Start Over
        </button>
      </div>
    );
  }

  // ── Loading ──
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-sm text-serpent-text-muted font-dm-sans animate-pulse">
          Analyzing your needs...
        </div>
      </div>
    );
  }

  // ── Question view ──
  const q = ADVISOR_QUESTIONS[step];

  return (
    <div className="animate-fade-slide-up">
      {/* Progress bar */}
      <div className="flex gap-[3px] mb-[18px]">
        {ADVISOR_QUESTIONS.map((_, i) => (
          <div
            key={i}
            className="flex-1 h-[2px] rounded-[1px] transition-all duration-300"
            style={{
              background:
                i <= step
                  ? 'linear-gradient(90deg, #C8F547, #2DD4A8)'
                  : '#1a1a1a',
            }}
          />
        ))}
      </div>

      <p className="text-[10px] text-serpent-text-dark mb-[6px] font-mono">
        Step {step + 1}/{ADVISOR_QUESTIONS.length}
      </p>

      <h3 className="text-[15px] text-serpent-text-secondary mb-[14px] font-outfit">
        {q.question}
      </h3>

      <div className="flex flex-col gap-[5px]">
        {q.options.map((opt) => (
          <button
            key={opt}
            onClick={() => handleAnswer(q.id, opt)}
            className="px-[13px] py-[9px] rounded-[7px] text-serpent-text-tertiary text-[12.5px] cursor-pointer text-left font-dm-sans transition-all duration-200 hover:border-serpent-border-hover hover:bg-[#111]"
            style={{
              background: answers[q.id] === opt ? '#C8F54708' : '#0e0e0e',
              border: `1px solid ${
                answers[q.id] === opt ? '#C8F54730' : '#181818'
              }`,
            }}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Local fallback scoring (from original JSX) ──

function getLocalRecommendation(
  answers: Record<string, string>,
): AdvisorResult[] {
  const scores: Record<string, number> = {
    agentic: 0,
    graph: 0,
    hybrid: 0,
    naive: 0,
  };

  if (
    answers.complexity === 'Multi-step reasoning needed' ||
    answers.complexity === 'Complex analytical workflows'
  ) {
    scores.agentic += 3;
    scores.graph += 1;
  }
  if (answers.complexity === 'Requires connecting multiple sources') {
    scores.agentic += 2;
    scores.graph += 2;
  }
  if (answers.complexity === 'Simple factual lookups') {
    scores.naive += 3;
    scores.hybrid += 1;
  }
  if (answers.data === 'Structured with entity relationships') scores.graph += 3;
  if (answers.data === 'Flat documents (PDFs, text)') {
    scores.hybrid += 2;
    scores.naive += 1;
  }
  if (answers.data === 'Mixed structured & unstructured') {
    scores.hybrid += 2;
    scores.agentic += 1;
  }
  if (
    answers.domain === 'Legal / Compliance' ||
    answers.domain === 'Medical / Healthcare'
  ) {
    scores.graph += 2;
    scores.agentic += 1;
  }
  if (answers.domain === 'Customer Support') {
    scores.hybrid += 2;
    scores.naive += 1;
  }
  if (answers.domain === 'Research / Academic') scores.agentic += 2;
  if (answers.priority === 'Speed / Low latency') {
    scores.naive += 2;
    scores.hybrid += 1;
  }
  if (answers.priority === 'Maximum accuracy') {
    scores.agentic += 2;
    scores.graph += 1;
  }
  if (answers.priority === 'Cost efficiency') scores.naive += 2;
  if (answers.priority === 'Explainability / Transparency') {
    scores.graph += 2;
    scores.agentic += 1;
  }

  const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  const maxScore = sorted[0]?.[1] ?? 1;

  return sorted.map(([id, score]) => ({
    strategy: STRATEGY_MAP[id as RAGStrategy] ?? STRATEGIES[0],
    score,
    percentage: Math.round((score / Math.max(maxScore, 1)) * 100),
  }));
}
