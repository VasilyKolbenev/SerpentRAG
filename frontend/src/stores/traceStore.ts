/**
 * Trace cache store for Chat → Debugger navigation.
 */

import { create } from 'zustand';
import type { PipelineTrace } from '@/types/api';

interface TraceState {
  traces: Map<string, PipelineTrace>;
  activeTraceId: string | null;

  setTrace: (trace: PipelineTrace) => void;
  setActiveTraceId: (id: string | null) => void;
  getTrace: (id: string) => PipelineTrace | undefined;
}

export const useTraceStore = create<TraceState>((set, get) => ({
  traces: new Map(),
  activeTraceId: null,

  setTrace: (trace) => {
    set((s) => {
      const next = new Map(s.traces);
      next.set(trace.trace_id, trace);
      return { traces: next };
    });
  },

  setActiveTraceId: (id) => set({ activeTraceId: id }),

  getTrace: (id) => get().traces.get(id),
}));
