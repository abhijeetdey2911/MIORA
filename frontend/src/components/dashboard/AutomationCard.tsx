import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  OctagonX,
  Pause,
  Play,
  SlidersHorizontal,
} from 'lucide-react';
import {
  pauseJobHunterWorkflow,
  resumeJobHunterWorkflow,
  startJobHunterWorkflow,
  stopJobHunterWorkflow,
} from '../../services/multiAgentService';
import type { WorkflowRunSummary } from '../../types/multiAgent';

interface AutomationCardProps {
  automationState: string;
  isKillSwitchEngaged: boolean;
  approvalMode: string;
  activePreferenceCount: number;
  pausedPreferenceCount: number;
  eligiblePreferenceCount: number;
  lastRun: WorkflowRunSummary | null;
  onWorkflowUpdated: () => void;
}

export function AutomationCard({
  automationState,
  isKillSwitchEngaged,
  approvalMode,
  activePreferenceCount,
  pausedPreferenceCount,
  eligiblePreferenceCount,
  lastRun,
  onWorkflowUpdated,
}: AutomationCardProps) {
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusBanner, setStatusBanner] = useState<string | null>(null);

  const normalizedState = isKillSwitchEngaged
    ? 'Stopped'
    : automationState === 'running'
      ? 'Running'
      : automationState === 'paused'
        ? 'Paused'
        : lastRun?.status === 'failed'
          ? 'Failed'
          : lastRun?.status === 'completed'
            ? 'Completed'
            : 'Ready';

  const badgeStyles: Record<string, { badge: string; dot: string }> = {
    Ready: {
      badge: 'bg-sky-500/10 text-sky-600 dark:bg-sky-400/15 dark:text-sky-300',
      dot: 'bg-sky-500',
    },
    Running: {
      badge: 'bg-accent-soft text-accent-ink',
      dot: 'bg-accent animate-pulse',
    },
    Paused: {
      badge:
        'bg-amber-500/10 text-amber-600 dark:bg-amber-400/15 dark:text-amber-300',
      dot: 'bg-amber-500',
    },
    Completed: {
      badge:
        'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-300',
      dot: 'bg-emerald-500',
    },
    Stopped: {
      badge:
        'bg-rose-500/10 text-rose-600 dark:bg-rose-400/15 dark:text-rose-300',
      dot: 'bg-rose-500',
    },
    Failed: {
      badge:
        'bg-rose-500/10 text-rose-600 dark:bg-rose-400/15 dark:text-rose-300',
      dot: 'bg-rose-500',
    },
  };

  const style = badgeStyles[normalizedState] ?? badgeStyles.Ready;

  const handleStart = async () => {
    setBusyAction('start');
    setErrorMessage(null);
    setStatusBanner(null);
    try {
      const run = await startJobHunterWorkflow({ trigger_source: 'manual' });
      setStatusBanner(
        `Completed workflow across ${run.active_preferences} active preference(s).`,
      );
      onWorkflowUpdated();
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to start JobHunter.',
      );
    } finally {
      setBusyAction(null);
    }
  };

  const handlePause = async () => {
    setBusyAction('pause');
    setErrorMessage(null);
    try {
      await pauseJobHunterWorkflow({ workflow_run_id: lastRun?.id });
      setStatusBanner('Workflow paused at safe agent boundary.');
      onWorkflowUpdated();
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to pause workflow.',
      );
    } finally {
      setBusyAction(null);
    }
  };

  const handleResume = async () => {
    setBusyAction('resume');
    setErrorMessage(null);
    try {
      await resumeJobHunterWorkflow({ workflow_run_id: lastRun?.id });
      setStatusBanner('Paused workflows resumed from PostgreSQL checkpoint.');
      onWorkflowUpdated();
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to resume workflow.',
      );
    } finally {
      setBusyAction(null);
    }
  };

  const handleEmergencyStop = async () => {
    setBusyAction('stop');
    setErrorMessage(null);
    try {
      await stopJobHunterWorkflow('Emergency kill switch engaged from Dashboard.');
      setStatusBanner('Emergency kill switch engaged. All active runs stopped.');
      onWorkflowUpdated();
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to engage kill switch.',
      );
    } finally {
      setBusyAction(null);
    }
  };

  return (
    <section
      aria-labelledby="automation-heading"
      className="flex h-full flex-col justify-between rounded-2xl border border-line bg-surface p-5 shadow-card"
    >
      <div>
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 id="automation-heading" className="text-sm font-semibold text-ink">
              Central Automation Control
            </h2>
            <p className="mt-0.5 text-[11px] text-muted">
              LangGraph 5-Agent Orchestrator ·{' '}
              {approvalMode === 'auto_authorised'
                ? 'Auto-Authorised Mode'
                : 'Manual Approval Mode'}
            </p>
          </div>

          <span
            className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${style.badge}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
            {normalizedState}
          </span>
        </div>

        <div className="mt-4 rounded-xl border border-line bg-surface-2 p-4">
          <p className="text-sm font-semibold text-ink">
            Multi-Preference JobHunter Engine
          </p>
          <p className="mt-1 text-xs text-muted">
            <span className="font-medium text-ink">
              {activePreferenceCount} active
            </span>{' '}
            {activePreferenceCount === 1 ? 'preference' : 'preferences'} ·{' '}
            <span>{pausedPreferenceCount} paused (excluded)</span> ·{' '}
            <span>{eligiblePreferenceCount} resume-ready</span>
          </p>

          <div className="mt-3.5 flex flex-wrap gap-2">
            {normalizedState === 'Paused' ? (
              <button
                type="button"
                disabled={busyAction !== null}
                onClick={handleResume}
                className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-white shadow-card transition hover:brightness-105 disabled:opacity-60"
              >
                {busyAction === 'resume' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4 fill-current" />
                )}
                Resume JobHunter
              </button>
            ) : (
              <button
                type="button"
                disabled={busyAction !== null}
                onClick={handleStart}
                className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-xs font-semibold text-white shadow-card transition hover:brightness-105 disabled:opacity-60"
              >
                {busyAction === 'start' ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Running Agents 1–5...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 fill-current" />
                    Start JobHunter
                  </>
                )}
              </button>
            )}

            <button
              type="button"
              disabled={busyAction !== null}
              onClick={handlePause}
              title="Pause at safe agent boundary"
              className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-line bg-surface px-3 py-2 text-xs font-medium text-ink transition hover:border-subtle/50 disabled:opacity-60"
            >
              <Pause className="h-3.5 w-3.5" />
              Pause
            </button>

            <button
              type="button"
              disabled={busyAction !== null}
              onClick={handleEmergencyStop}
              title="Emergency Stop / Kill Switch"
              className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs font-semibold text-rose-600 transition hover:bg-rose-500/20 dark:text-rose-300 disabled:opacity-60"
            >
              <OctagonX className="h-3.5 w-3.5" />
              Stop
            </button>
          </div>

          {lastRun && (
            <div className="mt-3 rounded-lg border border-line bg-surface px-3 py-2 text-[11px] text-muted">
              <div className="flex items-center justify-between">
                <span className="font-medium text-ink">Last Run Summary</span>
                <span className="capitalize">{lastRun.status}</span>
              </div>
              <p className="mt-0.5">
                {lastRun.preference_executions.length} preference workflow(s) ·
                API Spend: ${lastRun.api_spend_usd.toFixed(4)}
              </p>
            </div>
          )}
        </div>

        {errorMessage && (
          <div className="mt-3 flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-600 dark:text-rose-300">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {statusBanner && !errorMessage && (
          <div className="mt-3 flex items-start gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-700 dark:text-emerald-300">
            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>{statusBanner}</span>
          </div>
        )}
      </div>

      <div className="mt-3.5 flex items-center justify-between border-t border-line pt-3 text-xs">
        <span className="text-[11px] text-muted">
          Agents 1–5 execute per active preference
        </span>
        <Link
          to="/automation"
          className="inline-flex items-center gap-1 font-medium text-accent-ink hover:underline"
        >
          <SlidersHorizontal className="h-3.5 w-3.5" />
          Control Centre
        </Link>
      </div>
    </section>
  );
}
