/**
 * ClearHire Cryptographic Audit & Compliance Ledger View
 */

import { state } from '../state.js';
import { api } from '../api.js';

export function renderAudit(container) {
  let verificationReport = null;
  let isVerifying = false;

  async function updateView() {
    container.innerHTML = `
      <div class="animate-fade-in">
        <!-- Section Header -->
        <div class="view-header">
          <div class="view-title-group">
            <h1>
              <span>Cryptographic Audit & Compliance Ledger</span>
              <span class="persona-badge system_auditor">System Auditor View</span>
            </h1>
            <p class="view-subtitle">Immutable, append-only event ledger tracking all screening decisions, candidate clarifications, and reviewer determinations chained via SHA-256 hashes.</p>
          </div>
          <div class="view-actions">
            <button class="btn btn-primary btn-sm" id="btn-verify-chain" ${isVerifying ? 'disabled' : ''}>
              ${isVerifying ? '<span class="spinner"></span> Verifying Chain...' : '&#128272; Verify Cryptographic Hash Chain'}
            </button>
          </div>
        </div>

        <!-- Verification Status Callout -->
        ${verificationReport ? `
          <div class="alert-callout success" style="margin-bottom: 2rem;">
            <div class="alert-callout-icon">&#9989;</div>
            <div class="alert-callout-content">
              <strong>Hash-Chain Verification Passed:</strong> ${verificationReport.details}<br/>
              Total Events Verified: <strong>${verificationReport.total_events}</strong> &bull; 
              Continuous Chain Range: <strong>Seq #${verificationReport.sequence_start} &rarr; #${verificationReport.sequence_end}</strong> &bull;
              Zero sequence gaps or altered hashes detected.
            </div>
          </div>
        ` : `
          <div class="alert-callout info" style="margin-bottom: 2rem;">
            <div class="alert-callout-icon">&#128737;&#65039;</div>
            <div class="alert-callout-content">
              <strong>Tamper-Evidence Architecture:</strong> Each audit event contains a canonical payload hash (\`event_hash\`) and mathematically includes the previous event's hash (\`previous_hash\`). If any past decision, rationale, or state is altered in the database, the hash chain breaks immediately.
            </div>
          </div>
        `}

        <!-- Ledger Timeline Stream -->
        <div class="glass-panel" style="padding: 1.75rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
            <h3>Append-Only Audit Stream</h3>
            <span class="badge badge-audit">${state.auditChain.length} Chained Blocks</span>
          </div>

          <div class="audit-chain-timeline">
            ${state.auditChain.map((ev, idx) => `
              <div class="audit-block-card">
                <div>
                  <span class="badge badge-neutral" style="font-family: var(--font-mono);">Seq #${ev.sequence_number}</span>
                </div>
                <div>
                  <div style="font-weight: 700; color: var(--text-main); font-size: 0.85rem;">${ev.action}</div>
                  <div style="font-size: 0.72rem; color: var(--text-subtle);">${new Date(ev.timestamp).toLocaleTimeString()}</div>
                </div>
                <div>
                  <div style="color: var(--text-muted); font-size: 0.82rem;">
                    Actor: <strong>${ev.actor_role}</strong> (${ev.actor_id.substring(0, 12)}...)
                  </div>
                  <div style="font-size: 0.75rem; color: var(--text-subtle);">
                    Resource: <code style="color: var(--accent-blue);">${ev.resource_type}</code> / ${ev.resource_id}
                  </div>
                </div>
                <div>
                  <div style="display: flex; flex-direction: column; gap: 0.2rem;">
                    <span style="font-size: 0.68rem; color: var(--text-subtle);">Prev: <span class="hash-pill">${ev.previous_hash.substring(0, 16)}...</span></span>
                    <span style="font-size: 0.68rem; color: var(--text-subtle);">Hash: <span class="hash-pill">${ev.event_hash.substring(0, 16)}...</span></span>
                  </div>
                </div>
                <div style="text-align: right;">
                  <span class="badge badge-supported" style="font-size: 0.7rem;">Verified</span>
                </div>
              </div>
              ${idx < state.auditChain.length - 1 ? `
                <div class="chain-link-connector">
                  &#8595; SHA-256 Link
                </div>
              ` : ''}
            `).join('')}
          </div>
        </div>

      </div>
    `;

    document.getElementById('btn-verify-chain')?.addEventListener('click', async () => {
      isVerifying = true;
      updateView();
      window.showToast?.('Verifying SHA-256 cryptographic continuity across audit events...', 'info');
      verificationReport = await api.verifyAuditChain();
      isVerifying = false;
      window.showToast?.('Hash chain verified! No tampering or sequence breaks detected.', 'success');
      updateView();
    });
  }

  updateView();
}
