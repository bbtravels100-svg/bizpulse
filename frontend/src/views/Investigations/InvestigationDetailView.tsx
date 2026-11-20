import { useEffect, useState } from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { apiGet, apiPost } from '../../api/client';
import { useApp } from '../../context/AppContext';
import type {
  InvestigationResponse,
  BackendAction,
  ActionCreatePayload,
  BadgeVariant,
} from '../../types';

interface InvestigationDetailViewProps {
  investigation: InvestigationResponse;
  onBack: () => void;
  onReload?: () => void;
}

function confidenceVariant(conf: string): BadgeVariant {
  switch (conf.toLowerCase()) {
    case 'high':
      return 'success';
    case 'medium':
      return 'warning';
    case 'low':
      return 'neutral';
    default:
      return 'info';
  }
}

function actionStatusVariant(st: string): BadgeVariant {
  switch (st.toLowerCase()) {
    case 'approved':
      return 'info';
    case 'in progress':
      return 'warning';
    case 'completed':
      return 'success';
    case 'rejected':
      return 'danger';
    case 'overdue':
      return 'danger';
    case 'pending approval':
    default:
      return 'neutral';
  }
}

function priorityVariant(prio: string): BadgeVariant {
  switch (prio.toLowerCase()) {
    case 'critical':
      return 'danger';
    case 'high':
      return 'warning';
    case 'medium':
      return 'info';
    default:
      return 'neutral';
  }
}

