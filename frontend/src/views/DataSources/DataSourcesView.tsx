import React, { useState, useEffect, useCallback } from 'react';
import { ViewContainer } from '../../components/layout/ViewContainer';
import { Button } from '../../components/common/Button';
import { apiGet } from '../../api/client';
import { DatasetSummary } from '../../types/dataSources';
import { DataSourcesOverviewCards } from './DataSourcesOverviewCards';
import { DatasetsTable } from './DatasetsTable';
import { DataPreviewModal } from './DataPreviewModal';
import { CsvUploadModal } from './CsvUploadModal';
import { FutureIntegrationsSection } from './FutureIntegrationsSection';

export const DataSourcesView: React.FC = () => {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Modals state
  const [previewDataset, setPreviewDataset] = useState<DatasetSummary | null>(null);
  const [uploadDataset, setUploadDataset] = useState<DatasetSummary | null>(null);

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<DatasetSummary[]>('/api/datasets');
      setDatasets(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect to dataset repository');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchDatasets();
  }, [fetchDatasets]);

  // Filter datasets by search query
  const filteredDatasets = datasets.filter((d) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      d.name.toLowerCase().includes(q) ||
      d.description.toLowerCase().includes(q) ||
      d.filename.toLowerCase().includes(q) ||
      d.columns.some((c) => c.name.toLowerCase().includes(q))
    );
  });

  return (
    <ViewContainer
      title="Data Sources Centre"
      subtitle="Inspect, validate, and manage ground-truth CSV datasets powering all BizPulse intelligence engines."
    >
      {/* Top Action Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '1.25rem',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <input
            type="text"
            placeholder="Search datasets, files, columns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: '0.45rem 0.85rem',
              borderRadius: '6px',
              border: '1px solid var(--bp-border)',
              fontSize: '0.875rem',
              outline: 'none',
              width: '280px',
              background: '#FFFFFF',
            }}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--bp-text-muted)',
                cursor: 'pointer',
                fontSize: '0.8rem',
              }}
            >
              Clear
            </button>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Button
            size="sm"
            variant="secondary"
            onClick={fetchDatasets}
            disabled={loading}
          >
            {loading ? 'Refreshing...' : '↻ Refresh Status'}
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div
          style={{
            padding: '1rem 1.25rem',
            background: '#FEF2F2',
            border: '1px solid #FCA5A5',
            borderRadius: '8px',
            color: '#991B1B',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <strong>Backend Connection Error:</strong> {error}
          </div>
          <Button size="sm" variant="danger" onClick={fetchDatasets}>
            Retry
          </Button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && datasets.length === 0 && (
        <div style={{ textAlign: 'center', padding: '4rem 0', color: 'var(--bp-text-muted)' }}>
          <div
            style={{
              display: 'inline-block',
              width: '36px',
              height: '36px',
              border: '3px solid var(--bp-light-purple)',
              borderTopColor: 'var(--bp-purple)',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              marginBottom: '1rem',
            }}
          />
          <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--bp-navy)' }}>
            Inspecting data directory & validating CSV schemas...
          </div>
        </div>
      )}

      {/* Main Content */}
      {!loading && (
        <>
          {/* 1. Overview Cards */}
          <DataSourcesOverviewCards datasets={datasets} />

          {/* 2. Datasets Table */}
          <DatasetsTable
            datasets={filteredDatasets}
            onPreview={(d) => setPreviewDataset(d)}
            onUpload={(d) => setUploadDataset(d)}
          />

          {/* 3. Future Integrations Section */}
          <FutureIntegrationsSection />
        </>
      )}

      {/* Modals */}
      <DataPreviewModal
        isOpen={previewDataset !== null}
        dataset={previewDataset}
        onClose={() => setPreviewDataset(null)}
      />

      <CsvUploadModal
        isOpen={uploadDataset !== null}
        dataset={uploadDataset}
        onClose={() => setUploadDataset(null)}
        onSuccess={() => {
          void fetchDatasets();
        }}
      />
    </ViewContainer>
  );
};
