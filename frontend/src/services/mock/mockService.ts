import {
  MOCK_USERS,
  MOCK_JOBS,
  MOCK_APPLICATIONS,
  MOCK_EVALUATION,
  MOCK_REVIEW_FLAGS,
  MOCK_REVIEW_CASE_DETAIL,
  MOCK_CANDIDATE_SKILLS,
  MOCK_AUDIT_VERIFICATION,
  MOCK_AUDIT_EVENTS,
  MOCK_BENCHMARK_REPORT,
} from './fixtures/mockData';
import {
  User,
  Job,
  Application,
  Evaluation,
  ReviewCaseDetail,
  ReviewFlagSummary,
  AuditEvent,
  AuditVerificationReport,
  BenchmarkReport,
  CandidateSkill,
} from '../../contracts/models';
import {
  UserRole,
  ReviewDecisionType,
  VerificationState,
  ReviewFlagStatus,
  ApplicationStatus,
  CorrectionRequestStatus,
  JobStatus,
  CriterionCategory,
} from '../../contracts/enums';

// Helper for simulated latency
const delay = (ms = 180) => new Promise((resolve) => setTimeout(resolve, ms));

class MockStorage {
  private users: Record<string, User> = { ...MOCK_USERS };
  private jobs: Job[] = [...MOCK_JOBS];
  private applications: Application[] = [...MOCK_APPLICATIONS];
  private evaluation: Evaluation = { ...MOCK_EVALUATION };
  private reviewFlags: ReviewFlagSummary[] = [...MOCK_REVIEW_FLAGS];
  private reviewCaseDetail: ReviewCaseDetail = { ...MOCK_REVIEW_CASE_DETAIL };
  private auditEvents: AuditEvent[] = [...MOCK_AUDIT_EVENTS];
  private activeRole: UserRole = UserRole.EMPLOYER_ADMIN;

  getActiveUser(): User {
    const user = Object.values(this.users).find((u) => u.role === this.activeRole);
    return user || this.users.candidate;
  }

  setActiveRole(role: UserRole): User {
    this.activeRole = role;
    return this.getActiveUser();
  }

  // --- Auth ---
  async login(email: string): Promise<{ token: string; user: User }> {
    await delay();
    let user = Object.values(this.users).find((u) => u.email.toLowerCase() === email.toLowerCase());
    if (!user) {
      user = this.users.candidate;
    }
    this.activeRole = user.role;
    return { token: `mock-jwt-token-for-${user.id}`, user };
  }

  async getMe(): Promise<User> {
    await delay(50);
    return this.getActiveUser();
  }

  // --- Jobs ---
  async listJobs(statusFilter?: JobStatus): Promise<Job[]> {
    await delay();
    if (this.activeRole === UserRole.CANDIDATE) {
      return this.jobs.filter((j) => j.status === JobStatus.ACTIVE);
    }
    if (statusFilter) {
      return this.jobs.filter((j) => j.status === statusFilter);
    }
    return [...this.jobs];
  }

  async getJob(id: string): Promise<Job | null> {
    await delay();
    return this.jobs.find((j) => j.id === id) || null;
  }

  async createJob(data: {
    title: string;
    description: string;
    department: string;
    criteria: Array<{ name: string; description: string; category: CriterionCategory; weight: number }>;
  }): Promise<Job> {
    await delay();
    const newJob: Job = {
      id: `j-${Date.now()}`,
      employer_id: this.getActiveUser().id,
      title: data.title,
      description: data.description,
      department: data.department,
      status: JobStatus.ACTIVE,
      applicants_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      criteria: data.criteria.map((c, i) => ({
        id: `crit-new-${Date.now()}-${i}`,
        job_id: `j-${Date.now()}`,
        version: 1,
        name: c.name,
        description: c.description,
        category: c.category,
        weight: c.weight,
        is_active: true,
        created_at: new Date().toISOString(),
      })),
    };
    this.jobs.unshift(newJob);

    // Append audit event
    this.appendAuditEvent('JOB_CREATED', 'job', newJob.id, { title: newJob.title });
    return newJob;
  }

