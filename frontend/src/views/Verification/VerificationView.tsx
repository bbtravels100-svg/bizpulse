import { useEffect, useState, useCallback } from 'react';
import { ViewContainer } from '../../components/layout/ViewContainer';
import { Button } from '../../components/common/Button';
import { ErrorState } from '../../components/common/ErrorState';
import { useApp } from '../../context/AppContext';
import { apiGet } from '../../api/client';
import { VerificationOverviewCards } from './VerificationOverviewCards';
import { VerificationRecordsSection } from './VerificationRecordsSection';
import { RunVerificationModal } from './RunVerificationModal';
import { VerificationDetailModal } from './VerificationDetailModal';
import type {
  ActionResponse,
  ActionVerificationSummary,
  VerificationHistoryResponse,
  VerificationRunResponse,
} from '../../types';

export function VerificationView() {
  const { setView } = useApp();

  const [records, setRecords] = useState<ActionVerificationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedbackNotice, setFeedbackNotice] = useState<string | null>(null);

  // Modals state
  const [runModalTarget, setRunModalTarget] = useState<ActionVerificationSummary | null>(null);
  const [detailModalActionId, setDetailModalActionId] = useState<string | null>(null);

  // Sync actions & verification histories from backend
  const fetchAllVerificationData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const actions = await apiGet<ActionResponse[]>('/api/actions');
      if (!Array.isArray(actions)) {
        setRecords([]);
        return;
      }

      // Query verification histories in parallel for all actions
      const summaries: ActionVerificationSummary[] = await Promise.all(
        actions.map(async (act) => {
          let hist: VerificationHistoryResponse | null = null;
          try {
            hist = await apiGet<VerificationHistoryResponse>(`/api/verification/history/${act.id}`);
          } catch {
            // 404 indicates no baseline exists yet for this action
            hist = null;
          }

          const hasBaseline = Boolean(hist?.baseline);
          const runs = hist?.verification_runs || [];
          const latestRun = runs.length > 0 ? runs[runs.length - 1] : undefined;

          let resolutionStatus: 'Resolved' | 'Unresolved' | 'Awaiting Verification' | 'No Baseline' = 'No Baseline';
          if (hasBaseline) {
            if (runs.length === 0) {
              resolutionStatus = 'Awaiting Verification';
            } else if (latestRun?.is_resolved) {
              resolutionStatus = 'Resolved';
            } else {
              resolutionStatus = 'Unresolved';
            }
          }

          return {
            actionId: act.id,
            problemDescription: act.problem_description,
            recommendedAction: act.recommended_action,
            responsibleDepartment: act.responsible_department,
            actionStatus: act.status,
            baseline: hist?.baseline,
            latestRun,
            runsCount: runs.length,
            resolutionStatus,
          };
        })
      );

      // Sort: actions with active/verified runs first
      summaries.sort((a, b) => {
        if (a.runsCount > 0 && b.runsCount === 0) return -1;
        if (b.runsCount > 0 && a.runsCount === 0) return 1;
        if (a.baseline && !b.baseline) return -1;
        if (!a.baseline && b.baseline) return 1;
        return 0;
      });

      setRecords(summaries);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not fetch verification records');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAllVerificationData();
  }, [fetchAllVerificationData]);

  // Aggregate overview metrics strictly from backend results
  let totalRuns = 0;
  let improvedCount = 0;
  let notImprovedCount = 0;
  let deterioratedCount = 0;
  let inconclusiveCount = 0;

  records.forEach((rec) => {
    totalRuns += rec.runsCount;
    if (rec.latestRun) {
      const out = rec.latestRun.outcome;
      if (out === 'Improved') improvedCount += 1;
      else if (out === 'Not Improved') notImprovedCount += 1;
      else if (out === 'Deteriorated') deterioratedCount += 1;
      else inconclusiveCount += 1;
    }
  });

  const pendingCount = records.filter((r) => r.resolutionStatus === 'Awaiting Verification').length;

  const handleRunCompleted = (result: VerificationRunResponse) => {
    setFeedbackNotice(`Verification run ${result.id} executed successfully. Outcome: ${result.outcome}.`);
    void fetchAllVerificationData();
    setDetailModalActionId(result.action_id);
  };

  return (
    <ViewContainer
      title="Verification Centre"
      subtitle="Verify whether completed actions solved the underlying business problem using deterministic Python math and Gemini follow-up reasoning."
      actions={
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <Button variant="secondary" size="sm" onClick={() => void fetchAllVerificationData()}>
            ↻ Refresh Metrics
          </Button>
          <Button variant="primary" size="sm" onClick={() => setView('actions')}>
            Action Centre →
          </Button>
        </div>
      }
    >
      {/* Overview Statistics Cards */}
      <VerificationOverviewCards
        totalRuns={totalRuns}
        pendingCount={pendingCount}
        improvedCount={improvedCount}
        notImprovedCount={notImprovedCount}
        deterioratedCount={deterioratedCount}
        inconclusiveCount={inconclusiveCount}
        loading={loading}
        error={error}
      />

      {/* Global Feedback Banner */}
      {feedbackNotice && (
        <div
          style={{
            background: 'var(--bp-success-pale)',
            border: '1px solid var(--bp-success)',
            borderRadius: 'var(--bp-radius)',
            padding: '0.75rem 1rem',
            marginBottom: '1.25rem',
            color: 'var(--bp-success)',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>✓ {feedbackNotice}</span>
          <button
            type="button"
            onClick={() => setFeedbackNotice(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--bp-success)' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Global Error Banner */}
      {error && (
        <div style={{ marginBottom: '1.25rem' }}>
          <ErrorState message="Verification Notice" detail={error} onRetry={() => void fetchAllVerificationData()} />
        </div>
      )}

      {/* Verification Lifecycle Process Bar */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
          marginBottom: '1.5rem',
        }}
      >
        {[
          { icon: '📐', step: '1', label: 'Baseline Capture', desc: 'Immutable snapshot recorded on action approval' },
          { icon: '⚙️', step: '2', label: 'Execution Window', desc: 'Department team implements the remediation' },
          { icon: '📊', step: '3', label: 'Python Comparison', desc: 'Deterministic math: absolute and percentage change' },
          { icon: '✨', step: '4', label: 'Resolution Audit', desc: 'Target confirmed or reopened for secondary fix' },
        ].map((s) => (
          <div
            key={s.step}
            style={{
              background: 'var(--bp-surface)',
              border: '1px solid var(--bp-border)',
              borderRadius: 'var(--bp-radius-lg)',
              padding: '1.1rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.35rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
              <span style={{ fontSize: '1.2rem' }}>{s.icon}</span>
              <span
                style={{
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  color: 'var(--bp-purple)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Step {s.step}
              </span>
            </div>
            <div style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--bp-text)' }}>{s.label}</div>
            <div style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)', lineHeight: 1.45 }}>{s.desc}</div>
          </div>
        ))}
      </div>

      {/* Action Verification Records Section */}
      <VerificationRecordsSection
        records={records}
        onRunVerification={(rec) => setRunModalTarget(rec)}
        onViewDetails={(actionId) => setDetailModalActionId(actionId)}
        onGoToActionCentre={() => setView('actions')}
        loading={loading}
      />

      {/* Run Verification Modal */}
      <RunVerificationModal
        actionSummary={runModalTarget}
        isOpen={Boolean(runModalTarget)}
        onClose={() => setRunModalTarget(null)}
        onRunComplete={handleRunCompleted}
      />

      {/* Verification Details & Before/After Comparison Modal */}
      <VerificationDetailModal
        actionId={detailModalActionId}
        isOpen={Boolean(detailModalActionId)}
        onClose={() => setDetailModalActionId(null)}
        onReopenSuccess={() => void fetchAllVerificationData()}
      />
    </ViewContainer>
  );
}
