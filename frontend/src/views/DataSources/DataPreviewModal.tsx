import React, { useState, useEffect } from 'react';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { apiGet } from '../../api/client';
import { DatasetSummary, DatasetPreviewResponse } from '../../types/dataSources';

interface Props {
  isOpen: boolean;
  dataset: DatasetSummary | null;
  onClose: () => void;
}

export const DataPreviewModal: React.FC<Props> = ({ isOpen, dataset, onClose }) => {
  const [data, setData] = useState<DatasetPreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'preview' | 'schema'>('preview');

  useEffect(() => {
    if (isOpen && dataset) {
      setLoading(true);
      setError(null);
      setSearchQuery('');
      apiGet<DatasetPreviewResponse>(`/api/datasets/${dataset.id}/preview?limit=50`)
        .then((res) => {
          setData(res);
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : 'Failed to load dataset preview');
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setData(null);
    }
  }, [isOpen, dataset]);

  if (!isOpen || !dataset) return null;

  // Filter rows based on search
  const filteredRows =
    data?.rows.filter((row) => {
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return Object.values(row).some((val) => String(val ?? '').toLowerCase().includes(q));
    }) || [];

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
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.5rem',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          background: 'var(--bp-card-bg)',
          borderRadius: '12px',
          width: '100%',
          maxWidth: '1000px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 10px 10px -5px rgba(0, 0, 0, 0.1)',
          border: '1px solid var(--bp-border)',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--bp-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#FAF9FF',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--bp-navy)', margin: 0 }}>
                {dataset.name}
              </h2>
              <code
                style={{
                  fontSize: '0.78rem',
                  padding: '0.2rem 0.5rem',
                  background: 'var(--bp-light-purple)',
                  color: 'var(--bp-purple)',
                  borderRadius: '4px',
                  fontWeight: 600,
                }}
              >
                {dataset.filename}
              </code>
              <Badge variant="success">Loaded</Badge>
            </div>
            <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.825rem', color: 'var(--bp-text-muted)' }}>
              {dataset.description}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              fontSize: '1.25rem',
              cursor: 'pointer',
              color: 'var(--bp-text-muted)',
              padding: '0.25rem 0.5rem',
              borderRadius: '6px',
            }}
          >
            ✕
          </button>
        </div>

        {/* Tab navigation & Stats */}
        <div
          style={{
            padding: '0.75rem 1.5rem',
            borderBottom: '1px solid var(--bp-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#FFFFFF',
            flexWrap: 'wrap',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => setActiveTab('preview')}
              style={{
                padding: '0.4rem 0.85rem',
                borderRadius: '6px',
                border: 'none',
                fontWeight: 600,
                fontSize: '0.825rem',
                cursor: 'pointer',
                background: activeTab === 'preview' ? 'var(--bp-purple)' : '#F1F0F7',
                color: activeTab === 'preview' ? '#FFFFFF' : 'var(--bp-navy)',
                transition: 'all 0.15s ease',
              }}
            >
              Data Rows Preview ({data?.record_count ?? dataset.record_count} total)
            </button>
            <button
              onClick={() => setActiveTab('schema')}
              style={{
                padding: '0.4rem 0.85rem',
                borderRadius: '6px',
                border: 'none',
                fontWeight: 600,
                fontSize: '0.825rem',
                cursor: 'pointer',
                background: activeTab === 'schema' ? 'var(--bp-purple)' : '#F1F0F7',
                color: activeTab === 'schema' ? '#FFFFFF' : 'var(--bp-navy)',
                transition: 'all 0.15s ease',
              }}
            >
              Schema & Column Types ({dataset.columns.length})
            </button>
          </div>

          {activeTab === 'preview' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input
                type="text"
                placeholder="Search sample rows..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  padding: '0.35rem 0.75rem',
                  fontSize: '0.825rem',
                  border: '1px solid var(--bp-border)',
                  borderRadius: '6px',
                  outline: 'none',
                  width: '200px',
                }}
              />
              <span style={{ fontSize: '0.78rem', color: 'var(--bp-text-muted)' }}>
                Showing {filteredRows.length} of {data?.rows.length ?? 0} loaded rows
              </span>
            </div>
          )}
        </div>

        {/* Content Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem 1.5rem' }}>
          {loading && (
            <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--bp-text-muted)' }}>
              <div
                style={{
                  display: 'inline-block',
                  width: '32px',
                  height: '32px',
                  border: '3px solid var(--bp-light-purple)',
                  borderTopColor: 'var(--bp-purple)',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                  marginBottom: '0.75rem',
                }}
              />
              <div>Loading ground-truth dataset records...</div>
            </div>
          )}

          {error && (
            <div
              style={{
                padding: '1rem',
                background: '#FEF2F2',
                border: '1px solid #FCA5A5',
                borderRadius: '8px',
                color: '#991B1B',
                fontSize: '0.875rem',
              }}
            >
              <strong>Error loading preview:</strong> {error}
            </div>
          )}

          {!loading && !error && data && activeTab === 'preview' && (
            <div style={{ overflowX: 'auto', border: '1px solid var(--bp-border)', borderRadius: '8px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
                <thead>
                  <tr style={{ background: '#F8F8FC', borderBottom: '2px solid var(--bp-border)' }}>
                    <th style={{ padding: '0.65rem 0.85rem', color: 'var(--bp-text-muted)', fontWeight: 600, width: '40px' }}>
                      #
                    </th>
                    {data.columns.map((col) => (
                      <th
                        key={col.name}
                        style={{
                          padding: '0.65rem 0.85rem',
                          textAlign: 'left',
                          color: 'var(--bp-navy)',
                          fontWeight: 600,
                          whiteSpace: 'nowrap',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <span>{col.name}</span>
                          <span
                            style={{
                              fontSize: '0.68rem',
                              padding: '0.05rem 0.3rem',
                              background: '#E8E7EF',
                              borderRadius: '3px',
                              color: 'var(--bp-text-muted)',
                            }}
                          >
                            {col.data_type}
                          </span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.length === 0 ? (
                    <tr>
                      <td colSpan={data.columns.length + 1} style={{ padding: '2rem', textAlign: 'center', color: 'var(--bp-text-muted)' }}>
                        No records match the search filter.
                      </td>
                    </tr>
                  ) : (
                    filteredRows.map((row, idx) => (
                      <tr
                        key={idx}
                        style={{
                          borderBottom: '1px solid var(--bp-border)',
                          background: idx % 2 === 0 ? '#FFFFFF' : '#FAFAFE',
                        }}
                      >
                        <td style={{ padding: '0.65rem 0.85rem', color: 'var(--bp-text-muted)', fontSize: '0.75rem' }}>
                          {idx + 1}
                        </td>
                        {data.columns.map((col) => {
                          const val = row[col.name];
                          return (
                            <td
                              key={col.name}
                              style={{
                                padding: '0.65rem 0.85rem',
                                color: val === null || val === undefined ? '#DC2626' : 'var(--bp-navy)',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {val === null || val === undefined ? (
                                <span style={{ fontStyle: 'italic', fontSize: '0.75rem' }}>null</span>
                              ) : typeof val === 'number' ? (
                                col.name.includes('revenue') || col.name.includes('cost') ? (
                                  `$${val.toFixed(2)}`
                                ) : (
                                  val.toLocaleString()
                                )
                              ) : (
                                String(val)
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {!loading && !error && data && activeTab === 'schema' && (
            <div>
              <div style={{ overflowX: 'auto', border: '1px solid var(--bp-border)', borderRadius: '8px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ background: '#F8F8FC', borderBottom: '2px solid var(--bp-border)' }}>
                      <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600 }}>Field Name</th>
                      <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600 }}>Data Type</th>
                      <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600 }}>Requirement</th>
                      <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600 }}>Missing Values</th>
                      <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600 }}>Sample Values</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.columns.map((col) => (
                      <tr key={col.name} style={{ borderBottom: '1px solid var(--bp-border)' }}>
                        <td style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--bp-navy)' }}>
                          <code>{col.name}</code>
                        </td>
                        <td style={{ padding: '0.75rem 1rem' }}>
                          <span
                            style={{
                              fontSize: '0.78rem',
                              padding: '0.15rem 0.45rem',
                              background: '#F1F0F7',
                              color: 'var(--bp-purple)',
                              borderRadius: '4px',
                              fontWeight: 600,
                            }}
                          >
                            {col.data_type}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem 1rem' }}>
                          {col.required ? (
                            <Badge variant="danger">Required</Badge>
                          ) : (
                            <Badge variant="neutral">Optional</Badge>
                          )}
                        </td>
                        <td style={{ padding: '0.75rem 1rem' }}>
                          {col.missing_count === 0 ? (
                            <span style={{ color: '#16A34A', fontSize: '0.8rem', fontWeight: 600 }}>0 (100% Complete)</span>
                          ) : (
                            <span style={{ color: '#DC2626', fontSize: '0.8rem', fontWeight: 600 }}>
                              {col.missing_count} missing
                            </span>
                          )}
                        </td>
                        <td style={{ padding: '0.75rem 1rem', color: 'var(--bp-text-muted)', fontSize: '0.8rem' }}>
                          {col.sample_values.map((s, idx) => (
                            <span
                              key={idx}
                              style={{
                                display: 'inline-block',
                                background: '#F8F8FC',
                                border: '1px solid var(--bp-border)',
                                padding: '0.1rem 0.35rem',
                                borderRadius: '3px',
                                marginRight: '0.35rem',
                              }}
                            >
                              {String(s)}
                            </span>
                          ))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '1rem 1.5rem',
            borderTop: '1px solid var(--bp-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#FAF9FF',
          }}
        >
          <div style={{ fontSize: '0.8rem', color: 'var(--bp-text-muted)' }}>
            Dataset storage path: <code>{dataset.file_path}</code>
          </div>
          <Button size="sm" variant="secondary" onClick={onClose}>
            Close Preview
          </Button>
        </div>
      </div>
    </div>
  );
};
