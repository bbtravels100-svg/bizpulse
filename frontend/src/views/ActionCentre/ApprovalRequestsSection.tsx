import { useState } from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { EmptyState } from '../../components/common/EmptyState';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import { useAuth } from '../../context/AuthContext';
import type { ActionResponse, ActionUpdateRequest, BadgeVariant } from '../../types';

interface ApprovalRequestsSectionProps {
  proposals: ActionResponse[];
  onApprove: (actionId: string, notes?: string) => Promise<void>;
  onReject: (actionId: string, reason: string) => Promise<void>;
  onEdit: (actionId: string, updates: ActionUpdateRequest) => Promise<void>;
  onViewHistory: (actionId: string) => void;
  onGoToInvestigations?: () => void;
  loading?: boolean;
}

function priorityVariant(prio: string): BadgeVariant {
  switch (prio?.toLowerCase()) {
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

export function ApprovalRequestsSection({
  proposals,
  onApprove,
  onReject,
  onEdit,
  onViewHistory,
  onGoToInvestigations,
}: ApprovalRequestsSectionProps) {
  const { user } = useAuth();
  const isCeo = Boolean(user?.role && (user.role.includes('CEO') || user.role.includes('Admin')));

  // Confirm approve dialog
  const [approvingAction, setApprovingAction] = useState<ActionResponse | null>(null);
  const [approverNotes, setApproverNotes] = useState('');

  // Reject modal
  const [rejectingAction, setRejectingAction] = useState<ActionResponse | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [isRejecting, setIsRejecting] = useState(false);
  const [rejectionError, setRejectionError] = useState<string | null>(null);

  // Edit pre-approval modal
  const [editingAction, setEditingAction] = useState<ActionResponse | null>(null);
  const [editActionText, setEditActionText] = useState('');
  const [editDepartment, setEditDepartment] = useState('');
  const [editRole, setEditRole] = useState('');
  const [editPriority, setEditPriority] = useState<'Critical' | 'High' | 'Medium' | 'Low'>('High');
  const [editDeadline, setEditDeadline] = useState('');
  const [editOutcome, setEditOutcome] = useState('');
  const [editVerification, setEditVerification] = useState('');
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const openEditModal = (act: ActionResponse) => {
    setEditingAction(act);
    setEditActionText(act.recommended_action);
    setEditDepartment(act.responsible_department);
    setEditRole(act.suggested_owner_role);
    setEditPriority(act.priority);
    setEditDeadline(act.suggested_deadline);
    setEditOutcome(act.expected_outcome);
    setEditVerification(act.verification_criteria);
    setEditError(null);
  };

  const handleSaveEdit = async () => {
    if (!editingAction || !editActionText.trim()) return;
    setIsSavingEdit(true);
    setEditError(null);
    try {
      await onEdit(editingAction.id, {
        recommended_action: editActionText.trim(),
        responsible_department: editDepartment.trim(),
        suggested_owner_role: editRole.trim(),
        priority: editPriority,
        suggested_deadline: editDeadline,
        expected_outcome: editOutcome.trim(),
        verification_criteria: editVerification.trim(),
      });
      setEditingAction(null);
    } catch (err: unknown) {
      setEditError(err instanceof Error ? err.message : 'Failed to update proposal');
    } finally {
      setIsSavingEdit(false);
    }
  };

  const handleConfirmApprove = async () => {
    if (!approvingAction) return;
    try {
      await onApprove(approvingAction.id, approverNotes.trim() || undefined);
      setApprovingAction(null);
      setApproverNotes('');
    } catch {
      // Error handled by parent
    }
  };

  const handleConfirmReject = async () => {
    if (!rejectingAction) return;
    if (rejectionReason.trim().length < 3) {
      setRejectionError('A rejection reason of at least 3 characters is mandatory.');
      return;
    }
    setIsRejecting(true);
    setRejectionError(null);
    try {
      await onReject(rejectingAction.id, rejectionReason.trim());
      setRejectingAction(null);
      setRejectionReason('');
    } catch (err: unknown) {
      setRejectionError(err instanceof Error ? err.message : 'Rejection failed');
    } finally {
      setIsRejecting(false);
    }
  };

  return (
    <Card
      header={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.05rem', fontWeight: 600 }}>📝 Pending Action Proposals</span>
            <Badge variant={proposals.length > 0 ? 'danger' : 'neutral'}>
              {proposals.length} awaiting signoff
            </Badge>
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--bp-text-muted)' }}>
            Human Approval Gate — Only approved actions enter execution
          </span>
        </div>
      }
      padding="1.25rem"
    >
      {proposals.length === 0 ? (
        <EmptyState
          icon="✅"
          title="All action proposals have been reviewed"
          description="There are currently no actions pending approval. Run an investigation to generate new diagnostic proposals."
          actionLabel={onGoToInvestigations ? 'Go to Investigations' : undefined}
          onAction={onGoToInvestigations}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {proposals.map((act) => (
            <div
              key={act.id}
              style={{
                border: '1px solid var(--bp-border)',
                borderLeft: `4px solid ${
                  priorityVariant(act.priority) === 'danger'
                    ? 'var(--bp-danger)'
                    : priorityVariant(act.priority) === 'warning'
                    ? 'var(--bp-warning)'
                    : 'var(--bp-purple)'
                }`,
                borderRadius: 'var(--bp-radius)',
                padding: '1.25rem',
                background: 'var(--bp-surface)',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
                boxShadow: 'var(--bp-shadow)',
              }}
            >
              {/* Proposal Header */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '0.5rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <code
                    style={{
                      fontSize: '0.85rem',
                      fontWeight: 700,
                      background: 'var(--bp-purple-pale)',
                      color: 'var(--bp-purple)',
                      padding: '0.2rem 0.5rem',
                      borderRadius: '4px',
                    }}
                  >
                    {act.id}
                  </code>
                  <Badge variant={priorityVariant(act.priority)}>Priority: {act.priority}</Badge>
                  <Badge variant="neutral">Anomaly: {act.anomaly_id}</Badge>
                  <Badge variant="info">Investigation: {act.investigation_id}</Badge>
                </div>
                <span style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)' }}>
                  Proposed:{' '}
                  {new Date(act.created_at).toLocaleString(undefined, {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}
                </span>
              </div>

              {/* Recommended Action Title */}
              <div>
                <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--bp-text)', margin: '0 0 0.35rem 0' }}>
                  {act.recommended_action}
                </h4>
                <p style={{ fontSize: '0.86rem', color: 'var(--bp-text-muted)', margin: 0, lineHeight: 1.55 }}>
                  <strong>Diagnosed Problem:</strong> {act.problem_description}
                </p>
              </div>

              {/* Metadata Grid */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '0.75rem',
                  background: 'var(--bp-surface-alt)',
                  borderRadius: 'var(--bp-radius)',
                  padding: '0.75rem 1rem',
                  fontSize: '0.82rem',
                }}
              >
                <div>
                  <span style={{ color: 'var(--bp-text-muted)', display: 'block', fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 600 }}>
                    Accountable Dept
                  </span>
                  <strong style={{ color: 'var(--bp-text)' }}>{act.responsible_department}</strong>
                </div>

                <div>
                  <span style={{ color: 'var(--bp-text-muted)', display: 'block', fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 600 }}>
                    Owner Role
                  </span>
                  <strong style={{ color: 'var(--bp-text)' }}>{act.suggested_owner_role}</strong>
                </div>

                <div>
                  <span style={{ color: 'var(--bp-text-muted)', display: 'block', fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 600 }}>
                    Suggested Deadline
                  </span>
                  <strong style={{ color: 'var(--bp-text)' }}>{act.suggested_deadline}</strong>
                </div>

                <div>
                  <span style={{ color: 'var(--bp-text-muted)', display: 'block', fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 600 }}>
                    Expected Outcome
                  </span>
                  <span style={{ color: 'var(--bp-text)' }}>{act.expected_outcome}</span>
                </div>
              </div>

              {/* Verification Criteria */}
              <div style={{ fontSize: '0.8rem', color: 'var(--bp-text-muted)', lineHeight: 1.5 }}>
                <strong style={{ color: 'var(--bp-purple)' }}>Verification Criteria:</strong>{' '}
                {act.verification_criteria}
              </div>

              {/* Action Buttons Bar */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  borderTop: '1px solid var(--bp-border)',
                  paddingTop: '0.75rem',
                  flexWrap: 'wrap',
                  gap: '0.5rem',
                }}
              >
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <Button variant="ghost" size="sm" onClick={() => onViewHistory(act.id)}>
                    📜 Audit History
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => openEditModal(act)}>
                    ✏️ Edit Proposal
                  </Button>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {!isCeo && (
                    <span
                      style={{
                        fontSize: '0.75rem',
                        color: 'var(--bp-text-muted)',
                        padding: '0.2rem 0.5rem',
                        background: '#F1F5F9',
                        borderRadius: '4px',
                        border: '1px solid #CBD5E1',
                      }}
                      title="Only CEO / Admin can approve or reject proposals."
                    >
                      🔒 CEO / Admin Only
                    </span>
                  )}
                  <Button
                    variant="danger"
                    size="sm"
                    disabled={!isCeo}
                    title={!isCeo ? 'Rejection restricted to CEO / Admin' : undefined}
                    onClick={() => setRejectingAction(act)}
                  >
                    ✕ Reject
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={!isCeo}
                    title={!isCeo ? 'Approval restricted to CEO / Admin' : undefined}
                    onClick={() => setApprovingAction(act)}
                  >
                    ✓ Approve Action
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Confirmation Dialog for Approval */}
      <ConfirmDialog
        open={Boolean(approvingAction)}
        title="Approve Business Action"
        description={`Are you sure you want to approve proposal ${approvingAction?.id} (${approvingAction?.recommended_action})? Once approved, it will enter the active workflow.`}
        confirmLabel="Confirm & Approve"
        onConfirm={() => void handleConfirmApprove()}
        onCancel={() => {
          setApprovingAction(null);
          setApproverNotes('');
        }}
      />

      {/* Rejection Modal with Mandatory Reason */}
      {rejectingAction && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(8, 15, 32, 0.65)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem',
          }}
          onClick={() => setRejectingAction(null)}
        >
          <div
            style={{
              background: 'var(--bp-surface)',
              borderRadius: 'var(--bp-radius-lg)',
              maxWidth: '520px',
              width: '100%',
              padding: '1.5rem',
              border: '1px solid var(--bp-border)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.25)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: '0 0 0.5rem 0', color: 'var(--bp-danger)' }}>
              Reject Action Proposal
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--bp-text-muted)', margin: '0 0 1rem 0' }}>
              Rejecting proposal <code>{rejectingAction.id}</code> requires an explicit explanation reason for audit
              compliance.
            </p>

            {rejectionError && (
              <div style={{ color: 'var(--bp-danger)', fontSize: '0.82rem', marginBottom: '0.75rem' }}>
                ⚠️ {rejectionError}
              </div>
            )}

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text)', display: 'block', marginBottom: '0.35rem' }}>
                Rejection Reason (minimum 3 characters): *
              </label>
              <textarea
                rows={3}
                placeholder="Explain why this proposal is rejected (e.g. Budget constraints, prioritized alternative fix)..."
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: 'var(--bp-radius)',
                  border: '1px solid var(--bp-border)',
                  fontSize: '0.85rem',
                  fontFamily: 'inherit',
                  resize: 'none',
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <Button variant="secondary" size="sm" onClick={() => setRejectingAction(null)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                loading={isRejecting}
                disabled={rejectionReason.trim().length < 3}
                onClick={() => void handleConfirmReject()}
              >
                Confirm Rejection
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Proposal Pre-Approval Modal */}
      {editingAction && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(8, 15, 32, 0.65)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem',
          }}
          onClick={() => setEditingAction(null)}
        >
          <div
            style={{
              background: 'var(--bp-surface)',
              borderRadius: 'var(--bp-radius-lg)',
              maxWidth: '650px',
              width: '100%',
              padding: '1.5rem',
              border: '1px solid var(--bp-border)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.25)',
              maxHeight: '90vh',
              overflowY: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: '0 0 0.5rem 0', color: 'var(--bp-text)' }}>
              Edit Action Proposal Pre-Approval
            </h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--bp-text-muted)', margin: '0 0 1rem 0' }}>
              Modify proposal <code>{editingAction.id}</code> parameters before granting formal manager approval.
            </p>

            {editError && (
              <div style={{ color: 'var(--bp-danger)', fontSize: '0.82rem', marginBottom: '0.75rem' }}>
                ⚠️ {editError}
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text)', display: 'block', marginBottom: '0.25rem' }}>
                  Recommended Action:
                </label>
                <textarea
                  rows={2}
                  value={editActionText}
                  onChange={(e) => setEditActionText(e.target.value)}
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

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text)', display: 'block', marginBottom: '0.25rem' }}>
                    Department:
                  </label>
                  <input
                    type="text"
                    value={editDepartment}
                    onChange={(e) => setEditDepartment(e.target.value)}
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
                  <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text)', display: 'block', marginBottom: '0.25rem' }}>
                    Suggested Owner Role:
                  </label>
                  <input
                    type="text"
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value)}
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
                  <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text)', display: 'block', marginBottom: '0.25rem' }}>
                    Priority:
                  </label>
                  <select
                    value={editPriority}
                    onChange={(e) => setEditPriority(e.target.value as any)}
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
                  <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text)', display: 'block', marginBottom: '0.25rem' }}>
                    Deadline:
                  </label>
                  <input
                    type="date"
                    value={editDeadline}
                    onChange={(e) => setEditDeadline(e.target.value)}
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
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text)', display: 'block', marginBottom: '0.25rem' }}>
                  Expected Outcome:
                </label>
                <input
                  type="text"
                  value={editOutcome}
                  onChange={(e) => setEditOutcome(e.target.value)}
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
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text)', display: 'block', marginBottom: '0.25rem' }}>
                  Verification Criteria:
                </label>
                <input
                  type="text"
                  value={editVerification}
                  onChange={(e) => setEditVerification(e.target.value)}
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

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.25rem' }}>
              <Button variant="secondary" size="sm" onClick={() => setEditingAction(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                loading={isSavingEdit}
                disabled={!editActionText.trim()}
                onClick={() => void handleSaveEdit()}
              >
                Save Changes
              </Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
