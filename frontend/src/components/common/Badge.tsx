import type { ReactNode } from 'react';
import type { BadgeVariant } from '../../types';

interface BadgeProps {
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  children: ReactNode;
}

const styles: Record<BadgeVariant, { bg: string; color: string; border: string }> = {
  success: {
    bg: 'var(--bp-success-bg)',
    color: 'var(--bp-success)',
    border: 'var(--bp-success-border)',
  },
  warning: {
    bg: 'var(--bp-warning-bg)',
    color: 'var(--bp-warning)',
    border: 'var(--bp-warning-border)',
  },
  danger: {
    bg: 'var(--bp-danger-bg)',
    color: 'var(--bp-danger)',
    border: 'var(--bp-danger-border)',
  },
  info: {
    bg: 'var(--bp-info-bg)',         /* Light purple tint */
    color: 'var(--bp-purple)',
    border: 'var(--bp-info-border)',
  },
  neutral: {
    bg: 'var(--bp-surface-alt)',
    color: 'var(--bp-text-muted)',
    border: 'var(--bp-border)',
  },
};

export function Badge({ variant = 'neutral', size = 'sm', children }: BadgeProps) {
  const s = styles[variant];
  const fontSize = size === 'sm' ? '0.72rem' : '0.82rem';
  const padding  = size === 'sm' ? '0.15rem 0.5rem' : '0.2rem 0.65rem';

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.25rem',
        fontSize,
        fontWeight: 600,
        padding,
        borderRadius: '9999px',
        background: s.bg,
        color: s.color,
        border: `1px solid ${s.border}`,
        whiteSpace: 'nowrap',
        letterSpacing: '0.03em',
      }}
    >
      {children}
    </span>
  );
}
