import type { ReactNode } from 'react';
import { Button } from '../../components/common/Button';
import { useChat } from '../../context/ChatContext';
import type { ChatMessage } from '../../types/chat';
import { ActionProposals } from './ActionProposals';

function Section({
  title,
  tone,
  items,
}: {
  title: string;
  tone: 'success' | 'warning' | 'neutral';
  items: string[];
}) {
  if (items.length === 0) return null;
  const palette = {
    success: { bg: 'var(--bp-success-bg)', border: 'var(--bp-success-border)', fg: 'var(--bp-success)' },
    warning: { bg: 'var(--bp-warning-bg)', border: 'var(--bp-warning-border)', fg: 'var(--bp-warning)' },
    neutral: { bg: 'var(--bp-surface-alt)', border: 'var(--bp-border)', fg: 'var(--bp-text-muted)' },
  }[tone];
  return (
    <div
      style={{
        background: palette.bg,
        border: `1px solid ${palette.border}`,
        borderRadius: 'var(--bp-radius)',
        padding: '0.7rem 0.9rem',
      }}
    >
      <div
        style={{
          fontSize: '0.7rem',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.07em',
          color: palette.fg,
          marginBottom: '0.35rem',
        }}
      >
        {title}
      </div>
      <ul style={{ paddingLeft: '1.1rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
        {items.map((t, i) => (
          <li key={i} style={{ fontSize: '0.86rem', lineHeight: 1.55 }}>
            {t}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Avatar({ children }: { children: ReactNode }) {
  return (
    <div
      aria-hidden
      style={{
        width: '34px',
        height: '34px',
        borderRadius: '10px',
        flexShrink: 0,
        background: 'var(--bp-gradient-ai)',
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '1rem',
      }}
    >
      {children}
    </div>
  );
}

const time = (iso: string): string =>
  new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });

export function MessageBubble({ message }: { message: ChatMessage }) {
  const { retry, sendMessage, isLoading } = useChat();

  if (message.role === 'user') {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <div style={{ maxWidth: 'min(85%, 640px)' }}>
          <div
            style={{
              background: 'var(--bp-navy)',
              color: '#fff',
              padding: '0.7rem 1rem',
              borderRadius: '16px 16px 4px 16px',
              fontSize: '0.92rem',
              lineHeight: 1.55,
              whiteSpace: 'pre-wrap',
              overflowWrap: 'anywhere',
            }}
          >
            {message.content}
          </div>
          <div style={{ textAlign: 'right', fontSize: '0.68rem', color: 'var(--bp-text-light)', marginTop: '0.2rem' }}>
            You · {time(message.timestamp)}
          </div>
        </div>
      </div>
    );
  }

  if (message.role === 'error') {
    return (
      <div style={{ display: 'flex', gap: '0.65rem' }}>
        <Avatar>⚠</Avatar>
        <div
          role="alert"
          style={{
            background: 'var(--bp-danger-bg)',
            border: '1px solid var(--bp-danger-border)',
            borderRadius: '4px 16px 16px 16px',
            padding: '0.8rem 1rem',
            maxWidth: 'min(90%, 680px)',
          }}
        >
          <div style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--bp-danger)' }}>
            BizPulse AI couldn&apos;t answer
          </div>
          <div style={{ fontSize: '0.85rem', margin: '0.25rem 0 0.6rem', overflowWrap: 'anywhere' }}>{message.content}</div>
          <Button variant="secondary" size="sm" disabled={isLoading} onClick={() => void retry(message.id)}>
            Retry
          </Button>
        </div>
      </div>
    );
  }

  const r = message.response;
  const inv = r?.investigation;

  return (
    <div style={{ display: 'flex', gap: '0.65rem', minWidth: 0 }}>
      <Avatar>✨</Avatar>
      <div style={{ flex: 1, minWidth: 0, maxWidth: '760px' }}>
        <div
          style={{
            background: 'var(--bp-surface)',
            border: '1px solid var(--bp-border)',
            borderRadius: '4px 16px 16px 16px',
            padding: '1rem 1.1rem',
            boxShadow: 'var(--bp-shadow)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
          }}
        >
          {inv && (
            <div
              style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                letterSpacing: '0.07em',
                textTransform: 'uppercase',
                color: 'var(--bp-purple)',
              }}
            >
              Investigation brief · {inv.target_team_and_priority}
            </div>
          )}

          <div style={{ fontSize: '0.92rem', lineHeight: 1.65, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
            {message.content}
          </div>

          {r && (
            <>
              <Section title="Confirmed facts (from your data)" tone="success" items={r.confirmed_facts} />
              <Section
                title="Possible explanations (not confirmed)"
                tone="warning"
                items={r.possible_explanations}
              />
              {inv && <Section title="Recommended next steps" tone="neutral" items={inv.recommended_action_plan} />}
              {inv && (
                <Section
                  title="How to verify it's fixed"
                  tone="neutral"
                  items={inv.verification_and_success_criteria}
                />
              )}

              {r.follow_up_questions.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                  {r.follow_up_questions.map((q) => (
                    <button
                      key={q}
                      type="button"
                      disabled={isLoading}
                      onClick={() => void sendMessage(q)}
                      style={{
                        background: 'var(--bp-purple-pale)',
                        border: '1px solid var(--bp-info-border)',
                        color: 'var(--bp-purple)',
                        borderRadius: '9999px',
                        padding: '0.3rem 0.75rem',
                        fontSize: '0.78rem',
                        fontWeight: 500,
                        cursor: isLoading ? 'not-allowed' : 'pointer',
                        opacity: isLoading ? 0.6 : 1,
                      }}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}

              <ActionProposals message={message} />
            </>
          )}
        </div>
        <div style={{ fontSize: '0.68rem', color: 'var(--bp-text-light)', marginTop: '0.25rem' }}>
          BizPulse AI · {time(message.timestamp)}
          {r && r.data_sources_used.length > 0 && <> · Data: {r.data_sources_used.join(', ')}</>}
          {r && <> · {r.model_used}</>}
        </div>
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div style={{ display: 'flex', gap: '0.65rem', alignItems: 'center' }} role="status" aria-live="polite">
      <Avatar>✨</Avatar>
      <div
        style={{
          background: 'var(--bp-surface)',
          border: '1px solid var(--bp-border)',
          borderRadius: '4px 16px 16px 16px',
          padding: '0.75rem 1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
        }}
      >
        <span style={{ display: 'inline-flex', gap: '4px' }}>
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: 'var(--bp-purple-light)',
                animation: `bp-pulse 1.2s ${i * 0.2}s infinite`,
              }}
            />
          ))}
        </span>
        <span style={{ fontSize: '0.82rem', color: 'var(--bp-text-muted)' }}>
          Analysing your business data… investigations can take up to a minute.
        </span>
      </div>
    </div>
  );
}
