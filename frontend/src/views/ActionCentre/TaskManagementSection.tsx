import { useState } from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { EmptyState } from '../../components/common/EmptyState';
import { useAuth } from '../../context/AuthContext';
import type {
  ActionResponse,
  ActionStatus,
  TaskAssignmentUpdateRequest,
  BadgeVariant,
} from '../../types';

interface TaskManagementSectionProps {
  tasks: ActionResponse[];
  onUpdateStatus: (actionId: string, newStatus: ActionStatus, notes?: string, details?: string) => Promise<void>;
  onUpdateAssignment: (actionId: string, updates: TaskAssignmentUpdateRequest) => Promise<void>;
  onViewHistory: (actionId: string) => void;
  onRefresh?: () => void;
  loading?: boolean;
}

function statusVariant(st: string): BadgeVariant {
  switch (st?.toLowerCase()) {
    case 'approved':
      return 'info';
    case 'in progress':
      return 'warning';
    case 'completed':
      return 'success';
    case 'rejected':
    case 'overdue':
      return 'danger';
    case 'pending approval':
    default:
      return 'neutral';
  }
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

export function TaskManagementSection({
  tasks,
  onUpdateStatus,
  onUpdateAssignment,
  onViewHistory,
}: TaskManagementSectionProps) {
  const { user } = useAuth();
  const isEmployee = user?.role === 'Employee';
  const canAssign = Boolean(user?.role && (user.role.includes('CEO') || user.role.includes('Admin') || user.role.includes('Operations')));

  // Filter states
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [deptFilter, setDeptFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');

  // Complete task modal
  const [completingTask, setCompletingTask] = useState<ActionResponse | null>(null);
  const [completionDetails, setCompletionDetails] = useState('');
  const [completionNotes, setCompletionNotes] = useState('');
  const [isCompleting, setIsCompleting] = useState(false);
  const [completeError, setCompleteError] = useState<string | null>(null);

  // Assignment / Reassign modal
  const [reassigningTask, setReassigningTask] = useState<ActionResponse | null>(null);
  const [newDepartment, setNewDepartment] = useState('');
  const [newRole, setNewRole] = useState('');
  const [newDeadline, setNewDeadline] = useState('');
  const [reassignReason, setReassignReason] = useState('');
  const [isReassigning, setIsReassigning] = useState(false);
  const [reassignError, setReassignError] = useState<string | null>(null);

  // Status transition in-flight tracking
  const [transitioningId, setTransitioningId] = useState<string | null>(null);

  // Extract unique departments for filter
  const departments = Array.from(new Set(tasks.map((t) => t.responsible_department))).filter(Boolean);

  const filtered = tasks.filter((t) => {
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      const match =
        t.id.toLowerCase().includes(q) ||
        t.recommended_action.toLowerCase().includes(q) ||
        t.responsible_department.toLowerCase().includes(q) ||
        t.suggested_owner_role.toLowerCase().includes(q) ||
        t.anomaly_id.toLowerCase().includes(q);
      if (!match) return false;
    }
    if (statusFilter !== 'all' && t.status !== statusFilter) {
      return false;
    }
    if (deptFilter !== 'all' && t.responsible_department !== deptFilter) {
      return false;
    }
    if (priorityFilter !== 'all' && t.priority !== priorityFilter) {
      return false;
    }
    return true;
  });

  const handleStartExecution = async (act: ActionResponse) => {
    setTransitioningId(act.id);
    try {
      await onUpdateStatus(act.id, 'In Progress', 'Execution commenced by department lead');
    } finally {
      setTransitioningId(null);
    }
  };

  const handleMarkOverdue = async (act: ActionResponse) => {
    setTransitioningId(act.id);
    try {
      await onUpdateStatus(act.id, 'Overdue', 'Marked overdue: target deadline exceeded');
    } finally {
      setTransitioningId(null);
    }
  };

  const handleOpenCompleteModal = (act: ActionResponse) => {
    setCompletingTask(act);
    setCompletionDetails(`Remediation verified: ${act.verification_criteria.slice(0, 100)}`);
    setCompletionNotes('');
    setCompleteError(null);
  };

  const handleConfirmCompletion = async () => {
    if (!completingTask) return;
    setIsCompleting(true);
    setCompleteError(null);
    try {
      await onUpdateStatus(
        completingTask.id,
        'Completed',
        completionNotes.trim() || undefined,
        completionDetails.trim() || 'Remediation completed successfully'
      );
      setCompletingTask(null);
    } catch (err: unknown) {
      setCompleteError(err instanceof Error ? err.message : 'Failed to complete task');
    } finally {
      setIsCompleting(false);
    }
  };

  const handleOpenReassignModal = (act: ActionResponse) => {
    setReassigningTask(act);
    setNewDepartment(act.responsible_department);
    setNewRole(act.suggested_owner_role);
    setNewDeadline(act.suggested_deadline);
    setReassignReason('');
    setReassignError(null);
  };

  const handleConfirmReassign = async () => {
    if (!reassigningTask) return;
    setIsReassigning(true);
    setReassignError(null);
    try {
      await onUpdateAssignment(reassigningTask.id, {
        responsible_department: newDepartment.trim() || undefined,
        suggested_owner_role: newRole.trim() || undefined,
        suggested_deadline: newDeadline || undefined,
        reason: reassignReason.trim() || 'Workload adjustment and priority alignment',
      });
      setReassigningTask(null);
    } catch (err: unknown) {
      setReassignError(err instanceof Error ? err.message : 'Reassignment failed');
    } finally {
      setIsReassigning(false);
    }
  };

  return (
    <Card
      header={
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            width: '100%',
            flexWrap: 'wrap',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.05rem', fontWeight: 600 }}>⚡ Active Execution Workflow</span>
            <Badge variant="neutral">{tasks.length} total tasks</Badge>
          </div>

          {/* Filters Bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Search tasks…"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                fontSize: '0.82rem',
                padding: '0.35rem 0.65rem',
                borderRadius: 'var(--bp-radius)',
                border: '1px solid var(--bp-border)',
                background: 'var(--bp-surface)',
                color: 'var(--bp-text)',
                minWidth: '150px',
              }}
            />

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                fontSize: '0.82rem',
                padding: '0.35rem 0.65rem',
                borderRadius: 'var(--bp-radius)',
                border: '1px solid var(--bp-border)',
                background: 'var(--bp-surface)',
                color: 'var(--bp-text)',
              }}
            >
              <option value="all">All Statuses</option>
              <option value="Approved">Approved</option>
              <option value="In Progress">In Progress</option>
              <option value="Overdue">Overdue</option>
              <option value="Completed">Completed</option>
              <option value="Rejected">Rejected</option>
            </select>

            <select
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
              style={{
                fontSize: '0.82rem',
                padding: '0.35rem 0.65rem',
                borderRadius: 'var(--bp-radius)',
                border: '1px solid var(--bp-border)',
                background: 'var(--bp-surface)',
                color: 'var(--bp-text)',
              }}
            >
              <option value="all">All Departments</option>
              {departments.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>

            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              style={{
                fontSize: '0.82rem',
                padding: '0.35rem 0.65rem',
                borderRadius: 'var(--bp-radius)',
                border: '1px solid var(--bp-border)',
                background: 'var(--bp-surface)',
                color: 'var(--bp-text)',
              }}
            >
              <option value="all">All Priorities</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </div>
        </div>
      }
      padding="1.25rem"
    >
      {tasks.length === 0 ? (
        <EmptyState
          icon="📋"
          title="No active tasks in workflow"
          description="Approved action proposals enter active task execution here. Review and approve proposals in the Approvals tab."
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon="🔎"
          title="No tasks match your filters"
          description="Try broadening your search term or clearing the status, department, and priority filters."
          actionLabel="Reset Filters"
          onAction={() => {
            setSearchTerm('');
            setStatusFilter('all');
            setDeptFilter('all');
            setPriorityFilter('all');
          }}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {filtered.map((t) => {
            const isTransitioning = transitioningId === t.id;
            const isTerminal = t.status === 'Completed' || t.status === 'Rejected';
            const userDept = (user?.department || '').toLowerCase();
            const taskDept = (t.responsible_department || '').toLowerCase();
            const hasResourceAccess = !isEmployee || (userDept && (userDept.includes(taskDept) || taskDept.includes(userDept)));

            return (
              <div
                key={t.id}
                style={{
                  border: '1px solid var(--bp-border)',
                  borderLeft: `4px solid ${
                    statusVariant(t.status) === 'success'
                      ? 'var(--bp-success)'
                      : statusVariant(t.status) === 'warning'
                      ? 'var(--bp-warning)'
                      : statusVariant(t.status) === 'danger'
                      ? 'var(--bp-danger)'
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
                {/* Header */}
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
                      {t.id}
                    </code>
                    <Badge variant={statusVariant(t.status)}>{t.status.toUpperCase()}</Badge>
                    <Badge variant={priorityVariant(t.priority)}>{t.priority}</Badge>
                    <span style={{ fontSize: '0.8rem', color: 'var(--bp-text-muted)' }}>
                      Dept: <strong>{t.responsible_department}</strong>
                    </span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--bp-text-muted)' }}>
                      Role: <strong>{t.suggested_owner_role}</strong>
                    </span>
                  </div>

                  <div style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)' }}>
                    Due: <strong>{t.suggested_deadline}</strong>
                  </div>
                </div>

                {/* Task Title & Problem */}
                <div>
                  <h4 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--bp-text)', margin: '0 0 0.35rem 0' }}>
                    {t.recommended_action}
                  </h4>
                  <p style={{ fontSize: '0.84rem', color: 'var(--bp-text-muted)', margin: 0, lineHeight: 1.5 }}>
                    <strong>Problem:</strong> {t.problem_description}
                  </p>
                </div>

                {/* Expected Outcome & Verification */}
                <div
                  style={{
                    background: 'var(--bp-surface-alt)',
                    borderRadius: 'var(--bp-radius)',
                    padding: '0.65rem 0.85rem',
                    fontSize: '0.8rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.25rem',
                  }}
                >
                  <div>
                    <strong style={{ color: 'var(--bp-text)' }}>Expected Outcome:</strong>{' '}
                    <span style={{ color: 'var(--bp-text-muted)' }}>{t.expected_outcome}</span>
                  </div>
                  <div>
                    <strong style={{ color: 'var(--bp-purple)' }}>Verification:</strong>{' '}
                    <span style={{ color: 'var(--bp-text-muted)' }}>{t.verification_criteria}</span>
                  </div>
                  {t.completion_details && (
                    <div style={{ color: 'var(--bp-success)', marginTop: '0.25rem', fontWeight: 600 }}>
                      ✓ Completion Details: {t.completion_details} (Completed at {new Date(t.completed_at || '').toLocaleDateString()})
                    </div>
                  )}
                  {t.rejection_reason && (
                    <div style={{ color: 'var(--bp-danger)', marginTop: '0.25rem', fontWeight: 600 }}>
                      ✕ Rejection Reason: {t.rejection_reason}
                    </div>
                  )}
                </div>

                {/* Lifecycle Transitions & Task Actions */}
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
                    <Button variant="ghost" size="sm" onClick={() => onViewHistory(t.id)}>
                       📜 Audit & Notes
                    </Button>
                    {!isTerminal && (
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={!canAssign}
                        title={!canAssign ? 'Task reassignment restricted to CEO / Admin or Operations Manager' : undefined}
                        onClick={() => handleOpenReassignModal(t)}
                      >
                        ⚙️ Reassign / Due Date
                      </Button>
                    )}
                  </div>

                  {/* Transition buttons enforcing allowed state machine */}
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    {!hasResourceAccess && !isTerminal && (
                      <span
                        style={{
                          fontSize: '0.75rem',
                          color: 'var(--bp-text-muted)',
                          padding: '0.2rem 0.5rem',
                          background: '#F1F5F9',
                          borderRadius: '4px',
                          border: '1px solid #CBD5E1',
                        }}
                        title={`Task assigned to ${t.responsible_department}. Your department: ${user?.department}.`}
                      >
                        🔒 Dept Locked ({t.responsible_department})
                      </span>
                    )}

                    {t.status === 'Approved' && (
                      <>
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={!hasResourceAccess}
                          loading={isTransitioning}
                          onClick={() => void handleMarkOverdue(t)}
                        >
                          Mark Overdue
                        </Button>
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={!hasResourceAccess}
                          loading={isTransitioning}
                          onClick={() => void handleStartExecution(t)}
                        >
                          Start Execution ⏳
                        </Button>
                      </>
                    )}

                    {t.status === 'In Progress' && (
                      <>
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={!hasResourceAccess}
                          loading={isTransitioning}
                          onClick={() => void handleMarkOverdue(t)}
                        >
                          Mark Overdue
                        </Button>
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={!hasResourceAccess}
                          loading={isTransitioning}
                          onClick={() => handleOpenCompleteModal(t)}
                        >
                          Complete Task ✅
                        </Button>
                      </>
                    )}

                    {t.status === 'Overdue' && (
                      <>
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={!hasResourceAccess}
                          loading={isTransitioning}
                          onClick={() => void handleStartExecution(t)}
                        >
                          Resume In Progress ⏳
                        </Button>
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={!hasResourceAccess}
                          loading={isTransitioning}
                          onClick={() => handleOpenCompleteModal(t)}
                        >
                          Complete Task ✅
                        </Button>
                      </>
                    )}

                    {isTerminal && (
                      <span style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)' }}>
                        Terminal state: No further status transitions allowed.
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Complete Task Modal */}
      {completingTask && (
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
          onClick={() => setCompletingTask(null)}
        >
          <div
            style={{
              background: 'var(--bp-surface)',
              borderRadius: 'var(--bp-radius-lg)',
              maxWidth: '540px',
              width: '100%',
              padding: '1.5rem',
              border: '1px solid var(--bp-border)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.25)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: '0 0 0.5rem 0', color: 'var(--bp-success)' }}>
              Complete Task: {completingTask.id}
            </h3>
            <p style={{ fontSize: '0.84rem', color: 'var(--bp-text-muted)', margin: '0 0 1rem 0' }}>
              Record completion details and execution verification for audit compliance.
            </p>

            {completeError && (
              <div style={{ color: 'var(--bp-danger)', fontSize: '0.82rem', marginBottom: '0.75rem' }}>
                ⚠️ {completeError}
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text)', display: 'block', marginBottom: '0.25rem' }}>
                  Completion Summary & Findings: *
                </label>
                <textarea
                  rows={2}
                  value={completionDetails}
                  onChange={(e) => setCompletionDetails(e.target.value)}
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

              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text)', display: 'block', marginBottom: '0.25rem' }}>
                  Execution Notes (optional):
                </label>
                <input
                  type="text"
                  placeholder="e.g. Deployed hotfix v2.4.1 to production, verified 0 timeouts"
                  value={completionNotes}
                  onChange={(e) => setCompletionNotes(e.target.value)}
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
              <Button variant="secondary" size="sm" onClick={() => setCompletingTask(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                loading={isCompleting}
                disabled={!completionDetails.trim()}
                onClick={() => void handleConfirmCompletion()}
              >
                Confirm Completion ✓
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Reassign / Reschedule Modal */}
      {reassigningTask && (
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
          onClick={() => setReassigningTask(null)}
        >
          <div
            style={{
              background: 'var(--bp-surface)',
              borderRadius: 'var(--bp-radius-lg)',
              maxWidth: '540px',
              width: '100%',
              padding: '1.5rem',
              border: '1px solid var(--bp-border)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.25)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: '0 0 0.5rem 0', color: 'var(--bp-text)' }}>
              Reassign Task: {reassigningTask.id}
            </h3>
            <p style={{ fontSize: '0.84rem', color: 'var(--bp-text-muted)', margin: '0 0 1rem 0' }}>
              Update assigned department, owner role, or extend completion deadline.
            </p>

            {reassignError && (
              <div style={{ color: 'var(--bp-danger)', fontSize: '0.82rem', marginBottom: '0.75rem' }}>
                ⚠️ {reassignError}
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--bp-text)', display: 'block', marginBottom: '0.25rem' }}>
                  Responsible Department:
                </label>
                <input
                  type="text"
                  value={newDepartment}
                  onChange={(e) => setNewDepartment(e.target.value)}
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
                  Suggested Owner Role (no employee names):
                </label>
                <input
                  type="text"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
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
                  Adjusted Deadline:
                </label>
                <input
                  type="date"
                  value={newDeadline}
                  onChange={(e) => setNewDeadline(e.target.value)}
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
                  Reason for Reassignment / Extension:
                </label>
                <input
                  type="text"
                  placeholder="e.g. Dependent team approval pending, schedule extended by 3 days"
                  value={reassignReason}
                  onChange={(e) => setReassignReason(e.target.value)}
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
              <Button variant="secondary" size="sm" onClick={() => setReassigningTask(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                loading={isReassigning}
                onClick={() => void handleConfirmReassign()}
              >
                Apply Reassignment
              </Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
