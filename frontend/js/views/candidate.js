/**
 * ClearHire Candidate Evidence Portal View
 */

import { state } from '../state.js';
import { api } from '../api.js';

export function renderCandidate(container) {
  const applicant = state.selectedApplicant;
  const evaluation = applicant.evaluation;

  container.innerHTML = `
    <div class="animate-fade-in">
      <!-- Section Header -->
      <div class="view-header">
        <div class="view-title-group">
          <h1>
            <span>Candidate Evidence Transparency Portal</span>
            <span class="persona-badge candidate">Candidate View</span>
          </h1>
          <p class="view-subtitle">Inspect your extracted resume qualifications, review factual criteria coverage, and submit clarifications for ambiguous findings.</p>
        </div>
        <div class="view-actions">
          <div class="persona-selector-container">
            <span class="persona-label">Active Candidate:</span>
            <select class="persona-select" id="select-active-candidate">
              ${state.applicants.map(a => `
                <option value="${a.id}" ${a.id === applicant.id ? 'selected' : ''}>
                  ${a.name} (${a.scenario})
                </option>
              `).join('')}
            </select>
          </div>
        </div>
      </div>

      <!-- Candidate Scenario Explanation Banner -->
      <div class="alert-callout info">
        <div class="alert-callout-icon">&#128203;</div>
        <div class="alert-callout-content">
          <strong>Testing Profile (${applicant.name}):</strong> ${applicant.description}
        </div>
      </div>

      <!-- Main Layout: Sidebar (Upload & Skills) and Main (Evaluation & Criteria) -->
      <div class="view-sidebar-layout">
        
        <!-- Left Column: Document Upload & Verified Skills Inventory -->
        <div>
          <!-- Document Uploader Card -->
          <div class="glass-panel" style="padding: 1.5rem; margin-bottom: 1.5rem;">
            <h3 style="margin-bottom: 1rem; font-size: 1.1rem;">Resume Document</h3>
            <div class="drop-zone" id="resume-drop-zone">
              <svg class="drop-zone-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <div>
                <strong style="color: var(--text-main); font-size: 0.9rem;">Upload Candidate Resume (PDF)</strong>
                <p style="font-size: 0.75rem; color: var(--text-subtle); margin-top: 0.2rem;">Preserves page-layout and computes SHA-256 hash</p>
              </div>
              <input type="file" id="file-input-resume" accept=".pdf" style="display:none;" />
              <button class="btn btn-secondary btn-sm" id="btn-browse-file">Browse File</button>
            </div>

            <!-- Active Document Metadata -->
            <div style="margin-top: 1rem; padding: 0.85rem; background: var(--bg-secondary); border-radius: var(--radius-md); font-size: 0.8rem;">
              <div style="display: flex; justify-content: space-between; margin-bottom: 0.35rem;">
                <span style="color: var(--text-subtle);">Active Document:</span>
                <strong style="color: var(--text-main); font-family: var(--font-mono);">${applicant.resume_file}</strong>
              </div>
              <div style="display: flex; justify-content: space-between; margin-bottom: 0.35rem;">
                <span style="color: var(--text-subtle);">Page Count:</span>
                <span>${applicant.page_count} Pages (Preserved)</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--text-subtle);">Extraction Status:</span>
                <span class="badge badge-supported">Verified Grounded</span>
              </div>
            </div>
          </div>

          <!-- Verified Skills Inventory -->
          <div class="glass-panel" style="padding: 1.5rem;">
            <h3 style="margin-bottom: 0.4rem; font-size: 1.1rem;">Extracted Skills Inventory</h3>
            <p style="font-size: 0.8rem; margin-bottom: 1rem;">Structured claims extracted and verified against PDF text:</p>
            
            <div class="skills-pill-grid">
              ${applicant.skills.map(s => `
                <div class="skill-pill" title="Page ${s.source_page}: '${s.source_excerpt}'">
                  <span>${s.skill_name}</span>
                  <span class="skill-confidence">${Math.round(s.confidence * 100)}%</span>
                </div>
              `).join('')}
            </div>
          </div>
        </div>

        <!-- Right Column: Factual Criteria Coverage & Verification Breakdown -->
        <div>
          <div class="glass-panel" style="padding: 1.75rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
              <div>
                <h3 style="margin-bottom: 0.25rem;">Application Criteria Coverage</h3>
                <p style="font-size: 0.85rem;">Job Requisition: <strong>Senior Cloud Backend Engineer</strong> (REQ-CLOUD-2026)</p>
              </div>
              <!-- Coverage Breakdown Counters -->
              <div style="display: flex; gap: 0.5rem;">
                <span class="badge badge-supported">${evaluation.metrics.supported_count} Supported</span>
                <span class="badge badge-ambiguous">${evaluation.metrics.ambiguous_count} Ambiguous</span>
                <span class="badge badge-notfound">${evaluation.metrics.not_found_count} Not Found</span>
              </div>
            </div>

            <!-- Notes Callout -->
            <div style="background: var(--bg-secondary); padding: 0.95rem 1.25rem; border-radius: var(--radius-md); font-size: 0.85rem; margin-bottom: 1.5rem; border: 1px solid var(--border-subtle);">
              <span style="color: var(--accent-blue); font-weight: 600;">AI Evaluation Notes:</span>
              <span style="color: var(--text-muted); margin-left: 0.5rem;">${evaluation.summary_notes}</span>
            </div>

            <!-- Criteria List -->
            <div class="criteria-list">
              ${evaluation.criteria_evidence.map(ce => {
                const isAmbiguous = ce.ai_status === 'ambiguous';
                const isSupported = ce.ai_status === 'supported';
                const badgeClass = isSupported ? 'badge-supported' : (isAmbiguous ? 'badge-ambiguous' : 'badge-notfound');
                const quoteClass = isSupported ? 'supported' : (isAmbiguous ? 'ambiguous' : 'notfound');
                const catClass = ce.job_criterion_category === 'required' ? 'category-required' : 'category-preferred';

                return `
                  <div class="criteria-evidence-card">
                    <div class="criteria-header">
                      <div class="criteria-title-badge">
                        <span class="criterion-name">${ce.job_criterion_name}</span>
                        <span class="criterion-category-tag ${catClass}">${ce.job_criterion_category}</span>
                      </div>
                      <div style="display: flex; align-items: center; gap: 0.6rem;">
                        <span class="badge ${badgeClass}">${ce.ai_status}</span>
                        <span style="font-size: 0.75rem; color: var(--text-subtle); text-transform: capitalize;">
                          State: <strong>${ce.verification_state.replace('_', ' ')}</strong>
                        </span>
                      </div>
                    </div>

                    ${ce.source_excerpt ? `
                      <div class="evidence-quote-box ${quoteClass}">
                        <div class="quote-verbatim">"${ce.source_excerpt}"</div>
                        <div class="quote-provenance">
                          <span class="page-chip">Page ${ce.source_page}</span>
                          <span class="grounding-chip">&#10003; Verbatim Grounded</span>
                          <span>Confidence: ${Math.round(ce.ai_confidence * 100)}%</span>
                        </div>
                      </div>
                    ` : `
                      <div style="padding: 0.75rem; font-size: 0.85rem; color: var(--text-subtle); font-style: italic;">
                        No verbatim source excerpt found in candidate document.
                      </div>
                    `}

                    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 0.5rem; font-size: 0.82rem;">
                      <div style="color: var(--text-muted); max-width: 75%;">
                        <strong style="color: var(--text-main);">Reasoning:</strong> ${ce.ai_reasoning}
                      </div>
                      ${isAmbiguous || ce.verification_state === 'unverified' ? `
                        <button class="btn btn-outline btn-sm btn-clarify-criterion" data-criterion="${ce.job_criterion_name}" data-evidence-id="${ce.id}">
                          Provide Clarification &rarr;
                        </button>
                      ` : ''}
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        </div>
      </div>

      <!-- Candidate Clarification Modal / Drawer -->
      <div class="modal-overlay" id="modal-clarification">
        <div class="modal-box">
          <div class="modal-header">
            <h3>Candidate Clarification & Evidence Submission</h3>
            <button class="btn btn-outline btn-sm" id="btn-close-clarification">&times;</button>
          </div>
          <div class="modal-body">
            <p style="font-size: 0.85rem; margin-bottom: 1rem;">
              You are clarifying criterion: <strong id="modal-criterion-name" style="color: var(--accent-blue);"></strong>
            </p>
            <div class="alert-callout warning" style="padding: 0.75rem 1rem; margin-bottom: 1rem;">
              <div class="alert-callout-icon">&#9432;</div>
              <div class="alert-callout-content" style="font-size: 0.8rem;">
                Candidate clarification submissions remain unverified until approved by an authorized human reviewer.
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">Clarifying Statement & Production Context</label>
              <textarea class="form-textarea" id="input-clarification-text" rows="4" placeholder="Explain where this requirement was satisfied, clarify technical acronyms (e.g., K8s vs Kubernetes), or describe specific project architecture..."></textarea>
              <span class="form-hint">Provide factual, verifiable context. Vague claims will be rejected by the reviewer.</span>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary btn-sm" id="btn-cancel-clarification">Cancel</button>
            <button class="btn btn-primary btn-sm" id="btn-submit-clarification">Submit Clarification &rarr;</button>
          </div>
        </div>
      </div>

    </div>
  `;

  // Attach Event Handlers
  document.getElementById('select-active-candidate')?.addEventListener('change', (e) => {
    state.setSelectedApplicant(e.target.value);
    renderCandidate(container);
  });

  // Upload simulation
  const dropZone = document.getElementById('resume-drop-zone');
  const fileInput = document.getElementById('file-input-resume');

  document.getElementById('btn-browse-file')?.addEventListener('click', () => fileInput?.click());

  fileInput?.addEventListener('change', async (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      window.showToast?.(`Uploading ${file.name} to page-preserving parser...`, 'info');
      const res = await api.uploadDocument(file);
      window.showToast?.(`Uploaded ${file.name}. SHA-256: ${res.file_hash}`, 'success');
    }
  });

  // Modal Open/Close
  let activeEvidenceId = null;
  const modal = document.getElementById('modal-clarification');

  container.querySelectorAll('.btn-clarify-criterion').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const criterionName = btn.getAttribute('data-criterion');
      activeEvidenceId = btn.getAttribute('data-evidence-id');
      document.getElementById('modal-criterion-name').innerText = criterionName;
      document.getElementById('input-clarification-text').value = 
        criterionName === 'Kubernetes' 
          ? "In my role at CloudScale Systems, 'K8s' is our standard abbreviation for Kubernetes. I managed a 14-node production Kubernetes cluster on AWS EKS with Helm and Ingress-NGINX."
          : "";
      modal.classList.add('active');
    });
  });

  const closeModal = () => modal.classList.remove('active');
  document.getElementById('btn-close-clarification')?.addEventListener('click', closeModal);
  document.getElementById('btn-cancel-clarification')?.addEventListener('click', closeModal);

  document.getElementById('btn-submit-clarification')?.addEventListener('click', async () => {
    const text = document.getElementById('input-clarification-text').value.trim();
    if (!text) {
      window.showToast?.('Please write a clarifying statement.', 'error');
      return;
    }
    closeModal();
    window.showToast?.('Submitting candidate clarification...', 'info');
    await api.submitClarification(activeEvidenceId || 'ce-003', text);
    window.showToast?.('Clarification submitted! Sent to Human Reviewer desk for verification.', 'success');
    renderCandidate(container);
  });
}
