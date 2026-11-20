import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { Button } from '../../components/common/Button';
import { useApp } from '../../context/AppContext';
import { useChat } from '../../context/ChatContext';
import { MessageBubble, TypingIndicator } from './MessageBubble';

const SUGGESTED_QUESTIONS = [
  'Why did revenue decline?',
  'Which product has the lowest profit margin?',
  'What is happening with mobile conversions?',
  'What are the biggest problems in my business?',
];

export function AIAssistantView() {
  const { messages, isLoading, sendMessage, newConversation } = useChat();
  const { pendingChatPrompt, clearPendingChatPrompt } = useApp();
  const [draft, setDraft] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // A question picked on the Home dashboard is sent once when this page opens.
  useEffect(() => {
    if (pendingChatPrompt) {
      clearPendingChatPrompt();
      void sendMessage(pendingChatPrompt);
    }
  }, [pendingChatPrompt, clearPendingChatPrompt, sendMessage]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, isLoading]);

  const submit = () => {
    const text = draft.trim();
    if (!text || isLoading) return;
    setDraft('');
    void sendMessage(text);
    inputRef.current?.focus();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  const empty = messages.length === 0 && !isLoading;

  return (
    <div
      className="bp-chat-page"
      style={{
        maxWidth: '980px',
        margin: '0 auto',
        padding: '1rem 1.25rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        minHeight: 0,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
        <div
          style={{
            width: '40px',
            height: '40px',
            borderRadius: '12px',
            background: 'var(--bp-gradient-ai)',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.2rem',
          }}
        >
          ✨
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h2 style={{ fontSize: '1.1rem' }}>BizPulse AI</h2>
          <div style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)' }}>
            Answers come from your analytics engine. Facts and possible explanations are kept separate.
          </div>
        </div>
        <Button variant="secondary" size="sm" disabled={messages.length === 0} onClick={newConversation}>
          + New conversation
        </Button>
      </div>

      {/* Conversation */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          background: 'var(--bp-surface-alt)',
          border: '1px solid var(--bp-border)',
          borderRadius: 'var(--bp-radius-lg)',
          padding: '1.1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
        aria-label="Conversation"
      >
        {empty ? (
          <div
            style={{
              margin: 'auto',
              textAlign: 'center',
              maxWidth: '560px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '0.85rem',
            }}
          >
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '18px',
                background: 'var(--bp-gradient-ai)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.8rem',
                boxShadow: '0 4px 16px rgba(88,24,240,0.3)',
              }}
            >
              ✨
            </div>
            <h3 style={{ fontSize: '1.2rem' }}>How can I help with your business today?</h3>
            <p style={{ fontSize: '0.9rem', color: 'var(--bp-text-muted)', lineHeight: 1.6 }}>
              Ask about revenue, profit margins, website conversion or detected problems. I can investigate
              why something happened and draft actions for your approval.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', justifyContent: 'center' }}>
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => void sendMessage(q)}
                  style={{
                    background: 'var(--bp-surface)',
                    border: '1px solid var(--bp-info-border)',
                    color: 'var(--bp-purple)',
                    borderRadius: '9999px',
                    padding: '0.45rem 0.9rem',
                    fontSize: '0.84rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
            {isLoading && <TypingIndicator />}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Composer */}
      <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'flex-end' }}>
        <textarea
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          rows={2}
          maxLength={2000}
          placeholder="Ask BizPulse about your business…  (Enter to send, Shift+Enter for a new line)"
          aria-label="Message BizPulse AI"
          style={{ resize: 'none', flex: 1, minHeight: '48px', maxHeight: '140px', lineHeight: 1.5 }}
        />
        <Button variant="primary" size="lg" loading={isLoading} disabled={!draft.trim()} onClick={submit}>
          Send
        </Button>
      </div>
    </div>
  );
}
