/**
 * ClearHire Pending Document Storage Service
 * 
 * Provides durable browser-refresh recovery for uploaded resume documents
 * awaiting application submission.
 * 
 * CRITICAL PRIVACY & SECURITY RULES:
 * - NEVER stores PDF binary data, extracted text, JWT tokens, or sensitive resume contents.
 * - Stores ONLY minimal reference metadata: documentId, candidateId, jobId, fileName, savedAt.
 * - Keyed strictly by `${candidateId}:${jobId}` to guarantee multi-job and cross-candidate isolation.
 * - Expired entries (> 7 days) are automatically pruned.
 * - Authorization and document access verification remain strictly enforced by backend endpoints.
 */

export interface StoredPendingDocument {
  documentId: string;
  candidateId: string;
  jobId: string;
  fileName: string;
  savedAt: number;
}

interface PendingDocumentsPayload {
  version: 1;
  entries: Record<string, StoredPendingDocument>;
}

const STORAGE_KEY = 'clearhire_pending_documents_v1';
const EXPIRATION_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

function makeCompositeKey(candidateId: string, jobId: string): string {
  return `${candidateId}:${jobId}`;
}

function readPayload(): PendingDocumentsPayload {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { version: 1, entries: {} };
    }

    const parsed = JSON.parse(raw);
    if (!parsed || parsed.version !== 1 || typeof parsed.entries !== 'object') {
      return { version: 1, entries: {} };
    }

    // Prune expired entries
    const now = Date.now();
    let hasPruned = false;
    const cleanEntries: Record<string, StoredPendingDocument> = {};

    for (const [k, v] of Object.entries(parsed.entries as Record<string, StoredPendingDocument>)) {
      if (v && v.documentId && v.candidateId && v.jobId && v.savedAt && now - v.savedAt < EXPIRATION_TTL_MS) {
        cleanEntries[k] = v;
      } else {
        hasPruned = true;
      }
    }

    if (hasPruned) {
      writePayload({ version: 1, entries: cleanEntries });
    }

    return { version: 1, entries: cleanEntries };
  } catch (err) {
    console.warn('[pendingDocumentStore] Failed to read storage payload; resetting to empty.', err);
    return { version: 1, entries: {} };
  }
}

function writePayload(payload: PendingDocumentsPayload): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch (err) {
    console.warn('[pendingDocumentStore] Failed to write storage payload (localStorage unavailable or full).', err);
  }
}

class PendingDocumentStore {
  /**
   * Save a pending resume document reference for an authenticated candidate and job requisition.
   */
  savePendingDocument(
    candidateId: string,
    jobId: string,
    doc: { documentId: string; fileName?: string }
  ): void {
    if (!candidateId || !jobId || !doc.documentId) {
      return;
    }

    const payload = readPayload();
    const key = makeCompositeKey(candidateId, jobId);

    payload.entries[key] = {
      documentId: doc.documentId,
      candidateId,
      jobId,
      fileName: doc.fileName || 'resume.pdf',
      savedAt: Date.now(),
    };

    writePayload(payload);
  }

  /**
   * Retrieve a pending resume document reference for a specific candidate and job.
   * Returns null if not found, malformed, or expired.
   */
  getPendingDocument(candidateId: string, jobId: string): StoredPendingDocument | null {
    if (!candidateId || !jobId) {
      return null;
    }

    const payload = readPayload();
    const key = makeCompositeKey(candidateId, jobId);
    const entry = payload.entries[key];

    if (!entry || !entry.documentId) {
      return null;
    }

    // Verify candidate isolation
    if (entry.candidateId !== candidateId || entry.jobId !== jobId) {
      return null;
    }

    return entry;
  }

  /**
   * Remove a pending resume document reference (e.g. upon successful application submission
   * or when candidate chooses to upload a different resume).
   */
  removePendingDocument(candidateId: string, jobId: string): void {
    if (!candidateId || !jobId) {
      return;
    }

    const payload = readPayload();
    const key = makeCompositeKey(candidateId, jobId);

    if (payload.entries[key]) {
      delete payload.entries[key];
      writePayload(payload);
    }
  }

  /**
   * Remove all pending documents belonging to a candidate (e.g. on logout or account wipe).
   */
  clearPendingDocumentsForCandidate(candidateId: string): void {
    if (!candidateId) return;

    const payload = readPayload();
    let modified = false;

    for (const [k, v] of Object.entries(payload.entries)) {
      if (v.candidateId === candidateId) {
        delete payload.entries[k];
        modified = true;
      }
    }

    if (modified) {
      writePayload(payload);
    }
  }

  /**
   * Clear the entire storage namespace (used for test teardowns).
   */
  clearAll(): void {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignored
    }
  }
}

export const pendingDocumentStore = new PendingDocumentStore();