  // --- Applications ---
  async listApplications(jobId?: string): Promise<Application[]> {
    await delay();
    if (this.activeRole === UserRole.CANDIDATE) {
      return this.applications.filter((a) => a.candidate_id === this.getActiveUser().id);
    }
    if (jobId) {
      return this.applications.filter((a) => a.job_id === jobId);
    }
    return [...this.applications];
  }

  async getApplication(id: string): Promise<Application | null> {
    await delay();
    return this.applications.find((a) => a.id === id) || null;
  }

  async submitApplication(jobId: string, fileName = 'resume.pdf'): Promise<Application> {
    await delay(350);
    const user = this.getActiveUser();
    const job = this.jobs.find((j) => j.id === jobId) || this.jobs[0];
    const newApp: Application = {
      id: `app-${Date.now()}`,
      job_id: jobId,
      candidate_id: user.id,
      primary_document_id: `doc-${Date.now()}`,
      status: ApplicationStatus.NEEDS_REVIEW,
      submitted_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      job_title: job.title,
      candidate_name: user.full_name,
      candidate_email: user.email,
      department: job.department || 'Engineering',
    };
    this.applications.unshift(newApp);

    this.appendAuditEvent('APPLICATION_SUBMITTED', 'application', newApp.id, {
      job_title: job.title,
      file_name: fileName,
    });
    return newApp;
  }

  // --- Evaluations ---
  async getEvaluation(applicationId: string): Promise<Evaluation> {
    await delay();
    return {
      ...this.evaluation,
      application_id: applicationId,
    };
  }

  async evaluateApplication(applicationId: string): Promise<Evaluation> {
    await delay(400);
    const app = this.applications.find((a) => a.id === applicationId);
    if (app) {
      app.status = ApplicationStatus.SCREENING;
    }
    this.appendAuditEvent('EVALUATION_EXECUTED', 'evaluation', this.evaluation.id, {
      application_id: applicationId,
    });
    return { ...this.evaluation, application_id: applicationId };
  }

  // --- Review Cases ---
  async listReviewCases(statusFilter?: ReviewFlagStatus): Promise<ReviewFlagSummary[]> {
    await delay();
    if (statusFilter) {
      return this.reviewFlags.filter((f) => f.status === statusFilter);
    }
    return [...this.reviewFlags];
  }

  async getReviewCase(id: string): Promise<ReviewCaseDetail> {
    await delay();
    return { ...this.reviewCaseDetail, flag_id: id };
  }

  async recordReviewDecision(
    flagId: string,
    decision: ReviewDecisionType,
    mandatoryRationale: string
  ): Promise<ReviewCaseDetail> {
    await delay(300);
    const user = this.getActiveUser();
    const newState =
      decision === ReviewDecisionType.ACCEPTED
        ? VerificationState.HUMAN_VERIFIED
        : decision === ReviewDecisionType.REJECTED
        ? VerificationState.HUMAN_REJECTED
        : VerificationState.UNVERIFIED;

    const newFlagStatus =
      decision === ReviewDecisionType.REQUESTED_CLARIFICATION
        ? ReviewFlagStatus.UNDER_REVIEW
        : ReviewFlagStatus.RESOLVED;

    this.reviewCaseDetail.verification_state = newState;
    this.reviewCaseDetail.flag_status = newFlagStatus;
    this.reviewCaseDetail.resolved_at =
      newFlagStatus === ReviewFlagStatus.RESOLVED ? new Date().toISOString() : null;

    this.reviewCaseDetail.decisions.unshift({
      id: `dec-${Date.now()}`,
      reviewer_id: user.id,
      reviewer_name: user.full_name,
      decision,
      mandatory_rationale: mandatoryRationale,
      previous_verification_state: 'unverified',
      new_verification_state: newState,
      created_at: new Date().toISOString(),
    });

    // Update in summary list
    const summary = this.reviewFlags.find((f) => f.id === flagId);
    if (summary) {
      summary.status = newFlagStatus;
      summary.verification_state = newState;
    }

    this.appendAuditEvent('REVIEW_DECISION_RECORDED', 'review_decision', flagId, {
      decision,
      rationale: mandatoryRationale,
      new_state: newState,
    });

    return { ...this.reviewCaseDetail };
  }

