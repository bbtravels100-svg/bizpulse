interface LoadingSpinnerProps {
  label?: string;
  size?: number;
}

export function LoadingSpinner({ label, size = 32 }: LoadingSpinnerProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.75rem',
        padding: '2rem',
        color: 'var(--bp-text-muted)',
      }}
    >
      <span
        style={{
          width: size,
          height: size,
          border: `3px solid var(--bp-border)`,
          borderTopColor: 'var(--bp-purple)',
          borderRadius: '50%',
          display: 'inline-block',
          animation: 'bp-spin 0.8s linear infinite',
        }}
      />
      {label && (
        <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>{label}</span>
      )}
    </div>
  );
}
