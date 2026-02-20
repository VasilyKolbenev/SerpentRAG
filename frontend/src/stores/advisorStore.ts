/**
 * Zustand store for AI Advisor Chatbot state.
 */

import { create } from 'zustand';
import type { AdvisorRecommendation } from '@/types/api';
import { api } from '@/lib/api';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface AdvisorState {
  isOpen: boolean;
  sessionId: string | null;
  messages: ChatMessage[];
  recommendation: AdvisorRecommendation | null;
  isLoading: boolean;
  error: string | null;

  toggleOpen: () => void;
  sendMessage: (text: string) => Promise<void>;
  reset: () => void;
}

export const useAdvisorStore = create<AdvisorState>((set, get) => ({
  isOpen: false,
  sessionId: null,
  messages: [],
  recommendation: null,
  isLoading: false,
  error: null,

  toggleOpen: () => set((s) => ({ isOpen: !s.isOpen })),

  sendMessage: async (text: string) => {
    const { sessionId, messages } = get();

    // Add user message immediately
    const userMsg: ChatMessage = { role: 'user', content: text };
    set({ messages: [...messages, userMsg], isLoading: true, error: null });

    try {
      const response = await api.advisorChat({
        session_id: sessionId ?? undefined,
        message: text,
      });

      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: response.reply,
      };

      set({
        sessionId: response.session_id,
        messages: [...get().messages, assistantMsg],
        recommendation: response.recommendation ?? get().recommendation,
        isLoading: false,
      });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to send message',
        isLoading: false,
      });
    }
  },

  reset: () =>
    set({
      sessionId: null,
      messages: [],
      recommendation: null,
      isLoading: false,
      error: null,
    }),
}));
