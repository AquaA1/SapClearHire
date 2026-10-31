/**
 * ClearHire Phase 1 API Playground & Backend Connection Settings View
 */

import { state } from '../state.js';
import { api } from '../api.js';

export function renderSettings(container) {
  let lastResponse = null;
  let activeEndpoint = '/health/ready';

  async function updateView() {
    container.innerHTML = `
      <div class="animate-fade-in">
        <!-- Section Header -->
        <div class="view-header">
          <div class="view-title-group">
            <h1>
              <span>Phase 1 API Playground & Connection</span>
              <span class="badge badge-audit">Developer & Tester Hub</span>
            </h1>
            <p class="view-subtitle">Inspect live backend endpoint contracts, test API endpoints with active JWT persona roles, and configure connection parameters.</p>
          </div>
          <div class="view-actions">
            <span class="status-indicator">
              <span class="status-dot ${state.backendStatus}"></span>
              <span>Backend Status: <strong>${state.backendStatus.toUpperCase()}</strong></span>
            </span>
          </div>
        </div>

        <div class="view-grid-2" style="margin-bottom: 2rem;">
          <!-- Configuration Card -->
          <div class="glass-panel" style="padding: 1.5rem;">
            <h3 style="margin-bottom: 1rem; font-size: 1.1rem;">Backend Configuration</h3>
            
            <div class="form-group">
              <label class="form-label">FastAPI Base URL</label>
              <input type="text" class="form-input" id="input-api-url" value="${state.apiBaseUrl}" />
              <span class="form-hint">Default development backend runs on port 8000 (e.g., http://localhost:8000/api/v1)</span>
            </div>

            <div style="margin-bottom: 1.25rem;">
              <button class="btn btn-primary btn-sm" id="btn-save-api-url">Save URL & Probe Connection</button>
            </div>

            <div style="padding: 1rem; background: var(--bg-secondary); border-radius: var(--radius-md); font-size: 0.82rem;">
              <strong style="color: var(--text-main); display: block; margin-bottom: 0.4rem;">Backend Phase 1 Quickstart Instructions:</strong>
              <code style="color: #60a5fa; display: block; margin-bottom: 0.25rem;">cd backend</code>
              <code style="color: #60a5fa; display: block; margin-bottom: 0.25rem;">source .venv/bin/activate</code>
              <code style="color: #60a5fa; display: block; margin-bottom: 0.5rem;">uvicorn app.main:app --reload --port 8000</code>
              <span style="color: var(--text-subtle);">Interactive OpenAPI Docs: <a href="http://localhost:8000/docs" target="_blank">http://localhost:8000/docs</a></span>
            </div>
          </div>

          <!-- Active JWT Identity Inspector -->
          <div class="glass-panel" style="padding: 1.5rem;">
            <h3 style="margin-bottom: 1rem; font-size: 1.1rem;">Active JWT Identity Payload</h3>
            
            <div style="background: var(--bg-secondary); border-radius: var(--radius-md); padding: 1.25rem; font-family: var(--font-mono); font-size: 0.82rem; color: #a78bfa; margin-bottom: 1rem;">
              {<br/>
              &nbsp;&nbsp;"sub": "${state.currentRole.id}",<br/>
              &nbsp;&nbsp;"email": "${state.currentRole.email}",<br/>
              &nbsp;&nbsp;"role": "${state.currentRole.role}",<br/>
              &nbsp;&nbsp;"iss": "clearhire-auth",<br/>
              &nbsp;&nbsp;"iat": ${Math.floor(Date.now() / 1000)},<br/>
              &nbsp;&nbsp;"exp": ${Math.floor(Date.now() / 1000) + 3600}<br/>
              }
            </div>

            <p style="font-size: 0.82rem; color: var(--text-subtle);">
              Role-based authorization is enforced on all endpoints via <code>require_roles</code>. Switching personas updates the token payload instantaneously.
            </p>
          </div>
        </div>

        <!-- Interactive Endpoint Tester & JSON Response Viewer -->
        <div class="glass-panel" style="padding: 1.75rem;">
          <h3 style="margin-bottom: 0.5rem;">Interactive Endpoint Tester</h3>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1.25rem;">
            Select an endpoint to ping live backend or test fallback responses:
          </p>

          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.25rem;">
            <button class="btn btn-outline btn-sm btn-endpoint" data-ep="/health/ready">GET /health/ready</button>
            <button class="btn btn-outline btn-sm btn-endpoint" data-ep="/health">GET /health</button>
            <button class="btn btn-outline btn-sm btn-endpoint" data-ep="/jobs">GET /jobs</button>
            <button class="btn btn-outline btn-sm btn-endpoint" data-ep="/reviews">GET /reviews</button>
            <button class="btn btn-outline btn-sm btn-endpoint" data-ep="/audit/verify">GET /audit/verify</button>
            <button class="btn btn-outline btn-sm btn-endpoint" data-ep="/benchmark/run">GET /benchmark/run</button>
          </div>

          <!-- Raw Response Box -->
          <div style="background: var(--bg-primary); border: 1px solid var(--border-medium); border-radius: var(--radius-md); padding: 1.25rem; font-family: var(--font-mono); font-size: 0.82rem; max-height: 380px; overflow-y: auto; color: #34d399;">
            <pre id="json-response-output">${lastResponse ? JSON.stringify(lastResponse, null, 2) : '// Click an endpoint above to execute request and inspect response payload'}</pre>
          </div>
        </div>

      </div>
    `;

    // Event Handlers
    document.getElementById('btn-save-api-url')?.addEventListener('click', async () => {
      const url = document.getElementById('input-api-url').value.trim();
      state.apiBaseUrl = url;
      window.showToast?.(`Testing connectivity to ${url}...`, 'info');
      const health = await api.checkHealth();
      window.showToast?.(
        health.ready ? 'Connected to live backend successfully!' : 'Backend unreachable. Running in Phase 1 simulation mode.',
        health.ready ? 'success' : 'warning'
      );
      updateView();
    });

    container.querySelectorAll('.btn-endpoint').forEach(btn => {
      btn.addEventListener('click', async () => {
        const ep = btn.getAttribute('data-ep');
        activeEndpoint = ep;
        const out = document.getElementById('json-response-output');
        if (out) out.innerText = `// Executing GET ${state.apiBaseUrl}${ep}...`;

        let data = null;
        if (ep === '/health/ready' || ep === '/health') {
          const res = await api.checkHealth();
          data = res;
        } else if (ep === '/audit/verify') {
          data = await api.verifyAuditChain();
        } else if (ep === '/benchmark/run') {
          data = await api.runBenchmark();
        } else if (ep === '/jobs') {
          data = state.jobs;
        } else if (ep === '/reviews') {
          data = state.reviewFlags;
        } else {
          data = await api.request(ep);
        }

        lastResponse = data;
        if (out) out.innerText = JSON.stringify(data, null, 2);
      });
    });
  }

  updateView();
}
