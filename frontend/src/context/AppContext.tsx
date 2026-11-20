import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import type { BackendStatus, View } from '../types';

// ─── Shape ───────────────────────────────────────────────────
interface AppContextValue {
  currentView: View;
  setView: (view: View) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  backendStatus: BackendStatus;
  pendingApprovalCount: number;
  setPendingApprovalCount: (n: number) => void;
  criticalAnomalyCount: number;
  setCriticalAnomalyCount: (n: number) => void;
  /** Anomaly chosen from the dashboard; consumed by the Investigations page. */
  investigationTargetId: string | null;
  openInvestigation: (anomalyId: string) => void;
  /** Question chosen elsewhere (e.g. Home); the AI Assistant page sends it on open. */
  pendingChatPrompt: string | null;
  askAssistant: (question: string) => void;
  clearPendingChatPrompt: () => void;
}

// ─── Context ──────────────────────────────────────────────────
const AppContext = createContext<AppContextValue | null>(null);

// ─── Provider ─────────────────────────────────────────────────
export function AppProvider({ children }: { children: ReactNode }) {
  const [currentView, setCurrentView] = useState<View>('home');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking');
  const [pendingApprovalCount, setPendingApprovalCount] = useState(0);
  const [criticalAnomalyCount, setCriticalAnomalyCount] = useState(0);
  const [investigationTargetId, setInvestigationTargetId] = useState<string | null>(null);
  const [pendingChatPrompt, setPendingChatPrompt] = useState<string | null>(null);

  const apiBase =
    import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

  // Keep a ref so the interval callback always has the latest value
  const apiBaseRef = useRef(apiBase);
  apiBaseRef.current = apiBase;

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${apiBaseRef.current}/api/health`);
      if (res.ok) {
        setBackendStatus('connected');
      } else {
        setBackendStatus('disconnected');
      }
    } catch {
      setBackendStatus('disconnected');
    }
  }, []);

  // Poll every 30 s
  useEffect(() => {
    checkHealth();
    const id = setInterval(checkHealth, 30_000);
    return () => clearInterval(id);
  }, [checkHealth]);

  const setView = useCallback((view: View) => {
    setCurrentView(view);
  }, []);

  const openInvestigation = useCallback((anomalyId: string) => {
    setInvestigationTargetId(anomalyId);
    setCurrentView('investigations');
  }, []);

  const askAssistant = useCallback((question: string) => {
    setPendingChatPrompt(question);
    setCurrentView('assistant');
  }, []);

  const clearPendingChatPrompt = useCallback(() => setPendingChatPrompt(null), []);

  return (
    <AppContext.Provider
      value={{
        currentView,
        setView,
        sidebarCollapsed,
        setSidebarCollapsed,
        backendStatus,
        pendingApprovalCount,
        setPendingApprovalCount,
        criticalAnomalyCount,
        setCriticalAnomalyCount,
        investigationTargetId,
        openInvestigation,
        pendingChatPrompt,
        askAssistant,
        clearPendingChatPrompt,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

// ─── Hook ─────────────────────────────────────────────────────
export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used inside <AppProvider>');
  return ctx;
}
