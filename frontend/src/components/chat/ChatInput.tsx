/**
 * Chat input bar with strategy selector and send button.
 */

import { useState, useRef, useCallback } from 'react';
import { STRATEGY_MAP } from '@/lib/constants';
import { useAppStore } from '@/stores/appStore';

interface ChatInputProps {
  onSend: (query: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const pendingRef = useRef(false);
  const selectedStrategy = useAppStore((s) => s.selectedStrategy);
  const meta = STRATEGY_MAP[selectedStrategy];

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    // B13: Guard against double submit via rapid clicks/Enter
    if (!trimmed || disabled || pendingRef.current) return;
    pendingRef.current = true;
    onSend(trimmed);
    setValue('');
    inputRef.current?.focus();
    // Reset guard after microtask (allows React to update disabled prop)
    requestAnimationFrame(() => {
      pendingRef.current = false;
    });
  }, [value, disabled, onSend]);

  return (
    <div className="flex gap-[6px] p-2.5 bg-serpent-surface border border-serpent-border border-t-0 rounded-b-[14px]">
      {/* Strategy badge */}
      <div
        className="flex items-center gap-[5px] px-[9px] py-[3px] bg-serpent-bg rounded-[5px] border border-serpent-border text-[10px] font-mono shrink-0"
        style={{ color: meta?.color }}
      >
        {meta?.icon} {meta?.name}
      </div>

      {/* Input */}
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        placeholder="Ask the Serpent anything..."
        disabled={disabled}
        maxLength={5000}
        aria-label="Query input"
        className="flex-1 px-[13px] py-[9px] text-[12.5px] bg-serpent-bg border border-serpent-border rounded-[7px] text-serpent-text-secondary font-dm-sans placeholder:text-serpent-text-dark disabled:opacity-50"
      />

      {/* Send button */}
      <button
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        className="px-[18px] py-[9px] text-[11px] bg-gradient-to-br from-strategy-agentic to-strategy-hybrid text-[#0a0a0a] border-none rounded-[7px] font-semibold cursor-pointer font-outfit transition-opacity duration-200 hover:opacity-85 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Send
      </button>
    </div>
  );
}
