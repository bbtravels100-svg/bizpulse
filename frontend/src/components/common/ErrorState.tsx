import { Button } from './Button';

interface ErrorStateProps {
  message: string;
  detail?: string;
  onRetry?: () => void;
}

export function ErrorState({ message, detail, onRetry }: ErrorStateProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '0.75rem',
        padding: '2.5rem 1.5rem',
        textAlign: 'center',
      }}
    >
      <span style={{ fontSize: '2rem', lineHeight: 1 }}>⚠️</span>
      <h3
        style={{
          fontSize: '1rem',
          fontWeight: 600,
          color: 'var(--bp-danger)',
        }}
      >
        {message}
      </h3>
      {detail && (
        <p
          style={{
            fontSize: '0.85rem',
            color: 'var(--bp-text-muted)',
            maxWidth: '28rem',
          }}
        >
          {detail}
        </p>
      )}
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
