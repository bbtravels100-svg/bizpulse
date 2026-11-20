import { useEffect, useState, useCallback } from 'react';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { apiGet, apiPost } from '../../api/client';
import type { ActionHistoryResponse, BadgeVariant } from '../../types';

interface TaskHistoryModalProps {
  actionId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onNoteAdded?: () => void;
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

export function TaskHistoryModal({
  actionId,
  isOpen,
  onClose,
  onNoteAdded,
}: TaskHistoryModalProps) {
  const [data, setData] = useState<ActionHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // New note state
  const [newNote, setNewNote] = useState('');
  const [author, setAuthor] = useState('Business Manager');
  const [submittingNote, setSubmittingNote] = useState(false);

  const fetchHistory = useCallback(async () => {
    if (!actionId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<ActionHistoryResponse>(`/api/tasks/${actionId}/history`);
      setData(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not fetch action history');
    } finally {
      setLoading(false);
    }
  }, [actionId]);

  useEffect(() => {
    if (isOpen && actionId) {
      void fetchHistory();
    } else {
      setData(null);
      setNewNote('');
    }
  }, [isOpen, actionId, fetchHistory]);

  const handleAddNote = async () => {
    if (!actionId || !newNote.trim()) return;
    setSubmittingNote(true);
    try {
      await apiPost(`/api/tasks/${actionId}/notes`, {
        note: newNote.trim(),
        author: author.trim() || 'Manager',
      });
      setNewNote('');
      void fetchHistory();
      if (onNoteAdded) onNoteAdded();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to add progress note');
    } finally {
      setSubmittingNote(false);
    }
  };

  if (!isOpen || !actionId) return null;

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
          width: '100%',
          maxWidth: '750px',
          maxHeight: '90vh',
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
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--bp-surface-alt)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '1.2rem' }}>📜</span>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, color: 'var(--bp-text)' }}>
              Action Audit Log & History
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
              <>
                <Badge variant={statusVariant(data.action.status)}>{data.action.status}</Badge>
                <Badge variant={priorityVariant(data.action.priority)}>{data.action.priority}</Badge>
              </>
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
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '1.5rem', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {loading ? (
            <LoadingSpinner label="Fetching audit records…" />
          ) : error ? (
            <div style={{ color: 'var(--bp-danger)', fontSize: '0.9rem', padding: '1rem', textAlign: 'center' }}>
              ⚠️ {error}
            </div>
          ) : data ? (
            <>
              {/* Action Context Box */}
              <div
                style={{
                  background: 'var(--bp-surface-alt)',
                  border: '1px solid var(--bp-border)',
                  borderRadius: 'var(--bp-radius)',
                  padding: '1rem',
                  fontSize: '0.85rem',
                }}
              >
                <div style={{ fontWeight: 600, color: 'var(--bp-text)', marginBottom: '0.35rem' }}>
                  {data.action.recommended_action}
                </div>
                <p style={{ color: 'var(--bp-text-muted)', margin: 0, lineHeight: 1.5 }}>
                  {data.action.problem_description}
                </p>
                <div
                  style={{
                    display: 'flex',
                    gap: '1rem',
                    flexWrap: 'wrap',
                    marginTop: '0.6rem',
                    fontSize: '0.78rem',
                    color: 'var(--bp-text-muted)',
                    borderTop: '1px solid var(--bp-border)',
                    paddingTop: '0.5rem',
                  }}
                >
                  <span>
                    Dept: <strong>{data.action.responsible_department}</strong>
                  </span>
                  <span>
                    Owner: <strong>{data.action.suggested_owner_role}</strong>
                  </span>
                  <span>
                    Due: <strong>{data.action.suggested_deadline}</strong>
                  </span>
                  <span>
                    Ref: <code>{data.action.investigation_id}</code>
                  </span>
                </div>
              </div>

              {/* Chronological Audit Log */}
              <div>
                <h4 style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--bp-text)', marginBottom: '0.75rem' }}>
                  🕒 Chronological Audit Trail ({data.audit_log.length})
                </h4>
                {data.audit_log.length === 0 ? (
                  <p style={{ fontSize: '0.82rem', color: 'var(--bp-text-muted)' }}>No audit log entries recorded.</p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                    {data.audit_log.map((entry) => (
                      <div
                        key={entry.id}
                        style={{
                          border: '1px solid var(--bp-border)',
                          borderRadius: 'var(--bp-radius)',
                          padding: '0.75rem 1rem',
                          background: 'var(--bp-surface)',
                          fontSize: '0.82rem',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.3rem',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Badge variant="info">{entry.action_type}</Badge>
                          <span style={{ fontSize: '0.75rem', color: 'var(--bp-text-muted)' }}>
                            {new Date(entry.timestamp).toLocaleString(undefined, {
                              dateStyle: 'medium',
                              timeStyle: 'short',
                            })}
                          </span>
                        </div>
                        {entry.details && (
                          <div style={{ color: 'var(--bp-text)', marginTop: '0.2rem' }}>
                            {entry.details}
                          </div>
                        )}
                        {(entry.previous_value || entry.new_value) && (
                          <div style={{ fontSize: '0.76rem', color: 'var(--bp-text-muted)' }}>
                            Transition: <code style={{ color: 'var(--bp-danger)' }}>{entry.previous_value || 'None'}</code> →{' '}
                            <code style={{ color: 'var(--bp-success)' }}>{entry.new_value}</code>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Progress Notes */}
              <div>
                <h4 style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--bp-text)', marginBottom: '0.75rem' }}>
                  💬 Threaded Progress Notes ({data.notes.length})
                </h4>
                {data.notes.length === 0 ? (
                  <p style={{ fontSize: '0.82rem', color: 'var(--bp-text-muted)' }}>
                    No progress updates added yet. Add one below.
                  </p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
                    {data.notes.map((note) => (
                      <div
                        key={note.id}
                        style={{
                          background: 'var(--bp-surface-alt)',
                          border: '1px solid var(--bp-border)',
                          borderRadius: 'var(--bp-radius)',
                          padding: '0.75rem 1rem',
                          fontSize: '0.82rem',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
                          <strong style={{ color: 'var(--bp-purple)' }}>{note.author}</strong>
                          <span style={{ fontSize: '0.75rem', color: 'var(--bp-text-muted)' }}>
                            {new Date(note.created_at).toLocaleString(undefined, {
                              dateStyle: 'medium',
                              timeStyle: 'short',
                            })}
                          </span>
                        </div>
                        <p style={{ margin: 0, color: 'var(--bp-text)', lineHeight: 1.5 }}>
                          {note.note}
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Add Progress Note Form */}
                <div
                  style={{
                    background: 'var(--bp-surface)',
                    border: '1px solid var(--bp-border)',
                    borderRadius: 'var(--bp-radius)',
                    padding: '0.85rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem',
                  }}
                >
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <input
                      type="text"
                      placeholder="Your title / role (e.g. Lead Engineer)"
                      value={author}
                      onChange={(e) => setAuthor(e.target.value)}
                      style={{
                        fontSize: '0.82rem',
                        padding: '0.4rem 0.6rem',
                        borderRadius: 'var(--bp-radius)',
                        border: '1px solid var(--bp-border)',
                        width: '200px',
                      }}
                    />
                  </div>
                  <textarea
                    placeholder="Append a progress update or observation to this task…"
                    rows={2}
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      borderRadius: 'var(--bp-radius)',
                      border: '1px solid var(--bp-border)',
                      fontSize: '0.82rem',
                      fontFamily: 'inherit',
                      resize: 'none',
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <Button
                      variant="primary"
                      size="sm"
                      loading={submittingNote}
                      disabled={!newNote.trim()}
                      onClick={handleAddNote}
                    >
                      Post Note
                    </Button>
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '0.85rem 1.5rem',
            borderTop: '1px solid var(--bp-border)',
            display: 'flex',
            justifyContent: 'flex-end',
            background: 'var(--bp-surface-alt)',
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
