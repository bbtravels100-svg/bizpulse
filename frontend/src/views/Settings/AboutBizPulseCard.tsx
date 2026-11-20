import React from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';

export const AboutBizPulseCard: React.FC = () => {
  return (
    <Card
      header={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem' }}>ℹ️</span>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--bp-navy)', margin: 0 }}>
              About BizPulse
            </h3>
          </div>
          <Badge variant="info">Enterprise Edition</Badge>
        </div>
      }
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1.25rem', marginBottom: '1.25rem' }}>
        <div
          style={{
            width: '56px',
            height: '56px',
            borderRadius: '12px',
            background: 'var(--bp-navy)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.75rem',
            color: '#FFFFFF',
            flexShrink: 0,
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          }}
        >
          ⚡
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--bp-navy)', margin: 0, letterSpacing: '-0.02em' }}>
              BizPulse
            </h2>
            <code
              style={{
                fontSize: '0.78rem',
                padding: '0.15rem 0.45rem',
                background: 'var(--bp-light-purple)',
                color: 'var(--bp-purple)',
                borderRadius: '4px',
                fontWeight: 700,
              }}
            >
              v0.4.0
            </code>
          </div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--bp-purple)', marginTop: '0.15rem' }}>
            Your AI Business Assistant
          </div>
        </div>
      </div>

      <p style={{ fontSize: '0.85rem', color: 'var(--bp-navy)', lineHeight: 1.5, margin: '0 0 1rem 0' }}>
        BizPulse is an enterprise autonomous intelligence and operational execution platform. It bridges raw analytical telemetry with multi-agent AI reasoning to automatically detect business anomalies, conduct cross-system root cause investigations, generate actionable operational proposals, and verify metric impact through before-and-after baselines.
      </p>

      {/* Tech Specifications */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '0.75rem',
          padding: '0.85rem 1rem',
          background: '#F8F8FC',
          borderRadius: '8px',
          border: '1px solid var(--bp-border)',
          marginBottom: '1rem',
        }}
      >
        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--bp-text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
            Backend Architecture
          </div>
          <div style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--bp-navy)', marginTop: '0.15rem' }}>
            FastAPI + Python 3.13
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--bp-text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
            AI Reasoning Engine
          </div>
          <div style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--bp-navy)', marginTop: '0.15rem' }}>
            Google Gemini 3.1 Flash
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--bp-text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
            Frontend Shell
          </div>
          <div style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--bp-navy)', marginTop: '0.15rem' }}>
            React 18 + TypeScript + Vite
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--bp-text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
            Database & State
          </div>
          <div style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--bp-navy)', marginTop: '0.15rem' }}>
            SQLite (Immutable Audit Logs)
          </div>
        </div>
      </div>

      <div style={{ fontSize: '0.75rem', color: 'var(--bp-text-muted)', textAlign: 'center' }}>
        © 2026 BizPulse Technologies Inc. All rights reserved. • Enterprise SaaS Architecture
      </div>
    </Card>
  );
};
