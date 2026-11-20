import { useEffect, useRef, useState, useCallback } from 'react';
import { ViewContainer } from '../../components/layout/ViewContainer';
import { Button } from '../../components/common/Button';
import { ErrorState } from '../../components/common/ErrorState';
import { useApp } from '../../context/AppContext';
import { apiGet, apiPost } from '../../api/client';
import { InvestigationOverviewCards } from './InvestigationOverviewCards';
import { StartInvestigationSection } from './StartInvestigationSection';
import { InvestigationHistorySection } from './InvestigationHistorySection';
import { InvestigationDetailView } from './InvestigationDetailView';
import type {
  InvestigationResponse,
  HistoricalInvestigation,
  BackendAction,
  AnomaliesResponse,
} from '../../types';

const STORAGE_KEY = 'bizpulse_investigations_cache_v1';

function loadCachedInvestigations(): Record<string, InvestigationResponse> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveCachedInvestigation(inv: InvestigationResponse) {
  try {
    const current = loadCachedInvestigations();
    current[inv.investigation_id] = inv;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(current));
  } catch {
    // Ignore storage quota errors
  }
}

export function InvestigationsView() {
  const { investigationTargetId } = useApp();

  const [investigations, setInvestigations] = useState<HistoricalInvestigation[]>([]);
  const [activeInvestigation, setActiveInvestigation] = useState<InvestigationResponse | null>(null);
  const [runningAnomalyId, setRunningAnomalyId] = useState<string | null>(null);
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [anomaliesCount, setAnomaliesCount] = useState<number>(3);

  // Avoid running duplicate automatic investigations for the same target
  const handledTargetRef = useRef<string | null>(null);

  // Sync historical investigations from backend actions + local cache
  const refreshHistory = useCallback(async () => {
    setLoadingInitial(true);
    setError(null);
    try {
      // 1. Fetch detected anomalies count
      try {
        const anomRes = await apiGet<AnomaliesResponse>('/api/anomalies');
        if (anomRes && typeof anomRes.count === 'number') {
          setAnomaliesCount(anomRes.count);
        }
      } catch {
        // Fall back to default detected count
      }

      // 2. Fetch all recorded backend actions
      let actions: BackendAction[] = [];
      try {
        const actRes = await apiGet<BackendAction[]>('/api/actions');
        if (actRes && Array.isArray(actRes)) {
          actions = actRes;
        }
      } catch {
        actions = [];
      }

      // 3. Load locally cached full investigations
      const cached = loadCachedInvestigations();

      // 4. Group backend actions by investigation_id
      const actionsByInv: Record<string, BackendAction[]> = {};
      actions.forEach((a) => {
        if (!actionsByInv[a.investigation_id]) {
          actionsByInv[a.investigation_id] = [];
        }
        actionsByInv[a.investigation_id].push(a);
      });

      const list: HistoricalInvestigation[] = [];
      const seenIds = new Set<string>();

      // A) First add any cached full investigations
      Object.values(cached).forEach((full) => {
        seenIds.add(full.investigation_id);
        const relatedActions = actionsByInv[full.investigation_id] || [];
        const hasActiveActions = relatedActions.some(
          (a) => a.status === 'Pending Approval' || a.status === 'Approved' || a.status === 'In Progress'
        );

        let category = 'funnel';
        if (full.facts.anomaly_id.includes('REV')) category = 'revenue';
        else if (full.facts.anomaly_id.includes('PROFIT')) category = 'profit';

        list.push({
          id: full.investigation_id,
          title: full.facts.anomaly_title,
          category,
          severity: full.facts.anomaly_id.includes('PROFIT') ? 'warning' : 'critical',
          date: full.generated_at,
          status: hasActiveActions ? 'active' : 'completed',
          summary: full.analysis.what_happened,
          actionsCount: relatedActions.length,
          anomalyId: full.facts.anomaly_id,
          fullData: full,
        });
      });

      // B) Add backend investigations recorded in actions table that weren't in local cache
      Object.entries(actionsByInv).forEach(([invId, relatedActs]) => {
        if (seenIds.has(invId)) return;
        seenIds.add(invId);

        const first = relatedActs[0];
        const hasActiveActions = relatedActs.some(
          (a) => a.status === 'Pending Approval' || a.status === 'Approved' || a.status === 'In Progress'
        );

        let category = 'funnel';
        let title = 'Mobile Payment Conversion Deterioration';
        let severity = 'critical';

        if (first.anomaly_id.includes('REV')) {
          category = 'revenue';
          title = 'Week 1 vs Week 2 Revenue Decline (-18%)';
          severity = 'critical';
        } else if (first.anomaly_id.includes('PROFIT')) {
          category = 'profit';
          title = 'Low Product Gross Margin Deficit';
          severity = 'warning';
        }

        list.push({
          id: invId,
          title,
          category,
          severity,
          date: first.created_at,
          status: hasActiveActions ? 'active' : 'completed',
          summary: first.problem_description,
          actionsCount: relatedActs.length,
          anomalyId: first.anomaly_id,
        });
      });

      // Sort newest first
      list.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
      setInvestigations(list);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load investigation history');
    } finally {
      setLoadingInitial(false);
    }
  }, []);

  useEffect(() => {
    void refreshHistory();
  }, [refreshHistory]);

  // Execute an investigation
  const handleRunInvestigation = useCallback(async (anomalyId: string) => {
    if (runningAnomalyId) return; // Prevent duplicate concurrent runs
    setRunningAnomalyId(anomalyId);
    setError(null);

    try {
      const result = await apiPost<InvestigationResponse>('/api/investigate', {
        anomaly_id: anomalyId,
      });

      saveCachedInvestigation(result);
      setActiveInvestigation(result);
      void refreshHistory();
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : 'Investigation failed. Please check Gemini connectivity and try again.'
      );
    } finally {
      setRunningAnomalyId(null);
    }
  }, [runningAnomalyId, refreshHistory]);

  // Check if target was passed from Home dashboard
  useEffect(() => {
    if (
      investigationTargetId &&
      handledTargetRef.current !== investigationTargetId &&
      !runningAnomalyId &&
      !activeInvestigation
    ) {
      handledTargetRef.current = investigationTargetId;
      void handleRunInvestigation(investigationTargetId);
    }
  }, [investigationTargetId, runningAnomalyId, activeInvestigation, handleRunInvestigation]);

  // Open an investigation from the history list
  const handleOpenHistorical = async (inv: HistoricalInvestigation) => {
    if (inv.fullData) {
      setActiveInvestigation(inv.fullData);
      return;
    }

    // If only action record exists, fetch fresh diagnosis for this anomaly
    setRunningAnomalyId(inv.anomalyId);
    setError(null);
    try {
      const result = await apiPost<InvestigationResponse>('/api/investigate', {
        anomaly_id: inv.anomalyId,
      });
      saveCachedInvestigation(result);
      setActiveInvestigation(result);
      void refreshHistory();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not load investigation report.');
    } finally {
      setRunningAnomalyId(null);
    }
  };

  // Metrics overview calculations
  const totalCount = investigations.length;
  const activeCount = investigations.filter((i) => i.status === 'active').length;
  const completedCount = investigations.filter((i) => i.status === 'completed').length;

  // If viewing details of a specific investigation
  if (activeInvestigation) {
    return (
      <ViewContainer
        title="Investigation Report"
        subtitle={`Detailed diagnosis for ${activeInvestigation.facts.anomaly_title}`}
        actions={
          <Button variant="secondary" size="sm" onClick={() => setActiveInvestigation(null)}>
            ← Back to All Investigations
          </Button>
        }
      >
        <InvestigationDetailView
          investigation={activeInvestigation}
          onBack={() => setActiveInvestigation(null)}
          onReload={() => void handleRunInvestigation(activeInvestigation.facts.anomaly_id)}
        />
      </ViewContainer>
    );
  }

  return (
    <ViewContainer
      title="Investigations Centre"
      subtitle="Diagnose business anomalies using deterministic Python analytics, timeline correlation, and Gemini root-cause synthesis."
      actions={
        <Button
          variant="primary"
          size="sm"
          disabled={Boolean(runningAnomalyId)}
          onClick={() => void handleRunInvestigation('ANOMALY_FUNNEL_MOBILE_001')}
        >
          {runningAnomalyId ? 'Running Diagnosis…' : '▶ Quick Investigate Mobile Issue'}
        </Button>
      }
    >
      {/* Overview Cards */}
      <InvestigationOverviewCards
        totalCount={totalCount}
        activeCount={activeCount}
        completedCount={completedCount}
        anomaliesAvailableCount={anomaliesCount}
        loading={loadingInitial}
        error={error}
      />

      {/* Global Error Banner if any */}
      {error && (
        <div style={{ marginBottom: '1.5rem' }}>
          <ErrorState
            message="Investigation Engine Notice"
            detail={error}
            onRetry={() => {
              setError(null);
              void refreshHistory();
            }}
          />
        </div>
      )}

      {/* Running Diagnostic Banner */}
      {runningAnomalyId && (
        <div
          style={{
            background: 'linear-gradient(135deg, rgba(88,24,240,0.08), rgba(144,80,248,0.04))',
            border: '2px solid var(--bp-purple)',
            borderRadius: 'var(--bp-radius-lg)',
            padding: '1.25rem 1.5rem',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
          }}
        >
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '16px',
              border: '3px solid var(--bp-purple-pale)',
              borderTopColor: 'var(--bp-purple)',
              animation: 'spin 1s linear infinite',
              flexShrink: 0,
            }}
          />
          <div>
            <strong style={{ fontSize: '0.95rem', color: 'var(--bp-purple)' }}>
              Diagnosing Anomaly: {runningAnomalyId}
            </strong>
            <p style={{ fontSize: '0.82rem', color: 'var(--bp-text-muted)', margin: '0.2rem 0 0 0' }}>
              Extracting verified numbers from the Python Business Data Engine and generating root-cause hypotheses with
              Gemini…
            </p>
          </div>
        </div>
      )}

      {/* Start a New Investigation Section */}
      <StartInvestigationSection
        onRunInvestigation={(id) => void handleRunInvestigation(id)}
        runningAnomalyId={runningAnomalyId}
        targetAnomalyId={investigationTargetId}
      />

      {/* Historical Investigations Section */}
      <InvestigationHistorySection
        investigations={investigations}
        onOpenInvestigation={(inv) => void handleOpenHistorical(inv)}
      />
    </ViewContainer>
  );
}
