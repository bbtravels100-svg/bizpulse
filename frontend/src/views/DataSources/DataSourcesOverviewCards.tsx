import React from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { DatasetSummary } from '../../types/dataSources';

interface Props {
  datasets: DatasetSummary[];
}

export const DataSourcesOverviewCards: React.FC<Props> = ({ datasets }) => {
  const totalDatasets = datasets.length;
  const totalRecords = datasets.reduce((sum, d) => sum + (d.record_count || 0), 0);
  const healthyCount = datasets.filter((d) => d.status === 'healthy').length;
  const totalBytes = datasets.reduce((sum, d) => sum + (d.file_size_bytes || 0), 0);
  const totalKb = (totalBytes / 1024).toFixed(1);

  // Find most recent last_modified
  const lastUpdatedDates = datasets
    .map((d) => (d.last_modified ? new Date(d.last_modified).getTime() : 0))
    .filter((t) => t > 0);
  const latestTimestamp = lastUpdatedDates.length > 0 ? Math.max(...lastUpdatedDates) : null;
  const lastUpdatedStr = latestTimestamp
    ? new Date(latestTimestamp).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'Live';

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}
    >
      {/* 1. Total Datasets */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--bp-text-muted)', textTransform: 'uppercase' }}>
            Connected Datasets
          </span>
          <span style={{ fontSize: '1.25rem' }}>📂</span>
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--bp-navy)', lineHeight: 1.1 }}>
          {totalDatasets}
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)', marginTop: '0.35rem' }}>
          4 official business domains
        </div>
      </Card>

      {/* 2. Total Records */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--bp-text-muted)', textTransform: 'uppercase' }}>
            Total Ingested Rows
          </span>
          <span style={{ fontSize: '1.25rem' }}>📊</span>
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--bp-navy)', lineHeight: 1.1 }}>
          {totalRecords.toLocaleString()}
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)', marginTop: '0.35rem' }}>
          Active verified records
        </div>
      </Card>

      {/* 3. Pipeline Health */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--bp-text-muted)', textTransform: 'uppercase' }}>
            Pipeline Health
          </span>
          <Badge variant={healthyCount === totalDatasets && totalDatasets > 0 ? 'success' : 'warning'}>
            {healthyCount === totalDatasets && totalDatasets > 0 ? 'All Healthy' : 'Attention'}
          </Badge>
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--bp-navy)', lineHeight: 1.1 }}>
          {healthyCount} / {totalDatasets}
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)', marginTop: '0.35rem' }}>
          Validated against schemas
        </div>
      </Card>

      {/* 4. Storage Footprint */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--bp-text-muted)', textTransform: 'uppercase' }}>
            Data Storage
          </span>
          <span style={{ fontSize: '1.25rem' }}>💾</span>
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--bp-navy)', lineHeight: 1.1 }}>
          {totalKb} KB
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)', marginTop: '0.35rem' }}>
          On-disk CSV storage
        </div>
      </Card>

      {/* 5. Last Sync */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--bp-text-muted)', textTransform: 'uppercase' }}>
            Last Ingestion
          </span>
          <span style={{ fontSize: '1.25rem' }}>🕒</span>
        </div>
        <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--bp-navy)', lineHeight: 1.2, marginTop: '0.2rem' }}>
          {lastUpdatedStr}
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)', marginTop: '0.35rem' }}>
          Automatic file polling
        </div>
      </Card>
    </div>
  );
};
