/**
 * Chat message bubble with sources, strategy badge, and trace link.
 * Rewrites the JSX version with: markdown, streaming, traceId, real SourceInfo.
 */

import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import SourceChip from './SourceChip';
import { STRATEGY_MAP } from '@/lib/constants';
import { withAlpha, formatDuration } from '@/lib/utils';
import type { ChatMessage as ChatMessageType } from '@/types/ui';

interface ChatMessageProps {
  msg: ChatMessageType;
}

export default function ChatMessage({ msg }: ChatMessageProps) {
  const navigate = useNavigate();
  const isUser = msg.role === 'user';
  const strategyMeta = msg.strategy ? STRATEGY_MAP[msg.strategy] : null;

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-2.5 animate-fade-slide-up`}
    >
      <div
        className="max-w-[78%] px-[15px] py-[11px]"
        style={{
          borderRadius: isUser
            ? '12px 12px 3px 12px'
            : '12px 12px 12px 3px',
          background: isUser ? '#C8F54708' : '#0e0e0e',
          border: `1px solid ${isUser ? '#C8F54715' : '#181818'}`,
        }}
      >
        {/* Sources */}
        {msg.sources && msg.sources.length > 0 && (
          <div className="flex gap-1 mb-[7px] flex-wrap">
            {msg.sources.map((s, i) => (
              <SourceChip
                key={i}
                filename={
                  (s.metadata?.filename as string) ??
                  (s.metadata?.source as string) ??
                  `source-${i + 1}`
                }
                score={s.score}
                index={i}
              />
            ))}
          </div>
        )}

        {/* Content — markdown for assistant, plain for user */}
        {isUser ? (
          <p className="text-[13px] text-[#d5d5d5] leading-[1.6] m-0 font-dm-sans">
            {msg.content}
          </p>
        ) : (
          <div className="text-[13px] text-serpent-text-tertiary leading-[1.6] font-dm-sans prose prose-invert prose-sm max-w-none [&_pre]:bg-[#060606] [&_pre]:border [&_pre]:border-[#131313] [&_pre]:rounded-lg [&_pre]:p-3 [&_pre]:font-mono [&_pre]:text-[11px] [&_code]:font-mono [&_code]:text-[11px] [&_code]:bg-[#111] [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded">
            <ReactMarkdown>{msg.content || '\u00A0'}</ReactMarkdown>
            {msg.isStreaming && (
              <span className="inline-block w-[2px] h-4 bg-strategy-agentic animate-pulse ml-0.5 align-text-bottom" />
            )}
          </div>
        )}

        {/* Strategy badge + latency + trace link */}
        {strategyMeta && (
          <div className="mt-[7px] text-[10px] text-serpent-text-dark flex items-center gap-[5px] font-mono">
            <span
              className="inline-block w-[5px] h-[5px] rounded-full"
              style={{ background: strategyMeta.color }}
            />
            <span style={{ color: withAlpha(strategyMeta.color, 0.7) }}>
              {strategyMeta.name}
            </span>
            {msg.latencyMs && (
              <span className="ml-[6px] text-serpent-text-darker">
                {'\u00B7'} {formatDuration(msg.latencyMs)}
              </span>
            )}
            {msg.traceId && (
              <button
                onClick={() => navigate(`/debugger/${msg.traceId}`)}
                className="ml-2 text-strategy-graph/70 hover:text-strategy-graph transition-colors cursor-pointer bg-transparent border-none p-0 font-mono text-[10px]"
              >
                View trace {'\u2192'}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
