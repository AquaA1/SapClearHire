/**
 * ClearHire Employer Admin & Job Studio View
 */

import { state } from '../state.js';
import { api } from '../api.js';

export function renderEmployer(container) {
  let showCreateModal = false;

  function updateView() {
    container.innerHTML = `
      <div class="animate-fade-in">
        <!-- Section Header -->
        <div class="view-header">
          <div class="view-title-group">
            <h1>
              <span>Job Requisition & Criteria Studio</span>
              <span class="persona-badge employer_admin">Employer Admin View</span>
            </h1>
            <p class="view-subtitle">Define versioned screening criteria, configure explicit requirement benchmarks, and sync candidate pipelines with SAP SuccessFactors.</p>
          </div>
          <div class="view-actions">
            <button class="btn btn-secondary btn-sm" id="btn-sync-sf">
              &#128257; Sync Simulated SuccessFactors Feed
            </button>
            <button class="btn btn-primary btn-sm" id="btn-open-create-job">
              + New Job Requisition
            </button>
          </div>
        </div>

        <!-- SuccessFactors Feed Summary Card -->
        <div class="glass-panel" style="padding: 1.5rem; margin-bottom: 2rem; border-left: 3px solid #06b6d4;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <div style="display: flex; align-items: center; gap: 0.6rem;">
              <span style="font-weight: 700; color: var(--text-main); font-size: 1.05rem;">SAP SuccessFactors Recruiting Simulation</span>
              <span class="brand-tag">OData Feed Stub</span>
            </div>
            <span class="badge badge-supported">Connected (Simulated Feed)</span>
          </div>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">
            ClearHire integrates seamlessly with SAP SuccessFactors Job Requisitions and Application feeds, ingesting applicant attachments and converting them to grounded evidence packages without modifying existing HR workflows.
          </p>
          <div style="display: flex; gap: 1.5rem; font-size: 0.82rem; font-family: var(--font-mono);">
            <span>Active Batch: <strong>SF-BATCH-2026-Q1</strong></span>
            <span>Feed Requisition: <strong>REQ-CLOUD-2026</strong></span>
            <span>Applicants in Pipeline: <strong>4 Processed</strong></span>
          </div>
        </div>

        <!-- Active Jobs Table -->
        <div class="glass-panel" style="padding: 1.75rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
            <h3>Active Job Requisitions & Versioned Criteria</h3>
            <span class="badge badge-neutral">${state.jobs.length} Active Positions</span>
          </div>

          <div class="data-table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Requisition Title</th>
                  <th>Department</th>
                  <th>Ext. Requisition ID</th>
                  <th>Versioned Criteria</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                ${state.jobs.map(j => `
                  <tr>
                    <td>
                      <div style="font-weight: 700; color: var(--text-main);">${j.title}</div>
                      <div style="font-size: 0.78rem; color: var(--text-subtle);">${j.description.substring(0, 60)}...</div>
                    </td>
                    <td>${j.department}</td>
                    <td><code style="color: var(--accent-blue);">${j.external_requisition_id}</code></td>
                    <td>
                      <div style="display: flex; gap: 0.35rem; flex-wrap: wrap;">
                        ${j.criteria.map(c => `
                          <span class="badge ${c.category === 'required' ? 'badge-notfound' : 'badge-neutral'}" style="font-size: 0.7rem;">
                            ${c.name} (v${c.version})
                          </span>
                        `).join('')}
                      </div>
                    </td>
                    <td><span class="badge badge-supported">${j.status}</span></td>
                    <td>
                      <button class="btn btn-outline btn-sm btn-view-job-criteria" data-job-id="${j.id}">
                        Inspect &rarr;
                      </button>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Create Job Modal -->
        <div class="modal-overlay ${showCreateModal ? 'active' : ''}" id="modal-create-job">
          <div class="modal-box" style="max-width: 720px;">
            <div class="modal-header">
              <h3>Create Job Requisition with Versioned Criteria</h3>
              <button class="btn btn-outline btn-sm" id="btn-close-create-job">&times;</button>
            </div>
            <div class="modal-body">
              <div class="view-grid-2">
                <div class="form-group">
                  <label class="form-label">Position Title *</label>
                  <input type="text" class="form-input" id="new-job-title" placeholder="e.g. Lead SRE Engineer" value="Senior SRE & Platform Architect" />
                </div>
                <div class="form-group">
                  <label class="form-label">Department *</label>
                  <input type="text" class="form-input" id="new-job-dept" placeholder="e.g. Infrastructure" value="Global Cloud Infrastructure" />
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">External Requisition ID</label>
                <input type="text" class="form-input" id="new-job-req-id" placeholder="REQ-SRE-2026" value="REQ-SRE-2026" />
              </div>

              <div class="form-group">
                <label class="form-label">Job Description</label>
                <textarea class="form-textarea" id="new-job-desc" rows="2" placeholder="Brief summary of duties...">High-availability cloud infrastructure management and multi-cluster Kubernetes reliability.</textarea>
              </div>

              <div style="border-top: 1px solid var(--border-subtle); padding-top: 1rem; margin-top: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                  <strong style="color: var(--text-main); font-size: 0.9rem;">Initial Screening Criteria (Version 1)</strong>
                  <span class="form-hint">Criteria are explicitly versioned for auditability</span>
                </div>

                <div id="criteria-input-list">
                  <div class="view-grid-3" style="margin-bottom: 0.5rem; gap: 0.5rem;">
                    <input type="text" class="form-input" placeholder="Criterion Name (e.g. Terraform)" value="Terraform" />
                    <select class="form-select">
                      <option value="required" selected>Required</option>
                      <option value="preferred">Preferred</option>
                    </select>
                    <input type="text" class="form-input" placeholder="Verifiable Benchmark" value="Production IaC provisioning" />
                  </div>
                  <div class="view-grid-3" style="margin-bottom: 0.5rem; gap: 0.5rem;">
                    <input type="text" class="form-input" placeholder="Criterion Name" value="Prometheus" />
                    <select class="form-select">
                      <option value="required" selected>Required</option>
                      <option value="preferred">Preferred</option>
                    </select>
                    <input type="text" class="form-input" placeholder="Verifiable Benchmark" value="Observability and alerting" />
                  </div>
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary btn-sm" id="btn-cancel-create-job">Cancel</button>
              <button class="btn btn-primary btn-sm" id="btn-save-new-job">Save Requisition &rarr;</button>
            </div>
          </div>
        </div>

      </div>
    `;

    // Event handlers
    document.getElementById('btn-open-create-job')?.addEventListener('click', () => {
      showCreateModal = true;
      updateView();
    });

    const closeModal = () => {
      showCreateModal = false;
      updateView();
    };

    document.getElementById('btn-close-create-job')?.addEventListener('click', closeModal);
    document.getElementById('btn-cancel-create-job')?.addEventListener('click', closeModal);

    document.getElementById('btn-save-new-job')?.addEventListener('click', () => {
      const title = document.getElementById('new-job-title').value.trim();
      const department = document.getElementById('new-job-dept').value.trim();
      const reqId = document.getElementById('new-job-req-id').value.trim();
      const desc = document.getElementById('new-job-desc').value.trim();

      if (!title || !department) {
        window.showToast?.('Please fill out position title and department.', 'error');
        return;
      }

      state.addJobRequisition({
        title,
        department,
        external_requisition_id: reqId,
        description: desc,
        criteria: [
          { id: `c-${Date.now()}-1`, name: "Terraform", category: "required", weight: 1.0, version: 1, description: "Production IaC" },
          { id: `c-${Date.now()}-2`, name: "Prometheus", category: "required", weight: 1.0, version: 1, description: "Observability" }
        ]
      });

      closeModal();
      window.showToast?.(`Job Requisition '${title}' created with versioned criteria!`, 'success');
    });

    document.getElementById('btn-sync-sf')?.addEventListener('click', async () => {
      window.showToast?.('Syncing simulated SAP SuccessFactors applicant feed...', 'info');
      const feed = await api.getSuccessFactorsFeed();
      window.showToast?.(`Synchronized batch ${feed.batch_id} (${feed.applicant_count} applicants ingested).`, 'success');
    });
  }

  updateView();
}
