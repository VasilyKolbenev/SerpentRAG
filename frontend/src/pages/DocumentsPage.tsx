/**
 * Documents page — document library with upload zone and management.
 */

import DocumentList from '@/components/documents/DocumentList';
import UploadZone from '@/components/documents/UploadZone';

export default function DocumentsPage() {
  return (
    <div className="animate-fade-slide-up">
      <div className="mb-6">
        <h1 className="text-[26px] font-semibold tracking-tight font-outfit mb-[5px]">
          Document Library
        </h1>
        <p className="text-[13px] text-serpent-text-muted font-dm-sans">
          Upload documents and manage your knowledge base
        </p>
      </div>

      {/* Upload section */}
      <div className="bg-serpent-surface border border-serpent-border-light rounded-[14px] p-[18px] mb-5">
        <h4 className="text-[10px] text-serpent-text-dark mb-3 uppercase tracking-[1.5px] font-mono">
          Upload Documents
        </h4>
        <UploadZone />
      </div>

      <DocumentList />
    </div>
  );
}
