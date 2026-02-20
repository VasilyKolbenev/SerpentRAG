/**
 * Quality Dashboard page — RAGAS metrics.
 * Killer Feature #4.
 */

import QualityDashboard from '@/components/quality/QualityDashboard';

export default function QualityPage() {
  return (
    <div className="animate-fade-slide-up">
      <div className="mb-6">
        <h1 className="text-[26px] font-semibold tracking-tight font-outfit mb-[5px]">
          Quality Dashboard
        </h1>
        <p className="text-[13px] text-serpent-text-muted font-dm-sans">
          RAGAS evaluation metrics across strategies
        </p>
      </div>
      <QualityDashboard />
    </div>
  );
}
