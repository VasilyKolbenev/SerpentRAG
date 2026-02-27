/**
 * Global application state (Zustand).
 * Persists sessionId to localStorage for page refresh survival.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { DocumentStatus, RAGStrategy } from '@/types/api';
import type { ChatMessage } from '@/types/ui';
import { generateId } from '@/lib/utils';

type HealthStatus = 'healthy' | 'degraded' | 'offline';

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  status: DocumentStatus | 'uploading';
  processing_phase?: string;
  error?: string;
  collection: string;
}

const WELCOME_MESSAGE = (strategy: RAGStrategy): ChatMessage => ({
  id: 'welcome',
  role: 'assistant',
  content:
    'Welcome to Serpent RAG \u{1F40D} \u2014 I\'m ready to process your queries using the selected retrieval strategy. Upload documents and ask me anything.',
  strategy,
  timestamp: Date.now(),
});

interface AppState {
  // Strategy
  selectedStrategy: RAGStrategy;
  setSelectedStrategy: (s: RAGStrategy) => void;

  // Chat
  messages: ChatMessage[];
  addUserMessage: (content: string, strategy: RAGStrategy) => string;
  addAssistantMessage: (strategy: RAGStrategy) => string;
  updateAssistantMessage: (id: string, patch: Partial<ChatMessage>) => void;
  appendToken: (id: string, token: string) => void;
  clearMessages: () => void;

  // Session (conversation history)
  sessionId: string | null;
  setSessionId: (id: string) => void;
  clearSession: () => void;

  // Collection
  activeCollection: string;
  setActiveCollection: (c: string) => void;

  // Uploads (global, survives page navigation)
  uploads: Record<string, UploadedFile>;
  addUpload: (file: UploadedFile) => void;
  updateUpload: (id: string, patch: Partial<UploadedFile>) => void;
  removeUpload: (id: string) => void;
  clearFinishedUploads: () => void;

  // Health
  healthStatus: HealthStatus;
  setHealthStatus: (s: HealthStatus) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Strategy
      selectedStrategy: 'hybrid',
      setSelectedStrategy: (s) => set({ selectedStrategy: s }),

      // Chat
      messages: [WELCOME_MESSAGE('hybrid')],

      addUserMessage: (content, strategy) => {
        const id = generateId();
        set((s) => ({
          messages: [
            ...s.messages,
            {
              id,
              role: 'user',
              content,
              strategy,
              timestamp: Date.now(),
            },
          ],
        }));
        return id;
      },

      addAssistantMessage: (strategy) => {
        const id = generateId();
        set((s) => ({
          messages: [
            ...s.messages,
            {
              id,
              role: 'assistant',
              content: '',
              strategy,
              timestamp: Date.now(),
              isStreaming: true,
            },
          ],
        }));
        return id;
      },

      updateAssistantMessage: (id, patch) => {
        set((s) => ({
          messages: s.messages.map((m) =>
            m.id === id ? { ...m, ...patch } : m,
          ),
        }));
      },

      appendToken: (id, token) => {
        set((s) => ({
          messages: s.messages.map((m) =>
            m.id === id ? { ...m, content: m.content + token } : m,
          ),
        }));
      },

      clearMessages: () => {
        const { selectedStrategy } = get();
        set({
          messages: [WELCOME_MESSAGE(selectedStrategy)],
        });
      },

      // Session
      sessionId: null,
      setSessionId: (id) => set({ sessionId: id }),
      clearSession: () => {
        const { selectedStrategy } = get();
        set({
          sessionId: null,
          messages: [WELCOME_MESSAGE(selectedStrategy)],
        });
      },

      // Collection
      activeCollection: 'default',
      setActiveCollection: (c) => set({ activeCollection: c }),

      // Uploads
      uploads: {},
      addUpload: (file) =>
        set((s) => ({
          uploads: { ...s.uploads, [file.id]: file },
        })),
      updateUpload: (id, patch) =>
        set((s) => {
          const existing = s.uploads[id];
          if (!existing) return s;
          return {
            uploads: { ...s.uploads, [id]: { ...existing, ...patch } },
          };
        }),
      removeUpload: (id) =>
        set((s) => {
          const { [id]: _, ...rest } = s.uploads;
          return { uploads: rest };
        }),
      clearFinishedUploads: () =>
        set((s) => {
          const active: Record<string, UploadedFile> = {};
          for (const [k, v] of Object.entries(s.uploads)) {
            if (v.status === 'uploading' || v.status === 'processing') {
              active[k] = v;
            }
          }
          return { uploads: active };
        }),

      // Health
      healthStatus: 'offline',
      setHealthStatus: (s) => set({ healthStatus: s }),
    }),
    {
      name: 'serpent-app-session',
      // Only persist sessionId to localStorage (messages are ephemeral)
      partialize: (state) => ({ sessionId: state.sessionId }),
    },
  ),
);
