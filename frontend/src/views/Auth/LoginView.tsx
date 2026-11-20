import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';

interface DemoPersona {
  role: string;
  name: string;
  email: string;
  password: string;
  department: string;
}

const DEMO_PERSONAS: DemoPersona[] = [
  {
    role: 'CEO / Admin',
    name: 'Sarah Connor',
    email: 'ceo.sarah@bizpulse.internal',
    password: 'BizPulseCEO2026!',
    department: 'Executive Leadership',
  },
  {
    role: 'Operations Manager',
    name: 'Alex Morgan',
    email: 'alex.morgan@bizpulse.internal',
    password: 'BizPulseDemo2026!',
    department: 'Operations',
  },
  {
    role: 'Finance Analyst',
    name: 'Jordan Lee',
    email: 'jordan.lee@bizpulse.internal',
    password: 'BizPulseFinance2026!',
    department: 'Finance',
  },
  {
    role: 'Marketing Lead',
    name: 'Taylor Swift',
    email: 'taylor.swift@bizpulse.internal',
    password: 'BizPulseMarketing2026!',
    department: 'Marketing',
  },
  {
    role: 'Employee',
    name: 'Sam Coder',
    email: 'sam.coder@bizpulse.internal',
    password: 'BizPulseEmployee2026!',
    department: 'Engineering',
  },
];

