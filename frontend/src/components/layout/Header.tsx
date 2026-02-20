/**
 * Sticky header with navigation tabs, logo, and health indicator.
 */

import { useLocation, useNavigate } from 'react-router-dom';
import SerpentLogo from './SerpentLogo';
import { TABS } from '@/lib/constants';
import { useAppStore } from '@/stores/appStore';

export default function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const healthStatus = useAppStore((s) => s.healthStatus);

  const activeTab = location.pathname.split('/')[1] || 'strategies';

  const healthColor =
    healthStatus === 'healthy'
      ? 'bg-strategy-hybrid'
      : healthStatus === 'degraded'
        ? 'bg-yellow-500'
        : 'bg-red-500';

  const healthText =
    healthStatus === 'healthy'
      ? 'systems nominal'
      : healthStatus === 'degraded'
        ? 'degraded'
        : 'offline';

  return (
    <header className="sticky top-0 z-50 border-b border-serpent-border bg-serpent-bg/[0.88] backdrop-blur-[24px]">
      <div className="max-w-[1400px] mx-auto px-8 py-3 flex justify-between items-center">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <SerpentLogo size={30} />
          <div className="flex items-baseline gap-2">
            <span className="text-[16px] font-semibold tracking-tight font-outfit text-serpent-text">
              Serpent
            </span>
            <span className="text-[9px] px-[7px] py-[2px] bg-gradient-to-br from-strategy-agentic/[0.07] to-strategy-hybrid/[0.07] text-strategy-agentic rounded-[3px] font-medium border border-strategy-agentic/[0.09] font-mono tracking-wider">
              RAG
            </span>
          </div>
        </div>

        {/* Navigation tabs */}
        <nav className="flex gap-[3px]">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => navigate(`/${tab.id}`)}
                className={`px-[13px] py-[6px] text-[11.5px] rounded-[7px] cursor-pointer transition-all duration-200 font-dm-sans font-medium border ${
                  isActive
                    ? 'bg-[#111] border-serpent-border text-serpent-text-secondary'
                    : 'bg-transparent border-transparent text-serpent-text-muted hover:text-serpent-text-tertiary hover:bg-[#0c0c0c]'
                }`}
              >
                <span className="mr-[5px] text-[9px] opacity-70">
                  {tab.icon}
                </span>
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* Health indicator */}
        <div className="flex gap-[7px] items-center">
          <div
            className={`w-[6px] h-[6px] rounded-full animate-pulse ${healthColor}`}
          />
          <span className="text-[10px] text-serpent-text-muted font-mono">
            {healthText}
          </span>
        </div>
      </div>
    </header>
  );
}
