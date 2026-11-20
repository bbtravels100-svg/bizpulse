import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { apiPost } from '../api/client';
import type {
  ActionItem,
  ActionPanelState,
  ChatApiResponse,
  ChatMessage,
  ChatTurnPayload,
} from '../types/chat';

const MAX_HISTORY_TURNS = 8;

interface ChatContextValue {
  messages: ChatMessage[];
  isLoading: boolean;
  sendMessage: (text: string) => Promise<void>;
  retry: (errorMessageId: string) => Promise<void>;
  newConversation: () => void;
  prepareActions: (messageId: string) => Promise<void>;
  decideAction: (
    messageId: string,
    actionId: string,
    decision: 'approve' | 'reject',
    reason?: string,
  ) => Promise<void>;
}

const ChatContext = createContext<ChatContextValue | null>(null);

let idCounter = 0;
const nextId = (): string => `m${Date.now().toString(36)}${(idCounter++).toString(36)}`;

/** Conversation turns sent to the backend: only real user/assistant text. */
function buildHistory(msgs: ChatMessage[]): ChatTurnPayload[] {
  const turns: ChatTurnPayload[] = [];
  for (const m of msgs) {
    if (m.role === 'user') turns.push({ role: 'user', content: m.content });
    else if (m.role === 'assistant') turns.push({ role: 'assistant', content: m.response?.reply ?? m.content });
  }
  return turns.slice(-MAX_HISTORY_TURNS);
}

export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const messagesRef = useRef<ChatMessage[]>([]);
  const sendingRef = useRef(false);
  const epochRef = useRef(0); // bumped on "new conversation" to discard stale replies

  const commit = useCallback((next: ChatMessage[]) => {
    messagesRef.current = next;
    setMessages(next);
  }, []);

  const patchMessage = useCallback(
    (id: string, fn: (m: ChatMessage) => ChatMessage) => {
      commit(messagesRef.current.map((m) => (m.id === id ? fn(m) : m)));
    },
    [commit],
  );

  /** Ask the backend. `historyBefore` excludes the message being answered. */
  const ask = useCallback(
    async (text: string, historyBefore: ChatMessage[]) => {
      const epoch = epochRef.current;
      sendingRef.current = true;
      setIsLoading(true);
      try {
        const response = await apiPost<ChatApiResponse>('/api/chat', {
          message: text,
          history: buildHistory(historyBefore),
        });
        if (epoch !== epochRef.current) return;
        commit([
          ...messagesRef.current,
          {
            id: nextId(),
            role: 'assistant',
            content: response.reply,
            timestamp: new Date().toISOString(),
            response,
          },
        ]);
      } catch (e: unknown) {
        if (epoch !== epochRef.current) return;
        commit([
          ...messagesRef.current,
          {
            id: nextId(),
            role: 'error',
            content: e instanceof Error ? e.message : 'Something went wrong.',
            timestamp: new Date().toISOString(),
            retryText: text,
          },
        ]);
      } finally {
        if (epoch === epochRef.current) {
          sendingRef.current = false;
          setIsLoading(false);
        }
      }
    },
    [commit],
  );

  const sendMessage = useCallback(
    async (raw: string) => {
      const text = raw.trim();
      if (!text || sendingRef.current) return; // blocks duplicate submissions
      const historyBefore = messagesRef.current;
      commit([
        ...historyBefore,
        { id: nextId(), role: 'user', content: text, timestamp: new Date().toISOString() },
      ]);
      await ask(text, historyBefore);
    },
    [ask, commit],
  );

  const retry = useCallback(
    async (errorMessageId: string) => {
      if (sendingRef.current) return;
      const err = messagesRef.current.find((m) => m.id === errorMessageId);
      if (!err?.retryText) return;
      const withoutError = messagesRef.current.filter((m) => m.id !== errorMessageId);
      commit(withoutError);
      // History = everything before the user bubble that is being retried.
      const lastUser = [...withoutError].reverse().findIndex((m) => m.role === 'user');
      const cut = lastUser === -1 ? withoutError.length : withoutError.length - 1 - lastUser;
      await ask(err.retryText, withoutError.slice(0, cut));
    },
    [ask, commit],
  );

  const newConversation = useCallback(() => {
    epochRef.current += 1;
    sendingRef.current = false;
    setIsLoading(false);
    commit([]);
  }, [commit]);

  const setActions = useCallback(
    (messageId: string, fn: (a: ActionPanelState | undefined) => ActionPanelState) => {
      patchMessage(messageId, (m) => ({ ...m, actions: fn(m.actions) }));
    },
    [patchMessage],
  );

  /** Creates PENDING proposals via the existing API. Nothing is approved here. */
  const prepareActions = useCallback(
    async (messageId: string) => {
      const msg = messagesRef.current.find((m) => m.id === messageId);
      const anomalyId = msg?.response?.anomaly_id;
      if (!anomalyId || msg?.actions?.status === 'loading') return;
      setActions(messageId, () => ({ status: 'loading', items: [], decisions: {} }));
      try {
        const items = await apiPost<ActionItem[]>('/api/actions/generate', { anomaly_id: anomalyId });
        setActions(messageId, () => ({ status: 'ready', items, decisions: {} }));
      } catch (e: unknown) {
        setActions(messageId, () => ({
          status: 'error',
          items: [],
          decisions: {},
          error: e instanceof Error ? e.message : 'Could not prepare actions.',
        }));
      }
    },
    [setActions],
  );

  /** Approve/reject through the existing API — only invoked by an explicit user click. */
  const decideAction = useCallback(
    async (messageId: string, actionId: string, decision: 'approve' | 'reject', reason?: string) => {
      const setDecision = (state: ActionPanelState['decisions'][string]) =>
        setActions(messageId, (a) => ({
          status: 'ready',
          items: a?.items ?? [],
          decisions: { ...(a?.decisions ?? {}), [actionId]: state },
        }));

      setDecision({ state: 'working' });
      try {
        if (decision === 'approve') {
          await apiPost<ActionItem>(`/api/actions/${encodeURIComponent(actionId)}/approve`, {
            approver: 'Business Manager',
          });
          setDecision({ state: 'approved', message: 'Approved — now in the active task workflow.' });
        } else {
          await apiPost<ActionItem>(`/api/actions/${encodeURIComponent(actionId)}/reject`, {
            reason: reason ?? '',
            rejected_by: 'Business Manager',
          });
          setDecision({ state: 'rejected', message: 'Rejected and recorded with your reason.' });
        }
      } catch (e: unknown) {
        setDecision({ state: 'error', message: e instanceof Error ? e.message : 'Operation failed.' });
      }
    },
    [setActions],
  );

  const value = useMemo<ChatContextValue>(
    () => ({ messages, isLoading, sendMessage, retry, newConversation, prepareActions, decideAction }),
    [messages, isLoading, sendMessage, retry, newConversation, prepareActions, decideAction],
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat(): ChatContextValue {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChat must be used inside <ChatProvider>');
  return ctx;
}
