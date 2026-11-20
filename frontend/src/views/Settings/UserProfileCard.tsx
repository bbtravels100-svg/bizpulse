import React from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { UserProfile } from '../../types/settings';
import { useAuth } from '../../context/AuthContext';

const DEFAULT_USER: UserProfile = {
  name: 'Alex Morgan',
  role: 'Operations Manager',
  department: 'Operations & Executive Leadership',
  email: 'alex.morgan@bizpulse.internal',
  capabilities: [
    'Review & Approve Action Proposals',
    'Trigger Root Cause Investigations',
    'Manage Departmental Tasks',
    'Execute Verification Runs',
    'Manage Data Sources & CSV Telemetry',
  ],
};

export const UserProfileCard: React.FC = () => {
  const { user: authUser } = useAuth();
  const user: UserProfile = authUser
    ? {
        name: authUser.name,
        role: authUser.role,
        department: authUser.department,
        email: authUser.email,
        capabilities: DEFAULT_USER.capabilities,
      }
    : DEFAULT_USER;

  return (
    <Card
      header={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem' }}>👤</span>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--bp-navy)', margin: 0 }}>
              User Profile & Account
            </h3>
          </div>
          <Badge variant="success">Active Session</Badge>
        </div>
      }
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1.25rem', marginBottom: '1.25rem' }}>
        <div
          style={{
            width: '52px',
            height: '52px',
            borderRadius: '50%',
            background: 'var(--bp-light-purple)',
            color: 'var(--bp-purple)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.35rem',
            fontWeight: 700,
            flexShrink: 0,
            border: '2px solid var(--bp-purple)',
          }}
        >
          AM
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: 'var(--bp-navy)' }}>
              {user.name}
            </h4>
            <Badge variant="info">{user.role}</Badge>
          </div>
          <div style={{ fontSize: '0.825rem', color: 'var(--bp-text-muted)', marginTop: '0.2rem' }}>
            {user.email} • {user.department}
          </div>
        </div>
      </div>

      <div
        style={{
          padding: '0.85rem 1rem',
          background: '#F8F8FC',
          borderRadius: '8px',
          border: '1px solid var(--bp-border)',
          marginBottom: '1rem',
        }}
      >
        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--bp-navy)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
          Granted Operational Capabilities:
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
          {user.capabilities.map((cap) => (
            <span
              key={cap}
              style={{
                fontSize: '0.78rem',
                padding: '0.2rem 0.5rem',
                background: '#FFFFFF',
                border: '1px solid var(--bp-border)',
                borderRadius: '4px',
                color: 'var(--bp-navy)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
              }}
            >
              <span style={{ color: 'var(--bp-purple)', fontSize: '0.85rem' }}>✓</span>
              {cap}
            </span>
          ))}
        </div>
      </div>

      <div
        style={{
          padding: '0.75rem 1rem',
          background: '#FAF9FF',
          border: '1px solid var(--bp-info-border)',
          borderRadius: '6px',
          fontSize: '0.8rem',
          color: 'var(--bp-text-muted)',
          lineHeight: 1.4,
        }}
      >
        🔒 <strong>Enterprise Governance:</strong> User credentials, role assignments, and session tokens are authenticated via centralized SAML / OIDC Single Sign-On. Direct password modification is handled by your enterprise identity provider.
      </div>
    </Card>
  );
};
