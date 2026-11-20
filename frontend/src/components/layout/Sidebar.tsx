import { useApp } from '../../context/AppContext';
import type { View } from '../../types';

interface NavItem {
  view: View;
  label: string;
  icon: string;
  badgeCount?: number;
}

export function Sidebar() {
  const {
    currentView,
    setView,
    sidebarCollapsed,
    setSidebarCollapsed,
    pendingApprovalCount,
    criticalAnomalyCount,
  } = useApp();

  const navItems: NavItem[] = [
    { view: 'home',           label: 'Home',           icon: '🏠', badgeCount: criticalAnomalyCount || undefined },
    { view: 'assistant',      label: 'AI Assistant',   icon: '🤖' },
    { view: 'investigations', label: 'Investigations', icon: '🔍' },
    { view: 'actions',        label: 'Action Centre',  icon: '✅', badgeCount: pendingApprovalCount || undefined },
    { view: 'verification',   label: 'Verification',   icon: '📊' },
    { view: 'datasources',    label: 'Data Sources',   icon: '🗄️' },
    { view: 'settings',       label: 'Settings',       icon: '⚙️' },
  ];

  return (
    <>
    <aside
      className="bp-sidebar"
      style={{
        width: sidebarCollapsed ? 'var(--bp-sidebar-collapsed)' : 'var(--bp-sidebar-width)',
        minHeight: '100vh',
        background: 'var(--bp-navy)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        transition: 'width 0.2s ease',
        overflow: 'hidden',
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
        zIndex: 100,
      }}
    >
      {/* ── Logo / brand ─────────────────────────────────── */}
      <div
        style={{
          height: 'var(--bp-topbar-height)',
          display: 'flex',
          alignItems: 'center',
          padding: sidebarCollapsed ? '0 1rem' : '0 1.25rem',
          gap: '0.65rem',
          borderBottom: '1px solid rgba(255,255,255,0.07)',
          flexShrink: 0,
        }}
      >
        {/* Purple-gradient lightning bolt */}
        <span
          style={{
            fontSize: '1.3rem',
            flexShrink: 0,
            background: 'var(--bp-gradient-ai)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            filter: 'brightness(1.2)',
          }}
        >
          ⚡
        </span>
        {!sidebarCollapsed && (
          <div style={{ overflow: 'hidden' }}>
            <div
              style={{
                fontWeight: 800,
                fontSize: '1.05rem',
                color: '#ffffff',
                letterSpacing: '-0.03em',
                whiteSpace: 'nowrap',
              }}
            >
              BizPulse
            </div>
            <div
              style={{
                fontSize: '0.68rem',
                color: 'rgba(255,255,255,0.4)',
                whiteSpace: 'nowrap',
                letterSpacing: '0.03em',
                textTransform: 'uppercase',
              }}
            >
              AI Business Assistant
            </div>
          </div>
        )}
      </div>

      {/* ── Navigation ───────────────────────────────────── */}
      <nav
        style={{
          flex: 1,
          padding: '0.75rem 0.5rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.15rem',
          overflowY: 'auto',
          overflowX: 'hidden',
        }}
      >
        {navItems.map((item) => {
          const isActive = currentView === item.view;
          return (
            <button
              key={item.view}
              onClick={() => setView(item.view)}
              title={sidebarCollapsed ? item.label : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.7rem',
                padding: sidebarCollapsed ? '0.65rem 0' : '0.6rem 0.9rem',
                justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
                background: isActive
                  ? 'rgba(88, 24, 240, 0.25)'
                  : 'transparent',
                borderLeft: 'none',
                border: 'none',
                borderRadius: 'var(--bp-radius)',
                cursor: 'pointer',
                width: '100%',
                transition: 'background 0.15s',
                flexShrink: 0,
                position: 'relative',
              }}
              onMouseEnter={(e) => {
                if (!isActive)
                  (e.currentTarget as HTMLButtonElement).style.background =
                    'rgba(255,255,255,0.07)';
              }}
              onMouseLeave={(e) => {
                if (!isActive)
                  (e.currentTarget as HTMLButtonElement).style.background =
                    'transparent';
              }}
            >
              {/* Active left accent bar */}
              {isActive && (
                <span
                  style={{
                    position: 'absolute',
                    left: 0,
                    top: '20%',
                    height: '60%',
                    width: '3px',
                    background: 'var(--bp-gradient-ai)',
                    borderRadius: '0 2px 2px 0',
                  }}
                />
              )}

              <span style={{ fontSize: '1rem', flexShrink: 0 }}>
                {item.icon}
              </span>

              {!sidebarCollapsed && (
                <>
                  <span
                    style={{
                      fontSize: '0.875rem',
                      fontWeight: isActive ? 600 : 400,
                      color: isActive ? '#ffffff' : 'rgba(255,255,255,0.6)',
                      flex: 1,
                      textAlign: 'left',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {item.label}
                  </span>
                  {item.badgeCount !== undefined && item.badgeCount > 0 && (
                    <span
                      style={{
                        background: 'var(--bp-gradient-ai)',
                        color: '#fff',
                        borderRadius: '9999px',
                        fontSize: '0.68rem',
                        fontWeight: 700,
                        padding: '0.1rem 0.45rem',
                        minWidth: '20px',
                        textAlign: 'center',
                      }}
                    >
                      {item.badgeCount}
                    </span>
                  )}
                </>
              )}

              {/* Collapsed badge dot */}
              {sidebarCollapsed && item.badgeCount !== undefined && item.badgeCount > 0 && (
                <span
                  style={{
                    position: 'absolute',
                    top: '7px',
                    right: '9px',
                    width: '8px',
                    height: '8px',
                    background: 'var(--bp-purple-light)',
                    borderRadius: '50%',
                  }}
                />
              )}
            </button>
          );
        })}
      </nav>

      {/* ── Collapse toggle ───────────────────────────────── */}
      <button
        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0.9rem',
          background: 'transparent',
          border: 'none',
          borderTop: '1px solid rgba(255,255,255,0.07)',
          cursor: 'pointer',
          color: 'rgba(255,255,255,0.35)',
          fontSize: '0.9rem',
          transition: 'color 0.15s',
          flexShrink: 0,
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.color = 'rgba(255,255,255,0.75)';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.color = 'rgba(255,255,255,0.35)';
        }}
      >
        {sidebarCollapsed ? '→' : '←'}
      </button>
    </aside>

    {/* ── Mobile bottom navigation (≤768px) ─────────────── */}
    <nav className="bp-mobile-nav" aria-label="Primary">
      {navItems.map((item) => {
        const isActive = currentView === item.view;
        return (
          <button
            key={item.view}
            onClick={() => setView(item.view)}
            aria-label={item.label}
            aria-current={isActive ? 'page' : undefined}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.1rem',
              height: '100%',
              background: isActive ? 'rgba(88, 24, 240, 0.25)' : 'transparent',
              border: 'none',
              borderTop: isActive
                ? '2px solid var(--bp-purple-light)'
                : '2px solid transparent',
              cursor: 'pointer',
              color: isActive ? '#ffffff' : 'rgba(255,255,255,0.55)',
              fontSize: '0.58rem',
              fontWeight: isActive ? 700 : 500,
              minWidth: 0,
              position: 'relative',
            }}
          >
            <span style={{ fontSize: '1.1rem', lineHeight: 1 }}>{item.icon}</span>
            <span
              style={{
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                maxWidth: '100%',
              }}
            >
              {item.label.split(' ')[0]}
            </span>
            {item.badgeCount !== undefined && item.badgeCount > 0 && (
              <span
                style={{
                  position: 'absolute',
                  top: '6px',
                  right: '22%',
                  width: '8px',
                  height: '8px',
                  background: 'var(--bp-purple-light)',
                  borderRadius: '50%',
                }}
              />
            )}
          </button>
        );
      })}
    </nav>
    </>
  );
}
