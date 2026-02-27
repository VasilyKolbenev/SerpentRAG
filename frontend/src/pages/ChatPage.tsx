/**
 * Chat page — main RAG interface with streaming, upload sidebar, and pipeline config.
 * Supports conversation sessions (history persisted in Redis).
 */

import { useEffect, useCallback } from 'react';
import ChatPanel from '@/components/chat/ChatPanel';
import UploadZone from '@/components/documents/UploadZone';
import { useAppStore } from '@/stores/appStore';
import { useStreamQuery } from '@/hooks/useStreamQuery';
import { DEFAULT_QUERY_PARAMS, PIPELINE_CONFIGS, STRATEGY_MAP } from '@/lib/constants';
import { withAlpha } from '@/lib/utils';

export default function ChatPage() {
  const {
    messages,
    selectedStrategy,
    activeCollection,
    sessionId,
    addUserMessage,
    addAssistantMessage,
    updateAssistantMessage,
    setSessionId,
    clearSession,
  } = useAppStore();

  const { state: stream, start: startStream, isStreaming } = useStreamQuery();

  // Track the current assistant message ID for streaming
  const assistantMsgs = messages.filter((m) => m.role === 'assistant');
  const lastAssistant = assistantMsgs[assistantMsgs.length - 1] ?? null;
  const streamingMsgId = lastAssistant?.isStreaming ? lastAssistant.id : null;

  // Sync streaming tokens → store
  useEffect(() => {
    if (!streamingMsgId) return;

    if (stream.tokens) {
      updateAssistantMessage(streamingMsgId, { content: stream.tokens });
    }

    if (stream.sources.length > 0) {
      updateAssistantMessage(streamingMsgId, { sources: stream.sources });
    }

    if (stream.phase === 'done') {
      updateAssistantMessage(streamingMsgId, {
        isStreaming: false,
        traceId: stream.traceId ?? undefined,
        latencyMs: stream.latencyMs ?? undefined,
        strategy: stream.strategyUsed ?? undefined,
      });

      // Save session_id from backend response
      if (stream.sessionId) {
        setSessionId(stream.sessionId);
      }
    }

    if (stream.phase === 'error') {
      updateAssistantMessage(streamingMsgId, {
        isStreaming: false,
        content: stream.error
          ? `Error: ${stream.error}`
          : 'An error occurred while processing your query.',
      });
    }
  }, [
    stream.tokens,
    stream.sources,
    stream.phase,
    stream.traceId,
    stream.latencyMs,
    stream.strategyUsed,
    stream.sessionId,
    stream.error,
    streamingMsgId,
    updateAssistantMessage,
    setSessionId,
  ]);

  const handleSend = useCallback(
    (query: string) => {
      addUserMessage(query, selectedStrategy);
      addAssistantMessage(selectedStrategy);

      startStream({
        ...DEFAULT_QUERY_PARAMS,
        query,
        strategy: selectedStrategy,
        collection: activeCollection,
        session_id: sessionId ?? undefined,
      });
    },
    [selectedStrategy, activeCollection, sessionId, addUserMessage, addAssistantMessage, startStream],
  );

  const strategyMeta = STRATEGY_MAP[selectedStrategy];
  const pipelineConfig = PIPELINE_CONFIGS[selectedStrategy] ?? [];

  return (
    <div
      className="grid gap-4 animate-fade-slide-up grid-cols-1 lg:grid-cols-[1fr_300px]"
      style={{ height: 'calc(100vh - 130px)' }}
    >
      {/* Main chat area */}
      <ChatPanel
        messages={messages}
        streamPhase={stream.phase}
        onSend={handleSend}
        isStreaming={isStreaming}
      />

      {/* Sidebar — hidden on mobile, visible on large screens */}
      <div className="hidden lg:flex flex-col gap-3 overflow-y-auto">
        {/* New Chat button */}
        <button
          onClick={clearSession}
          className="w-full py-2 px-3 rounded-[10px] border border-serpent-border-light bg-serpent-surface text-serpent-text-muted hover:text-serpent-text-light hover:border-serpent-accent/30 transition-colors duration-200 text-[11px] font-mono uppercase tracking-[1.5px] flex items-center justify-center gap-2"
        >
          <span className="text-[13px]">+</span> New Chat
        </button>

        {/* Upload section */}
        <div className="bg-serpent-surface border border-serpent-border-light rounded-[14px] p-[18px]">
          <h4 className="text-[10px] text-serpent-text-dark mb-3 uppercase tracking-[1.5px] font-mono">
            Documents
          </h4>
          <UploadZone />
        </div>

        {/* Pipeline config */}
        <div className="bg-serpent-surface border border-serpent-border-light rounded-[14px] p-[18px]">
          <h4 className="text-[10px] text-serpent-text-dark mb-3 uppercase tracking-[1.5px] font-mono">
            Pipeline Config
          </h4>
          {pipelineConfig.map((cfg, i) => (
            <div
              key={i}
              className="flex justify-between items-center py-[7px]"
              style={{
                borderBottom:
                  i < pipelineConfig.length - 1
                    ? '1px solid #131313'
                    : 'none',
              }}
            >
              <span className="text-[11px] text-serpent-text-muted font-dm-sans">
                {cfg.label}
              </span>
              {cfg.type === 'toggle' ? (
                <div
                  className="w-7 h-4 rounded-full relative cursor-pointer transition-colors duration-200"
                  style={{
                    background: cfg.value
                      ? strategyMeta?.color
                      : '#252525',
                  }}
                >
                  <div
                    className="w-3 h-3 rounded-full bg-white absolute top-[2px] transition-[left] duration-200"
                    style={{
                      left: cfg.value ? '14px' : '2px',
                    }}
                  />
                </div>
              ) : (
                <span
                  className="text-[10.5px] font-mono px-[7px] py-[2px] rounded-[3px]"
                  style={{
                    color: strategyMeta?.color,
                    background: withAlpha(
                      strategyMeta?.color ?? '#fff',
                      0.03,
                    ),
                  }}
                >
                  {String(cfg.value)}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
