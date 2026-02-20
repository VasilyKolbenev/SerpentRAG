/**
 * A/B Compare page.
 * Killer Feature #2.
 */

import CompareView from '@/components/compare/CompareView';

export default function ComparePage() {
  return (
    <div className="animate-fade-slide-up">
      <div className="mb-6">
        <h1 className="text-[26px] font-semibold tracking-tight font-outfit mb-[5px]">
          A/B Compare
        </h1>
        <p className="text-[13px] text-serpent-text-muted font-dm-sans">
          Run the same query through multiple strategies side by side
        </p>
      </div>
      <CompareView />
    </div>
  );
}
