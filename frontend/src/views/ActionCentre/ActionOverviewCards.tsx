import { MetricCard } from '../../components/common/MetricCard';

interface ActionOverviewCardsProps {
  pendingCount: number;
  approvedCount: number;
  inProgressCount: number;
  completedCount: number;
  overdueCount: number;
  loading?: boolean;
  error?: string | null;
}

export function ActionOverviewCards({
  pendingCount,
  approvedCount,
  inProgressCount,
  completedCount,
  overdueCount,
  loading,
  error,
}: ActionOverviewCardsProps) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}
    >
      <MetricCard
        label="Pending Approval"
        value={pendingCount}
        icon="⏳"
        loading={loading}
        error={error ?? undefined}
        note="Proposals awaiting executive signoff"
      />
      <MetricCard
        label="Approved Tasks"
        value={approvedCount}
        icon="📋"
        loading={loading}
        error={error ?? undefined}
        note="Ready to start execution"
      />
      <MetricCard
        label="In Progress"
        value={inProgressCount}
        icon="⚡"
        loading={loading}
        error={error ?? undefined}
        note="Currently under remediation"
      />
      <MetricCard
        label="Completed"
        value={completedCount}
        icon="✅"
        loading={loading}
        error={error ?? undefined}
        note="Resolved business actions"
      />
      <MetricCard
        label="Overdue Tasks"
        value={overdueCount}
        icon="🚨"
        loading={loading}
        error={error ?? undefined}
        note="Exceeded target deadline"
      />
    </div>
  );
}
