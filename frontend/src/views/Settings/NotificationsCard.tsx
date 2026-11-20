import React from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';

interface NotificationItem {
  id: string;
  title: string;
  description: string;
  category: string;
  defaultEmail: boolean;
  defaultInApp: boolean;
}

const NOTIFICATION_EVENTS: NotificationItem[] = [
  {
    id: 'anomaly',
    title: 'New Anomaly Detected',
    description: 'Immediate alert when quantitative metric shifts trigger critical or warning anomalies.',
    category: 'Telemetry Intelligence',
    defaultEmail: true,
    defaultInApp: true,
  },
  {
    id: 'investigation',
    title: 'Multi-Agent Investigation Completed',
    description: 'Notification when Analyst, Connector, Router, and Writer synthesize a root cause brief.',
    category: 'Investigation Engine',
    defaultEmail: false,
    defaultInApp: true,
  },
  {
    id: 'action_approval',
    title: 'Action Proposal Pending Approval',
    description: 'High-priority alert requiring executive/director sign-off for operational interventions.',
    category: 'Action Governance',
    defaultEmail: true,
    defaultInApp: true,
  },
  {
    id: 'task_update',
    title: 'Departmental Task Assigned or Updated',
    description: 'Alerts for team leads on status changes, deadline shifts, and department task completions.',
    category: 'Task Management',
    defaultEmail: false,
    defaultInApp: true,
  },
  {
    id: 'verification_result',
    title: 'Verification Milestone Evaluated',
    description: 'Follow-up alert reporting whether an approved action achieved its intended metric improvement.',
    category: 'Outcome Verification',
    defaultEmail: true,
    defaultInApp: true,
  },
];

export const NotificationsCard: React.FC = () => {
  return (
    <Card
      header={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem' }}>🔔</span>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--bp-navy)', margin: 0 }}>
              Notification Preferences
            </h3>
          </div>
          <Badge variant="neutral">Planned Functionality</Badge>
        </div>
      }
    >
      <p style={{ fontSize: '0.825rem', color: 'var(--bp-text-muted)', margin: '0 0 1rem 0' }}>
        Configure outbound alerting channels for business events, multi-agent briefs, and verification milestones.
      </p>

      {/* Active In-App Status Note */}
      <div
        style={{
          padding: '0.75rem 1rem',
          background: '#F0FDF4',
          border: '1px solid #86EFAC',
          borderRadius: '6px',
          fontSize: '0.8rem',
          color: '#166534',
          marginBottom: '1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        <span>✓</span>
        <div>
          <strong>Active Live Telemetry:</strong> In-app navigation badges for <strong>Pending Approvals</strong> and <strong>Critical Anomalies</strong> are live and updating across the application sidebar and topbar.
        </div>
      </div>

      {/* Planned Channels Table */}
      <div style={{ overflowX: 'auto', border: '1px solid var(--bp-border)', borderRadius: '8px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
          <thead>
            <tr style={{ background: '#F8F8FC', borderBottom: '2px solid var(--bp-border)', color: 'var(--bp-text-muted)' }}>
              <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600 }}>Event & Trigger</th>
              <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600 }}>Category</th>
              <th style={{ padding: '0.75rem 1rem', textAlign: 'center', fontWeight: 600 }}>Email Digest</th>
              <th style={{ padding: '0.75rem 1rem', textAlign: 'center', fontWeight: 600 }}>In-App Push</th>
              <th style={{ padding: '0.75rem 1rem', textAlign: 'right', fontWeight: 600 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {NOTIFICATION_EVENTS.map((item) => (
              <tr key={item.id} style={{ borderBottom: '1px solid var(--bp-border)' }}>
                <td style={{ padding: '0.75rem 1rem' }}>
                  <div style={{ fontWeight: 600, color: 'var(--bp-navy)', marginBottom: '0.15rem' }}>
                    {item.title}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--bp-text-muted)' }}>
                    {item.description}
                  </div>
                </td>
                <td style={{ padding: '0.75rem 1rem', color: 'var(--bp-text-muted)' }}>
                  {item.category}
                </td>
                <td style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                  <input
                    type="checkbox"
                    disabled
                    checked={item.defaultEmail}
                    style={{ cursor: 'not-allowed', accentColor: 'var(--bp-purple)' }}
                  />
                </td>
                <td style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                  <input
                    type="checkbox"
                    disabled
                    checked={item.defaultInApp}
                    style={{ cursor: 'not-allowed', accentColor: 'var(--bp-purple)' }}
                  />
                </td>
                <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                  <Badge variant="neutral">Roadmap</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ fontSize: '0.75rem', color: 'var(--bp-text-muted)', marginTop: '0.75rem' }}>
        * External webhook (Slack/Teams) and SMTP dispatch engine controls will become configurable in a future release.
      </div>
    </Card>
  );
};
