import React, { useEffect, useState, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from '../common/Header';
import { Sidebar } from '../common/Sidebar';
import { Footer } from '../common/Footer';
import { checkBackendHealth } from '../../services/api';
import type { HealthCheckResult } from '../../types/health';

export const AppLayout: React.FC = () => {
  const [health, setHealth] = useState<HealthCheckResult>({
    state: 'checking',
    data: null,
    latencyMs: null,
    error: null,
    lastChecked: null,
  });

  const [isRefreshing, setIsRefreshing] = useState(false);

  const runHealthCheck = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const result = await checkBackendHealth();
      setHealth(result);
    } catch (err) {
      setHealth({
        state: 'offline',
        data: null,
        latencyMs: null,
        error: err instanceof Error ? err.message : 'Failed health check',
        lastChecked: new Date(),
      });
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    runHealthCheck();
    // Poll health every 12 seconds
    const interval = setInterval(runHealthCheck, 12000);
    return () => clearInterval(interval);
  }, [runHealthCheck]);

  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* Background ambient lighting */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-indigo-600/10 blur-[120px]" />
        <div className="absolute top-[20%] right-[-5%] w-[450px] h-[450px] rounded-full bg-cyan-600/10 blur-[130px]" />
        <div className="absolute bottom-[-10%] left-[30%] w-[600px] h-[600px] rounded-full bg-violet-600/5 blur-[150px]" />
      </div>

      <Header
        connectionState={health.state}
        latencyMs={health.latencyMs}
        onRefresh={runHealthCheck}
        isRefreshing={isRefreshing}
      />

      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        <Sidebar />
        <main className="flex-1 p-4 sm:p-6 lg:p-8 min-w-0 overflow-y-auto">
          <Outlet context={{ health, runHealthCheck, isRefreshing }} />
        </main>
      </div>

      <Footer />
    </div>
  );
};
