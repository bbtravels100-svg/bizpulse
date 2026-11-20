import { useEffect, useState, useCallback } from 'react';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { apiGet, apiPost } from '../../api/client';
import type {
  VerificationHistoryResponse,
  VerificationRunResponse,
  ReopenResponse,
  BadgeVariant,
} from '../../types';

interface VerificationDetailModalProps {
  actionId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onReopenSuccess?: () => void;
}

function outcomeVariant(out: string): BadgeVariant {
  switch (out?.toLowerCase()) {
    case 'improved':
      return 'success';
    case 'not improved':
      return 'neutral';
    case 'deteriorated':
      return 'danger';
    case 'inconclusive':
    case 'insufficient data':
    default:
      return 'warning';
  }
}

function confidenceVariant(conf: string): BadgeVariant {
  switch (conf?.toLowerCase()) {
    case 'high':
      return 'success';
    case 'medium':
      return 'warning';
    case 'low':
      return 'neutral';
    case 'unsubstantiated':
    default:
      return 'danger';
  }
}

export function VerificationDetailModal({
  actionId,
  isOpen,
  onClose,
  onReopenSuccess,
}: VerificationDetailModalProps) {
  const [data, setData] = useState<VerificationHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Selected run tab (defaults to latest)
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  // Reopen form state
  const [isReopening, setIsReopening] = useState(false);
  const [reopenReason, setReopenReason] = useState('');
  const [reopenRequestedBy, setReopenRequestedBy] = useState('QA / Verification Lead');
  const [reopenSuccessMsg, setReopenSuccessMsg] = useState<string | null>(null);
  const [reopenError, setReopenError] = useState<string | null>(null);

  // Add note state
  const [noteText, setNoteText] = useState('');
  const [noteAuthor, setNoteAuthor] = useState('QA Lead');
  const [submittingNote, setSubmittingNote] = useState(false);

  const fetchHistory = useCallback(async () => {
    if (!actionId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<VerificationHistoryResponse>(`/api/verification/history/${actionId}`);
      setData(res);
      if (res.verification_runs.length > 0) {
        setSelectedRunId(res.verification_runs[res.verification_runs.length - 1].id);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not fetch verification details');
    } finally {
      setLoading(false);
    }
  }, [actionId]);

  useEffect(() => {
    if (isOpen && actionId) {
      void fetchHistory();
      setReopenSuccessMsg(null);
      setReopenError(null);
      setReopenReason('');
    } else {
      setData(null);
    }
  }, [isOpen, actionId, fetchHistory]);

  const handleAddNote = async () => {
    if (!actionId || !selectedRunId || !noteText.trim()) return;
    setSubmittingNote(true);
    try {
      await apiPost('/api/verification/notes', {
        verification_id: selectedRunId,
        action_id: actionId,
        note: noteText.trim(),
        author: noteAuthor.trim() || 'QA Lead',
      });
      setNoteText('');
      void fetchHistory();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to add verification note');
    } finally {
      setSubmittingNote(false);
    }
  };

  const handleReopen = async () => {
    if (!actionId) return;
    if (reopenReason.trim().length < 5) {
      setReopenError('Reopening justification must be at least 5 characters long.');
      return;
    }
    setIsReopening(true);
    setReopenError(null);
    try {
      const res = await apiPost<ReopenResponse>('/api/verification/reopen', {
        action_id: actionId,
        reason: reopenReason.trim(),
        requested_by: reopenRequestedBy.trim() || 'QA Lead',
      });
      setReopenSuccessMsg(res.message || `Action reopened successfully. Created secondary proposal ${res.new_action_id}.`);
      void fetchHistory();
      if (onReopenSuccess) onReopenSuccess();
    } catch (err: unknown) {
      setReopenError(err instanceof Error ? err.message : 'Reopen request failed.');
    } finally {
      setIsReopening(false);
    }
  };

  if (!isOpen || !actionId) return null;

  const runs = data?.verification_runs || [];
  const activeRun: VerificationRunResponse | undefined = runs.find((r) => r.id === selectedRunId) || runs[runs.length - 1];
  const baseline = data?.baseline;

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
          maxWidth: '850px',
          width: '100%',
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          border: '1px solid var(--bp-border)',
          overflow: 'hidden',
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
            flexWrap: 'wrap',
            gap: '0.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '1.2rem' }}>⚖️</span>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, color: 'var(--bp-text)' }}>
              Before-and-After Verification Analysis
            </h3>
            <code
              style={{
                fontSize: '0.82rem',
                fontWeight: 700,
                background: 'var(--bp-purple-pale)',
                color: 'var(--bp-purple)',
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
              }}
            >
              {actionId}
            </code>
            {data && (
              <Badge variant={data.current_resolution_status === 'Resolved' ? 'success' : 'warning'}>
                {data.current_resolution_status}
              </Badge>
            )}
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
        <div style={{ padding: '1.5rem', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {loading ? (
            <LoadingSpinner label="Loading verification history and metrics…" />
          ) : error ? (
            <div style={{ color: 'var(--bp-danger)', fontSize: '0.9rem', padding: '1rem', textAlign: 'center' }}>
              ⚠️ {error}
            </div>
          ) : data && baseline ? (
            <>
              {/* Runs Selector Tab Bar */}
              {runs.length > 1 && (
                <div style={{ display: 'flex', gap: '0.4rem', borderBottom: '1px solid var(--bp-border)', paddingBottom: '0.5rem' }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)', alignSelf: 'center', marginRight: '0.25rem' }}>
                    Evaluation Runs:
                  </span>
                  {runs.map((r, i) => (
                    <button
                      key={r.id}
                      type="button"
                      onClick={() => setSelectedRunId(r.id)}
                      style={{
                        padding: '0.35rem 0.7rem',
                        fontSize: '0.78rem',
                        borderRadius: 'var(--bp-radius)',
                        border: '1px solid var(--bp-border)',
                        background: selectedRunId === r.id ? 'var(--bp-purple)' : 'var(--bp-surface)',
                        color: selectedRunId === r.id ? '#fff' : 'var(--bp-text)',
                        cursor: 'pointer',
                        fontWeight: selectedRunId === r.id ? 600 : 400,
                      }}
                    >
                      Run #{i + 1} ({r.verification_stage}) — {r.outcome}
                    </button>
                  ))}
                </div>
              )}

              {activeRun ? (
                <>
                  {/* Before-and-After Comparison Card */}
                  <div
                    style={{
                      border: '1px solid var(--bp-border)',
                      borderRadius: 'var(--bp-radius-lg)',
                      padding: '1.25rem',
                      background: 'var(--bp-surface)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                      <strong style={{ fontSize: '0.95rem', color: 'var(--bp-text)' }}>
                        📈 Quantitative Comparison ({baseline.metric_name})
                      </strong>
                      <div style={{ display: 'flex', gap: '0.4rem' }}>
                        <Badge variant={outcomeVariant(activeRun.outcome)}>
                          Outcome: {activeRun.outcome.toUpperCase()}
                        </Badge>
                        <Badge variant={activeRun.target_met ? 'success' : 'danger'}>
                          {activeRun.target_met ? 'Target Met ✓' : 'Target Unmet ✗'}
                        </Badge>
                      </div>
                    </div>

                    {/* Side-by-Side Comparison Grid */}
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: '1rem',
                        marginBottom: '1rem',
                      }}
                    >
                      {/* Before (Baseline) */}
                      <div
                        style={{
                          background: 'var(--bp-surface-alt)',
                          border: '1px solid var(--bp-border)',
                          borderRadius: 'var(--bp-radius)',
                          padding: '1rem',
                        }}
                      >
                        <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--bp-text-muted)', fontWeight: 600 }}>
                          Original Baseline (Before Action)
                        </div>
                        <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--bp-danger)', marginTop: '0.2rem' }}>
                          {baseline.baseline_value}
                        </div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--bp-text-muted)', marginTop: '0.3rem' }}>
                          Period: {baseline.baseline_period}
                        </div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--bp-purple)', marginTop: '0.2rem', fontWeight: 600 }}>
                          Target: {baseline.target_value} ({baseline.comparison_direction === 'increase' ? 'Higher is better' : 'Lower is better'})
                        </div>
                      </div>

                      {/* After (Current Verified) */}
                      <div
                        style={{
                          background: 'var(--bp-surface-alt)',
                          border: '1px solid var(--bp-border)',
                          borderRadius: 'var(--bp-radius)',
                          padding: '1rem',
                        }}
                      >
                        <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--bp-text-muted)', fontWeight: 600 }}>
                          Current Value (After Action)
                        </div>
                        <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--bp-success)', marginTop: '0.2rem' }}>
                          {activeRun.comparison.current_value}
                        </div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--bp-text-muted)', marginTop: '0.3rem' }}>
                          Period: {activeRun.evaluation_period}
                        </div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--bp-text-muted)', marginTop: '0.2rem' }}>
                          Source: {activeRun.data_source}
                        </div>
                      </div>

                      {/* Computed Movement */}
                      <div
                        style={{
                          background: 'var(--bp-surface-alt)',
                          border: '1px solid var(--bp-border)',
                          borderRadius: 'var(--bp-radius)',
                          padding: '1rem',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'center',
                        }}
                      >
                        <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--bp-text-muted)', fontWeight: 600 }}>
                          Computed Net Movement
                        </div>
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginTop: '0.2rem' }}>
                          <span
                            style={{
                              fontSize: '1.4rem',
                              fontWeight: 700,
                              color: activeRun.comparison.absolute_change >= 0 ? 'var(--bp-success)' : 'var(--bp-danger)',
                            }}
                          >
                            {activeRun.comparison.absolute_change > 0
                              ? `+${activeRun.comparison.absolute_change}`
                              : activeRun.comparison.absolute_change}
                          </span>
                          <span
                            style={{
                              fontSize: '0.95rem',
                              fontWeight: 600,
                              color: activeRun.comparison.percentage_change >= 0 ? 'var(--bp-success)' : 'var(--bp-danger)',
                            }}
                          >
                            ({activeRun.comparison.percentage_change > 0
                              ? `+${activeRun.comparison.percentage_change}%`
                              : `${activeRun.comparison.percentage_change}%`})
                          </span>
                        </div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--bp-text-muted)', marginTop: '0.4rem' }}>
                          Calculation: Deterministic Python subtraction & ratio arithmetic
                        </div>
                      </div>
                    </div>

                    {/* Summary string banner */}
                    <div
                      style={{
                        background: 'var(--bp-surface-alt)',
                        border: '1px solid var(--bp-border)',
                        borderRadius: 'var(--bp-radius)',
                        padding: '0.65rem 0.85rem',
                        fontSize: '0.8rem',
                        color: 'var(--bp-text)',
                      }}
                    >
                      {activeRun.comparison.calculation_summary}
                    </div>
                  </div>

                  {/* Gemini AI Follow-Up Interpretation */}
                  {activeRun.gemini_analysis && (
                    <div
                      style={{
                        background: 'linear-gradient(135deg, rgba(88,24,240,0.06), rgba(144,80,248,0.02))',
                        border: '1px solid var(--bp-info-border)',
                        borderRadius: 'var(--bp-radius-lg)',
                        padding: '1.25rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.85rem',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span style={{ fontSize: '1.1rem' }}>✨</span>
                          <strong style={{ fontSize: '0.95rem', color: 'var(--bp-purple)' }}>
                            Gemini AI Follow-Up Interpretation
                          </strong>
                        </div>
                        <Badge variant={confidenceVariant(activeRun.gemini_analysis.causal_attribution_confidence)}>
                          Causal Attribution: {activeRun.gemini_analysis.causal_attribution_confidence.toUpperCase()}
                        </Badge>
                      </div>

                      <div style={{ fontSize: '0.86rem', color: 'var(--bp-text)', lineHeight: 1.55 }}>
                        <strong>What Changed:</strong> {activeRun.gemini_analysis.what_changed}
                      </div>

                      {/* Plausible Explanations */}
                      {activeRun.gemini_analysis.possible_explanations.length > 0 && (
                        <div>
                          <strong style={{ fontSize: '0.78rem', textTransform: 'uppercase', color: 'var(--bp-text-muted)' }}>
                            Plausible Causal Explanations:
                          </strong>
                          <ul style={{ margin: '0.35rem 0 0 1.25rem', padding: 0, fontSize: '0.84rem', color: 'var(--bp-text)' }}>
                            {activeRun.gemini_analysis.possible_explanations.map((exp, idx) => (
                              <li key={idx} style={{ marginBottom: '0.25rem', lineHeight: 1.5 }}>
                                {exp}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Recommended Next Steps */}
                      {activeRun.gemini_analysis.recommended_next_steps.length > 0 && (
                        <div>
                          <strong style={{ fontSize: '0.78rem', textTransform: 'uppercase', color: 'var(--bp-purple)' }}>
                            Recommended Next Business Steps:
                          </strong>
                          <ul style={{ margin: '0.35rem 0 0 1.25rem', padding: 0, fontSize: '0.84rem', color: 'var(--bp-text)' }}>
                            {activeRun.gemini_analysis.recommended_next_steps.map((st, idx) => (
                              <li key={idx} style={{ marginBottom: '0.25rem', lineHeight: 1.5 }}>
                                {st}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div style={{ fontSize: '0.74rem', color: 'var(--bp-text-muted)', borderTop: '1px solid var(--bp-border)', paddingTop: '0.5rem' }}>
                        🔒 <em>Verification Principle: Completing a business task does not equal solving the underlying business problem until telemetry verifies that the target was achieved.</em>
                      </div>
                    </div>
                  )}

                  {/* Reopening Workflow Section (if problem is unresolved) */}
                  {activeRun.needs_reopening && (
                    <div
                      style={{
                        background: 'var(--bp-danger-pale)',
                        border: '1px solid var(--bp-danger)',
                        borderRadius: 'var(--bp-radius-lg)',
                        padding: '1.25rem',
                      }}
                    >
                      <h4 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--bp-danger)', margin: '0 0 0.4rem 0' }}>
                        ⚠️ Action Unsuccessful: Problem Not Fully Resolved
                      </h4>
                      <p style={{ fontSize: '0.82rem', color: 'var(--bp-text)', margin: '0 0 0.85rem 0' }}>
                        The verified telemetry indicates the target threshold was not met. Reopen the investigation to
                        dispatch secondary remediation proposals to the Action Centre.
                      </p>

                      {reopenSuccessMsg && (
                        <div style={{ background: 'var(--bp-success-pale)', color: 'var(--bp-success)', padding: '0.5rem 0.75rem', borderRadius: 'var(--bp-radius)', fontSize: '0.82rem', marginBottom: '0.75rem' }}>
                          ✓ {reopenSuccessMsg}
                        </div>
                      )}

                      {reopenError && (
                        <div style={{ color: 'var(--bp-danger)', fontSize: '0.82rem', marginBottom: '0.75rem' }}>
                          ⚠️ {reopenError}
                        </div>
                      )}

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        <textarea
                          rows={2}
                          placeholder="State the justification reason for reopening (e.g. Telemetry indicates mobile payment rate remains under 60%)..."
                          value={reopenReason}
                          onChange={(e) => setReopenReason(e.target.value)}
                          style={{
                            width: '100%',
                            padding: '0.5rem',
                            borderRadius: 'var(--bp-radius)',
                            border: '1px solid var(--bp-border)',
                            fontSize: '0.82rem',
                            fontFamily: 'inherit',
                          }}
                        />
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <input
                            type="text"
                            placeholder="Requested by (e.g. QA Lead)"
                            value={reopenRequestedBy}
                            onChange={(e) => setReopenRequestedBy(e.target.value)}
                            style={{
                              padding: '0.35rem 0.5rem',
                              fontSize: '0.78rem',
                              borderRadius: 'var(--bp-radius)',
                              border: '1px solid var(--bp-border)',
                              width: '200px',
                            }}
                          />
                          <Button
                            variant="danger"
                            size="sm"
                            loading={isReopening}
                            disabled={reopenReason.trim().length < 5}
                            onClick={() => void handleReopen()}
                          >
                            Reopen Investigation 🔄
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Diagnostic Notes Thread */}
                  <div>
                    <h4 style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--bp-text)', marginBottom: '0.5rem' }}>
                      💬 Verification Diagnostic Notes ({data.notes.length})
                    </h4>
                    {data.notes.length > 0 && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginBottom: '0.75rem' }}>
                        {data.notes.map((n) => (
                          <div
                            key={n.id}
                            style={{
                              background: 'var(--bp-surface-alt)',
                              borderRadius: 'var(--bp-radius)',
                              padding: '0.6rem 0.8rem',
                              fontSize: '0.8rem',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                              <strong style={{ color: 'var(--bp-purple)' }}>{n.author}</strong>
                              <span style={{ fontSize: '0.72rem', color: 'var(--bp-text-muted)' }}>
                                {new Date(n.created_at).toLocaleString()}
                              </span>
                            </div>
                            <p style={{ margin: 0, color: 'var(--bp-text)' }}>{n.note}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <input
                        type="text"
                        placeholder="Author"
                        value={noteAuthor}
                        onChange={(e) => setNoteAuthor(e.target.value)}
                        style={{
                          width: '130px',
                          padding: '0.4rem 0.6rem',
                          borderRadius: 'var(--bp-radius)',
                          border: '1px solid var(--bp-border)',
                          fontSize: '0.82rem',
                        }}
                      />
                      <input
                        type="text"
                        placeholder="Append diagnostic note or observation…"
                        value={noteText}
                        onChange={(e) => setNoteText(e.target.value)}
                        style={{
                          flex: 1,
                          minWidth: '200px',
                          padding: '0.4rem 0.6rem',
                          borderRadius: 'var(--bp-radius)',
                          border: '1px solid var(--bp-border)',
                          fontSize: '0.82rem',
                        }}
                      />
                      <Button
                        variant="secondary"
                        size="sm"
                        loading={submittingNote}
                        disabled={!noteText.trim()}
                        onClick={() => void handleAddNote()}
                      >
                        Add Note
                      </Button>
                    </div>
                  </div>
                </>
              ) : (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--bp-text-muted)' }}>
                  A baseline has been captured, but no verification run has been executed yet. Click &apos;Run
                  Verification&apos; to evaluate metric movement.
                </div>
              )}
            </>
          ) : (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--bp-text-muted)' }}>
              No baseline or verification record found for this action.
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '0.85rem 1.5rem',
            borderTop: '1px solid var(--bp-border)',
            background: 'var(--bp-surface-alt)',
            display: 'flex',
            justifyContent: 'flex-end',
          }}
        >
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
