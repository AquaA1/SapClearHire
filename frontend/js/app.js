/**
 * ClearHire Main Application Entry Point & Router
 */

import { state } from './state.js';
import { api } from './api.js';
import { renderDashboard } from './views/dashboard.js';
import { renderCandidate } from './views/candidate.js';
import { renderReviewer } from './views/reviewer.js';
import { renderEmployer } from './views/employer.js';
import { renderBenchmark } from './views/benchmark.js';
import { renderAudit } from './views/audit.js';
import { renderSettings } from './views/settings.js';

// Global Toast Notification Helper
window.showToast = function(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  let icon = '&#9432;';
  if (type === 'success') icon = '&#9989;';
  if (type === 'error') icon = '&#9888;&#65039;';
  if (type === 'warning') icon = '&#9888;&#65039;';

  toast.innerHTML = `
    <span style="font-size: 1.1rem; flex-shrink: 0;">${icon}</span>
    <span style="flex: 1;">${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4200);
};

// Main App Initialization
class Application {
  constructor() {
    this.mainContentEl = document.getElementById('main-content');
    this.personaSelectEl = document.getElementById('header-persona-select');
    this.statusDotEl = document.getElementById('header-status-dot');
    this.statusTextEl = document.getElementById('header-status-text');
  }

  init() {
    this.bindNavigation();
    this.bindPersonaSwitcher();
    this.subscribeToState();
    this.route(state.activeTab);

    // Initial silent health check
    api.checkHealth().then(res => {
      this.updateStatusDisplay();
    });
  }

  bindNavigation() {
    document.querySelectorAll('.nav-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = btn.getAttribute('data-tab');
        if (tab) {
          state.setActiveTab(tab);
        }
      });
    });
  }

  bindPersonaSwitcher() {
    if (this.personaSelectEl) {
      this.personaSelectEl.value = state.currentRoleKey;
      this.personaSelectEl.addEventListener('change', (e) => {
        state.setRole(e.target.value);
        window.showToast(`Switched persona to ${state.currentRole.name}`, 'info');
      });
    }
  }

  subscribeToState() {
    state.subscribe('tabChanged', (tab) => {
      this.route(tab);
    });

    state.subscribe('roleChanged', (role) => {
      if (this.personaSelectEl) {
        this.personaSelectEl.value = state.currentRoleKey;
      }
      this.route(state.activeTab);
    });

    state.subscribe('reviewFlagUpdated', () => {
      this.updateTabBadges();
    });
  }

  updateTabBadges() {
    const pendingCount = state.reviewFlags.filter(f => f.status === 'pending').length;
    const badge = document.getElementById('badge-review-count');
    if (badge) {
      badge.innerText = pendingCount;
      if (pendingCount > 0) {
        badge.classList.add('highlight');
      } else {
        badge.classList.remove('highlight');
      }
    }
  }

  updateStatusDisplay() {
    if (!this.statusDotEl || !this.statusTextEl) return;
    this.statusDotEl.className = `status-dot ${state.backendStatus}`;
    if (state.backendStatus === 'live') {
      this.statusTextEl.innerText = 'FastAPI Connected';
    } else {
      this.statusTextEl.innerText = 'Phase 1 Offline Sim';
    }
  }

  route(tabName) {
    // Update active nav button
    document.querySelectorAll('.nav-tab-btn').forEach(btn => {
      if (btn.getAttribute('data-tab') === tabName) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Render corresponding view
    switch (tabName) {
      case 'dashboard':
        renderDashboard(this.mainContentEl);
        break;
      case 'candidate':
        renderCandidate(this.mainContentEl);
        break;
      case 'reviewer':
        renderReviewer(this.mainContentEl);
        break;
      case 'employer':
        renderEmployer(this.mainContentEl);
        break;
      case 'benchmark':
        renderBenchmark(this.mainContentEl);
        break;
      case 'audit':
        renderAudit(this.mainContentEl);
        break;
      case 'settings':
        renderSettings(this.mainContentEl);
        break;
      default:
        renderDashboard(this.mainContentEl);
    }

    this.updateTabBadges();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const app = new Application();
  app.init();
});
