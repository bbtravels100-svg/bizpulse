import React from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';

interface IntegrationItem {
  id: string;
  name: string;
  category: string;
  icon: string;
  description: string;
  entities: string[];
}

const FUTURE_INTEGRATIONS: IntegrationItem[] = [
  {
    id: 'ga4',
    name: 'Google Analytics 4',
    category: 'Web & App Analytics',
    icon: '📊',
    description:
      'Direct synchronization of e-commerce checkout events, organic campaign channels, and real-time user retention cohorts.',
    entities: ['checkout_events', 'traffic_source', 'session_bounce_rate'],
  },
  {
    id: 'shopify',
    name: 'Shopify Store Connect',
    category: 'E-commerce & Orders',
    icon: '🛍️',
    description:
      'Real-time webhook ingestion of transactions, inventory restocks, order refunds, and customer lifetime value metrics.',
    entities: ['orders', 'line_items', 'inventory_levels', 'refunds'],
  },
  {
    id: 'hubspot',
    name: 'HubSpot / Salesforce CRM',
    category: 'Sales & Customer Pipeline',
    icon: '🤝',
    description:
      'Cross-departmental pipeline synchronization: deals won, enterprise contract renewals, and sales cycle stage velocity.',
    entities: ['deals', 'lead_velocity', 'account_arr'],
  },
  {
    id: 'quickbooks',
    name: 'QuickBooks / Xero',
    category: 'Financial Ledger & ERP',
    icon: '🧾',
    description:
      'Continuous general ledger ingestion for live COGS reconciliation, operating expenditures, and automated margin audits.',
    entities: ['journal_entries', 'cogs_reconciliation', 'vendor_bills'],
  },
  {
    id: 'warehouse',
    name: 'Snowflake / BigQuery / Postgres',
    category: 'Enterprise Data Warehouse',
    icon: '🗄️',
    description:
      'Direct SQL warehouse connectors allowing automated scheduled extraction into BizPulse analytical feature stores.',
    entities: ['dbt_models', 'fact_tables', 'read_replica_queries'],
  },
];

export const FutureIntegrationsSection: React.FC = () => {
  return (
    <div style={{ marginTop: '2rem' }}>
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--bp-navy)', margin: 0 }}>
            Enterprise Integration Readiness
          </h3>
          <Badge variant="neutral">Roadmap</Badge>
        </div>
        <p style={{ fontSize: '0.825rem', color: 'var(--bp-text-muted)', margin: '0.25rem 0 0 0' }}>
          Direct native cloud connectors and live streaming webhooks currently scheduled in the BizPulse enterprise integration roadmap.
        </p>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))',
          gap: '1rem',
        }}
      >
        {FUTURE_INTEGRATIONS.map((item) => (
          <Card
            key={item.id}
            header={
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, color: 'var(--bp-navy)' }}>
                  <span style={{ fontSize: '1.25rem' }}>{item.icon}</span>
                  {item.name}
                </span>
                <Badge variant="neutral">Coming Soon</Badge>
              </div>
            }
          >
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--bp-purple)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
              {item.category}
            </div>
            <p style={{ fontSize: '0.825rem', color: 'var(--bp-text-muted)', margin: '0 0 0.85rem 0', lineHeight: 1.4 }}>
              {item.description}
            </p>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--bp-text-muted)', fontWeight: 600, marginBottom: '0.35rem' }}>
                Planned Data Entities:
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                {item.entities.map((e) => (
                  <span
                    key={e}
                    style={{
                      fontSize: '0.7rem',
                      padding: '0.1rem 0.35rem',
                      background: '#F8F8FC',
                      border: '1px solid var(--bp-border)',
                      borderRadius: '4px',
                      color: 'var(--bp-navy)',
                    }}
                  >
                    {e}
                  </span>
                ))}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
