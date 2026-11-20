import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import type { BadgeVariant } from '../../types';

export interface InvestigationOption {
  anomalyId: string;
  title: string;
  category: string;
  severity: 'critical' | 'warning' | 'high' | 'medium';
  triggerMetric: string;
  description: string;
  icon: string;
}

export const SUPPORTED_INVESTIGATION_OPTIONS: InvestigationOption[] = [
  {
    anomalyId: 'ANOMALY_FUNNEL_MOBILE_001',
    title: 'Mobile Payment Deterioration',
    category: 'Funnel & Engineering',
    severity: 'critical',
    triggerMetric: 'Payment completion plummeted from 74.98% to 21.95% (-70.7%)',
    description:
      'Investigate checkout funnel drop following checkout frontend v2.4.0 deployment, gateway 504 timeouts, and customer support ticket surges.',
    icon: '📱',
  },
  {
    anomalyId: 'ANOMALY_REV_001',
    title: 'Weekly Revenue Decline (-18%)',
    category: 'Sales & Revenue',
    severity: 'critical',
    triggerMetric: 'Revenue dropped -$15,300 (-18.00%) from $85,000 to $69,700',
    description:
      'Examine weekly revenue reduction across all five product categories, daily sales trends, and cross-departmental correlation.',
    icon: '📉',
  },
  {
    anomalyId: 'ANOMALY_PROFIT_PROD_005',
    title: 'Low Gross Margin: Gaming Monitor Stand',
    category: 'Pricing & Procurement',
    severity: 'warning',
    triggerMetric: 'Gross margin at 4.00% ($1.80/unit) vs peer avg 46.25%',
    description:
      'Analyze unit cost ($43.20) against selling price ($45.00), supplier cost revisions on Nov 11, and margin deficits.',
    icon: '💰',
  },
];

function severityVariant(sev: string): BadgeVariant {
  switch (sev.toLowerCase()) {
    case 'critical':
    case 'danger':
      return 'danger';
    case 'warning':
    case 'high':
      return 'warning';
    default:
      return 'info';
  }
}

interface StartInvestigationSectionProps {
  onRunInvestigation: (anomalyId: string) => void;
  runningAnomalyId: string | null;
  targetAnomalyId?: string | null;
}

export function StartInvestigationSection({
  onRunInvestigation,
  runningAnomalyId,
  targetAnomalyId,
}: StartInvestigationSectionProps) {
  const isRunning = Boolean(runningAnomalyId);

  return (
    <div style={{ marginBottom: '2rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <div>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--bp-text)' }}>
            Start a New Investigation
          </h3>
          <p style={{ fontSize: '0.82rem', color: 'var(--bp-text-muted)', marginTop: '0.2rem' }}>
            Choose a detected problem. BizPulse extracts verified metrics from the Python analytics engine and synthesizes root-cause hypotheses using Gemini.
          </p>
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '1rem',
        }}
      >
        {SUPPORTED_INVESTIGATION_OPTIONS.map((opt) => {
          const isThisRunning = runningAnomalyId === opt.anomalyId;
          const isTarget = targetAnomalyId === opt.anomalyId;

          return (
            <Card
              key={opt.anomalyId}
              header={
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    width: '100%',
                    gap: '0.5rem',
                  }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
                    <span style={{ fontSize: '1.2rem' }}>{opt.icon}</span>
                    <span style={{ fontSize: '0.95rem' }}>{opt.title}</span>
                  </span>
                  <Badge variant={severityVariant(opt.severity)}>
                    {opt.severity.toUpperCase()}
                  </Badge>
                </div>
              }
              padding="1.25rem"
            >
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.75rem',
                  height: '100%',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div
                    style={{
                      background: 'var(--bp-surface-alt)',
                      padding: '0.5rem 0.75rem',
                      borderRadius: 'var(--bp-radius)',
                      fontSize: '0.78rem',
                      color: 'var(--bp-purple)',
                      fontWeight: 600,
                      marginBottom: '0.5rem',
                    }}
                  >
                    📊 {opt.triggerMetric}
                  </div>
                  <p style={{ fontSize: '0.84rem', color: 'var(--bp-text-muted)', lineHeight: 1.55 }}>
                    {opt.description}
                  </p>
                </div>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    paddingTop: '0.5rem',
                    borderTop: '1px solid var(--bp-border)',
                  }}
                >
                  <span style={{ fontSize: '0.75rem', color: 'var(--bp-text-muted)' }}>
                    Domain: <strong>{opt.category}</strong>
                  </span>
                  <Button
                    variant={isTarget ? 'primary' : 'secondary'}
                    size="sm"
                    loading={isThisRunning}
                    disabled={isRunning && !isThisRunning}
                    onClick={() => onRunInvestigation(opt.anomalyId)}
                  >
                    {isThisRunning ? 'Diagnosing…' : 'Investigate →'}
                  </Button>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
