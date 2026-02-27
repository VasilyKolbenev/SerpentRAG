/**
 * Document list with status, chunk count, and delete functionality.
 * Fetches all documents from the backend and auto-refreshes.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '@/lib/api';
import { formatFileSize } from '@/lib/utils';
import { useAppStore } from '@/stores/appStore';
import type { DocumentResponse } from '@/types/api';

const REFRESH_INTERVAL = 30_000; // 30s
const UPLOAD_REFRESH_DEBOUNCE = 1000; // 1s debounce for upload-triggered refresh

const STATUS_STYLES: Record<string, { color: string; bg: string }> = {
  indexed: { color: '#2DD4A8', bg: 'rgba(45, 212, 168, 0.06)' },
  processing: { color: '#C8F547', bg: 'rgba(200, 245, 71, 0.06)' },
  failed: { color: '#ef4444', bg: 'rgba(239, 68, 68, 0.06)' },
  pending: { color: '#a1a1aa', bg: 'rgba(161, 161, 170, 0.06)' },
};

export default function DocumentList() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await api.listDocuments();
      setDocuments(res.documents);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch documents');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
    const interval = setInterval(fetchDocuments, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchDocuments]);

  // Auto-refresh when any upload finishes (indexed/failed)
  const uploads = useAppStore((s) => s.uploads);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevIndexedCount = useRef(0);

  useEffect(() => {
    const indexedCount = Object.values(uploads).filter(
      (u) => u.status === 'indexed',
    ).length;

    if (indexedCount > prevIndexedCount.current) {
      // New upload just finished — debounce refresh
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
      debounceTimer.current = setTimeout(fetchDocuments, UPLOAD_REFRESH_DEBOUNCE);
    }
    prevIndexedCount.current = indexedCount;

    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [uploads, fetchDocuments]);

  const handleDelete = useCallback(
    async (docId: string) => {
      setDeletingId(docId);
      setConfirmDeleteId(null);
      try {
        await api.deleteDocument(docId);
        setDocuments((prev) => prev.filter((d) => d.id !== docId));
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to delete document',
        );
      } finally {
        setDeletingId(null);
      }
    },
    [],
  );

  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className="h-[52px] bg-serpent-surface border border-serpent-border-light rounded-[10px] animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/5 border border-red-500/20 rounded-[10px] p-4 text-center">
        <p className="text-[12px] text-red-400 font-mono">{error}</p>
        <button
          onClick={fetchDocuments}
          className="mt-2 text-[11px] text-serpent-text-muted hover:text-serpent-text-secondary transition-colors cursor-pointer"
        >
          Retry
        </button>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="bg-serpent-surface border border-serpent-border-light rounded-[14px] p-10 text-center">
        <div className="text-[36px] mb-3 opacity-40">{'\uD83D\uDCC2'}</div>
        <p className="text-[13px] text-serpent-text-muted font-dm-sans mb-1">
          No documents uploaded yet
        </p>
        <p className="text-[11px] text-serpent-text-darker font-mono">
          Use the upload zone above or in Chat to add documents
        </p>
      </div>
    );
  }

  return (
    <div className="bg-serpent-surface border border-serpent-border-light rounded-[14px] overflow-hidden">
      {/* Header row */}
      <div className="grid grid-cols-[1fr_90px_80px_90px_140px_40px] gap-3 px-4 py-2.5 border-b border-serpent-border-light">
        <span className="text-[10px] text-serpent-text-dark uppercase tracking-[1.5px] font-mono">
          Filename
        </span>
        <span className="text-[10px] text-serpent-text-dark uppercase tracking-[1.5px] font-mono">
          Status
        </span>
        <span className="text-[10px] text-serpent-text-dark uppercase tracking-[1.5px] font-mono text-right">
          Chunks
        </span>
        <span className="text-[10px] text-serpent-text-dark uppercase tracking-[1.5px] font-mono text-right">
          Size
        </span>
        <span className="text-[10px] text-serpent-text-dark uppercase tracking-[1.5px] font-mono">
          Uploaded
        </span>
        <span />
      </div>

      {/* Document rows */}
      {documents.map((doc) => {
        const status = STATUS_STYLES[doc.status] ?? STATUS_STYLES.pending;
        const isDeleting = deletingId === doc.id;
        const isConfirming = confirmDeleteId === doc.id;

        return (
          <div
            key={doc.id}
            className="grid grid-cols-[1fr_90px_80px_90px_140px_40px] gap-3 px-4 py-3 border-b border-serpent-border-light last:border-b-0 hover:bg-[#0a0a0a] transition-colors"
          >
            {/* Filename */}
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-[10px] opacity-60">
                {doc.status === 'indexed'
                  ? '\u2705'
                  : doc.status === 'failed'
                    ? '\u274C'
                    : '\u23F3'}
              </span>
              <span
                className="text-[12px] text-serpent-text-secondary font-mono truncate"
                title={doc.filename}
              >
                {doc.filename}
              </span>
            </div>

            {/* Status badge */}
            <div className="flex items-center">
              <span
                className="text-[10px] font-mono px-2 py-[2px] rounded-[4px]"
                style={{ color: status.color, background: status.bg }}
                title={doc.processing_phase ?? undefined}
              >
                {doc.status === 'processing' && doc.processing_phase
                  ? doc.processing_phase
                  : doc.status}
              </span>
            </div>

            {/* Chunks */}
            <div className="flex items-center justify-end">
              <span className="text-[11px] text-serpent-text-muted font-mono">
                {doc.chunks}
              </span>
            </div>

            {/* Size */}
            <div className="flex items-center justify-end">
              <span className="text-[11px] text-serpent-text-muted font-mono">
                {formatFileSize(doc.file_size)}
              </span>
            </div>

            {/* Date */}
            <div className="flex items-center">
              <span className="text-[10px] text-serpent-text-darker font-mono">
                {formatDate(doc.created_at)}
              </span>
            </div>

            {/* Delete */}
            <div className="flex items-center justify-center">
              {isDeleting ? (
                <span className="text-[10px] text-serpent-text-darker animate-pulse">
                  ...
                </span>
              ) : isConfirming ? (
                <div className="flex gap-1">
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="text-[9px] text-red-400 hover:text-red-300 cursor-pointer font-mono"
                    title="Confirm delete"
                  >
                    {'\u2713'}
                  </button>
                  <button
                    onClick={() => setConfirmDeleteId(null)}
                    className="text-[9px] text-serpent-text-muted hover:text-serpent-text-secondary cursor-pointer font-mono"
                    title="Cancel"
                  >
                    {'\u2715'}
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmDeleteId(doc.id)}
                  className="text-[12px] opacity-30 hover:opacity-80 hover:text-red-400 cursor-pointer transition-all"
                  title="Delete document"
                >
                  {'\uD83D\uDDD1'}
                </button>
              )}
            </div>
          </div>
        );
      })}

      {/* Footer */}
      <div className="px-4 py-2 border-t border-serpent-border-light flex justify-between items-center">
        <span className="text-[10px] text-serpent-text-darker font-mono">
          {documents.length} document{documents.length !== 1 ? 's' : ''}
        </span>
        <span className="text-[10px] text-serpent-text-darker font-mono">
          {documents.reduce((sum, d) => sum + d.chunks, 0)} total chunks
        </span>
      </div>
    </div>
  );
}

function formatDate(iso: string): string {
  if (!iso) return '-';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso.slice(0, 16);
  }
}
