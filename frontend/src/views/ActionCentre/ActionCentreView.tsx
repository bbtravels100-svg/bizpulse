import { useEffect, useState, useCallback } from 'react';
import { ViewContainer } from '../../components/layout/ViewContainer';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { ErrorState } from '../../components/common/ErrorState';
import { useApp } from '../../context/AppContext';
import { apiGet, apiPost, apiPatch } from '../../api/client';
import { ActionOverviewCards } from './ActionOverviewCards';
import { ApprovalRequestsSection } from './ApprovalRequestsSection';
import { TaskManagementSection } from './TaskManagementSection';
import { TaskHistoryModal } from './TaskHistoryModal';
import type {
  ActionResponse,
  ActionStatus,
  ActionUpdateRequest,
  TaskAssignmentUpdateRequest,
} from '../../types';

type Tab = 'approvals' | 'tasks' | 'audit';
type RolePerspective = 'ceo' | 'manager' | 'team';

export function ActionCentreView() {
  const { setView, setPendingApprovalCount } = useApp();

  const [activeTab, setActiveTab] = useState<Tab>('approvals');
  const [rolePerspective, setRolePerspective] = useState<RolePerspective>('ceo');

  const [actions, setActions] = useState<ActionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedbackNotice, setFeedbackNotice] = useState<string | null>(null);

  // History modal
  const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(null);

  // Load all actions from backend
  const fetchActions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<ActionResponse[]>('/api/actions');
      if (Array.isArray(res)) {
        setActions(res);
        const pending = res.filter((a) => a.status === 'Pending Approval').length;
        setPendingApprovalCount(pending);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not retrieve actions from backend');
    } finally {
      setLoading(false);
    }
  }, [setPendingApprovalCount]);

  useEffect(() => {
    void fetchActions();
  }, [fetchActions]);

  // Approve proposal handler
  const handleApprove = async (actionId: string, notes?: string) => {
    try {
      await apiPost(`/api/actions/${actionId}/approve`, {
        approver: 'Executive Business Manager',
        notes: notes || undefined,
      });
      setFeedbackNotice(`Action ${actionId} approved. It has entered the active task workflow.`);
      void fetchActions();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Approval failed');
      throw err;
    }
  };

  // Reject proposal handler
  const handleReject = async (actionId: string, reason: string) => {
    try {
      await apiPost(`/api/actions/${actionId}/reject`, {
        reason,
        rejected_by: 'Executive Business Manager',
      });
      setFeedbackNotice(`Proposal ${actionId} rejected. Reason logged to audit trail.`);
      void fetchActions();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Rejection failed');
      throw err;
    }
  };

  // Edit proposal pre-approval
  const handleEditProposal = async (actionId: string, updates: ActionUpdateRequest) => {
    try {
      await apiPatch(`/api/actions/${actionId}`, updates);
      setFeedbackNotice(`Proposal ${actionId} parameters updated successfully.`);
      void fetchActions();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Edit failed');
      throw err;
    }
  };

  // Task status transition
  const handleUpdateStatus = async (
    actionId: string,
    newStatus: ActionStatus,
    notes?: string,
    completionDetails?: string
  ) => {
    try {
      await apiPatch(`/api/tasks/${actionId}/status`, {
        new_status: newStatus,
        notes: notes || undefined,
        completion_details: completionDetails || undefined,
      });
      setFeedbackNotice(`Task ${actionId} status transitioned to '${newStatus}'.`);
      void fetchActions();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Status transition failed');
      throw err;
    }
  };

  // Task assignment update
  const handleUpdateAssignment = async (actionId: string, updates: TaskAssignmentUpdateRequest) => {
    try {
      await apiPatch(`/api/tasks/${actionId}/assignment`, updates);
      setFeedbackNotice(`Task ${actionId} assignment and deadline updated.`);
      void fetchActions();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Assignment update failed');
      throw err;
    }
  };

  // Breakdown counts
  const pendingProposals = actions.filter((a) => a.status === 'Pending Approval');
  const activeWorkflowTasks = actions.filter((a) => a.status !== 'Pending Approval');

  const pendingCount = pendingProposals.length;
  const approvedCount = actions.filter((a) => a.status === 'Approved').length;
  const inProgressCount = actions.filter((a) => a.status === 'In Progress').length;
  const completedCount = actions.filter((a) => a.status === 'Completed').length;
  const overdueCount = actions.filter((a) => a.status === 'Overdue').length;

  return (
    <ViewContainer
      title="Action Centre"
      subtitle="Executive oversight, human manager approval workflows, and business task execution tracking."
      actions={
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <Button variant="secondary" size="sm" onClick={() => void fetchActions()}>
            ↻ Refresh Tasks
          </Button>
          <Button variant="primary" size="sm" onClick={() => setView('investigations')}>
            + New Investigation
          </Button>
        </div>
      }
    >
      {/* Real Backend Statistics Cards */}
      <ActionOverviewCards
        pendingCount={pendingCount}
        approvedCount={approvedCount}
        inProgressCount={inProgressCount}
        completedCount={completedCount}
        overdueCount={overdueCount}
        loading={loading}
        error={error}
      />

      {/* Role Perspective Selector & Compliance Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--bp-surface)',
          border: '1px solid var(--bp-border)',
          borderRadius: 'var(--bp-radius-lg)',
          padding: '0.75rem 1.25rem',
          marginBottom: '1.25rem',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--bp-text-muted)' }}>
            View Perspective:
          </span>
          <div style={{ display: 'flex', gap: '0.35rem' }}>
            <button
              type="button"
              onClick={() => {
                setRolePerspective('ceo');
                setActiveTab('approvals');
              }}
              style={{
                fontSize: '0.8rem',
                padding: '0.35rem 0.75rem',
                borderRadius: 'var(--bp-radius)',
                border: '1px solid var(--bp-border)',
                background: rolePerspective === 'ceo' ? 'var(--bp-purple)' : 'transparent',
                color: rolePerspective === 'ceo' ? '#fff' : 'var(--bp-text)',
                cursor: 'pointer',
                fontWeight: rolePerspective === 'ceo' ? 600 : 400,
              }}
            >
              👔 Executive / CEO (Approvals)
            </button>
            <button
              type="button"
              onClick={() => {
                setRolePerspective('manager');
                setActiveTab('tasks');
              }}
              style={{
                fontSize: '0.8rem',
                padding: '0.35rem 0.75rem',
                borderRadius: 'var(--bp-radius)',
                border: '1px solid var(--bp-border)',
                background: rolePerspective === 'manager' ? 'var(--bp-purple)' : 'transparent',
                color: rolePerspective === 'manager' ? '#fff' : 'var(--bp-text)',
                cursor: 'pointer',
                fontWeight: rolePerspective === 'manager' ? 600 : 400,
              }}
            >
              🏢 Department Manager (Active Tasks)
            </button>
            <button
              type="button"
              onClick={() => {
                setRolePerspective('team');
                setActiveTab('tasks');
              }}
              style={{
                fontSize: '0.8rem',
                padding: '0.35rem 0.75rem',
                borderRadius: 'var(--bp-radius)',
                border: '1px solid var(--bp-border)',
                background: rolePerspective === 'team' ? 'var(--bp-purple)' : 'transparent',
                color: rolePerspective === 'team' ? '#fff' : 'var(--bp-text)',
                cursor: 'pointer',
                fontWeight: rolePerspective === 'team' ? 600 : 400,
              }}
            >
              👷 Team Lead (Execution)
            </button>
          </div>
        </div>

        <div style={{ fontSize: '0.76rem', color: 'var(--bp-text-muted)' }}>
          🔒 <em>Backend RBAC notice: Authenticated user roles are not yet implemented in API. Full controls are available.</em>
        </div>
      </div>

      {/* Global Feedback Notice if any */}
      {feedbackNotice && (
        <div
          style={{
            background: 'var(--bp-success-pale)',
            border: '1px solid var(--bp-success)',
            borderRadius: 'var(--bp-radius)',
            padding: '0.75rem 1rem',
            marginBottom: '1.25rem',
            color: 'var(--bp-success)',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>✓ {feedbackNotice}</span>
          <button
            type="button"
            onClick={() => setFeedbackNotice(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--bp-success)' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Global Error Banner */}
      {error && (
        <div style={{ marginBottom: '1.25rem' }}>
          <ErrorState message="Action Management Notice" detail={error} onRetry={() => void fetchActions()} />
        </div>
      )}

      {/* Tab Navigation Bar */}
      <div
        style={{
          display: 'flex',
          gap: '0.5rem',
          borderBottom: '2px solid var(--bp-border)',
          marginBottom: '1.25rem',
        }}
      >
        <button
          type="button"
          onClick={() => setActiveTab('approvals')}
          style={{
            padding: '0.65rem 1.25rem',
            background: 'transparent',
            border: 'none',
            borderBottom: activeTab === 'approvals' ? '2px solid var(--bp-purple)' : '2px solid transparent',
            marginBottom: '-2px',
            cursor: 'pointer',
            fontSize: '0.88rem',
            fontWeight: activeTab === 'approvals' ? 700 : 500,
            color: activeTab === 'approvals' ? 'var(--bp-purple)' : 'var(--bp-text-muted)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            transition: 'color 0.15s',
          }}
        >
          <span>Approval Requests</span>
          {pendingCount > 0 && <Badge variant="danger">{pendingCount}</Badge>}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('tasks')}
          style={{
            padding: '0.65rem 1.25rem',
            background: 'transparent',
            border: 'none',
            borderBottom: activeTab === 'tasks' ? '2px solid var(--bp-purple)' : '2px solid transparent',
            marginBottom: '-2px',
            cursor: 'pointer',
            fontSize: '0.88rem',
            fontWeight: activeTab === 'tasks' ? 700 : 500,
            color: activeTab === 'tasks' ? 'var(--bp-purple)' : 'var(--bp-text-muted)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            transition: 'color 0.15s',
          }}
        >
          <span>Active Tasks</span>
          <Badge variant="neutral">{activeWorkflowTasks.length}</Badge>
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'approvals' && (
        <ApprovalRequestsSection
          proposals={pendingProposals}
          onApprove={handleApprove}
          onReject={handleReject}
          onEdit={handleEditProposal}
          onViewHistory={(id) => setSelectedHistoryId(id)}
          onGoToInvestigations={() => setView('investigations')}
          loading={loading}
        />
      )}

      {activeTab === 'tasks' && (
        <TaskManagementSection
          tasks={activeWorkflowTasks}
          onUpdateStatus={handleUpdateStatus}
          onUpdateAssignment={handleUpdateAssignment}
          onViewHistory={(id) => setSelectedHistoryId(id)}
          onRefresh={() => void fetchActions()}
          loading={loading}
        />
      )}

      {/* Task History Modal / Drawer */}
      <TaskHistoryModal
        actionId={selectedHistoryId}
        isOpen={Boolean(selectedHistoryId)}
        onClose={() => setSelectedHistoryId(null)}
        onNoteAdded={() => void fetchActions()}
      />
    </ViewContainer>
  );
}
