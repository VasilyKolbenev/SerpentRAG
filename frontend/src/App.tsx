import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import Header from '@/components/layout/Header';
import AnimatedBG from '@/components/layout/AnimatedBG';
import StrategiesPage from '@/pages/StrategiesPage';
import ChatPage from '@/pages/ChatPage';
import DebuggerPage from '@/pages/DebuggerPage';
import ComparePage from '@/pages/ComparePage';
import GraphPage from '@/pages/GraphPage';
import QualityPage from '@/pages/QualityPage';
import DocumentsPage from '@/pages/DocumentsPage';
import { AdvisorChatbot } from '@/components/advisor/AdvisorChatbot';
import { useAppStore } from '@/stores/appStore';
import { api } from '@/lib/api';
import { HEALTH_POLL_INTERVAL } from '@/lib/constants';

function AppShell() {
  const setHealthStatus = useAppStore((s) => s.setHealthStatus);

  useEffect(() => {
    let mounted = true;

    const checkHealth = async () => {
      try {
        const res = await api.health();
        if (!mounted) return;
        const allHealthy = Object.values(res.services).every(
          (s) => s === 'healthy',
        );
        setHealthStatus(allHealthy ? 'healthy' : 'degraded');
      } catch {
        if (mounted) setHealthStatus('offline');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, HEALTH_POLL_INTERVAL);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [setHealthStatus]);

  return (
    <div className="min-h-screen bg-serpent-bg text-serpent-text font-dm-sans relative">
      <AnimatedBG />
      <Header />
      <main className="max-w-[1400px] mx-auto px-8 py-7 relative z-10">
        <Routes>
          <Route path="/strategies" element={<StrategiesPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/debugger" element={<DebuggerPage />} />
          <Route path="/debugger/:traceId" element={<DebuggerPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/quality" element={<QualityPage />} />
          <Route path="*" element={<Navigate to="/strategies" replace />} />
        </Routes>
      </main>
      <AdvisorChatbot />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}
