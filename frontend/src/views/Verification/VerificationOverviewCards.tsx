import { MetricCard } from '../../components/common/MetricCard';

interface VerificationOverviewCardsProps {
  totalRuns: number;
  pendingCount: number;
  improvedCount: number;
  notImprovedCount: number;
  deterioratedCount: number;
  inconclusiveCount: number;
  loading?: boolean;
  error?: string | null;
}

export function VerificationOverviewCards({
  totalRuns,
  pendingCount,
  improvedCount,
  notImprovedCount,
  deterioratedCount,
  inconclusiveCount,
  loading,
  error,
}: VerificationOverviewCardsProps) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}
    >
      <MetricCard
        label="Total Verifications"
        value={totalRuns}
        icon="📊"
        loading={loading}
        error={error ?? undefined}
        note="Total verification runs executed"
      />
      <MetricCard
        label="Awaiting Verification"
        value={pendingCount}
        icon="⏳"
        loading={loading}
        error={error ?? undefined}
        note="Actions with baseline awaiting follow-up"
      />
      <MetricCard
        label="Improved Outcomes"
        value={improvedCount}
        icon="📈"
        loading={loading}
        error={error ?? undefined}
        note="Metrics showed positive movement"
      />
      <MetricCard
        label="Not Improved"
        value={notImprovedCount}
        icon="➖"
        loading={loading}
        error={error ?? undefined}
        note="No significant metric change"
      />
      <MetricCard
        label="Deteriorated"
        value={deterioratedCount}
        icon="📉"
        loading={loading}
        error={error ?? undefined}
        note="Problem worsened post-action"
      />
      <MetricCard
        label="Inconclusive / Insufficient"
        value={inconclusiveCount}
        icon="⚠️"
        loading={loading}
        error={error ?? undefined}
        note="Missing telemetry feed or data gap"
      />
    </div>
  );
}
