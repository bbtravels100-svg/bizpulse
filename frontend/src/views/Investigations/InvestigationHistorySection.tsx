import { useState } from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { EmptyState } from '../../components/common/EmptyState';
import type { HistoricalInvestigation } from '../../types';
import type { BadgeVariant } from '../../types';

function severityVariant(sev: string): BadgeVariant {
  switch (sev?.toLowerCase()) {
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

function statusVariant(st: string): BadgeVariant {
  switch (st?.toLowerCase()) {
    case 'completed':
      return 'success';
    case 'active':
      return 'warning';
    default:
      return 'neutral';
  }
}

interface InvestigationHistorySectionProps {
  investigations: HistoricalInvestigation[];
  onOpenInvestigation: (inv: HistoricalInvestigation) => void;
  onClearHistory?: () => void;
}

export function InvestigationHistorySection({
  investigations,
  onOpenInvestigation,
}: InvestigationHistorySectionProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filtered = investigations.filter((inv) => {
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      const matchText =
        inv.id.toLowerCase().includes(q) ||
        inv.title.toLowerCase().includes(q) ||
        inv.summary.toLowerCase().includes(q);
      if (!matchText) return false;
    }
    if (categoryFilter !== 'all') {
      if (!inv.category.toLowerCase().includes(categoryFilter.toLowerCase())) {
        return false;
      }
    }
    if (statusFilter !== 'all') {
      if (inv.status !== statusFilter) {
        return false;
      }
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
            <span style={{ fontSize: '1.05rem', fontWeight: 600 }}>📋 Investigation History</span>
            <Badge variant="neutral">{investigations.length} recorded</Badge>
          </div>

          {/* Filter Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Search investigations…"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                fontSize: '0.82rem',
                padding: '0.35rem 0.65rem',
                borderRadius: 'var(--bp-radius)',
                border: '1px solid var(--bp-border)',
                background: 'var(--bp-surface)',
                color: 'var(--bp-text)',
                minWidth: '160px',
              }}
            />

            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              style={{
                fontSize: '0.82rem',
                padding: '0.35rem 0.65rem',
                borderRadius: 'var(--bp-radius)',
                border: '1px solid var(--bp-border)',
                background: 'var(--bp-surface)',
                color: 'var(--bp-text)',
              }}
            >
              <option value="all">All Categories</option>
              <option value="funnel">Funnel & Technology</option>
              <option value="revenue">Sales & Revenue</option>
              <option value="profit">Pricing & Profitability</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                fontSize: '0.82rem',
                padding: '0.35rem 0.65rem',
                borderRadius: 'var(--bp-radius)',
                border: '1px solid var(--bp-border)',
                background: 'var(--bp-surface)',
                color: 'var(--bp-text)',
              }}
            >
              <option value="all">All Statuses</option>
              <option value="completed">Completed</option>
              <option value="active">Active Tasks</option>
            </select>
          </div>
        </div>
      }
      padding="1.25rem"
    >
      {investigations.length === 0 ? (
        <EmptyState
          icon="🔍"
          title="No previous investigations recorded"
          description="Click 'Investigate Anomaly' above to run an AI diagnostic report on any detected business anomaly."
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon="🔎"
          title="No investigations match your filters"
          description="Try adjusting your search terms or clearing the category and status filters."
          actionLabel="Reset Filters"
          onAction={() => {
            setSearchTerm('');
            setCategoryFilter('all');
            setStatusFilter('all');
          }}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {filtered.map((inv) => (
            <div
              key={inv.id}
              style={{
                border: '1px solid var(--bp-border)',
                borderRadius: 'var(--bp-radius)',
                padding: '1rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.6rem',
                background: 'var(--bp-surface)',
                transition: 'border-color 0.15s',
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--bp-purple-light)';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--bp-border)';
              }}
            >
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
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      background: 'var(--bp-purple-pale)',
                      color: 'var(--bp-purple)',
                      padding: '0.2rem 0.45rem',
                      borderRadius: '4px',
                    }}
                  >
                    {inv.id}
                  </code>
                  <strong style={{ fontSize: '0.92rem', color: 'var(--bp-text)' }}>{inv.title}</strong>
                  <Badge variant={severityVariant(inv.severity)}>{inv.severity.toUpperCase()}</Badge>
                  <Badge variant="info">{inv.category}</Badge>
                  <Badge variant={statusVariant(inv.status)}>{inv.status.toUpperCase()}</Badge>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)' }}>
                    {new Date(inv.date).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                  <Button variant="secondary" size="sm" onClick={() => onOpenInvestigation(inv)}>
                    View Details →
                  </Button>
                </div>
              </div>

              <p
                style={{
                  fontSize: '0.85rem',
                  color: 'var(--bp-text-muted)',
                  lineHeight: 1.55,
                  margin: 0,
                }}
              >
                {inv.summary}
              </p>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '1rem',
                  fontSize: '0.78rem',
                  color: 'var(--bp-text-muted)',
                  borderTop: '1px solid var(--bp-border)',
                  paddingTop: '0.5rem',
                }}
              >
                <span>
                  Target Anomaly: <code>{inv.anomalyId}</code>
                </span>
                {inv.actionsCount > 0 && (
                  <span style={{ color: 'var(--bp-success)', fontWeight: 600 }}>
                    ⚡ {inv.actionsCount} task{inv.actionsCount > 1 ? 's' : ''} linked
                  </span>
                )}
                {inv.fullData && (
                  <span style={{ color: 'var(--bp-purple)' }}>
                    ✨ AI synthesis ready ({inv.fullData.model_used})
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
