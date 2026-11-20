import { Button } from '../../components/common/Button';
import { useApp } from '../../context/AppContext';

const SUGGESTED_QUESTIONS = [
  'Why did revenue decline?',
  'Which product has the lowest profit margin?',
  'What is happening with mobile conversions?',
  'What are the biggest problems in my business?',
];

/** Entry point only — the chatbot itself lives on the AI Assistant page. */
export function AssistantSection() {
  const { setView, askAssistant } = useApp();

  return (
    <section
      aria-label="BizPulse AI Assistant"
      style={{
        background: 'var(--bp-gradient-ai-soft)',
        border: '1px solid var(--bp-info-border)',
        borderRadius: 'var(--bp-radius-xl)',
        padding: '1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        boxShadow: 'var(--bp-shadow)',
      }}
    >
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <div
          style={{
            width: '52px',
            height: '52px',
            borderRadius: '14px',
            background: 'var(--bp-gradient-ai)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.5rem',
            boxShadow: '0 4px 14px rgba(88,24,240,0.3)',
            flexShrink: 0,
          }}
        >
          ✨
        </div>
        <div style={{ flex: '1 1 260px', minWidth: 0 }}>
          <h3 style={{ fontSize: '1.15rem', color: 'var(--bp-navy)' }}>BizPulse AI</h3>
          <p style={{ fontSize: '0.88rem', color: 'var(--bp-text-muted)', marginTop: '0.15rem' }}>
            Ask about your business in plain language. BizPulse investigates using your real
            analytics data and tells you what happened, why, and what to do next.
          </p>
        </div>
        <Button variant="primary" size="md" onClick={() => setView('assistant')}>
          Open AI Assistant →
        </Button>
      </div>

      <div>
        <div
          style={{
            fontSize: '0.72rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.07em',
            color: 'var(--bp-purple)',
            marginBottom: '0.5rem',
          }}
        >
          Suggested questions
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => askAssistant(q)}
              style={{
                background: 'var(--bp-surface)',
                border: '1px solid var(--bp-info-border)',
                borderRadius: '9999px',
                padding: '0.4rem 0.85rem',
                fontSize: '0.82rem',
                fontWeight: 500,
                color: 'var(--bp-purple)',
                cursor: 'pointer',
              }}
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
