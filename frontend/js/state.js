/**
 * ClearHire Reactive State Management & Event Bus
 */

import { MOCK_ROLES, MOCK_APPLICANTS, MOCK_JOBS, MOCK_REVIEW_FLAGS, MOCK_AUDIT_CHAIN } from './data/mockData.js';

class AppState {
  constructor() {
    this.currentRoleKey = 'REVIEWER';
    this.currentRole = MOCK_ROLES.REVIEWER;
    this.activeTab = 'dashboard';
    
    // API Configuration
    this.apiBaseUrl = 'http://localhost:8000/api/v1';
    this.backendStatus = 'checking'; // 'live', 'offline', 'checking'
    this.useMockFallback = true;
    
    // Domain State
    this.jobs = [...MOCK_JOBS];
    this.selectedJob = this.jobs[0];
    
    this.applicants = [...MOCK_APPLICANTS];
    this.selectedApplicant = this.applicants[0];
    
    this.reviewFlags = [...MOCK_REVIEW_FLAGS];
    this.selectedReviewFlag = this.reviewFlags[0];
    
    this.auditChain = [...MOCK_AUDIT_CHAIN];

    // Event Listeners Map
    this.listeners = new Map();
  }

  // Event bus
  subscribe(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
    return () => {
      const list = this.listeners.get(event) || [];
      this.listeners.set(event, list.filter(cb => cb !== callback));
    };
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(cb => {
        try { cb(data); } catch (err) { console.error(`Error in event listener for ${event}:`, err); }
      });
    }
  }

  // Persona actions
  setRole(roleKey) {
    if (MOCK_ROLES[roleKey]) {
      this.currentRoleKey = roleKey;
      this.currentRole = MOCK_ROLES[roleKey];
      this.emit('roleChanged', this.currentRole);
    }
  }

  // Tab navigation
  setActiveTab(tabName) {
    this.activeTab = tabName;
    this.emit('tabChanged', tabName);
  }

  // Applicant selection
  setSelectedApplicant(applicantId) {
    const found = this.applicants.find(a => a.id === applicantId);
    if (found) {
      this.selectedApplicant = found;
      this.emit('applicantChanged', found);
    }
  }

  // Record reviewer decision
  recordDecision(flagId, decision, rationale) {
    const flag = this.reviewFlags.find(f => f.id === flagId);
    if (flag) {
      flag.status = 'resolved';
      flag.verification_state = decision === 'accepted' ? 'human_verified' : 'human_rejected';
      flag.decision = decision;
      flag.mandatory_rationale = rationale;
      flag.resolved_by = this.currentRole.name;
      flag.resolved_at = new Date().toISOString();

      // Also append to audit chain
      const nextSeq = this.auditChain.length + 1;
      const prevHash = this.auditChain[this.auditChain.length - 1].event_hash;
      const newEvent = {
        id: `audit-${String(nextSeq).padStart(3, '0')}`,
        sequence_number: nextSeq,
        timestamp: new Date().toISOString(),
        actor_id: this.currentRole.id,
        actor_role: this.currentRole.role,
        action: `record_reviewer_decision_${decision}`,
        resource_type: 'review_decision',
        resource_id: flagId,
        entity_version: 1,
        previous_hash: prevHash,
        event_hash: Array.from({length: 64}, () => Math.floor(Math.random()*16).toString(16)).join(''),
        is_verified: true,
        details: {
          decision,
          rationale,
          candidate: flag.candidate_name,
          criterion: flag.criterion_name
        }
      };
      this.auditChain.push(newEvent);

      this.emit('reviewFlagUpdated', flag);
      this.emit('auditChainUpdated', this.auditChain);
    }
  }

  // Submit candidate clarification
  submitClarification(flagId, statement) {
    const flag = this.reviewFlags.find(f => f.id === flagId);
    if (flag) {
      flag.candidate_statement = statement;
      flag.verification_state = 'candidate_clarified';
      flag.status = 'under_review';

      // Update in applicant evaluation as well
      if (this.selectedApplicant && this.selectedApplicant.evaluation) {
        const item = this.selectedApplicant.evaluation.criteria_evidence.find(
          ce => ce.job_criterion_name.toLowerCase() === flag.criterion_name.toLowerCase()
        );
        if (item) {
          item.verification_state = 'candidate_clarified';
        }
      }

      // Add to audit chain
      const nextSeq = this.auditChain.length + 1;
      const prevHash = this.auditChain[this.auditChain.length - 1].event_hash;
      const newEvent = {
        id: `audit-${String(nextSeq).padStart(3, '0')}`,
        sequence_number: nextSeq,
        timestamp: new Date().toISOString(),
        actor_id: this.currentRole.id,
        actor_role: this.currentRole.role,
        action: 'submit_candidate_clarification',
        resource_type: 'correction_request',
        resource_id: flagId,
        entity_version: 1,
        previous_hash: prevHash,
        event_hash: Array.from({length: 64}, () => Math.floor(Math.random()*16).toString(16)).join(''),
        is_verified: true,
        details: {
          flag_id: flagId,
          statement_length: statement.length,
          candidate: this.currentRole.name
        }
      };
      this.auditChain.push(newEvent);

      this.emit('clarificationSubmitted', flag);
      this.emit('auditChainUpdated', this.auditChain);
    }
  }

  // Add new job requisition
  addJobRequisition(jobData) {
    const newJob = {
      id: `j${Date.now()}`,
      title: jobData.title,
      department: jobData.department,
      external_requisition_id: jobData.external_requisition_id || `REQ-${Math.floor(Math.random()*9000)+1000}`,
      status: 'active',
      description: jobData.description,
      created_at: new Date().toISOString(),
      criteria: jobData.criteria || []
    };
    this.jobs.unshift(newJob);
    this.selectedJob = newJob;
    this.emit('jobsUpdated', this.jobs);
  }
}

export const state = new AppState();
