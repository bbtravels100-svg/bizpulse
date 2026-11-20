import type { ReactNode } from 'react';
import type { ButtonVariant, ButtonSize } from '../../types';

interface ButtonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  disabled?: boolean;
  title?: string;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  children: ReactNode;
  style?: React.CSSProperties;
}

type StyleMap = {
  bg: string;
  color: string;
  border: string;
  hoverBg: string;
};

const variantMap: Record<ButtonVariant, StyleMap> = {
  primary: {
    bg: 'var(--bp-purple)',
    color: '#fff',
    border: 'var(--bp-purple)',
    hoverBg: 'var(--bp-purple-mid)',
  },
  secondary: {
    bg: 'var(--bp-surface)',
    color: 'var(--bp-text)',
    border: 'var(--bp-border-dark)',
    hoverBg: 'var(--bp-surface-alt)',
  },
  danger: {
    bg: 'var(--bp-danger)',
    color: '#fff',
    border: 'var(--bp-danger)',
    hoverBg: '#B91C1C',
  },
  ghost: {
    bg: 'transparent',
    color: 'var(--bp-text-muted)',
    border: 'transparent',
    hoverBg: 'var(--bp-surface-alt)',
  },
};

const sizeMap: Record<ButtonSize, { padding: string; fontSize: string; height: string }> = {
  sm: { padding: '0 0.75rem', fontSize: '0.8rem',   height: '30px' },
  md: { padding: '0 1rem',    fontSize: '0.875rem',  height: '36px' },
  lg: { padding: '0 1.25rem', fontSize: '0.95rem',   height: '42px' },
};

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  title,
  onClick,
  type = 'button',
  children,
  style,
}: ButtonProps) {
  const v = variantMap[variant];
  const s = sizeMap[size];
  const isDisabled = disabled || loading;

  return (
    <button
      type={type}
      title={title}
      disabled={isDisabled}
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.4rem',
        height: s.height,
        padding: s.padding,
        fontSize: s.fontSize,
        fontWeight: 600,
        letterSpacing: '0.01em',
        borderRadius: 'var(--bp-radius)',
        border: `1px solid ${v.border}`,
        background: v.bg,
        color: v.color,
        cursor: isDisabled ? 'not-allowed' : 'pointer',
        opacity: isDisabled ? 0.55 : 1,
        transition: 'background 0.15s, opacity 0.15s, box-shadow 0.15s',
        whiteSpace: 'nowrap',
        boxShadow: variant === 'primary' && !isDisabled
          ? '0 1px 4px rgba(88,24,240,0.25)'
          : 'none',
        ...style,
      }}
      onMouseEnter={(e) => {
        if (!isDisabled) {
          const el = e.currentTarget as HTMLButtonElement;
          el.style.background = v.hoverBg;
          if (variant === 'primary') el.style.boxShadow = '0 2px 8px rgba(88,24,240,0.35)';
        }
      }}
      onMouseLeave={(e) => {
        if (!isDisabled) {
          const el = e.currentTarget as HTMLButtonElement;
          el.style.background = v.bg;
          if (variant === 'primary') el.style.boxShadow = '0 1px 4px rgba(88,24,240,0.25)';
        }
      }}
    >
      {loading ? (
        <span
          style={{
            width: '14px',
            height: '14px',
            border: '2px solid currentColor',
            borderTopColor: 'transparent',
            borderRadius: '50%',
            animation: 'bp-spin 0.7s linear infinite',
            display: 'inline-block',
          }}
        />
      ) : null}
      {children}
    </button>
  );
}
