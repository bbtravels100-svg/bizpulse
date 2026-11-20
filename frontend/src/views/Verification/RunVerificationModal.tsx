import { useState } from 'react';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { apiPost } from '../../api/client';
import type {
  ActionVerificationSummary,
  VerificationRunResponse,
  VerificationStage,
  VerificationTriggerRequest,
} from '../../types';

interface RunVerificationModalProps {
  actionSummary: ActionVerificationSummary | null;
  isOpen: boolean;
  onClose: () => void;
  onRunComplete: (result: VerificationRunResponse) => void;
}

export function RunVerificationModal({
  actionSummary,
  isOpen,
  onClose,
  onRunComplete,
}: RunVerificationModalProps) {
  const [stage, setStage] = useState<VerificationStage>('initial');
  const [evaluationPeriod, setEvaluationPeriod] = useState('Post-Fix 24-Hour Telemetry');
  const [inputMode, setInputMode] = useState<'measured' | 'scenario'>('measured');
  const [currentValue, setCurrentValue] = useState<string>('75.2');
  const [scenario, setScenario] = useState<'improved' | 'not_improved' | 'deteriorated' | 'insufficient_data'>('improved');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !actionSummary) return null;

  const baseline = actionSummary.baseline;

  const handleStageChange = (newStage: VerificationStage) => {
    setStage(newStage);
    switch (newStage) {
      case 'initial':
        setEvaluationPeriod('Post-Fix 24-Hour Telemetry');
        break;
      case 'follow_up':
        setEvaluationPeriod('Post-Fix 7-Day Sustained Telemetry');
        break;
      case 'final':
        setEvaluationPeriod('Post-Fix 30-Day Permanent Audit');
        break;
      case 'manual':
        setEvaluationPeriod('On-Demand Diagnostic Probe');
        break;
    }
  };

  const handleExecute = async () => {
    setLoading(true);
    setError(null);

    const payload: VerificationTriggerRequest = {
      action_id: actionSummary.actionId,
      stage,
      evaluation_period: evaluationPeriod.trim() || undefined,
    };

    if (inputMode === 'measured') {
      const val = parseFloat(currentValue);
      if (isNaN(val)) {
        setError('Please enter a valid numerical value for current telemetry.');
        setLoading(false);
        return;
      }
      payload.current_value = val;
    } else {
      payload.simulated_data_scenario = scenario;
    }

    try {
      const result = await apiPost<VerificationRunResponse>('/api/verification/verify', payload);
      onRunComplete(result);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Verification run failed.');
    } finally {
      setLoading(false);
    }
  };

  // Live preview calculations for user entry
  const parsedVal = parseFloat(currentValue);
  const hasValidPreview = inputMode === 'measured' && !isNaN(parsedVal) && baseline;
  let previewAbs = 0;
  let previewPct = 0;
  let previewTargetMet = false;

  if (hasValidPreview && baseline) {
    previewAbs = parsedVal - baseline.baseline_value;
    previewPct = baseline.baseline_value !== 0 ? (previewAbs / Math.abs(baseline.baseline_value)) * 100 : 0;
    previewTargetMet =
      baseline.comparison_direction === 'increase'
        ? parsedVal >= baseline.target_value
        : parsedVal <= baseline.target_value;
  }

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(8, 15, 32, 0.65)',
        backdropFilter: 'blur(3px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--bp-surface)',
          borderRadius: 'var(--bp-radius-lg)',
          boxShadow: '0 20px 40px rgba(0,0,0,0.25)',
          maxWidth: '580px',
          width: '100%',
          border: '1px solid var(--bp-border)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '90vh',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--bp-border)',
            background: 'var(--bp-surface-alt)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, color: 'var(--bp-text)' }}>
              Execute Follow-Up Verification
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--bp-text-muted)' }}>
              Task: <code>{actionSummary.actionId}</code> ({actionSummary.responsibleDepartment})
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '1.3rem',
              cursor: 'pointer',
              color: 'var(--bp-text-muted)',
            }}
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '1.5rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {error && (
            <div
              style={{
                background: 'var(--bp-danger-pale)',
                border: '1px solid var(--bp-danger)',
                borderRadius: 'var(--bp-radius)',
                padding: '0.75rem 1rem',
                color: 'var(--bp-danger)',
                fontSize: '0.82rem',
              }}
            >
              ⚠️ {error}
            </div>
          )}

          {/* Baseline Context */}
          {baseline && (
            <div
              style={{
                background: 'var(--bp-surface-alt)',
                border: '1px solid var(--bp-border)',
                borderRadius: 'var(--bp-radius)',
                padding: '0.85rem 1rem',
                fontSize: '0.82rem',
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                gap: '0.5rem',
              }}
            >
              <div>
                <span style={{ color: 'var(--bp-text-muted)', display: 'block', fontSize: '0.72rem', textTransform: 'uppercase' }}>
                  Metric Name
                </span>
                <strong style={{ color: 'var(--bp-purple)' }}>{baseline.metric_name}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--bp-text-muted)', display: 'block', fontSize: '0.72rem', textTransform: 'uppercase' }}>
                  Baseline Value
                </span>
                <strong style={{ color: 'var(--bp-danger)' }}>{baseline.baseline_value}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--bp-text-muted)', display: 'block', fontSize: '0.72rem', textTransform: 'uppercase' }}>
                  Target Benchmark
                </span>
                <strong style={{ color: 'var(--bp-success)' }}>{baseline.target_value}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--bp-text-muted)', display: 'block', fontSize: '0.72rem', textTransform: 'uppercase' }}>
                  Direction
                </span>
                <span>{baseline.comparison_direction === 'increase' ? 'Higher is better' : 'Lower is better'}</span>
              </div>
            </div>
          )}

          {/* Verification Stage */}
          <div>
            <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text)', display: 'block', marginBottom: '0.35rem' }}>
              Verification Evaluation Stage:
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '0.4rem' }}>
              {(['initial', 'follow_up', 'final', 'manual'] as const).map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => handleStageChange(st)}
                  style={{
                    padding: '0.45rem 0.5rem',
                    fontSize: '0.78rem',
                    borderRadius: 'var(--bp-radius)',
                    border: '1px solid var(--bp-border)',
                    background: stage === st ? 'var(--bp-purple)' : 'var(--bp-surface)',
                    color: stage === st ? '#fff' : 'var(--bp-text)',
                    cursor: 'pointer',
                    fontWeight: stage === st ? 600 : 400,
                  }}
                >
                  {st === 'initial' ? 'Initial (24h)' : st === 'follow_up' ? 'Follow-Up (7d)' : st === 'final' ? 'Final (30d)' : 'Manual Probe'}
                </button>
              ))}
            </div>
          </div>

          {/* Evaluation Period Label */}
          <div>
            <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text)', display: 'block', marginBottom: '0.25rem' }}>
              Evaluation Measurement Window:
            </label>
            <input
              type="text"
              value={evaluationPeriod}
              onChange={(e) => setEvaluationPeriod(e.target.value)}
              style={{
                width: '100%',
                padding: '0.45rem',
                borderRadius: 'var(--bp-radius)',
                border: '1px solid var(--bp-border)',
                fontSize: '0.85rem',
              }}
            />
          </div>

          {/* Mode Switcher */}
          <div>
            <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text)', display: 'block', marginBottom: '0.35rem' }}>
              Telemetry Input Method:
            </label>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <button
                type="button"
                onClick={() => setInputMode('measured')}
                style={{
                  flex: 1,
                  padding: '0.4rem',
                  fontSize: '0.8rem',
                  borderRadius: 'var(--bp-radius)',
                  border: '1px solid var(--bp-border)',
                  background: inputMode === 'measured' ? 'var(--bp-purple-pale)' : 'var(--bp-surface)',
                  color: inputMode === 'measured' ? 'var(--bp-purple)' : 'var(--bp-text-muted)',
                  fontWeight: inputMode === 'measured' ? 600 : 400,
                  cursor: 'pointer',
                }}
              >
                ✏️ Enter Measured Current Value
              </button>
              <button
                type="button"
                onClick={() => setInputMode('scenario')}
                style={{
                  flex: 1,
                  padding: '0.4rem',
                  fontSize: '0.8rem',
                  borderRadius: 'var(--bp-radius)',
                  border: '1px solid var(--bp-border)',
                  background: inputMode === 'scenario' ? 'var(--bp-purple-pale)' : 'var(--bp-surface)',
                  color: inputMode === 'scenario' ? 'var(--bp-purple)' : 'var(--bp-text-muted)',
                  fontWeight: inputMode === 'scenario' ? 600 : 400,
                  cursor: 'pointer',
                }}
              >
                🧪 Select Telemetry Scenario Probe
              </button>
            </div>

            {inputMode === 'measured' ? (
              <div>
                <label style={{ fontSize: '0.76rem', color: 'var(--bp-text-muted)', display: 'block', marginBottom: '0.25rem' }}>
                  Current Measured Metric Value:
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={currentValue}
                  onChange={(e) => setCurrentValue(e.target.value)}
                  placeholder="e.g. 75.2"
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    borderRadius: 'var(--bp-radius)',
                    border: '1px solid var(--bp-border)',
                    fontSize: '0.95rem',
                    fontWeight: 600,
                  }}
                />

                {hasValidPreview && (
                  <div
                    style={{
                      marginTop: '0.6rem',
                      background: 'var(--bp-surface-alt)',
                      borderRadius: 'var(--bp-radius)',
                      padding: '0.6rem 0.8rem',
                      fontSize: '0.78rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <span>
                      Δ Absolute: <strong>{previewAbs > 0 ? `+${previewAbs.toFixed(2)}` : previewAbs.toFixed(2)}</strong>
                    </span>
                    <span>
                      Δ Relative: <strong>{previewPct > 0 ? `+${previewPct.toFixed(1)}%` : `${previewPct.toFixed(1)}%`}</strong>
                    </span>
                    <Badge variant={previewTargetMet ? 'success' : 'danger'}>
                      {previewTargetMet ? 'Target Met ✓' : 'Target Unmet ✗'}
                    </Badge>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                {[
                  { id: 'improved', label: '📈 Improved', desc: 'Recovers past target' },
                  { id: 'not_improved', label: '➖ Not Improved', desc: 'Remains stagnant' },
                  { id: 'deteriorated', label: '📉 Deteriorated', desc: 'Drops further' },
                  { id: 'insufficient_data', label: '⚠️ Insufficient Data', desc: 'Missing telemetry' },
                ].map((sc) => (
                  <button
                    key={sc.id}
                    type="button"
                    onClick={() => setScenario(sc.id as any)}
                    style={{
                      padding: '0.6rem',
                      borderRadius: 'var(--bp-radius)',
                      border: scenario === sc.id ? '2px solid var(--bp-purple)' : '1px solid var(--bp-border)',
                      background: scenario === sc.id ? 'var(--bp-purple-pale)' : 'var(--bp-surface)',
                      textAlign: 'left',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--bp-text)' }}>{sc.label}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--bp-text-muted)' }}>{sc.desc}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div
            style={{
              fontSize: '0.76rem',
              color: 'var(--bp-text-muted)',
              borderTop: '1px solid var(--bp-border)',
              paddingTop: '0.5rem',
            }}
          >
            🔒 <em>Python engine strictly performs numerical subtraction and percentage math. Gemini will synthesize qualitative observations and causal confidence.</em>
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '1rem 1.5rem',
            borderTop: '1px solid var(--bp-border)',
            background: 'var(--bp-surface-alt)',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '0.5rem',
          }}
        >
          <Button variant="secondary" size="sm" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" loading={loading} onClick={() => void handleExecute()}>
            Run Verification 📊
          </Button>
        </div>
      </div>
    </div>
  );
}
