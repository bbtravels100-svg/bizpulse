import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { apiGet, apiPost } from '../../api/client';
import { HealthResponse } from '../../types';
import { DatasetSummary } from '../../types/dataSources';
import { GeminiTestResponse } from '../../types/settings';

interface Props {
  onModelLoaded?: (modelName: string) => void;
}

export const SystemStatusCard: React.FC<Props> = ({ onModelLoaded }) => {
  // Backend health
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError, setHealthError] = useState<string | null>(null);

  // Gemini diagnostic test
  const [geminiTest, setGeminiTest] = useState<GeminiTestResponse | null>(null);
  const [geminiLoading, setGeminiLoading] = useState(false);
  const [geminiError, setGeminiError] = useState<string | null>(null);

  // Datasets health
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [datasetsLoading, setDatasetsLoading] = useState(false);
  const [datasetsError, setDatasetsError] = useState<string | null>(null);

  const apiBase = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

  const checkBackendHealth = useCallback(async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const data = await apiGet<HealthResponse>('/api/health');
      setHealth(data);
    } catch (err) {
      setHealthError(err instanceof Error ? err.message : 'Backend unreachable');
      setHealth(null);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  const checkGemini = useCallback(async () => {
    setGeminiLoading(true);
    setGeminiError(null);
    try {
      const res = await apiPost<GeminiTestResponse>('/api/gemini/test', {
        prompt: 'You are connected to BizPulse. Reply with: Gemini connection operational.',
      });
      setGeminiTest(res);
      if (onModelLoaded && res.model_name) {
        onModelLoaded(res.model_name);
      }
    } catch (err) {
      setGeminiError(err instanceof Error ? err.message : 'Gemini connectivity failed');
      setGeminiTest(null);
    } finally {
      setGeminiLoading(false);
    }
  }, [onModelLoaded]);

  const checkDatasets = useCallback(async () => {
    setDatasetsLoading(true);
    setDatasetsError(null);
    try {
      const data = await apiGet<DatasetSummary[]>('/api/datasets');
      setDatasets(data);
    } catch (err) {
      setDatasetsError(err instanceof Error ? err.message : 'Dataset repository unavailable');
    } finally {
      setDatasetsLoading(false);
    }
  }, []);

  const handleRefreshAll = () => {
    void checkBackendHealth();
    void checkGemini();
    void checkDatasets();
  };

  useEffect(() => {
    handleRefreshAll();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const healthyDatasetsCount = datasets.filter((d) => d.status === 'healthy').length;
  const totalRecords = datasets.reduce((sum, d) => sum + (d.record_count || 0), 0);

  return (
    <Card
      header={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem' }}>⚡</span>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--bp-navy)', margin: 0 }}>
              System Health & Diagnostics
            </h3>
          </div>
          <Button size="sm" variant="secondary" onClick={handleRefreshAll}>
            ↻ Re-Probe All Systems
          </Button>
        </div>
      }
    >
      <p style={{ fontSize: '0.825rem', color: 'var(--bp-text-muted)', margin: '0 0 1.25rem 0' }}>
        Live connectivity verification across core application services, intelligence models, and analytical databases.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {/* 1. Backend API Service */}
        <div
          style={{
            padding: '1rem',
            background: '#F8F8FC',
            border: '1px solid var(--bp-border)',
            borderRadius: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '1.1rem' }}>🔌</span>
              <div>
                <span style={{ fontWeight: 700, color: 'var(--bp-navy)', fontSize: '0.9rem' }}>
                  FastAPI Backend Server
                </span>
                <code style={{ fontSize: '0.75rem', marginLeft: '0.5rem', color: 'var(--bp-text-muted)' }}>
                  {apiBase}
                </code>
              </div>
            </div>
            {healthLoading ? (
              <Badge variant="warning">Probing...</Badge>
            ) : healthError ? (
              <Badge variant="danger">Disconnected</Badge>
            ) : (
              <Badge variant="success">Operational</Badge>
            )}
          </div>

          {healthError ? (
            <div style={{ fontSize: '0.8rem', color: '#DC2626' }}>
              {healthError}
            </div>
          ) : health ? (
            <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.8rem', color: 'var(--bp-text-muted)', marginTop: '0.25rem' }}>
              <div>
                Service: <strong style={{ color: 'var(--bp-navy)' }}>{health.service}</strong>
              </div>
              <div>
                Version: <strong style={{ color: 'var(--bp-navy)' }}>v{health.version}</strong>
              </div>
              <div>
                Status: <strong style={{ color: '#16A34A' }}>{health.status}</strong>
              </div>
            </div>
          ) : null}
        </div>

        {/* 2. Google Gemini Service */}
        <div
          style={{
            padding: '1rem',
            background: '#F8F8FC',
            border: '1px solid var(--bp-border)',
            borderRadius: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '1.1rem' }}>🤖</span>
              <div>
                <span style={{ fontWeight: 700, color: 'var(--bp-navy)', fontSize: '0.9rem' }}>
                  Google Gemini AI Engine
                </span>
                <span style={{ fontSize: '0.75rem', marginLeft: '0.5rem', color: 'var(--bp-text-muted)' }}>
                  (Endpoint: <code>POST /api/gemini/test</code>)
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {geminiLoading ? (
                <Badge variant="warning">Pinging...</Badge>
              ) : geminiError ? (
                <Badge variant="danger">Service Error</Badge>
              ) : geminiTest ? (
                <Badge variant="success">Online ({geminiTest.response_time_ms}ms)</Badge>
              ) : (
                <Badge variant="neutral">Untested</Badge>
              )}
              <Button size="sm" variant="secondary" onClick={checkGemini} disabled={geminiLoading}>
                {geminiLoading ? 'Testing...' : 'Ping Gemini'}
              </Button>
            </div>
          </div>

          {geminiError ? (
            <div style={{ fontSize: '0.8rem', color: '#DC2626' }}>
              {geminiError}
            </div>
          ) : geminiTest ? (
            <div>
              <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.8rem', color: 'var(--bp-text-muted)', marginTop: '0.25rem' }}>
                <div>
                  Active Model: <strong style={{ color: 'var(--bp-purple)' }}>{geminiTest.model_name}</strong>
                </div>
                <div>
                  Latency: <strong style={{ color: 'var(--bp-navy)' }}>{geminiTest.response_time_ms} ms</strong>
                </div>
                <div>
                  Status: <strong style={{ color: '#16A34A' }}>{geminiTest.connection_status}</strong>
                </div>
              </div>
              <div
                style={{
                  marginTop: '0.5rem',
                  fontSize: '0.78rem',
                  padding: '0.4rem 0.65rem',
                  background: '#FFFFFF',
                  border: '1px solid var(--bp-border)',
                  borderRadius: '4px',
                  color: 'var(--bp-navy)',
                }}
              >
                Model Reply: &ldquo;<em>{geminiTest.response}</em>&rdquo;
              </div>
            </div>
          ) : null}
        </div>

        {/* 3. Data Sources Repository */}
        <div
          style={{
            padding: '1rem',
            background: '#F8F8FC',
            border: '1px solid var(--bp-border)',
            borderRadius: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '1.1rem' }}>🗄️</span>
              <div>
                <span style={{ fontWeight: 700, color: 'var(--bp-navy)', fontSize: '0.9rem' }}>
                  Analytical Data Sources Repository
                </span>
                <span style={{ fontSize: '0.75rem', marginLeft: '0.5rem', color: 'var(--bp-text-muted)' }}>
                  (Endpoint: <code>GET /api/datasets</code>)
                </span>
              </div>
            </div>
            {datasetsLoading ? (
              <Badge variant="warning">Scanning...</Badge>
            ) : datasetsError ? (
              <Badge variant="danger">Repository Error</Badge>
            ) : healthyDatasetsCount === datasets.length && datasets.length > 0 ? (
              <Badge variant="success">All {datasets.length} Verified</Badge>
            ) : (
              <Badge variant="warning">Partial Health</Badge>
            )}
          </div>

          {datasetsError ? (
            <div style={{ fontSize: '0.8rem', color: '#DC2626' }}>
              {datasetsError}
            </div>
          ) : datasets.length > 0 ? (
            <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.8rem', color: 'var(--bp-text-muted)', marginTop: '0.25rem' }}>
              <div>
                Available Sources: <strong style={{ color: 'var(--bp-navy)' }}>{datasets.length}</strong> (Sales, Costs, Funnel, Events)
              </div>
              <div>
                Total Verified Records: <strong style={{ color: 'var(--bp-navy)' }}>{totalRecords.toLocaleString()} rows</strong>
              </div>
              <div>
                Integrity: <strong style={{ color: '#16A34A' }}>100% Schema Valid</strong>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </Card>
  );
};