export function InvestigationDetailView({
  investigation,
  onBack,
}: InvestigationDetailViewProps) {
  const { setView } = useApp();
  const [actions, setActions] = useState<BackendAction[]>([]);
  const [loadingActions, setLoadingActions] = useState(false);

  // Proposal modal/form state
  const [proposingAction, setProposingAction] = useState<string | null>(null);
  const [submittingProposal, setSubmittingProposal] = useState(false);
  const [proposalSuccess, setProposalSuccess] = useState<string | null>(null);
  const [proposalError, setProposalError] = useState<string | null>(null);

  // Form fields
  const [department, setDepartment] = useState(
    investigation.analysis.responsible_department.split('(')[0].trim() || 'Engineering'
  );
  const [ownerRole, setOwnerRole] = useState('Remediation Lead');
  const [priority, setPriority] = useState<'Critical' | 'High' | 'Medium' | 'Low'>('High');
  const [deadline, setDeadline] = useState(
    new Date(Date.now() + 5 * 86400000).toISOString().split('T')[0]
  );
  const [customActionText, setCustomActionText] = useState('');
  const [expectedOutcome, setExpectedOutcome] = useState(investigation.analysis.why_important);
  const [verificationCriteria, setVerificationCriteria] = useState(
    investigation.analysis.verification_steps.join('; ')
  );

  // Fetch actions already created for this investigation
  const fetchRelatedActions = async () => {
    setLoadingActions(true);
    try {
      // Query by investigation_id
      const res = await apiGet<BackendAction[]>(
        `/api/actions?investigation_id=${encodeURIComponent(investigation.investigation_id)}`
      );
      if (res && Array.isArray(res)) {
        setActions(res);
      }
    } catch {
      // If none found or error, fall back to empty
      setActions([]);
    } finally {
      setLoadingActions(false);
    }
  };

  useEffect(() => {
    void fetchRelatedActions();
  }, [investigation.investigation_id]);

  const handleOpenProposalForm = (recommendedAction: string) => {
    setCustomActionText(recommendedAction);
    setProposingAction(recommendedAction);
    setProposalSuccess(null);
    setProposalError(null);
  };

  const handleSubmitProposal = async () => {
    if (!customActionText.trim()) return;
    setSubmittingProposal(true);
    setProposalError(null);
    setProposalSuccess(null);

    const payload: ActionCreatePayload = {
      investigation_id: investigation.investigation_id,
      anomaly_id: investigation.facts.anomaly_id,
      problem_description: investigation.analysis.what_happened,
      recommended_action: customActionText.trim(),
      responsible_department: department.trim() || 'Cross-Functional',
      suggested_owner_role: ownerRole.trim() || 'Remediation Team',
      priority,
      suggested_deadline: deadline,
      expected_outcome: expectedOutcome.trim() || 'Remediate anomaly and recover performance.',
      verification_criteria:
        verificationCriteria.trim() || 'Verify metrics return to established baseline.',
    };

    try {
      const created = await apiPost<BackendAction>('/api/actions/propose', payload);
      setProposalSuccess(`Action proposal ${created.id} submitted in 'Pending Approval' status.`);
      setProposingAction(null);
      void fetchRelatedActions();
    } catch (err: unknown) {
      setProposalError(err instanceof Error ? err.message : 'Failed to create action proposal.');
    } finally {
      setSubmittingProposal(false);
    }
  };

  const { facts, analysis } = investigation;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', paddingBottom: '3rem' }}>
      {/* Top Navigation & Status Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          background: 'var(--bp-surface)',
          border: '1px solid var(--bp-border)',
          borderRadius: 'var(--bp-radius-lg)',
          padding: '1rem 1.25rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <Button variant="secondary" size="sm" onClick={onBack}>
            ← Back to All Investigations
          </Button>
          <code
            style={{
              fontSize: '0.88rem',
              fontWeight: 700,
              background: 'var(--bp-purple-pale)',
              color: 'var(--bp-purple)',
              padding: '0.25rem 0.6rem',
              borderRadius: '6px',
            }}
          >
            {investigation.investigation_id}
          </code>
          <Badge variant="success">{investigation.status.toUpperCase()}</Badge>
          <Badge variant="info">Model: {investigation.model_used}</Badge>
        </div>

        <div style={{ fontSize: '0.8rem', color: 'var(--bp-text-muted)' }}>
          Generated:{' '}
          {new Date(investigation.generated_at).toLocaleString(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short',
          })}
        </div>
      </div>

      {/* Main Title & Problem Header */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(88,24,240,0.06), rgba(144,80,248,0.02))',
          border: '1px solid var(--bp-info-border)',
          borderRadius: 'var(--bp-radius-lg)',
          padding: '1.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '1.25rem' }}>🔬</span>
          <h2 style={{ fontSize: '1.25rem', color: 'var(--bp-text)', fontWeight: 700 }}>
            {facts.anomaly_title}
          </h2>
        </div>
        <p style={{ fontSize: '0.88rem', color: 'var(--bp-text-muted)', marginBottom: '0.75rem' }}>
          Target Anomaly: <code>{facts.anomaly_id}</code>
        </p>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '1rem',
            marginTop: '1rem',
          }}
        >
          <div
            style={{
              background: 'var(--bp-surface)',
              border: '1px solid var(--bp-border)',
              borderRadius: 'var(--bp-radius)',
              padding: '1rem',
            }}
          >
            <strong style={{ fontSize: '0.78rem', textTransform: 'uppercase', color: 'var(--bp-purple)' }}>
              1. Observed Problem
            </strong>
            <p style={{ fontSize: '0.88rem', color: 'var(--bp-text)', marginTop: '0.4rem', lineHeight: 1.55 }}>
              {analysis.what_happened}
            </p>
          </div>

          <div
            style={{
              background: 'var(--bp-surface)',
              border: '1px solid var(--bp-border)',
              borderRadius: 'var(--bp-radius)',
              padding: '1rem',
            }}
          >
            <strong style={{ fontSize: '0.78rem', textTransform: 'uppercase', color: 'var(--bp-purple)' }}>
              2. Business & Financial Significance
            </strong>
            <p style={{ fontSize: '0.88rem', color: 'var(--bp-text)', marginTop: '0.4rem', lineHeight: 1.55 }}>
              {analysis.why_important}
            </p>
          </div>

          <div
            style={{
              background: 'var(--bp-surface)',
              border: '1px solid var(--bp-border)',
              borderRadius: 'var(--bp-radius)',
              padding: '1rem',
            }}
          >
            <strong style={{ fontSize: '0.78rem', textTransform: 'uppercase', color: 'var(--bp-purple)' }}>
              3. Accountable Department
            </strong>
            <div style={{ marginTop: '0.5rem' }}>
              <Badge variant="info">{analysis.responsible_department}</Badge>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--bp-text-muted)', marginTop: '0.5rem' }}>
              Primary functional owner responsible for resolution and cross-team alignment.
            </p>
          </div>
        </div>
      </div>

      {/* Section 1: Verified Quantitative Evidence (Python Engine) */}
      <Card
        header={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
            <span style={{ fontWeight: 600, fontSize: '1rem' }}>
              📊 Verified Quantitative Evidence (Python Data Engine)
            </span>
            <Badge variant="success">0% LLM Arithmetic — Python Verified</Badge>
          </div>
        }
        padding="1.25rem"
      >
        <p style={{ fontSize: '0.82rem', color: 'var(--bp-text-muted)', marginBottom: '1rem' }}>
          The metrics below were computed directly from underlying transaction logs and funnel telemetry by BizPulse&apos;s
          Python analytics engine.
        </p>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '0.85rem',
          }}
        >
          {Object.entries(facts.metric_facts).map(([key, val]) => {
            // If the value is a complex array/object, format it in a structured box
            if (typeof val === 'object' && val !== null) {
              return (
                <div
                  key={key}
                  style={{
                    gridColumn: '1 / -1',
                    background: 'var(--bp-surface-alt)',
                    border: '1px solid var(--bp-border)',
                    borderRadius: 'var(--bp-radius)',
                    padding: '0.85rem',
                  }}
                >
                  <strong style={{ fontSize: '0.78rem', textTransform: 'uppercase', color: 'var(--bp-text-muted)' }}>
                    {key.replace(/_/g, ' ')}
                  </strong>
                  <div style={{ overflowX: 'auto', marginTop: '0.5rem' }}>
                    <table style={{ width: '100%', fontSize: '0.82rem', borderCollapse: 'collapse' }}>
                      <tbody>
                        {Array.isArray(val) ? (
                          val.map((item, idx) => (
                            <tr key={idx} style={{ borderBottom: '1px solid var(--bp-border)' }}>
                              <td style={{ padding: '0.35rem 0.5rem', fontWeight: 600 }}>
                                {item.product_name || item.product_id || `#${idx + 1}`}
                              </td>
                              <td style={{ padding: '0.35rem 0.5rem' }}>
                                {item.gross_profit_margin_pct || item.week1_revenue || JSON.stringify(item)}
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td style={{ padding: '0.5rem' }}>
                              <pre style={{ margin: 0, fontSize: '0.75rem' }}>{JSON.stringify(val, null, 2)}</pre>
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            }

            return (
              <div
                key={key}
                style={{
                  background: 'var(--bp-surface)',
                  border: '1px solid var(--bp-border)',
                  borderRadius: 'var(--bp-radius)',
                  padding: '0.75rem 1rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.25rem',
                }}
              >
                <span
                  style={{
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    color: 'var(--bp-text-muted)',
                    letterSpacing: '0.04em',
                  }}
                >
                  {key.replace(/_/g, ' ')}
                </span>
                <span style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--bp-text)' }}>
                  {String(val)}
                </span>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Section 2: Correlated Timeline Events */}
      <Card
        header={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
            <span style={{ fontWeight: 600, fontSize: '1rem' }}>⏱️ Correlated Business Events</span>
            <Badge variant="neutral">{facts.timeline_events.length} events logged</Badge>
          </div>
        }
        padding="1.25rem"
      >
        <div
          style={{
            background: 'var(--bp-warning-pale)',
            border: '1px solid var(--bp-warning-border)',
            borderRadius: 'var(--bp-radius)',
            padding: '0.75rem 1rem',
            fontSize: '0.82rem',
            color: 'var(--bp-warning)',
            marginBottom: '1rem',
            lineHeight: 1.5,
          }}
        >
          ⚠️ <strong>Correlation in time does not prove causation:</strong> The events below occurred during or
          immediately preceding the detected anomaly window. They represent potential triggers that require engineering
          or operational verification.
        </div>

        {facts.timeline_events.length === 0 ? (
          <p style={{ fontSize: '0.85rem', color: 'var(--bp-text-muted)' }}>
            No system or operational events were logged during this window.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {facts.timeline_events.map((ev, idx) => (
              <div
                key={idx}
                style={{
                  border: '1px solid var(--bp-border)',
                  borderRadius: 'var(--bp-radius)',
                  padding: '0.8rem 1rem',
                  background: 'var(--bp-surface)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '0.75rem',
                }}
              >
                <div style={{ flex: '1 1 300px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
                    <Badge variant="info">{ev.event_type}</Badge>
                    <Badge variant="neutral">System: {ev.affected_system}</Badge>
                  </div>
                  <p style={{ fontSize: '0.86rem', color: 'var(--bp-text)', margin: 0, lineHeight: 1.5 }}>
                    {ev.description}
                  </p>
                </div>
                <span style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)', fontWeight: 500 }}>
                  {new Date(ev.timestamp).toLocaleString(undefined, {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Section 3: Possible Explanations (Hypotheses) */}
      <Card
        header={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
            <span style={{ fontWeight: 600, fontSize: '1rem' }}>💡 Possible Causal Explanations</span>
            <Badge variant="info">AI Synthesized Hypotheses</Badge>
          </div>
        }
        padding="1.25rem"
      >
        <p style={{ fontSize: '0.82rem', color: 'var(--bp-text-muted)', marginBottom: '1rem' }}>
          Ranked root-cause hypotheses synthesized from verified metrics and event correlation.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {analysis.hypotheses.map((hyp, idx) => (
            <div
              key={idx}
              style={{
                border: '1px solid var(--bp-border)',
                borderLeft: `4px solid ${
                  hyp.confidence_level === 'high' ? 'var(--bp-success)' : 'var(--bp-warning)'
                }`,
                borderRadius: 'var(--bp-radius)',
                padding: '1rem',
                background: 'var(--bp-surface)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <strong style={{ fontSize: '0.92rem', color: 'var(--bp-text)' }}>
                  Hypothesis #{idx + 1}: {hyp.cause}
                </strong>
                <Badge variant={confidenceVariant(hyp.confidence_level)}>
                  Confidence: {hyp.confidence_level.toUpperCase()}
                </Badge>
              </div>

              <div style={{ marginTop: '0.6rem' }}>
                <strong style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--bp-text-muted)' }}>
                  Supporting Evidence:
                </strong>
                <ul style={{ margin: '0.35rem 0 0 1.25rem', padding: 0, fontSize: '0.84rem', color: 'var(--bp-text)' }}>
                  {hyp.supporting_evidence.map((evItem, evIdx) => (
                    <li key={evIdx} style={{ marginBottom: '0.3rem', lineHeight: 1.5 }}>
                      {evItem}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Section 4: Recommended Actions & Task Proposals */}
      <Card
        header={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
            <span style={{ fontWeight: 600, fontSize: '1rem' }}>🎯 AI Remediation Recommendations</span>
            <Badge variant="neutral">Phase 3B Action Integration</Badge>
          </div>
        }
        padding="1.25rem"
      >
        <p style={{ fontSize: '0.82rem', color: 'var(--bp-text-muted)', marginBottom: '1rem' }}>
          Convert any recommendation into a structured business task. Proposed actions enter the Phase 3B approval
          workflow and must be approved by a human manager before execution.
        </p>

        {proposalSuccess && (
          <div
            style={{
              background: 'var(--bp-success-pale)',
              border: '1px solid var(--bp-success)',
              borderRadius: 'var(--bp-radius)',
              padding: '0.75rem 1rem',
              color: 'var(--bp-success)',
              fontSize: '0.85rem',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span>✅ {proposalSuccess}</span>
            <Button variant="secondary" size="sm" onClick={() => setView('actions')}>
              Go to Action Centre →
            </Button>
          </div>
        )}

        {proposalError && (
          <div
            style={{
              background: 'var(--bp-danger-pale)',
              border: '1px solid var(--bp-danger)',
              borderRadius: 'var(--bp-radius)',
              padding: '0.75rem 1rem',
              color: 'var(--bp-danger)',
              fontSize: '0.85rem',
              marginBottom: '1rem',
            }}
          >
            ❌ {proposalError}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
          {analysis.recommended_actions.map((act, idx) => (
            <div
              key={idx}
              style={{
                border: '1px solid var(--bp-border)',
                borderRadius: 'var(--bp-radius)',
                padding: '0.85rem 1rem',
                background: 'var(--bp-surface)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '0.75rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem', flex: '1 1 350px' }}>
                <span
                  style={{
                    background: 'var(--bp-purple-pale)',
                    color: 'var(--bp-purple)',
                    width: '24px',
                    height: '24px',
                    borderRadius: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {idx + 1}
                </span>
                <span style={{ fontSize: '0.88rem', color: 'var(--bp-text)', lineHeight: 1.5 }}>
                  {act}
                </span>
              </div>

              <Button variant="primary" size="sm" onClick={() => handleOpenProposalForm(act)}>
                Propose as Task ⚡
              </Button>
            </div>
          ))}
        </div>

        {/* Action Proposal Modal / Inline Form */}
        {proposingAction && (
          <div
            style={{
              background: 'var(--bp-surface-alt)',
              border: '2px solid var(--bp-purple)',
              borderRadius: 'var(--bp-radius-lg)',
              padding: '1.25rem',
              marginTop: '1rem',
              marginBottom: '1rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h4 style={{ fontSize: '0.98rem', fontWeight: 600, color: 'var(--bp-purple)' }}>
                📝 Propose Structured Business Task
              </h4>
              <Button variant="ghost" size="sm" onClick={() => setProposingAction(null)}>
                ✕ Cancel
              </Button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text-muted)', display: 'block', marginBottom: '0.25rem' }}>
                  Action Description:
                </label>
                <textarea
                  value={customActionText}
                  onChange={(e) => setCustomActionText(e.target.value)}
                  rows={2}
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    borderRadius: 'var(--bp-radius)',
                    border: '1px solid var(--bp-border)',
                    fontSize: '0.85rem',
                    fontFamily: 'inherit',
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
                <div>
                  <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text-muted)', display: 'block', marginBottom: '0.25rem' }}>
                    Accountable Department:
                  </label>
                  <input
                    type="text"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.45rem',
                      borderRadius: 'var(--bp-radius)',
                      border: '1px solid var(--bp-border)',
                      fontSize: '0.85rem',
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text-muted)', display: 'block', marginBottom: '0.25rem' }}>
                    Suggested Owner Role (no employee names):
                  </label>
                  <input
                    type="text"
                    value={ownerRole}
                    onChange={(e) => setOwnerRole(e.target.value)}
                    placeholder="e.g. Checkout Frontend Team"
                    style={{
                      width: '100%',
                      padding: '0.45rem',
                      borderRadius: 'var(--bp-radius)',
                      border: '1px solid var(--bp-border)',
                      fontSize: '0.85rem',
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text-muted)', display: 'block', marginBottom: '0.25rem' }}>
                    Urgency Priority:
                  </label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value as any)}
                    style={{
                      width: '100%',
                      padding: '0.45rem',
                      borderRadius: 'var(--bp-radius)',
                      border: '1px solid var(--bp-border)',
                      fontSize: '0.85rem',
                      background: 'var(--bp-surface)',
                    }}
                  >
                    <option value="Critical">Critical</option>
                    <option value="High">High</option>
                    <option value="Medium">Medium</option>
                    <option value="Low">Low</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text-muted)', display: 'block', marginBottom: '0.25rem' }}>
                    Target Completion Deadline:
                  </label>
                  <input
                    type="date"
                    value={deadline}
                    onChange={(e) => setDeadline(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.45rem',
                      borderRadius: 'var(--bp-radius)',
                      border: '1px solid var(--bp-border)',
                      fontSize: '0.85rem',
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text-muted)', display: 'block', marginBottom: '0.25rem' }}>
                  Expected Business Outcome:
                </label>
                <input
                  type="text"
                  value={expectedOutcome}
                  onChange={(e) => setExpectedOutcome(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.45rem',
                    borderRadius: 'var(--bp-radius)',
                    border: '1px solid var(--bp-border)',
                    fontSize: '0.85rem',
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text-muted)', display: 'block', marginBottom: '0.25rem' }}>
                  Verification Criteria (measurable outcome):
                </label>
                <input
                  type="text"
                  value={verificationCriteria}
                  onChange={(e) => setVerificationCriteria(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.45rem',
                    borderRadius: 'var(--bp-radius)',
                    border: '1px solid var(--bp-border)',
                    fontSize: '0.85rem',
                  }}
                />
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  paddingTop: '0.5rem',
                  borderTop: '1px solid var(--bp-border)',
                  flexWrap: 'wrap',
                  gap: '0.5rem',
                }}
              >
                <span style={{ fontSize: '0.76rem', color: 'var(--bp-text-muted)' }}>
                  🔒 Will enter &apos;Pending Approval&apos; status. Consequential changes are never executed automatically.
                </span>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <Button variant="secondary" size="sm" onClick={() => setProposingAction(null)}>
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    loading={submittingProposal}
                    disabled={!customActionText.trim()}
                    onClick={handleSubmitProposal}
                  >
                    Submit Proposal →
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Existing Actions Associated with this Investigation */}
        <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--bp-border)', paddingTop: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <strong style={{ fontSize: '0.88rem', color: 'var(--bp-text)' }}>
              Linked Tasks in Action Management System ({actions.length})
            </strong>
            {actions.length > 0 && (
              <Button variant="ghost" size="sm" onClick={() => setView('actions')}>
                Open in Action Centre →
              </Button>
            )}
          </div>

          {loadingActions ? (
            <LoadingSpinner label="Loading associated actions…" />
          ) : actions.length === 0 ? (
            <p style={{ fontSize: '0.82rem', color: 'var(--bp-text-muted)' }}>
              No tasks have been proposed for this investigation yet. Use the buttons above to propose tasks for manager
              approval.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {actions.map((act) => (
                <div
                  key={act.id}
                  style={{
                    background: 'var(--bp-surface-alt)',
                    border: '1px solid var(--bp-border)',
                    borderRadius: 'var(--bp-radius)',
                    padding: '0.75rem 1rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <code style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--bp-purple)' }}>{act.id}</code>
                    <Badge variant={actionStatusVariant(act.status)}>{act.status}</Badge>
                    <Badge variant={priorityVariant(act.priority)}>{act.priority}</Badge>
                    <span style={{ fontSize: '0.84rem', color: 'var(--bp-text)' }}>{act.recommended_action}</span>
                  </div>
                  <div style={{ fontSize: '0.76rem', color: 'var(--bp-text-muted)' }}>
                    Dept: <strong>{act.responsible_department}</strong> | Due: {act.suggested_deadline}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      {/* Section 5: Verification Steps */}
      <Card
        header={<span style={{ fontWeight: 600, fontSize: '1rem' }}>✅ Resolution Verification Steps</span>}
        padding="1.25rem"
      >
        <p style={{ fontSize: '0.82rem', color: 'var(--bp-text-muted)', marginBottom: '0.75rem' }}>
          Criteria and benchmarks to measure whether remediations successfully resolved the business problem.
        </p>

        <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.86rem', color: 'var(--bp-text)' }}>
          {analysis.verification_steps.map((step, idx) => (
            <li key={idx} style={{ marginBottom: '0.4rem', lineHeight: 1.55 }}>
              {step}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
