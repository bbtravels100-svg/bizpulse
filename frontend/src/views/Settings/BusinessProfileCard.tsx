import React from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { BusinessProfile } from '../../types/settings';

const DEFAULT_BUSINESS_PROFILE: BusinessProfile = {
  businessName: 'BizPulse Retail Store',
  businessEmail: 'operations@bizpulse.internal',
  industry: 'Consumer Hardware & Ergonomics',
  timezone: 'UTC (Coordinated Universal Time)',
  currency: 'USD ($)',
  fiscalPeriod: 'November 2026 Reporting Cycle',
};

export const BusinessProfileCard: React.FC = () => {
  const profile = DEFAULT_BUSINESS_PROFILE;

  return (
    <Card
      header={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem' }}>🏢</span>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--bp-navy)', margin: 0 }}>
              Business Profile
            </h3>
          </div>
          <Badge variant="info">Verified Domain</Badge>
        </div>
      }
    >
      <p style={{ fontSize: '0.825rem', color: 'var(--bp-text-muted)', margin: '0 0 1rem 0' }}>
        Operational business parameters synchronized directly with the connected data warehouse and sales catalog.
      </p>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '1rem',
          padding: '1rem',
          background: '#F8F8FC',
          borderRadius: '8px',
          border: '1px solid var(--bp-border)',
        }}
      >
        <div>
          <div style={{ fontSize: '0.72rem', color: 'var(--bp-text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.25rem' }}>
            Business Name
          </div>
          <div style={{ fontWeight: 600, color: 'var(--bp-navy)', fontSize: '0.9rem' }}>
            {profile.businessName}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.72rem', color: 'var(--bp-text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.25rem' }}>
            Industry
          </div>
          <div style={{ fontWeight: 600, color: 'var(--bp-navy)', fontSize: '0.9rem' }}>
            {profile.industry}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.72rem', color: 'var(--bp-text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.25rem' }}>
            Reporting Timezone
          </div>
          <div style={{ fontWeight: 600, color: 'var(--bp-navy)', fontSize: '0.9rem' }}>
            {profile.timezone}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.72rem', color: 'var(--bp-text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.25rem' }}>
            Base Currency
          </div>
          <div style={{ fontWeight: 600, color: 'var(--bp-navy)', fontSize: '0.9rem' }}>
            {profile.currency}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.72rem', color: 'var(--bp-text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.25rem' }}>
            Primary Operations Email
          </div>
          <div style={{ fontWeight: 600, color: 'var(--bp-navy)', fontSize: '0.9rem' }}>
            <code>{profile.businessEmail}</code>
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.72rem', color: 'var(--bp-text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.25rem' }}>
            Active Fiscal Window
          </div>
          <div style={{ fontWeight: 600, color: 'var(--bp-navy)', fontSize: '0.9rem' }}>
            {profile.fiscalPeriod}
          </div>
        </div>
      </div>
    </Card>
  );
};
