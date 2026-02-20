/**
 * Code block with copy button.
 */

import { useState, useCallback } from 'react';

interface CodeBlockProps {
  code: string;
  language?: string;
}

export default function CodeBlock({ code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = code;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [code]);

  return (
    <div className="relative group">
      {language && (
        <div className="absolute top-2 left-3 text-[9px] text-serpent-text-dark font-mono uppercase">
          {language}
        </div>
      )}
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 text-[10px] px-2 py-[3px] bg-[#111] border border-serpent-border rounded font-mono cursor-pointer transition-all duration-200 opacity-0 group-hover:opacity-100 hover:border-serpent-border-hover"
        style={{ color: copied ? '#2DD4A8' : '#666' }}
      >
        {copied ? 'Copied' : 'Copy'}
      </button>
      <pre className="bg-[#060606] border border-[#131313] rounded-lg p-4 pt-7 text-[10.5px] leading-[1.7] text-serpent-text-muted font-mono overflow-x-auto">
        {code}
      </pre>
    </div>
  );
}
