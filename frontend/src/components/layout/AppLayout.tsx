import type { ReactNode } from 'react';
import { useApp } from '../../context/AppContext';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { sidebarCollapsed } = useApp();

  const sidebarWidth = sidebarCollapsed
    ? 'var(--bp-sidebar-collapsed)'
    : 'var(--bp-sidebar-width)';

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />

      {/* Main content — offset by sidebar width */}
      <div
        className="bp-main-shell"
        style={{
          flex: 1,
          marginLeft: sidebarWidth,
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh',
          transition: 'margin-left 0.2s ease',
          minWidth: 0,
          background: 'var(--bp-bg)',
        }}
      >
        <Topbar />
        <main
          style={{
            flex: 1,
            overflowY: 'auto',
          }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
