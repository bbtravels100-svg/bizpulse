import type { ReactNode } from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  delta?: number;
  deltaLabel?: string;
  icon?: ReactNode;
  loading?: boolean;
  /** Small explanatory text under the value (e.g. data caveat). */
  note?: string;
  /** When set, the card shows this error instead of a value. */
  error?: string;
}

export function MetricCard({
  label,
  value,
  delta,
  deltaLabel,
  icon,
  loading,
  note,
  error,
}: MetricCardProps) {
  const isPositive = delta !== undefined && delta >= 0;
  const deltaColor = delta === undefined
    ? 'var(--bp-text-muted)'
    : isPositive ? 'var(--bp-success)' : 'var(--bp-danger)';

  return (
    <div
      style={{
        background: 'var(--bp-surface)',
        border: '1px solid var(--bp-border)',
        borderRadius: 'var(--bp-radius-lg)',
        boxShadow: 'var(--bp-shadow)',
        padding: '1.25rem 1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
        transition: 'box-shadow 0.15s',
        minWidth: 0,
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.boxShadow = 'var(--bp-shadow-md)';
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.boxShadow = 'var(--bp-shadow)';
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span
          style={{
            fontSize: '0.72rem',
            fontWeight: 700,
            color: 'var(--bp-text-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.07em',
          }}
        >
          {label}
        </span>
        {icon && (
          <span
            style={{
              color: 'var(--bp-purple-light)',
              fontSize: '1.1rem',
              background: 'var(--bp-purple-pale)',
              padding: '0.25rem',
              borderRadius: 'var(--bp-radius)',
              lineHeight: 1,
            }}
          >
            {icon}
          </span>
        )}
      </div>

      {loading ? (
        <div
          style={{
            height: '2rem',
            background: 'var(--bp-surface-alt)',
            borderRadius: 'var(--bp-radius)',
            animation: 'bp-pulse 1.5s infinite',
          }}
        />
      ) : error ? (
        <span style={{ fontSize: '0.82rem', color: 'var(--bp-danger)', fontWeight: 500 }}>
          Unavailable — {error}
        </span>
      ) : (
        <span
          style={{
            fontSize: '1.75rem',
            fontWeight: 700,
            color: 'var(--bp-text)',
            lineHeight: 1.2,
            letterSpacing: '-0.02em',
          }}
        >
          {value}
        </span>
      )}

      {delta !== undefined && !loading && !error && (
        <span
          style={{
            fontSize: '0.78rem',
            color: deltaColor,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '0.2rem',
          }}
        >
          {isPositive ? '▲' : '▼'} {Math.abs(delta).toFixed(1)}%
          {deltaLabel ? ` ${deltaLabel}` : ''}
        </span>
      )}

      {note && !loading && !error && (
        <span style={{ fontSize: '0.74rem', color: 'var(--bp-text-muted)' }}>{note}</span>
      )}
    </div>
  );
}
