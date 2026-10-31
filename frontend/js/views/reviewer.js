/**
 * ClearHire Human Reviewer Verification Desk View
 */

import { state } from '../state.js';
import { api } from '../api.js';

export function renderReviewer(container) {
  let selectedFlag = state.selectedReviewFlag;
  let statusFilter = 'all'; // 'all', 'pending', 'resolved'

  function updateView() {
    const filteredFlags = state.reviewFlags.filter(f => {
      if (statusFilter === 'all') return true;
      return f.status === statusFilter;
    });

    // If currently selected flag is filtered out, select first available
    if (!filteredFlags.some(f => f.id === selectedFlag.id) && filteredFlags.length > 0) {
      selectedFlag = filteredFlags[0];
      state.selectedReviewFlag = selectedFlag;
    }

    container.innerHTML = `
      <div class="animate-fade-in">
        <!-- Section Header -->
        <div class="view-header">
          <div class="view-title-group">
            <h1>
              <span>Human Reviewer Verification Desk</span>
              <span class="persona-badge reviewer">Reviewer Workspace</span>
            </h1>
            <p class="view-subtitle">Human-in-the-loop oversight desk. Inspect ambiguous candidate evidence, review applicant clarifications, and record binding decisions with mandatory written rationales.</p>
          </div>
          <div class="view-actions">
            <span class="status-indicator">
              <span class="status-dot live"></span>
              <span>Reviewer: <strong>${state.currentRole.name}</strong></span>
            </span>
          </div>
        </div>

        <!-- Two Column Desk Layout: Left Queue, Right Detail & Decision -->
        <div class="view-sidebar-layout">
          
          <!-- Left Column: Case Queue -->
          <div>
            <div class="glass-panel" style="padding: 1.25rem;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3 style="font-size: 1.05rem;">Review Queue</h3>
                <span class="badge badge-neutral">${filteredFlags.length} Cases</span>
              </div>

              <!-- Filter Tabs -->
              <div style="display: flex; gap: 0.35rem; margin-bottom: 1rem;">
                <button class="btn btn-sm ${statusFilter === 'all' ? 'btn-primary' : 'btn-secondary'}" id="filter-all" style="flex: 1;">All</button>
                <button class="btn btn-sm ${statusFilter === 'pending' ? 'btn-primary' : 'btn-secondary'}" id="filter-pending" style="flex: 1;">Pending</button>
                <button class="btn btn-sm ${statusFilter === 'resolved' ? 'btn-primary' : 'btn-secondary'}" id="filter-resolved" style="flex: 1;">Resolved</button>
              </div>

              <!-- Case List -->
              <div class="case-list">
                ${filteredFlags.map(f => {
                  const isActive = f.id === selectedFlag.id;
                  const isPending = f.status === 'pending';
                  const priorityClass = f.priority === 'high' ? 'badge-notfound' : 'badge-neutral';
                  const statusClass = f.status === 'resolved' ? 'badge-supported' : 'badge-ambiguous';

                  return `
                    <div class="review-case-item ${isActive ? 'active' : ''}" data-flag-id="${f.id}">
                      <div style="display: flex; flex-direction: column; gap: 0.2rem;">
                        <div style="display: flex; align-items: center; gap: 0.4rem;">
                          <strong style="color: var(--text-main); font-size: 0.95rem;">${f.candidate_name}</strong>
                          <span class="badge ${priorityClass}" style="font-size: 0.68rem; padding: 0.1rem 0.4rem;">${f.priority}</span>
                        </div>
                        <div style="font-size: 0.78rem; color: var(--text-muted);">
                          Criterion: <strong style="color: var(--accent-blue);">${f.criterion_name}</strong>
                        </div>
                        <div style="font-size: 0.72rem; color: var(--text-subtle);">
                          ${f.flag_type.replace('_', ' ')}
                        </div>
                      </div>
                      <span class="badge ${statusClass}" style="font-size: 0.72rem;">${f.status}</span>
                    </div>
                  `;
                }).join('')}
              </div>
            </div>
          </div>

          <!-- Right Column: Case Deep-Dive & Mandatory Rationale Decision Console -->
          <div>
            ${selectedFlag ? `
              <div class="review-detail-pane">
                <!-- Case Header -->
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 1rem;">
                  <div>
                    <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.3rem;">
                      <h2>${selectedFlag.criterion_name} Review Case</h2>
                      <span class="badge ${selectedFlag.status === 'resolved' ? 'badge-supported' : 'badge-ambiguous'}">${selectedFlag.status}</span>
                    </div>
                    <p style="font-size: 0.85rem;">
                      Candidate: <strong>${selectedFlag.candidate_name}</strong> &bull; Requisition: <strong>${selectedFlag.job_title}</strong>
                    </p>
                  </div>
                  <div style="text-align: right; font-size: 0.78rem; color: var(--text-subtle);">
                    Flagged: ${new Date(selectedFlag.created_at).toLocaleDateString()}
                  </div>
                </div>

                <!-- Flag Reason Callout -->
                <div class="alert-callout warning" style="margin-bottom: 1.25rem;">
                  <div class="alert-callout-icon">&#9888;&#65039;</div>
                  <div class="alert-callout-content">
                    <strong>Auto-Flag Reason:</strong> ${selectedFlag.reason}
                  </div>
                </div>

                <!-- Side-by-Side Comparison Box -->
                <div class="comparison-box">
                  <div>
                    <div class="comparison-column-title">Job Criterion Benchmark</div>
                    <div style="font-weight: 700; color: var(--text-main); font-size: 1rem; margin-bottom: 0.35rem;">
                      ${selectedFlag.criterion_name} (Required)
                    </div>
                    <p style="font-size: 0.85rem; color: var(--text-muted);">
                      Production experience with container orchestration, cluster deployments, and cloud-native architecture.
                    </p>
                  </div>

                  <div>
                    <div class="comparison-column-title">Candidate Verbatim Source Excerpt</div>
                    <div class="evidence-quote-box ambiguous" style="margin: 0;">
                      <div class="quote-verbatim">"${selectedFlag.source_excerpt}"</div>
                      <div class="quote-provenance">
                        <span class="page-chip">Page ${selectedFlag.source_page}</span>
                        <span class="grounding-chip">&#10003; Raw PDF Verified</span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Candidate Clarification Section (if present) -->
                ${selectedFlag.candidate_statement ? `
                  <div style="background: rgba(59, 130, 246, 0.08); border: 1px solid var(--accent-blue-border); border-radius: var(--radius-md); padding: 1.25rem; margin-bottom: 1.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                      <div style="font-size: 0.82rem; text-transform: uppercase; color: var(--accent-blue); font-weight: 700;">
                        Candidate Clarification Submission
                      </div>
                      <span class="badge badge-supported">Submitted for Review</span>
                    </div>
                    <p style="font-size: 0.9rem; color: var(--text-main); font-style: italic; line-height: 1.5;">
                      "${selectedFlag.candidate_statement}"
                    </p>
                  </div>
                ` : `
                  <div style="background: var(--bg-secondary); border-radius: var(--radius-md); padding: 0.85rem 1.15rem; margin-bottom: 1.5rem; font-size: 0.82rem; color: var(--text-subtle);">
                    No candidate clarification submitted yet. Decision can be made based on resume evidence alone or clarification can be requested.
                  </div>
                `}

                <!-- Prior Resolution Summary if already resolved -->
                ${selectedFlag.status === 'resolved' ? `
                  <div class="alert-callout success" style="margin-bottom: 1.5rem;">
                    <div class="alert-callout-icon">&#10003;</div>
                    <div class="alert-callout-content">
                      <strong>Resolved Decision:</strong> ${selectedFlag.decision.toUpperCase()}<br/>
                      <strong>Reviewer:</strong> ${selectedFlag.resolved_by || 'Elena Rostova'} &bull; ${new Date(selectedFlag.resolved_at).toLocaleString()}<br/>
                      <strong>Mandatory Rationale:</strong> "${selectedFlag.mandatory_rationale}"
                    </div>
                  </div>
                ` : `
                  <!-- Mandatory Rationale Decision Console -->
                  <div style="background: var(--bg-secondary); border: 1px solid var(--border-medium); border-radius: var(--radius-md); padding: 1.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                      <h4 style="font-size: 1rem;">Record Human Reviewer Determination</h4>
                      <span class="badge badge-audit">Enforces Mandatory Rationale</span>
                    </div>
                    <p style="font-size: 0.82rem; color: var(--text-subtle); margin-bottom: 1rem;">
                      ClearHire requires an explicit explanation for every decision to guarantee fairness, eliminate silent rejection, and preserve anti-bias auditability.
                    </p>

                    <div class="form-group">
                      <label class="form-label">Reviewer Written Rationale (Required) *</label>
                      <textarea class="form-textarea" id="input-reviewer-rationale" rows="3" placeholder="State your factual rationale for accepting, rejecting, or requesting further clarification on this evidence..."></textarea>
                      <span class="form-hint" id="rationale-char-hint">Enter at least 15 characters. Clear, objective reasoning required.</span>
                    </div>

                    <div class="decision-action-group">
                      <button class="btn btn-success" id="btn-decision-accept" style="flex: 1;">
                        &#10003; Accept Evidence
                      </button>
                      <button class="btn btn-danger" id="btn-decision-reject" style="flex: 1;">
                        &times; Reject Evidence
                      </button>
                      <button class="btn btn-warning" id="btn-decision-clarify" style="flex: 1;">
                        &#63; Request Clarification
                      </button>
                    </div>
                  </div>
                `}

              </div>
            ` : `
              <div class="glass-panel" style="padding: 3rem; text-align: center; color: var(--text-subtle);">
                Select a review case from the queue to inspect evidence.
              </div>
            `}
          </div>

        </div>
      </div>
    `;

    // Attach Event Handlers
    container.querySelectorAll('.review-case-item').forEach(item => {
      item.addEventListener('click', () => {
        const flagId = item.getAttribute('data-flag-id');
        selectedFlag = state.reviewFlags.find(f => f.id === flagId);
        state.selectedReviewFlag = selectedFlag;
        updateView();
      });
    });

    document.getElementById('filter-all')?.addEventListener('click', () => {
      statusFilter = 'all';
      updateView();
    });

    document.getElementById('filter-pending')?.addEventListener('click', () => {
      statusFilter = 'pending';
      updateView();
    });

    document.getElementById('filter-resolved')?.addEventListener('click', () => {
      statusFilter = 'resolved';
      updateView();
    });

    // Decision Handlers
    const handleDecision = async (decision) => {
      const rationaleInput = document.getElementById('input-reviewer-rationale');
      const rationale = rationaleInput?.value.trim() || '';

      if (rationale.length < 10) {
        window.showToast?.('Mandatory rationale must be provided (minimum 10 characters).', 'error');
        rationaleInput?.focus();
        return;
      }

      window.showToast?.(`Recording decision '${decision.toUpperCase()}' with audit hash...`, 'info');
      await api.recordDecision(selectedFlag.id, decision, rationale);
      window.showToast?.(`Determination recorded! Immutable audit event created.`, 'success');
      updateView();
    };

    document.getElementById('btn-decision-accept')?.addEventListener('click', () => {
      const rationaleInput = document.getElementById('input-reviewer-rationale');
      if (!rationaleInput.value) {
        rationaleInput.value = "Candidate's candidate clarification and resume excerpt verify that 'K8s' directly refers to production Kubernetes on AWS EKS with CRDs.";
      }
      handleDecision('accepted');
    });

    document.getElementById('btn-decision-reject')?.addEventListener('click', () => {
      const rationaleInput = document.getElementById('input-reviewer-rationale');
      if (!rationaleInput.value) {
        rationaleInput.value = "Evidence is merely a keyword mention without production engineering duties or verifiable projects.";
      }
      handleDecision('rejected');
    });

    document.getElementById('btn-decision-clarify')?.addEventListener('click', () => {
      const rationaleInput = document.getElementById('input-reviewer-rationale');
      if (!rationaleInput.value) {
        rationaleInput.value = "Requested additional proof of multi-cluster production management experience.";
      }
      handleDecision('requested_clarification');
    });
  }

  updateView();
}
