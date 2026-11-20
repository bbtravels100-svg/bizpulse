import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { useApiData } from '../../hooks/useApiData';
import { useApp } from '../../context/AppContext';
import type { AnomaliesResponse } from '../../types';
import type { BadgeVariant } from '../../types';

function severityVariant(severity: string): BadgeVariant {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'danger';
    case 'warning':
    case 'high':
      return 'warning';
    default:
      return 'neutral';
  }
}

const capitalise = (s: string): string => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

export function AlertsSection() {
  const { data, loading, error, reload } = useApiData<AnomaliesResponse>('/api/anomalies');
  const { openInvestigation } = useApp();

  const alerts = data?.anomalies ?? [];

  return (
    <Card
      header={
        <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
          <span>🚨 Business Alerts</span>
          {data && alerts.length > 0 && (
            <Badge variant="danger">{alerts.length} detected</Badge>
          )}
        </div>
      }
      padding="1.25rem"
    >
      {loading ? (
        <LoadingSpinner label="Checking for anomalies…" />
      ) : error ? (
        <ErrorState message="Could not load alerts" detail={error} onRetry={reload} />
      ) : alerts.length === 0 ? (
        <EmptyState
          icon="✅"
          title="No anomalies detected"
          description="The anomaly engine found nothing unusual in the current data."
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {alerts.map((a) => (
            <div
              key={a.anomaly_id}
              style={{
                border: '1px solid var(--bp-border)',
                borderLeft: `4px solid ${
                  severityVariant(a.severity) === 'danger' ? 'var(--bp-danger)' : 'var(--bp-warning)'
                }`,
                borderRadius: 'var(--bp-radius)',
                padding: '1rem',
                display: 'flex',
                gap: '1rem',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
              }}
            >
              <div style={{ flex: '1 1 320px', minWidth: 0 }}>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <strong style={{ fontSize: '0.92rem' }}>{a.title}</strong>
                  <Badge variant={severityVariant(a.severity)}>{capitalise(a.severity)}</Badge>
                  <Badge variant="info">{capitalise(a.category)}</Badge>
                </div>
                <p
                  style={{
                    fontSize: '0.84rem',
                    color: 'var(--bp-text-muted)',
                    marginTop: '0.4rem',
                    lineHeight: 1.55,
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  {a.description}
                </p>
              </div>
              <Button variant="primary" size="sm" onClick={() => openInvestigation(a.anomaly_id)}>
                Investigate →
              </Button>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
