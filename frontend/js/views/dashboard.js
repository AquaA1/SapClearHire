/**
 * ClearHire Dashboard & Command Center View
 */

import { state } from '../state.js';
import { api } from '../api.js';

export function renderDashboard(container) {
  const pendingFlags = state.reviewFlags.filter(f => f.status === 'pending').length;
  const totalAuditEvents = state.auditChain.length;
  const totalJobs = state.jobs.length;

  container.innerHTML = `
    <div class="animate-fade-in">
      <!-- Section Header -->
      <div class="view-header">
        <div class="view-title-group">
          <h1>
            <span>Command Center & System Overview</span>
            <span class="brand-tag">SAP Hackfest 2026</span>
          </h1>
          <p class="view-subtitle">Verifiable candidate evidence transparency platform with human-in-the-loop oversight and cryptographic integrity.</p>
        </div>
        <div class="view-actions">
          <button class="btn btn-secondary btn-sm" id="btn-refresh-health">
            <span id="health-spin" style="display:none;" class="spinner"></span>
            Test Backend Health
          </button>
          <button class="btn btn-primary btn-sm" id="btn-quick-benchmark">
            Run Screening Benchmark &rarr;
          </button>
        </div>
      </div>

      <!-- Core Transparency Principle Callout -->
      <div class="alert-callout info">
        <div class="alert-callout-icon">&#9878;&#65039;</div>
        <div class="alert-callout-content">
          <strong>Fundamental Architecture Guarantee:</strong> ClearHire never makes automated hiring decisions and never generates opaque fit scores. Instead, it extracts verbatim, page-referenced evidence claims from candidate documents and maps them to versioned criteria. Final evaluations remain strictly in the hands of authorized human reviewers.
        </div>
      </div>

      <!-- Quick KPI Stats Grid -->
      <div class="view-grid-4" style="margin-bottom: 2rem;">
        <div class="glass-panel stat-card">
          <div class="stat-label">
            <span>Backend Readiness</span>
            <span class="status-dot ${state.backendStatus}"></span>
          </div>
          <div class="stat-value" id="dash-backend-status">${state.backendStatus.toUpperCase()}</div>
          <div class="stat-desc">FastAPI + Async PostgreSQL Probe</div>
        </div>

        <div class="glass-panel stat-card">
          <div class="stat-label">
            <span>Pending Review Cases</span>
            <span class="badge badge-ambiguous">${pendingFlags} Actionable</span>
          </div>
          <div class="stat-value">${pendingFlags}</div>
          <div class="stat-desc">Ambiguous or disputed criteria flags</div>
        </div>

        <div class="glass-panel stat-card">
          <div class="stat-label">
            <span>Cryptographic Ledger</span>
            <span class="badge badge-audit">SHA-256 Chained</span>
          </div>
          <div class="stat-value">${totalAuditEvents}</div>
          <div class="stat-desc">Immutable append-only audit events</div>
        </div>

        <div class="glass-panel stat-card">
          <div class="stat-label">
            <span>Active Job Requisitions</span>
            <span class="badge badge-supported">Versioned</span>
          </div>
          <div class="stat-value">${totalJobs}</div>
          <div class="stat-desc">SAP SuccessFactors Synced</div>
        </div>
      </div>

      <!-- Interactive Persona Selector / Flow Guide -->
      <div class="glass-panel" style="padding: 1.75rem; margin-bottom: 2rem;">
        <h3 style="margin-bottom: 0.5rem;">Explore by User Persona</h3>
        <p style="margin-bottom: 1.5rem; font-size: 0.9rem;">
          Select a role below to simulate the exact workflows and permission boundaries enforced by the backend:
        </p>

        <div class="view-grid-4">
          <!-- Candidate Card -->
          <div class="glass-panel" style="padding: 1.25rem; background: var(--bg-surface); cursor: pointer;" id="card-persona-candidate">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
              <span class="persona-badge candidate">Candidate</span>
              <span style="font-size: 1.2rem;">&#128100;</span>
            </div>
            <h4 style="margin-bottom: 0.35rem;">Candidate Evidence Portal</h4>
            <p style="font-size: 0.8rem; margin-bottom: 1rem;">Upload resume PDF, inspect page-by-page extractions, view factual criteria status, and submit clarifications.</p>
            <span class="btn btn-outline btn-sm" style="width: 100%;">Switch to Candidate &rarr;</span>
          </div>

          <!-- Reviewer Card -->
          <div class="glass-panel" style="padding: 1.25rem; background: var(--bg-surface); cursor: pointer;" id="card-persona-reviewer">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
              <span class="persona-badge reviewer">Reviewer</span>
              <span style="font-size: 1.2rem;">&#128269;</span>
            </div>
            <h4 style="margin-bottom: 0.35rem;">Human Review Desk</h4>
            <p style="font-size: 0.8rem; margin-bottom: 1rem;">Inspect side-by-side resume quotes, review candidate clarifications, and record mandatory written rationales.</p>
            <span class="btn btn-outline btn-sm" style="width: 100%;">Switch to Reviewer &rarr;</span>
          </div>

          <!-- Employer Admin Card -->
          <div class="glass-panel" style="padding: 1.25rem; background: var(--bg-surface); cursor: pointer;" id="card-persona-employer">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
              <span class="persona-badge employer_admin">Employer Admin</span>
              <span style="font-size: 1.2rem;">&#128188;</span>
            </div>
            <h4 style="margin-bottom: 0.35rem;">Job & Criteria Studio</h4>
            <p style="font-size: 0.8rem; margin-bottom: 1rem;">Manage versioned criteria, trigger screening runs, and import simulated SAP SuccessFactors applicant feeds.</p>
            <span class="btn btn-outline btn-sm" style="width: 100%;">Switch to Admin &rarr;</span>
          </div>

          <!-- Auditor Card -->
          <div class="glass-panel" style="padding: 1.25rem; background: var(--bg-surface); cursor: pointer;" id="card-persona-auditor">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
              <span class="persona-badge system_auditor">System Auditor</span>
              <span style="font-size: 1.2rem;">&#128272;</span>
            </div>
            <h4 style="margin-bottom: 0.35rem;">Cryptographic Ledger</h4>
            <p style="font-size: 0.8rem; margin-bottom: 1rem;">Verify continuous SHA-256 hash chains, inspect tamper resistance, and audit compliance logs.</p>
            <span class="btn btn-outline btn-sm" style="width: 100%;">Switch to Auditor &rarr;</span>
          </div>
        </div>
      </div>

      <!-- Architecture Workflow Diagram -->
      <div class="glass-panel" style="padding: 1.75rem;">
        <h3 style="margin-bottom: 1.25rem;">ClearHire 5-Stage Evidence Lifecycle</h3>
        <div class="view-grid-3" style="gap: 1.5rem;">
          <div style="background: var(--bg-secondary); padding: 1.25rem; border-radius: var(--radius-md); border-left: 3px solid var(--accent-blue);">
            <div style="font-size: 0.75rem; text-transform: uppercase; color: var(--accent-blue); font-weight: 700; margin-bottom: 0.3rem;">Stage 1 & 2</div>
            <h4 style="margin-bottom: 0.5rem;">Page Extraction & Grounding</h4>
            <p style="font-size: 0.82rem;">PDF text is preserved page-by-page. LLM claims must pass strict substring validation against raw document text. Hallucinated quotes fail immediately.</p>
          </div>

          <div style="background: var(--bg-secondary); padding: 1.25rem; border-radius: var(--radius-md); border-left: 3px solid var(--status-ambiguous);">
            <div style="font-size: 0.75rem; text-transform: uppercase; color: var(--status-ambiguous); font-weight: 700; margin-bottom: 0.3rem;">Stage 3 & 4</div>
            <h4 style="margin-bottom: 0.5rem;">Criteria Mapping & Auto-Flag</h4>
            <p style="font-size: 0.82rem;">Claims map to explicit versioned criteria. Supported items are verified. Ambiguous items (synonyms, missing context) trigger human review flags.</p>
          </div>

          <div style="background: var(--bg-secondary); padding: 1.25rem; border-radius: var(--radius-md); border-left: 3px solid var(--status-audit);">
            <div style="font-size: 0.75rem; text-transform: uppercase; color: var(--status-audit); font-weight: 700; margin-bottom: 0.3rem;">Stage 5</div>
            <h4 style="margin-bottom: 0.5rem;">Human Review & Hash Chaining</h4>
            <p style="font-size: 0.82rem;">Authorized reviewers inspect exact quotes and record mandatory rationales. All transitions are cryptographically committed to the tamper-evident ledger.</p>
          </div>
        </div>
      </div>
    </div>
  `;

  // Attach event handlers
  document.getElementById('card-persona-candidate')?.addEventListener('click', () => {
    state.setRole('CANDIDATE');
    state.setActiveTab('candidate');
  });

  document.getElementById('card-persona-reviewer')?.addEventListener('click', () => {
    state.setRole('REVIEWER');
    state.setActiveTab('reviewer');
  });

  document.getElementById('card-persona-employer')?.addEventListener('click', () => {
    state.setRole('EMPLOYER_ADMIN');
    state.setActiveTab('employer');
  });

  document.getElementById('card-persona-auditor')?.addEventListener('click', () => {
    state.setRole('SYSTEM_AUDITOR');
    state.setActiveTab('audit');
  });

  document.getElementById('btn-quick-benchmark')?.addEventListener('click', () => {
    state.setActiveTab('benchmark');
  });

  document.getElementById('btn-refresh-health')?.addEventListener('click', async () => {
    const spin = document.getElementById('health-spin');
    if (spin) spin.style.display = 'inline-block';
    const res = await api.checkHealth();
    if (spin) spin.style.display = 'none';
    const el = document.getElementById('dash-backend-status');
    if (el) el.innerText = res.status.toUpperCase();
    window.showToast?.(
      res.status === 'live' 
        ? 'Backend is online and PostgreSQL database is connected!' 
        : 'Backend probe offline. Running in deterministic Phase 1 simulation mode.',
      res.status === 'live' ? 'success' : 'warning'
    );
  });
}
