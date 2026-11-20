import React, { useState } from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { AiPreferences } from '../../types/settings';

const STORAGE_KEY = 'bizpulse_ai_preferences';

const DEFAULT_PREFERENCES: AiPreferences = {
  explanationDetail: 'concise',
  autoSuggestActions: true,
  includeEvidence: true,
};

interface Props {
  configuredModel?: string;
}

export const AiPreferencesCard: React.FC<Props> = ({ configuredModel = 'gemini-3.1-flash-lite' }) => {
  const [preferences, setPreferences] = useState<AiPreferences>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {
      /* ignore */
    }
    return DEFAULT_PREFERENCES;
  });

  const [savedNotice, setSavedNotice] = useState(false);

  const handleSave = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
      setSavedNotice(true);
      setTimeout(() => setSavedNotice(false), 3000);
    } catch {
      /* ignore */
    }
  };

  return (
    <Card
      header={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem' }}>🤖</span>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--bp-navy)', margin: 0 }}>
              AI Assistant Preferences
            </h3>
          </div>
          <Badge variant="info">Active Tuning</Badge>
        </div>
      }
    >
      <p style={{ fontSize: '0.825rem', color: 'var(--bp-text-muted)', margin: '0 0 1.25rem 0' }}>
        Configure the response depth, evidence linkage, and reasoning behaviour of the BizPulse conversational assistant.
      </p>

      {/* Configured Model Info */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.85rem 1rem',
          background: '#FAF9FF',
          border: '1px solid var(--bp-border)',
          borderRadius: '8px',
          marginBottom: '1.25rem',
        }}
      >
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--bp-text-muted)', textTransform: 'uppercase' }}>
            Active Foundation Model
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.2rem' }}>
            <span style={{ fontWeight: 700, color: 'var(--bp-navy)', fontSize: '0.95rem' }}>
              Google Gemini
            </span>
            <code
              style={{
                fontSize: '0.78rem',
                padding: '0.15rem 0.45rem',
                background: 'var(--bp-light-purple)',
                color: 'var(--bp-purple)',
                borderRadius: '4px',
                fontWeight: 600,
              }}
            >
              {configuredModel}
            </code>
          </div>
        </div>
        <span
          style={{
            fontSize: '0.75rem',
            color: 'var(--bp-text-muted)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
          }}
        >
          🔒 Server-Managed Environment
        </span>
      </div>

      {/* Preferences Form */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {/* Explanation Detail */}
        <div>
          <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--bp-navy)', marginBottom: '0.35rem' }}>
            Explanation Detail Level
          </label>
          <p style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)', margin: '0 0 0.5rem 0' }}>
            Choose whether assistant replies focus on brief executive metrics or comprehensive diagnostic analysis.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <label
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem',
                padding: '0.75rem 1rem',
                border: preferences.explanationDetail === 'concise' ? '2px solid var(--bp-purple)' : '1px solid var(--bp-border)',
                background: preferences.explanationDetail === 'concise' ? '#FAF9FF' : '#FFFFFF',
                borderRadius: '8px',
                cursor: 'pointer',
              }}
            >
              <input
                type="radio"
                name="detailLevel"
                checked={preferences.explanationDetail === 'concise'}
                onChange={() => setPreferences({ ...preferences, explanationDetail: 'concise' })}
              />
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--bp-navy)' }}>
                  Concise (Executive)
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--bp-text-muted)' }}>
                  Bullet points, key deltas, and actionable findings.
                </div>
              </div>
            </label>

            <label
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem',
                padding: '0.75rem 1rem',
                border: preferences.explanationDetail === 'detailed' ? '2px solid var(--bp-purple)' : '1px solid var(--bp-border)',
                background: preferences.explanationDetail === 'detailed' ? '#FAF9FF' : '#FFFFFF',
                borderRadius: '8px',
                cursor: 'pointer',
              }}
            >
              <input
                type="radio"
                name="detailLevel"
                checked={preferences.explanationDetail === 'detailed'}
                onChange={() => setPreferences({ ...preferences, explanationDetail: 'detailed' })}
              />
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--bp-navy)' }}>
                  Detailed (Analytical)
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--bp-text-muted)' }}>
                  In-depth causal reasoning, multi-system correlations, and step-by-step context.
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Action Proposal Suggestions Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem 0', borderTop: '1px solid var(--bp-border)' }}>
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--bp-navy)' }}>
              Automated Action Proposal Drafting
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)' }}>
              Enable AI assistant to formulate ready-to-approve operational proposals directly within conversation.
            </div>
          </div>
          <input
            type="checkbox"
            checked={preferences.autoSuggestActions}
            onChange={(e) => setPreferences({ ...preferences, autoSuggestActions: e.target.checked })}
            style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: 'var(--bp-purple)' }}
          />
        </div>

        {/* Evidence Citations Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem 0', borderTop: '1px solid var(--bp-border)' }}>
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--bp-navy)' }}>
              Strict Telemetry Evidence Citations
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)' }}>
              Require AI answers to explicitly cite underlying CSV files and metrics.
            </div>
          </div>
          <input
            type="checkbox"
            checked={preferences.includeEvidence}
            onChange={(e) => setPreferences({ ...preferences, includeEvidence: e.target.checked })}
            style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: 'var(--bp-purple)' }}
          />
        </div>
      </div>

      {/* Save Button & Feedback */}
      <div style={{ marginTop: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <Button size="sm" variant="primary" onClick={handleSave}>
          Save AI Preferences
        </Button>
        {savedNotice && (
          <span style={{ fontSize: '0.8rem', color: '#16A34A', fontWeight: 600 }}>
            ✓ Preferences saved locally
          </span>
        )}
      </div>
    </Card>
  );
};
