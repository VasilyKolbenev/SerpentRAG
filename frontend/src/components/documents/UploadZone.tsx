/**
 * Drag-drop upload zone — uses global Zustand store for upload state
 * so status persists across page navigation.
 *
 * Features:
 *  - SHA256 dedup (backend returns already_exists)
 *  - Exponential backoff polling (2s → 4s → 8s → 16s → 30s)
 *  - Granular processing phases (parsing → chunking → embedding → storing → extracting_entities)
 *  - Global upload state survives page changes
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { api } from '@/lib/api';
import { formatFileSize } from '@/lib/utils';
import { useAppStore } from '@/stores/appStore';
import type { UploadedFile } from '@/stores/appStore';

const PHASE_LABELS: Record<string, string> = {
  queued: 'Queued',
  parsing: 'Parsing',
  chunking: 'Chunking',
  embedding: 'Embedding',
  storing: 'Storing',
  extracting_entities: 'Extracting entities',
};

const BACKOFF_INITIAL_MS = 2000;
const BACKOFF_MAX_MS = 30_000;
const BACKOFF_MULTIPLIER = 2;
const MAX_POLL_TIME_MS = 5 * 60 * 1000; // 5 minutes

export default function UploadZone() {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const mountedRef = useRef(true);
  const pollTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const activeCollection = useAppStore((s) => s.activeCollection);
  const uploads = useAppStore((s) => s.uploads);
  const addUpload = useAppStore((s) => s.addUpload);
  const updateUpload = useAppStore((s) => s.updateUpload);
  const clearFinishedUploads = useAppStore((s) => s.clearFinishedUploads);

  // Track mount state for polling cleanup
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      // Clear all pending polling timers
      for (const timer of pollTimers.current.values()) {
        clearTimeout(timer);
      }
      pollTimers.current.clear();
    };
  }, []);

  // Resume polling for any in-progress uploads on mount
  useEffect(() => {
    for (const upload of Object.values(uploads)) {
      if (upload.status === 'processing') {
        pollDocumentStatus(upload.id);
      }
    }
    // Only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const uploadFile = useCallback(
    async (file: File) => {
      const tempId = `temp-${Date.now()}-${file.name}`;

      addUpload({
        id: tempId,
        name: file.name,
        size: file.size,
        status: 'uploading',
        collection: activeCollection,
      });

      try {
        const res = await api.uploadDocument(file, activeCollection);

        if (!mountedRef.current) return;

        if (res.status === 'already_exists') {
          // Duplicate — update with real id and already_exists status
          updateUpload(tempId, {
            id: res.id,
            status: 'already_exists',
          });
          return;
        }

        // Replace temp entry with real doc_id
        updateUpload(tempId, {
          id: res.id,
          status: 'processing',
          processing_phase: 'queued',
        });

        // Start polling
        pollDocumentStatus(res.id);
      } catch (err) {
        if (!mountedRef.current) return;
        updateUpload(tempId, {
          status: 'failed',
          error: err instanceof Error ? err.message : 'Upload failed',
        });
      }
    },
    [activeCollection, addUpload, updateUpload],
  );

  const pollDocumentStatus = useCallback(
    (docId: string) => {
      let delay = BACKOFF_INITIAL_MS;
      const startTime = Date.now();

      const check = async () => {
        if (!mountedRef.current) return;
        if (Date.now() - startTime > MAX_POLL_TIME_MS) return;

        try {
          const doc = await api.getDocument(docId);
          if (!mountedRef.current) return;

          updateUpload(docId, {
            status: doc.status as UploadedFile['status'],
            processing_phase: doc.processing_phase ?? undefined,
            error: doc.status === 'failed' ? 'Processing failed' : undefined,
          });

          if (doc.status === 'processing') {
            // Exponential backoff
            delay = Math.min(delay * BACKOFF_MULTIPLIER, BACKOFF_MAX_MS);
            const timer = setTimeout(check, delay);
            pollTimers.current.set(docId, timer);
          } else {
            pollTimers.current.delete(docId);
          }
        } catch {
          if (!mountedRef.current) return;
          // Retry with backoff on network error
          delay = Math.min(delay * BACKOFF_MULTIPLIER, BACKOFF_MAX_MS);
          const timer = setTimeout(check, delay);
          pollTimers.current.set(docId, timer);
        }
      };

      const timer = setTimeout(check, BACKOFF_INITIAL_MS);
      pollTimers.current.set(docId, timer);
    },
    [updateUpload],
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

  const uploadList = Object.values(uploads);
  const hasFinished = uploadList.some(
    (f) =>
      f.status === 'indexed' ||
      f.status === 'failed' ||
      f.status === 'already_exists',
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
      {uploadList.length > 0 && (
        <div className="mt-2.5">
          {uploadList.map((f) => (
            <div
              key={f.id}
              className="flex items-center gap-2 px-2.5 py-[6px] mb-[3px] bg-serpent-surface rounded-[6px] border border-serpent-border-light"
            >
              <span className="text-[10px]">
                {f.status === 'indexed'
                  ? '\u2705'
                  : f.status === 'already_exists'
                    ? '\u26A0\uFE0F'
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
                      : f.status === 'already_exists'
                        ? '#facc15'
                        : f.status === 'failed'
                          ? '#ef4444'
                          : '#C8F547',
                }}
              >
                {f.status === 'processing' && f.processing_phase
                  ? PHASE_LABELS[f.processing_phase] ?? f.processing_phase
                  : f.status === 'already_exists'
                    ? 'duplicate'
                    : f.status}
              </span>
            </div>
          ))}

          {/* Clear finished button */}
          {hasFinished && (
            <button
              onClick={clearFinishedUploads}
              className="w-full mt-1 py-1 text-[9px] text-serpent-text-darker hover:text-serpent-text-muted font-mono uppercase tracking-wider transition-colors"
            >
              Clear finished
            </button>
          )}
        </div>
      )}
    </div>
  );
}
