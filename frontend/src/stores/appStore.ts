/**
 * Global application state (Zustand).
 */

import { create } from 'zustand';
import type { RAGStrategy } from '@/types/api';
import type { ChatMessage } from '@/types/ui';
import { generateId } from '@/lib/utils';

type HealthStatus = 'healthy' | 'degraded' | 'offline';

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

  // Collection
  activeCollection: string;
  setActiveCollection: (c: string) => void;

  // Health
  healthStatus: HealthStatus;
  setHealthStatus: (s: HealthStatus) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Strategy
  selectedStrategy: 'hybrid',
  setSelectedStrategy: (s) => set({ selectedStrategy: s }),

  // Chat
  messages: [
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Welcome to Serpent RAG \u{1F40D} \u2014 I\'m ready to process your queries using the selected retrieval strategy. Upload documents and ask me anything.',
      strategy: 'hybrid',
      timestamp: Date.now(),
    },
  ],

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
      messages: [
        {
          id: 'welcome',
          role: 'assistant',
          content:
            'Welcome to Serpent RAG \u{1F40D} \u2014 I\'m ready to process your queries using the selected retrieval strategy. Upload documents and ask me anything.',
          strategy: selectedStrategy,
          timestamp: Date.now(),
        },
      ],
    });
  },

  // Collection
  activeCollection: 'default',
  setActiveCollection: (c) => set({ activeCollection: c }),

  // Health
  healthStatus: 'offline',
  setHealthStatus: (s) => set({ healthStatus: s }),
}));
