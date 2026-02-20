/**
 * Drag-drop upload zone — ported from JSX, rewired to real API.
 */

import { useState, useCallback, useRef } from 'react';
import { api } from '@/lib/api';
import { formatFileSize } from '@/lib/utils';
import { useAppStore } from '@/stores/appStore';

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  status: 'uploading' | 'processing' | 'indexed' | 'failed';
  error?: string;
}

export default function UploadZone() {
  const [dragging, setDragging] = useState(false);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const activeCollection = useAppStore((s) => s.activeCollection);

  const uploadFile = useCallback(
    async (file: File) => {
      const tempId = `${Date.now()}-${file.name}`;

      setFiles((prev) => [
        ...prev,
        {
          id: tempId,
          name: file.name,
          size: file.size,
          status: 'uploading',
        },
      ]);

      try {
        const res = await api.uploadDocument(file, activeCollection);

        setFiles((prev) =>
          prev.map((f) =>
            f.id === tempId
              ? { ...f, id: res.id, status: 'processing' }
              : f,
          ),
        );

        // Poll for status
        pollDocumentStatus(res.id, tempId);
      } catch (err) {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === tempId
              ? {
                  ...f,
                  status: 'failed',
                  error: err instanceof Error ? err.message : 'Upload failed',
                }
              : f,
          ),
        );
      }
    },
    [activeCollection],
  );

  const pollDocumentStatus = useCallback(
    async (docId: string, tempId: string) => {
      let attempts = 0;
      const maxAttempts = 60; // 5 minutes max

      const check = async () => {
        try {
          const doc = await api.getDocument(docId);

          setFiles((prev) =>
            prev.map((f) =>
              f.id === docId || f.id === tempId
                ? {
                    ...f,
                    id: docId,
                    status: doc.status as UploadedFile['status'],
                    error:
                      doc.status === 'failed'
                        ? 'Processing failed'
                        : undefined,
                  }
                : f,
            ),
          );

          if (doc.status === 'processing' && attempts < maxAttempts) {
            attempts++;
            setTimeout(check, 5000);
          }
        } catch {
          // Silently continue polling
          if (attempts < maxAttempts) {
            attempts++;
            setTimeout(check, 5000);
          }
        }
      };

      setTimeout(check, 3000);
    },
    [],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const droppedFiles = Array.from(e.dataTransfer.files);
      droppedFiles.forEach(uploadFile);
    },
    [uploadFile],
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFiles = Array.from(e.target.files ?? []);
      selectedFiles.forEach(uploadFile);
      if (inputRef.current) inputRef.current.value = '';
    },
    [uploadFile],
  );

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.txt,.md,.csv,.json"
        className="hidden"
        onChange={handleFileInput}
      />

      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className="rounded-[10px] p-7 text-center cursor-pointer transition-all duration-300"
        style={{
          border: `1.5px dashed ${dragging ? '#C8F547' : '#1e1e1e'}`,
          background: dragging ? '#C8F54704' : '#080808',
        }}
      >
        <div className="text-[28px] mb-2.5 opacity-50">{'\uD83D\uDC0D'}</div>
        <p className="text-xs text-serpent-text-muted mb-[3px] font-dm-sans">
          Drop files here to feed the Serpent
        </p>
        <p className="text-[10px] text-serpent-text-darker font-mono">
          PDF {'\u00B7'} DOCX {'\u00B7'} TXT {'\u00B7'} MD {'\u00B7'} CSV{' '}
          {'\u00B7'} JSON
        </p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="mt-2.5">
          {files.map((f) => (
            <div
              key={f.id}
              className="flex items-center gap-2 px-2.5 py-[6px] mb-[3px] bg-serpent-surface rounded-[6px] border border-serpent-border-light"
            >
              <span className="text-[10px]">
                {f.status === 'indexed'
                  ? '\u2705'
                  : f.status === 'failed'
                    ? '\u274C'
                    : '\u23F3'}
              </span>
              <span className="text-[11px] text-serpent-text-muted flex-1 font-mono truncate">
                {f.name}
              </span>
              <span className="text-[9px] text-serpent-text-dark font-mono">
                {formatFileSize(f.size)}
              </span>
              <span
                className="text-[9px] font-mono"
                style={{
                  color:
                    f.status === 'indexed'
                      ? '#2DD4A8'
                      : f.status === 'failed'
                        ? '#ef4444'
                        : '#C8F547',
                }}
              >
                {f.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
