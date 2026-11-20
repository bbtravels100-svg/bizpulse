import { useState } from 'react';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { ConfirmDialog } from '../../components/common/ConfirmDialog';
import { useChat } from '../../context/ChatContext';
import type { BadgeVariant } from '../../types';
import type { ActionItem, ActionPanelState, ChatMessage } from '../../types/chat';

const PRIORITY_VARIANT: Record<ActionItem['priority'], BadgeVariant> = {
  Critical: 'danger',
  High: 'warning',
  Medium: 'info',
  Low: 'neutral',
};

const Field = ({ label, value }: { label: string; value: string }) => (
  <div style={{ minWidth: 0 }}>
    <div
      style={{
        fontSize: '0.68rem',
        fontWeight: 700,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        color: 'var(--bp-text-muted)',
      }}
    >
      {label}
    </div>
    <div style={{ fontSize: '0.84rem', lineHeight: 1.5, overflowWrap: 'anywhere' }}>{value}</div>
  </div>
);

function ActionCard({ messageId, item, panel }: { messageId: string; item: ActionItem; panel: ActionPanelState }) {
  const { decideAction } = useChat();
  const decision = panel.decisions[item.id];
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState('');

  const working = decision?.state === 'working';
  const finished = decision?.state === 'approved' || decision?.state === 'rejected';

  return (
    <div
      style={{
        border: '1px solid var(--bp-border)',
        borderRadius: 'var(--bp-radius)',
        background: 'var(--bp-surface)',
        padding: '0.9rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.7rem',
      }}
    >
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <strong style={{ fontSize: '0.88rem', flex: '1 1 220px' }}>{item.recommended_action}</strong>
        <Badge variant={PRIORITY_VARIANT[item.priority]}>{item.priority}</Badge>
        <Badge variant="neutral">{item.status}</Badge>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '0.6rem 1rem',
        }}
      >
        <Field label="Department" value={item.responsible_department} />
        <Field label="Suggested owner (role)" value={item.suggested_owner_role} />
        <Field label="Suggested deadline" value={item.suggested_deadline} />
        <Field label="Expected outcome" value={item.expected_outcome} />
        <Field label="Verification criteria" value={item.verification_criteria} />
      </div>

      {finished ? (
        <div
          style={{
            fontSize: '0.82rem',
            fontWeight: 600,
            color: decision.state === 'approved' ? 'var(--bp-success)' : 'var(--bp-text-muted)',
          }}
        >
          {decision.state === 'approved' ? '✓ ' : '✕ '}
          {decision.message}
        </div>
      ) : rejecting ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reason for rejecting (required, at least 3 characters)"
            rows={2}
            style={{ resize: 'vertical' }}
            aria-label="Rejection reason"
          />
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <Button
              variant="danger"
              size="sm"
              loading={working}
              disabled={reason.trim().length < 3}
              onClick={() => void decideAction(messageId, item.id, 'reject', reason.trim())}
            >
              Confirm rejection
            </Button>
            <Button variant="ghost" size="sm" disabled={working} onClick={() => setRejecting(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <Button variant="primary" size="sm" loading={working} onClick={() => setConfirmOpen(true)}>
            Approve
          </Button>
          <Button variant="secondary" size="sm" disabled={working} onClick={() => setRejecting(true)}>
            Reject…
          </Button>
          <span style={{ fontSize: '0.74rem', color: 'var(--bp-text-muted)' }}>
            Awaiting your decision — nothing happens until you choose.
          </span>
        </div>
      )}

      {decision?.state === 'error' && (
        <div style={{ fontSize: '0.8rem', color: 'var(--bp-danger)' }}>{decision.message}</div>
      )}

      <ConfirmDialog
        open={confirmOpen}
        title="Approve this action?"
        description="The action will enter the active task workflow. BizPulse does not send emails, WhatsApp, Slack or Teams messages — nobody is notified automatically."
        confirmLabel="Approve action"
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => {
          setConfirmOpen(false);
          void decideAction(messageId, item.id, 'approve');
        }}
      />
    </div>
  );
}

export function ActionProposals({ message }: { message: ChatMessage }) {
  const { prepareActions, isLoading } = useChat();
  const panel = message.actions;

  if (!message.response?.can_propose_actions) return null;

  return (
    <div
      style={{
        borderTop: '1px dashed var(--bp-border-dark)',
        marginTop: '0.25rem',
        paddingTop: '0.85rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.7rem',
      }}
    >
      {!panel && (
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <Button variant="primary" size="sm" disabled={isLoading} onClick={() => void prepareActions(message.id)}>
            Prepare action proposals
          </Button>
          <span style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)' }}>
            Drafts proposals only. You review and approve each one.
          </span>
        </div>
      )}

      {panel?.status === 'loading' && (
        <div style={{ fontSize: '0.85rem', color: 'var(--bp-text-muted)' }}>
          Preparing proposals with the existing action system… this can take up to a minute.
        </div>
      )}

      {panel?.status === 'error' && (
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.84rem', color: 'var(--bp-danger)' }}>{panel.error}</span>
          <Button variant="secondary" size="sm" onClick={() => void prepareActions(message.id)}>
            Try again
          </Button>
        </div>
      )}

      {panel?.status === 'ready' && (
        <>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--bp-purple)' }}>
            {panel.items.length} proposed action{panel.items.length === 1 ? '' : 's'} — pending your approval
          </div>
          {panel.items.length === 0 && (
            <div style={{ fontSize: '0.84rem', color: 'var(--bp-text-muted)' }}>
              The action system returned no proposals.
            </div>
          )}
          {panel.items.map((item) => (
            <ActionCard key={item.id} messageId={message.id} item={item} panel={panel} />
          ))}
        </>
      )}
    </div>
  );
}
