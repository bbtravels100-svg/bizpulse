import React from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { DatasetSummary } from '../../types/dataSources';
import { useAuth } from '../../context/AuthContext';

interface Props {
  datasets: DatasetSummary[];
  onPreview: (dataset: DatasetSummary) => void;
  onUpload: (dataset: DatasetSummary) => void;
}

const DATASET_ICONS: Record<string, string> = {
  sales: '💳',
  costs: '🏷️',
  funnel: '🔽',
  events: '⚡',
};

export const DatasetsTable: React.FC<Props> = ({ datasets, onPreview, onUpload }) => {
  const { user } = useAuth();
  const isCeo = Boolean(user?.role && (user.role.includes('CEO') || user.role.includes('Admin')));
  return (
    <Card
      header={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--bp-navy)', margin: 0 }}>
              Primary Business Datasets
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--bp-text-muted)', margin: '0.2rem 0 0 0' }}>
              Ground-truth CSV datasets powering BizPulse analytics, anomaly detection, and verification models.
            </p>
          </div>
          <Badge variant="info">{datasets.length} Active Sources</Badge>
        </div>
      }
    >
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid var(--bp-border)', color: 'var(--bp-text-muted)' }}>
              <th style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>Dataset</th>
              <th style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>Records</th>
              <th style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>Schema & Columns</th>
              <th style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>File Size</th>
              <th style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>Status</th>
              <th style={{ padding: '0.75rem 1rem', fontWeight: 600 }}>Last Modified</th>
              <th style={{ padding: '0.75rem 1rem', fontWeight: 600, textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((d) => {
              const icon = DATASET_ICONS[d.id] || '📄';
              const sizeKb = (d.file_size_bytes / 1024).toFixed(1);
              const lastMod = d.last_modified
                ? new Date(d.last_modified).toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                : 'Unknown';

              const statusBadgeVariant =
                d.status === 'healthy' ? 'success' : d.status === 'validation_error' ? 'danger' : 'warning';

              return (
                <tr
                  key={d.id}
                  style={{
                    borderBottom: '1px solid var(--bp-border)',
                    transition: 'background-color 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#FAF9FF')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  {/* Dataset Name & Description */}
                  <td style={{ padding: '1rem', verticalAlign: 'top' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.65rem' }}>
                      <span style={{ fontSize: '1.35rem', lineHeight: 1 }}>{icon}</span>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{ fontWeight: 700, color: 'var(--bp-navy)', fontSize: '0.925rem' }}>
                            {d.name}
                          </span>
                          <code
                            style={{
                              fontSize: '0.72rem',
                              padding: '0.15rem 0.35rem',
                              background: '#F1F0F7',
                              borderRadius: '4px',
                              color: 'var(--bp-purple)',
                              fontWeight: 600,
                            }}
                          >
                            {d.filename}
                          </code>
                        </div>
                        <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.8rem', color: 'var(--bp-text-muted)', maxWidth: '320px' }}>
                          {d.description}
                        </p>
                      </div>
                    </div>
                  </td>

                  {/* Records Count */}
                  <td style={{ padding: '1rem', verticalAlign: 'top', fontWeight: 600, color: 'var(--bp-navy)' }}>
                    {d.record_count.toLocaleString()} rows
                  </td>

                  {/* Schema & Columns */}
                  <td style={{ padding: '1rem', verticalAlign: 'top' }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', maxWidth: '240px' }}>
                      {d.columns.slice(0, 4).map((col) => (
                        <span
                          key={col.name}
                          style={{
                            fontSize: '0.72rem',
                            padding: '0.1rem 0.35rem',
                            background: '#F8F8FC',
                            border: '1px solid var(--bp-border)',
                            borderRadius: '4px',
                            color: 'var(--bp-navy)',
                          }}
                        >
                          {col.name}
                        </span>
                      ))}
                      {d.columns.length > 4 && (
                        <span
                          style={{
                            fontSize: '0.72rem',
                            padding: '0.1rem 0.35rem',
                            background: 'var(--bp-light-purple)',
                            color: 'var(--bp-purple)',
                            borderRadius: '4px',
                            fontWeight: 600,
                          }}
                        >
                          +{d.columns.length - 4} more
                        </span>
                      )}
                    </div>
                  </td>

                  {/* File Size */}
                  <td style={{ padding: '1rem', verticalAlign: 'top', color: 'var(--bp-text-muted)', fontSize: '0.825rem' }}>
                    {sizeKb} KB
                  </td>

                  {/* Status Badge */}
                  <td style={{ padding: '1rem', verticalAlign: 'top' }}>
                    <Badge variant={statusBadgeVariant}>
                      {d.status === 'healthy' ? 'Healthy' : d.status === 'validation_error' ? 'Schema Error' : d.status}
                    </Badge>
                  </td>

                  {/* Last Modified */}
                  <td style={{ padding: '1rem', verticalAlign: 'top', fontSize: '0.8rem', color: 'var(--bp-text-muted)' }}>
                    {lastMod}
                  </td>

                  {/* Actions */}
                  <td style={{ padding: '1rem', verticalAlign: 'top', textAlign: 'right' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.5rem' }}>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => onPreview(d)}
                      >
                        Preview
                      </Button>
                      <Button
                        size="sm"
                        variant="primary"
                        disabled={!isCeo}
                        title={!isCeo ? 'CSV dataset upload restricted to CEO / Admin' : undefined}
                        onClick={() => onUpload(d)}
                      >
                        Upload CSV
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
};