export const LoginView: React.FC = () => {
  const { login, error, sessionExpired, clearError } = useAuth();
  const [email, setEmail] = useState('ceo.sarah@bizpulse.internal');
  const [password, setPassword] = useState('BizPulseCEO2026!');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim() || !password) {
      setLocalError('Please enter both email and password.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login(email.trim(), password);
    } catch {
      // Error handled by AuthContext
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSelectPersona = (p: DemoPersona) => {
    setEmail(p.email);
    setPassword(p.password);
    setLocalError(null);
    clearError();
  };

  const activeError = localError || error;

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #0A0E1A 0%, #151A2E 50%, #1C233D 100%)',
        padding: '1.5rem',
        fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '480px',
          background: 'var(--bp-surface, #FFFFFF)',
          borderRadius: '16px',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.35)',
          overflow: 'hidden',
          border: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        {/* Header / Brand */}
        <div
          style={{
            background: 'var(--bp-navy, #0F172A)',
            padding: '2rem 2rem 1.75rem',
            textAlign: 'center',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          }}
        >
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '48px',
              height: '48px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%)',
              fontSize: '1.75rem',
              marginBottom: '0.85rem',
              boxShadow: '0 8px 16px rgba(124, 58, 237, 0.35)',
            }}
          >
            ⚡
          </div>
          <h1
            style={{
              margin: '0 0 0.35rem',
              fontSize: '1.5rem',
              fontWeight: 800,
              color: '#FFFFFF',
              letterSpacing: '-0.02em',
            }}
          >
            BizPulse
          </h1>
          <p
            style={{
              margin: 0,
              fontSize: '0.85rem',
              color: 'rgba(255, 255, 255, 0.65)',
            }}
          >
            AI Business Intelligence & Remediation Platform
          </p>
        </div>

        {/* Content & Form */}
        <div style={{ padding: '2rem' }}>
          {/* Session Expired Notice */}
          {sessionExpired && (
            <div
              style={{
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                background: '#FEF3C7',
                border: '1px solid #F59E0B',
                color: '#92400E',
                fontSize: '0.825rem',
                marginBottom: '1.25rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <span>⚠️</span>
              <span>Your session has expired. Please log in again to continue.</span>
            </div>
          )}

          {/* Error Banner */}
          {activeError && (
            <div
              style={{
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                background: '#FEE2E2',
                border: '1px solid #EF4444',
                color: '#991B1B',
                fontSize: '0.825rem',
                marginBottom: '1.25rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <span>❌</span>
              <span>{activeError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {/* Email Field */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label
                htmlFor="bizpulse-email"
                style={{
                  display: 'block',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: 'var(--bp-navy, #1E293B)',
                  marginBottom: '0.4rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.03em',
                }}
              >
                Work Email
              </label>
              <input
                id="bizpulse-email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.internal"
                required
                style={{
                  width: '100%',
                  padding: '0.75rem 0.85rem',
                  borderRadius: '8px',
                  border: '1px solid #CBD5E1',
                  fontSize: '0.925rem',
                  color: '#0F172A',
                  background: '#FFFFFF',
                  outline: 'none',
                  boxSizing: 'border-box',
                  transition: 'border-color 0.15s ease',
                }}
              />
            </div>

            {/* Password Field */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label
                htmlFor="bizpulse-password"
                style={{
                  display: 'block',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: 'var(--bp-navy, #1E293B)',
                  marginBottom: '0.4rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.03em',
                }}
              >
                Password
              </label>
              <input
                id="bizpulse-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
                style={{
                  width: '100%',
                  padding: '0.75rem 0.85rem',
                  borderRadius: '8px',
                  border: '1px solid #CBD5E1',
                  fontSize: '0.925rem',
                  color: '#0F172A',
                  background: '#FFFFFF',
                  outline: 'none',
                  boxSizing: 'border-box',
                  transition: 'border-color 0.15s ease',
                }}
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                width: '100%',
                padding: '0.85rem',
                borderRadius: '8px',
                border: 'none',
                background: isSubmitting
                  ? '#94A3B8'
                  : 'linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%)',
                color: '#FFFFFF',
                fontSize: '0.95rem',
                fontWeight: 700,
                cursor: isSubmitting ? 'not-allowed' : 'pointer',
                boxShadow: isSubmitting
                  ? 'none'
                  : '0 4px 12px rgba(124, 58, 237, 0.35)',
                transition: 'opacity 0.15s ease',
              }}
            >
              {isSubmitting ? 'Verifying RBAC Session…' : 'Sign In to BizPulse'}
            </button>
          </form>

          {/* RBAC Demo Personas Helper */}
          <div
            style={{
              marginTop: '1.5rem',
              padding: '1rem',
              borderRadius: '8px',
              background: '#F8FAFC',
              border: '1px dashed #CBD5E1',
            }}
          >
            <div
              style={{
                fontSize: '0.72rem',
                color: '#64748B',
                fontWeight: 700,
                marginBottom: '0.6rem',
                textTransform: 'uppercase',
                textAlign: 'center',
              }}
            >
              Select RBAC Demo Persona:
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              {DEMO_PERSONAS.map((p) => {
                const isSelected = email === p.email;
                return (
                  <button
                    key={p.email}
                    type="button"
                    onClick={() => handleSelectPersona(p)}
                    style={{
                      background: isSelected ? 'var(--bp-purple-pale, #F5F3FF)' : '#FFFFFF',
                      border: isSelected ? '1px solid var(--bp-purple, #7C3AED)' : '1px solid #E2E8F0',
                      color: isSelected ? 'var(--bp-purple, #7C3AED)' : '#1E293B',
                      borderRadius: '6px',
                      padding: '0.4rem 0.65rem',
                      fontSize: '0.78rem',
                      fontWeight: isSelected ? 700 : 500,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      textAlign: 'left',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div>
                      <strong>{p.role}</strong>
                      <span style={{ fontSize: '0.72rem', color: '#64748B', marginLeft: '0.4rem' }}>
                        ({p.name})
                      </span>
                    </div>
                    <span style={{ fontSize: '0.7rem', color: isSelected ? 'var(--bp-purple)' : '#94A3B8' }}>
                      {isSelected ? '✓ Selected' : p.department}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Security Notice */}
          <div
            style={{
              marginTop: '1.25rem',
              textAlign: 'center',
              fontSize: '0.72rem',
              color: '#94A3B8',
            }}
          >
            🔒 Enforced by Backend RBAC, Argon2id & Signed JWT Cookies
          </div>
        </div>
      </div>
    </div>
  );
};
