import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';
import type { View } from '../../types';

const PAGE_TITLES: Record<View, string> = {
  home:           'Home',
  assistant:      'AI Assistant',
  investigations: 'Investigations',
  actions:        'Action Centre',
  verification:   'Verification',
  datasources:    'Data Sources',
  settings:       'Settings',
};

const PAGE_SUBTITLES: Record<View, string> = {
  home:           'Business health overview',
  assistant:      'Powered by Gemini AI',
  investigations: 'AI-powered root cause analysis',
  actions:        'Proposals, approvals & task tracking',
  verification:   'Measuring real-world impact',
  datasources:    'Connected analytics engine',
  settings:       'Configuration & diagnostics',
};

export function Topbar() {
  const { currentView, backendStatus } = useApp();
  const { user, logout } = useAuth();

  const statusDot: Record<typeof backendStatus, { color: string; label: string }> = {
    connected:    { color: 'var(--bp-success)', label: 'Backend connected' },
    disconnected: { color: 'var(--bp-danger)',  label: 'Backend disconnected' },
    checking:     { color: 'var(--bp-warning)', label: 'Checking backend…' },
  };
  const dot = statusDot[backendStatus];

  const handleLogout = async () => {
    if (window.confirm('Are you sure you want to log out of BizPulse?')) {
      await logout();
    }
  };

  return (
    <header
      style={{
        height: 'var(--bp-topbar-height)',
        background: 'var(--bp-surface)',
        borderBottom: '1px solid var(--bp-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 1.5rem',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        boxShadow: 'var(--bp-shadow)',
        gap: '1rem',
      }}
    >
      {/* Page title + subtitle */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.05rem' }}>
        <h1
          style={{
            fontSize: '1rem',
            fontWeight: 700,
            color: 'var(--bp-text)',
            letterSpacing: '-0.02em',
          }}
        >
          {PAGE_TITLES[currentView]}
        </h1>
        <span
          style={{
            fontSize: '0.72rem',
            color: 'var(--bp-text-muted)',
            letterSpacing: '0.01em',
          }}
        >
          {PAGE_SUBTITLES[currentView]}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {/* Backend status */}
        <div
          title={dot.label}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            fontSize: '0.78rem',
            color: 'var(--bp-text-muted)',
            fontWeight: 500,
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: dot.color,
              display: 'inline-block',
              flexShrink: 0,
              animation: backendStatus === 'checking' ? 'bp-pulse 1.4s infinite' : 'none',
            }}
          />
          <span className="topbar-status-label">{dot.label}</span>
        </div>

        {/* Divider */}
        <div
          style={{
            width: '1px',
            height: '20px',
            background: 'var(--bp-border)',
          }}
        />

        {/* Identity chip */}
        <div
          title={user?.email || 'Authenticated User'}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.3rem 0.75rem',
            background: 'var(--bp-purple-pale, #F5F3FF)',
            border: '1px solid var(--bp-info-border, #DDD6FE)',
            borderRadius: '9999px',
            fontSize: '0.78rem',
            fontWeight: 600,
            color: 'var(--bp-purple, #7C3AED)',
            cursor: 'default',
          }}
        >
          <span>👤</span>
          <span>{user?.name ? `${user.name} (${user.role})` : 'Manager'}</span>
        </div>

        {/* Logout button */}
        <button
          type="button"
          onClick={handleLogout}
          title="Sign out of BizPulse"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
            padding: '0.3rem 0.65rem',
            background: 'transparent',
            border: '1px solid var(--bp-border, #E2E8F0)',
            borderRadius: '6px',
            fontSize: '0.75rem',
            fontWeight: 600,
            color: 'var(--bp-text-muted, #64748B)',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
        >
          <span>🚪</span>
          <span>Logout</span>
        </button>
      </div>
    </header>
  );
}
