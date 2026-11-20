import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  header?: ReactNode;
  footer?: ReactNode;
  padding?: string;
  /** Pass 'ai' to render subtle purple gradient accent on the top border */
  accent?: 'ai' | 'none';
  style?: React.CSSProperties;
}

export function Card({
  children,
  header,
  footer,
  padding = '1.5rem',
  accent = 'none',
  style,
}: CardProps) {
  return (
    <div
      style={{
        background: 'var(--bp-surface)',
        border: '1px solid var(--bp-border)',
        borderRadius: 'var(--bp-radius-lg)',
        boxShadow: 'var(--bp-shadow)',
        overflow: 'hidden',
        borderTop: accent === 'ai' ? '2px solid var(--bp-purple)' : undefined,
        ...style,
      }}
    >
      {header && (
        <div
          style={{
            padding: `1rem ${padding}`,
            borderBottom: '1px solid var(--bp-border)',
            fontWeight: 600,
            fontSize: '0.9rem',
            color: 'var(--bp-text)',
            background: 'var(--bp-surface)',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          {header}
        </div>
      )}
      <div style={{ padding }}>{children}</div>
      {footer && (
        <div
          style={{
            padding: `0.75rem ${padding}`,
            borderTop: '1px solid var(--bp-border)',
            background: 'var(--bp-surface-alt)',
            fontSize: '0.85rem',
            color: 'var(--bp-text-muted)',
          }}
        >
          {footer}
        </div>
      )}
    </div>
  );
}
