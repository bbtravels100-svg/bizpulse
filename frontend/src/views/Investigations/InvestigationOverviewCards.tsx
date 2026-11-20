import { MetricCard } from '../../components/common/MetricCard';

interface InvestigationOverviewCardsProps {
  totalCount: number;
  activeCount: number;
  completedCount: number;
  anomaliesAvailableCount: number;
  loading?: boolean;
  error?: string | null;
}

export function InvestigationOverviewCards({
  totalCount,
  activeCount,
  completedCount,
  anomaliesAvailableCount,
  loading,
  error,
}: InvestigationOverviewCardsProps) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}
    >
      <MetricCard
        label="Total Investigations"
        value={totalCount}
        icon="🔍"
        loading={loading}
        error={error ?? undefined}
        note="From backend action records & active reports"
      />
      <MetricCard
        label="Active Investigations"
        value={activeCount}
        icon="⚡"
        loading={loading}
        error={error ?? undefined}
        note="Investigations with pending or in-progress tasks"
      />
      <MetricCard
        label="Completed Investigations"
        value={completedCount}
        icon="✅"
        loading={loading}
        error={error ?? undefined}
        note="Resolved problems with completed actions"
      />
      <MetricCard
        label="Detected Anomalies"
        value={anomaliesAvailableCount}
        icon="🚨"
        loading={loading}
        error={error ?? undefined}
        note="Ready for automated root-cause analysis"
      />
    </div>
  );
}
