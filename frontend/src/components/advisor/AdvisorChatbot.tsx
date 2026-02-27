/**
 * AI Advisor Chatbot — floating widget (like Intercom).
 * Conversational AI that guides users to the best RAG strategy.
 */

import { useState, useRef, useEffect } from 'react';
import { useAdvisorStore } from '@/stores/advisorStore';
import { STRATEGY_COLORS } from '@/lib/constants';
import type { RAGStrategy, AdvisorRecommendation } from '@/types/api';

export function AdvisorChatbot() {
  const {
    isOpen,
    messages,
    recommendation,
    isLoading,
    error,
    toggleOpen,
    sendMessage,
    reset,
  } = useAdvisorStore();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput('');
    await sendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* Floating trigger button */}
      <button
        onClick={toggleOpen}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-gradient-to-br from-[#C8F547] to-[#2DD4A8] shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center group"
        aria-label="Open AI Advisor"
      >
        <span className="text-2xl group-hover:scale-110 transition-transform">
          {isOpen ? '\u2715' : '\uD83D\uDC0D'}
        </span>
        {!isOpen && messages.length === 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full animate-pulse" />
        )}
      </button>

      {/* Chat window */}
      {isOpen && (
        <div className="fixed bottom-24 right-6 z-50 w-[400px] h-[500px] bg-[#1A1B23] border border-white/10 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 bg-gradient-to-r from-[#C8F547]/10 to-[#2DD4A8]/10 border-b border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xl">{'\uD83D\uDC0D'}</span>
              <div>
                <h3 className="text-sm font-semibold text-white">Serpent Advisor</h3>
                <p className="text-xs text-white/50">AI Strategy Consultant</p>
              </div>
            </div>
            <button
              onClick={reset}
              className="text-xs text-white/40 hover:text-white/70 transition-colors px-2 py-1 rounded"
              title="Start new conversation"
            >
              Reset
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {messages.length === 0 && (
              <div className="text-center text-white/40 text-sm mt-8">
                <p className="text-2xl mb-2">{'\uD83D\uDC0D'}</p>
                <p>Hi! I&apos;m Serpent, your AI advisor.</p>
                <p className="mt-1">Tell me about your use case and</p>
                <p>I&apos;ll recommend the best RAG strategy.</p>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] px-3 py-2 rounded-xl text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-[#C8F547]/20 text-white'
                      : 'bg-white/5 text-white/90'
                  }`}
                >
                  <MessageContent content={msg.content} />
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white/5 px-3 py-2 rounded-xl">
                  <span className="text-white/50 text-sm animate-pulse">
                    Thinking...
                  </span>
                </div>
              </div>
            )}

            {error && (
              <div className="text-red-400 text-xs text-center">{error}</div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Recommendation card */}
          {recommendation && (
            <RecommendationCard recommendation={recommendation} />
          )}

          {/* Input */}
          <div className="px-4 py-3 border-t border-white/10">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Describe your use case..."
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-[#C8F547]/50"
                disabled={isLoading}
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                className="px-4 py-2 bg-[#C8F547] text-black rounded-lg text-sm font-medium hover:bg-[#C8F547]/90 disabled:opacity-30 transition-all"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/** Renders message content with basic markdown-like formatting. */
function MessageContent({ content }: { content: string }) {
  // Simple bold rendering
  const parts = content.split(/(\*\*.*?\*\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return (
            <strong key={i} className="font-semibold text-[#C8F547]">
              {part.slice(2, -2)}
            </strong>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

/** Recommendation card shown when advisor makes a recommendation. */
function RecommendationCard({
  recommendation,
}: {
  recommendation: AdvisorRecommendation;
}) {
  const color =
    STRATEGY_COLORS[recommendation.recommended as RAGStrategy] ?? '#C8F547';

  return (
    <div className="mx-4 mb-2 p-3 rounded-xl bg-gradient-to-r from-white/5 to-white/[0.02] border border-white/10">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs text-white/50">Recommended:</span>
        <span
          className="text-sm font-bold uppercase"
          style={{ color }}
        >
          {recommendation.recommended}
        </span>
      </div>
      {recommendation.reasoning && (
        <p className="text-xs text-white/60 leading-relaxed">
          {recommendation.reasoning}
        </p>
      )}
      {Object.keys(recommendation.scores).length > 0 && (
        <div className="flex gap-1 mt-2 flex-wrap">
          {Object.entries(recommendation.scores)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 4)
            .map(([name, score]) => (
              <span
                key={name}
                className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-white/50"
              >
                {name}: {(score * 100).toFixed(0)}%
              </span>
            ))}
        </div>
      )}
    </div>
  );
}
