import type { ReactNode } from 'react';

interface ViewContainerProps {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  maxWidth?: string;
}

export function ViewContainer({
  title,
  subtitle,
  actions,
  children,
  maxWidth = '1280px',
}: ViewContainerProps) {
  return (
    <div
      style={{
        maxWidth,
        margin: '0 auto',
        padding: '1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
        animation: 'bp-fade-in 0.2s ease-out',
      }}
    >
      {(title || actions) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '1rem',
            flexWrap: 'wrap',
          }}
        >
          {title && (
            <div>
              <h2
                style={{
                  fontSize: '1.4rem',
                  fontWeight: 700,
                  color: 'var(--bp-text)',
                  letterSpacing: '-0.02em',
                }}
              >
                {title}
              </h2>
              {subtitle && (
                <p
                  style={{
                    fontSize: '0.875rem',
                    color: 'var(--bp-text-muted)',
                    marginTop: '0.25rem',
                  }}
                >
                  {subtitle}
                </p>
              )}
            </div>
          )}
          {actions && (
            <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
              {actions}
            </div>
          )}
        </div>
      )}

      {children}
    </div>
  );
}