  async submitClarification(statement: string): Promise<ReviewCaseDetail> {
    await delay(300);
    this.reviewCaseDetail.verification_state = VerificationState.CANDIDATE_CLARIFIED;
    this.reviewCaseDetail.flag_status = ReviewFlagStatus.PENDING;

    this.reviewCaseDetail.clarifications.unshift({
      id: `clar-${Date.now()}`,
      candidate_statement: statement,
      additional_document_id: null,
      status: CorrectionRequestStatus.SUBMITTED,
      created_at: new Date().toISOString(),
    });

    // Update summary
    const summary = this.reviewFlags.find((f) => f.id === this.reviewCaseDetail.flag_id);
    if (summary) {
      summary.verification_state = VerificationState.CANDIDATE_CLARIFIED;
      summary.status = ReviewFlagStatus.PENDING;
    }

    this.appendAuditEvent('CANDIDATE_CLARIFICATION_SUBMITTED', 'correction_request', `clar-${Date.now()}`, {
      statement,
    });

    return { ...this.reviewCaseDetail };
  }

  async createReviewFlags(applicationId: string): Promise<ReviewFlagSummary[]> {
    await delay(250);
    const app = this.applications.find((a) => a.id === applicationId);
    if (app) {
      app.status = ApplicationStatus.NEEDS_REVIEW;
    }
    this.appendAuditEvent('REVIEW_FLAGS_AUTO_GENERATED', 'review_flag', `batch-${Date.now()}`, {
      application_id: applicationId,
    });
    return this.reviewFlags;
  }

  // --- Profiles ---
  async getCandidateSkills(): Promise<CandidateSkill[]> {
    await delay();
    return [...MOCK_CANDIDATE_SKILLS];
  }

  // --- Audit ---
  async getAuditVerification(): Promise<AuditVerificationReport> {
    await delay(200);
    return {
      ...MOCK_AUDIT_VERIFICATION,
      total_events: this.auditEvents.length,
      verified_events: this.auditEvents.length,
    };
  }

  async listAuditEvents(resourceType?: string): Promise<AuditEvent[]> {
    await delay();
    if (resourceType) {
      return this.auditEvents.filter((e) => e.resource_type === resourceType);
    }
    return [...this.auditEvents];
  }

  // --- Benchmark ---
  async runBenchmark(): Promise<BenchmarkReport> {
    await delay(450);
    return { ...MOCK_BENCHMARK_REPORT };
  }

  private appendAuditEvent(action: string, resourceType: string, resourceId: string, details: Record<string, any>) {
    const user = this.getActiveUser();
    const prev = this.auditEvents[0];
    const prevHash = prev ? prev.event_hash : '0000000000000000000000000000000000000000000000000000000000000000';
    // Deterministic synthetic SHA256 simulation
    const eventHash = Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join('');

    const event: AuditEvent = {
      id: `aud-${Date.now()}`,
      sequence_number: this.auditEvents.length + 1,
      timestamp: new Date().toISOString(),
      actor_id: user.id,
      actor_role: user.role,
      action,
      resource_type: resourceType,
      resource_id: resourceId,
      entity_version: 1,
      prior_state: null,
      new_state: details,
      details,
      ip_address: '127.0.0.1',
      previous_hash: prevHash,
      event_hash: eventHash,
      is_verified: true,
    };
    this.auditEvents.unshift(event);
  }
}

export const mockService = new MockStorage();
