import { useState } from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { EmptyState } from '../../components/common/EmptyState';
import type { ActionVerificationSummary, BadgeVariant } from '../../types';

interface VerificationRecordsSectionProps {
  records: ActionVerificationSummary[];
  onRunVerification: (record: ActionVerificationSummary) => void;
  onViewDetails: (actionId: string) => void;
  onGoToActionCentre?: () => void;
  loading?: boolean;
}

function outcomeVariant(out?: string): BadgeVariant {
  switch (out?.toLowerCase()) {
    case 'improved':
      return 'success';
    case 'not improved':
      return 'neutral';
    case 'deteriorated':
      return 'danger';
    case 'inconclusive':
    case 'insufficient data':
      return 'warning';
    default:
      return 'neutral';
  }
}

function resolutionVariant(res: string): BadgeVariant {
  switch (res) {
    case 'Resolved':
      return 'success';
    case 'Unresolved':
      return 'danger';
    case 'Awaiting Verification':
      return 'warning';
    default:
      return 'neutral';
  }
}

export function VerificationRecordsSection({
  records,
  onRunVerification,
  onViewDetails,
  onGoToActionCentre,
}: VerificationRecordsSectionProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [resolutionFilter, setResolutionFilter] = useState<string>('all');
  const [outcomeFilter, setOutcomeFilter] = useState<string>('all');

  const filtered = records.filter((rec) => {
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      const match =
        rec.actionId.toLowerCase().includes(q) ||
        rec.problemDescription.toLowerCase().includes(q) ||
        rec.recommendedAction.toLowerCase().includes(q) ||
        rec.responsibleDepartment.toLowerCase().includes(q) ||
        (rec.baseline?.metric_name.toLowerCase().includes(q) ?? false);
      if (!match) return false;
    }
    if (resolutionFilter !== 'all' && rec.resolutionStatus !== resolutionFilter) {
      return false;
    }
    if (outcomeFilter !== 'all') {
      const out = rec.latestRun?.outcome;
      if (!out || out !== outcomeFilter) return false;
    }
    return true;
  });

  return (
    <Card
      header={
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            width: '100%',
            flexWrap: 'wrap',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.05rem', fontWeight: 600 }}>📋 Action Verification Records</span>
            <Badge variant="neutral">{records.length} tracked</Badge>
          </div>

          {/* Filter Bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Search actions or metrics…"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                fontSize: '0.82rem',
                padding: '0.35rem 0.65rem',
                borderRadius: 'var(--bp-radius)',
                border: '1px solid var(--bp-border)',
                background: 'var(--bp-surface)',
                color: 'var(--bp-text)',
                minWidth: '150px',
              }}
            />

            <select
              value={resolutionFilter}
              onChange={(e) => setResolutionFilter(e.target.value)}
              style={{
                fontSize: '0.82rem',
                padding: '0.35rem 0.65rem',
                borderRadius: 'var(--bp-radius)',
                border: '1px solid var(--bp-border)',
                background: 'var(--bp-surface)',
                color: 'var(--bp-text)',
              }}
            >
              <option value="all">All Resolutions</option>
              <option value="Resolved">Resolved ✓</option>
              <option value="Unresolved">Unresolved ✗</option>
              <option value="Awaiting Verification">Awaiting Verification ⏳</option>
              <option value="No Baseline">No Baseline</option>
            </select>

            <select
              value={outcomeFilter}
              onChange={(e) => setOutcomeFilter(e.target.value)}
              style={{
                fontSize: '0.82rem',
                padding: '0.35rem 0.65rem',
                borderRadius: 'var(--bp-radius)',
                border: '1px solid var(--bp-border)',
                background: 'var(--bp-surface)',
                color: 'var(--bp-text)',
              }}
            >
              <option value="all">All Outcomes</option>
              <option value="Improved">Improved</option>
              <option value="Not Improved">Not Improved</option>
              <option value="Deteriorated">Deteriorated</option>
              <option value="Inconclusive">Inconclusive</option>
              <option value="Insufficient Data">Insufficient Data</option>
            </select>
          </div>
        </div>
      }
      padding="1.25rem"
    >
      {records.length === 0 ? (
        <EmptyState
          icon="📊"
          title="No action verification records available"
          description="Baselines are automatically captured when action proposals are approved in Action Centre."
          actionLabel={onGoToActionCentre ? 'Go to Action Centre' : undefined}
          onAction={onGoToActionCentre}
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon="🔎"
          title="No records match your filters"
          description="Try broadening your search term or resetting the resolution and outcome filters."
          actionLabel="Reset Filters"
          onAction={() => {
            setSearchTerm('');
            setResolutionFilter('all');
            setOutcomeFilter('all');
          }}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {filtered.map((rec) => {
            const hasBaseline = Boolean(rec.baseline);
            const latest = rec.latestRun;

            return (
              <div
                key={rec.actionId}
                style={{
                  border: '1px solid var(--bp-border)',
                  borderLeft: `4px solid ${
                    rec.resolutionStatus === 'Resolved'
                      ? 'var(--bp-success)'
                      : rec.resolutionStatus === 'Unresolved'
                      ? 'var(--bp-danger)'
                      : rec.resolutionStatus === 'Awaiting Verification'
                      ? 'var(--bp-warning)'
                      : 'var(--bp-border)'
                  }`,
                  borderRadius: 'var(--bp-radius)',
                  padding: '1.25rem',
                  background: 'var(--bp-surface)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.75rem',
                  boxShadow: 'var(--bp-shadow)',
                }}
              >
                {/* Header */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <code
                      style={{
                        fontSize: '0.85rem',
                        fontWeight: 700,
                        background: 'var(--bp-purple-pale)',
                        color: 'var(--bp-purple)',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                      }}
                    >
                      {rec.actionId}
                    </code>
                    <Badge variant={resolutionVariant(rec.resolutionStatus)}>
                      {rec.resolutionStatus.toUpperCase()}
                    </Badge>
                    <Badge variant="neutral">Task: {rec.actionStatus}</Badge>
                    <span style={{ fontSize: '0.8rem', color: 'var(--bp-text-muted)' }}>
                      Dept: <strong>{rec.responsibleDepartment}</strong>
                    </span>
                  </div>

                  {rec.runsCount > 0 && (
                    <Badge variant="info">
                      {rec.runsCount} verification run{rec.runsCount > 1 ? 's' : ''}
                    </Badge>
                  )}
                </div>

                {/* Action & Problem */}
                <div>
                  <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--bp-text)', margin: '0 0 0.35rem 0' }}>
                    {rec.recommendedAction}
                  </h4>
                  <p style={{ fontSize: '0.84rem', color: 'var(--bp-text-muted)', margin: 0, lineHeight: 1.5 }}>
                    <strong>Problem:</strong> {rec.problemDescription}
                  </p>
                </div>

                {/* Baseline & Before/After Snapshot */}
                {hasBaseline && rec.baseline ? (
                  <div
                    style={{
                      background: 'var(--bp-surface-alt)',
                      borderRadius: 'var(--bp-radius)',
                      padding: '0.85rem 1rem',
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                      gap: '0.75rem',
                      fontSize: '0.82rem',
                    }}
                  >
                    <div>
                      <span style={{ color: 'var(--bp-text-muted)', display: 'block', fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 600 }}>
                        Target Metric
                      </span>
                      <strong style={{ color: 'var(--bp-purple)' }}>{rec.baseline.metric_name}</strong>
                    </div>

                    <div>
                      <span style={{ color: 'var(--bp-text-muted)', display: 'block', fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 600 }}>
                        Baseline Snapshot
                      </span>
                      <strong style={{ color: 'var(--bp-danger)' }}>{rec.baseline.baseline_value}</strong>{' '}
                      <span style={{ fontSize: '0.74rem', color: 'var(--bp-text-muted)' }}>(Target: {rec.baseline.target_value})</span>
                    </div>

                    {latest ? (
                      <>
                        <div>
                          <span style={{ color: 'var(--bp-text-muted)', display: 'block', fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 600 }}>
                            Current Telemetry
                          </span>
                          <strong style={{ color: 'var(--bp-success)' }}>{latest.comparison.current_value}</strong>{' '}
                          <Badge variant={outcomeVariant(latest.outcome)} size="sm">
                            {latest.outcome}
                          </Badge>
                        </div>

                        <div>
                          <span style={{ color: 'var(--bp-text-muted)', display: 'block', fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 600 }}>
                            Net Movement
                          </span>
                          <span
                            style={{
                              fontWeight: 700,
                              color: latest.comparison.absolute_change >= 0 ? 'var(--bp-success)' : 'var(--bp-danger)',
                            }}
                          >
                            {latest.comparison.absolute_change > 0
                              ? `+${latest.comparison.absolute_change}`
                              : latest.comparison.absolute_change}{' '}
                            ({latest.comparison.percentage_change > 0
                              ? `+${latest.comparison.percentage_change}%`
                              : `${latest.comparison.percentage_change}%`})
                          </span>
                        </div>
                      </>
                    ) : (
                      <div style={{ gridColumn: 'span 2', display: 'flex', alignItems: 'center' }}>
                        <span style={{ color: 'var(--bp-warning)', fontWeight: 600 }}>
                          ⏳ Baseline recorded on {new Date(rec.baseline.captured_at).toLocaleDateString()}. Awaiting verification run.
                        </span>
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: '0.8rem', color: 'var(--bp-text-muted)', fontStyle: 'italic' }}>
                    No baseline metric captured yet. Action must be approved to initiate baseline tracking.
                  </div>
                )}

                {/* Action Buttons */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    borderTop: '1px solid var(--bp-border)',
                    paddingTop: '0.75rem',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                  }}
                >
                  <div style={{ fontSize: '0.76rem', color: 'var(--bp-text-muted)' }}>
                    {hasBaseline ? (
                      <span>Baseline ID: <code>{rec.baseline?.id}</code></span>
                    ) : (
                      <span>Pending baseline capture</span>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {latest && (
                      <Button variant="ghost" size="sm" onClick={() => onViewDetails(rec.actionId)}>
                        🔍 View AI Analysis
                      </Button>
                    )}
                    {hasBaseline && (
                      <Button variant="primary" size="sm" onClick={() => onRunVerification(rec)}>
                        📊 Run Verification
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
