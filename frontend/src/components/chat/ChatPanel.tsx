/**
 * Chat panel — messages + input container.
 */

import { useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import StreamingIndicator from './StreamingIndicator';
import type { ChatMessage as ChatMessageType } from '@/types/ui';
import type { StreamPhase } from '@/types/ui';

interface ChatPanelProps {
  messages: ChatMessageType[];
  streamPhase: StreamPhase;
  onSend: (query: string) => void;
  isStreaming: boolean;
}

export default function ChatPanel({
  messages,
  streamPhase,
  onSend,
  isStreaming,
}: ChatPanelProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamPhase]);

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-[18px] bg-[#090909] border border-[#141414] rounded-t-[14px]">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} msg={msg} />
        ))}
        {isStreaming && <StreamingIndicator phase={streamPhase} />}
        <div ref={endRef} />
      </div>

      {/* Input bar */}
      <ChatInput onSend={onSend} disabled={isStreaming} />
    </div>
  );
}
