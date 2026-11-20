import './App.css';
import { AppProvider, useApp } from './context/AppContext';
import { ChatProvider } from './context/ChatContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { LoadingSpinner } from './components/common/LoadingSpinner';
import {
  HomeView,
  AIAssistantView,
  InvestigationsView,
  ActionCentreView,
  VerificationView,
  DataSourcesView,
  SettingsView,
  LoginView,
} from './views';
import type { View } from './types';
import type { ReactNode } from 'react';

// ─── View router ─────────────────────────────────────────────
const VIEW_MAP: Record<View, ReactNode> = {
  home:           <HomeView />,
  assistant:      <AIAssistantView />,
  investigations: <InvestigationsView />,
  actions:        <ActionCentreView />,
  verification:   <VerificationView />,
  datasources:    <DataSourcesView />,
  settings:       <SettingsView />,
};

function AppInner() {
  const { currentView } = useApp();
  return (
    <AppLayout>
      {VIEW_MAP[currentView]}
    </AppLayout>
  );
}

function AppContent() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bp-navy, #0B0F19)',
          color: '#FFFFFF',
        }}
      >
        <LoadingSpinner size={36} label="Verifying security session…" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginView />;
  }

  return (
    <AppProvider>
      <ChatProvider>
        <AppInner />
      </ChatProvider>
    </AppProvider>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
