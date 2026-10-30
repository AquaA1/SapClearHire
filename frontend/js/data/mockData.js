/**
 * ClearHire Mock Data & Fixtures
 * Matches backend domain models and SAP Hackfest 2026 fixtures 1:1.
 */

export const MOCK_ROLES = {
  CANDIDATE: {
    id: "a1111111-1111-4111-8111-111111111111",
    role: "candidate",
    email: "marcus.vance@example.com",
    name: "Marcus Vance",
    badgeClass: "candidate",
    label: "Candidate (Marcus Vance)"
  },
  REVIEWER: {
    id: "b2222222-2222-4222-8222-222222222222",
    role: "reviewer",
    email: "elena.rostova@enterprise.example.com",
    name: "Elena Rostova",
    badgeClass: "reviewer",
    label: "Reviewer (Elena Rostova)"
  },
  EMPLOYER_ADMIN: {
    id: "c3333333-3333-4333-8333-333333333333",
    role: "employer_admin",
    email: "admin@enterprise.example.com",
    name: "Enterprise Admin",
    badgeClass: "employer_admin",
    label: "Employer Admin (Enterprise HR)"
  },
  SYSTEM_AUDITOR: {
    id: "d4444444-4444-4444-8444-444444444444",
    role: "system_auditor",
    email: "auditor@compliance.sap.example.com",
    name: "SAP Compliance Auditor",
    badgeClass: "system_auditor",
    label: "System Auditor (Compliance)"
  }
};

export const MOCK_JOBS = [
  {
    id: "j1000000-0000-0000-0000-000000000001",
    title: "Senior Cloud Backend Engineer",
    department: "Enterprise Cloud Architecture",
    external_requisition_id: "REQ-CLOUD-2026",
    status: "active",
    description: "Lead the design and high-scale implementation of cloud services supporting SAP BTP and enterprise microservice architectures.",
    created_at: "2026-10-15T09:00:00Z",
    criteria: [
      {
        id: "c101",
        name: "Python",
        category: "required",
        weight: 1.0,
        version: 1,
        description: "Production experience building backend microservices in Python 3.10+ using FastAPI or AsyncIO"
      },
      {
        id: "c102",
        name: "PostgreSQL",
        category: "required",
        weight: 1.0,
        version: 1,
        description: "Relational database schema design, complex query optimization, and transaction isolation"
      },
      {
        id: "c103",
        name: "Kubernetes",
        category: "required",
        weight: 1.0,
        version: 1,
        description: "Container orchestration, Helm charts, ingress controllers, and production cluster deployment"
      },
      {
        id: "c104",
        name: "Docker",
        category: "preferred",
        weight: 0.8,
        version: 1,
        description: "Multi-stage container packaging, build optimization, and CI/CD pipeline integration"
      },
      {
        id: "c105",
        name: "React",
        category: "preferred",
        weight: 0.5,
        version: 1,
        description: "Frontend integration using modern component-driven React architecture"
      }
    ]
  },
  {
    id: "j1000000-0000-0000-0000-000000000002",
    title: "Staff Data Platform Architect",
    department: "Data Intelligence Group",
    external_requisition_id: "REQ-DATA-2026",
    status: "active",
    description: "Architect mission-critical data pipelines and high-throughput real-time streaming engines.",
    created_at: "2026-10-20T11:30:00Z",
    criteria: [
      { id: "c201", name: "Distributed Systems", category: "required", weight: 1.0, version: 1, description: "Hands-on experience architecting distributed consensus and partition-tolerant services" },
      { id: "c202", name: "Apache Kafka", category: "required", weight: 1.0, version: 1, description: "Stream processing, topic partitioning, and event-driven architecture" },
      { id: "c203", name: "Golang or Rust", category: "preferred", weight: 0.8, version: 1, description: "High performance systems programming" }
    ]
  }
];

export const MOCK_APPLICANTS = [
  {
    id: "a1111111-1111-4111-8111-111111111111",
    name: "Marcus Vance",
    email: "marcus.vance@example.com",
    role: "Senior Distributed Systems Engineer",
    resume_file: "marcus_vance_resume.pdf",
    page_count: 2,
    scenario: "Synonym-based Evidence (K8s & Postgres)",
    description: "Marcus mentions 'K8s cluster operator' and 'Postgres tuning' instead of exact keywords 'Kubernetes' and 'PostgreSQL'. Rigid ATS filters drop him; ClearHire grounds both.",
    skills: [
      { skill_name: "Python", category: "Language", confidence: 0.98, source_page: 1, source_excerpt: "Developed asynchronous Python microservices handling 25,000 req/sec." },
      { skill_name: "PostgreSQL (Postgres)", category: "Database", confidence: 0.94, source_page: 1, source_excerpt: "Architected high-throughput Postgres read-replicas with connection pooling." },
      { skill_name: "Kubernetes (K8s)", category: "Infrastructure", confidence: 0.91, source_page: 2, source_excerpt: "Deployed multi-tenant K8s operators and customized Helm charts in AWS EKS." },
      { skill_name: "Docker", category: "DevOps", confidence: 0.99, source_page: 2, source_excerpt: "Packaged multi-stage Docker images reducing production container size by 65%." }
    ],
    evaluation: {
      id: "eval-001",
      overall_status: "ambiguous",
      summary_notes: "4 criteria verified directly or via grounded synonyms. 1 criterion flagged for reviewer confirmation of synonym mapping.",
      metrics: {
        total_criteria: 5,
        supported_count: 3,
        ambiguous_count: 1,
        not_found_count: 1
      },
      criteria_evidence: [
        {
          id: "ce-001",
          job_criterion_name: "Python",
          job_criterion_category: "required",
          ai_status: "supported",
          ai_confidence: 0.98,
          ai_reasoning: "Explicitly demonstrated 6+ years building asynchronous Python backend services.",
          verification_state: "human_verified",
          source_page: 1,
          source_excerpt: "Developed asynchronous Python microservices handling 25,000 req/sec with FastAPI."
        },
        {
          id: "ce-002",
          job_criterion_name: "PostgreSQL",
          job_criterion_category: "required",
          ai_status: "supported",
          ai_confidence: 0.94,
          ai_reasoning: "Demonstrated production Postgres database schema optimization and indexing.",
          verification_state: "human_verified",
          source_page: 1,
          source_excerpt: "Architected high-throughput Postgres read-replicas with connection pooling and custom partition tables."
        },
        {
          id: "ce-003",
          job_criterion_name: "Kubernetes",
          job_criterion_category: "required",
          ai_status: "ambiguous",
          ai_confidence: 0.88,
          ai_reasoning: "Candidate explicitly uses industry-standard abbreviation 'K8s' instead of exact term 'Kubernetes'. Semantic match verified, flagged for human reviewer sign-off.",
          verification_state: "candidate_clarified",
          source_page: 2,
          source_excerpt: "Maintained 14-node production K8s cluster on AWS EKS; authored Custom Resource Definitions (CRDs)."
        },
        {
          id: "ce-004",
          job_criterion_name: "Docker",
          job_criterion_category: "preferred",
          ai_status: "supported",
          ai_confidence: 0.99,
          ai_reasoning: "Extensive multi-stage Docker packaging and CI/CD pipelines.",
          verification_state: "human_verified",
          source_page: 2,
          source_excerpt: "Authored multi-stage Dockerfiles optimizing base Alpine image security."
        },
        {
          id: "ce-005",
          job_criterion_name: "React",
          job_criterion_category: "preferred",
          ai_status: "not_found",
          ai_confidence: 0.95,
          ai_reasoning: "No verbatim frontend React experience found in candidate's backend-focused document.",
          verification_state: "unverified",
          source_page: null,
          source_excerpt: null
        }
      ]
    }
  },
  {
    id: "a2222222-2222-4222-8222-222222222222",
    name: "Elena Chen",
    email: "elena.chen@example.com",
    role: "Lead Cloud Architect",
    resume_file: "elena_chen_resume.pdf",
    page_count: 3,
    scenario: "Skills Demonstrated via Architecture Projects",
    description: "Elena shows skills embedded within end-to-end cloud platform achievements rather than standalone keyword lists.",
    skills: [
      { skill_name: "Python", category: "Language", confidence: 0.99, source_page: 1, source_excerpt: "Engineered core Python orchestration daemon for automated cluster scaling." },
      { skill_name: "Kubernetes", category: "Infrastructure", confidence: 0.97, source_page: 2, source_excerpt: "Architected enterprise Kubernetes control plane migration across 3 AWS regions." },
      { skill_name: "PostgreSQL", category: "Database", confidence: 0.95, source_page: 2, source_excerpt: "Managed zero-downtime PostgreSQL 14 to 16 major version upgrade for 12TB database." },
      { skill_name: "Docker", category: "DevOps", confidence: 0.96, source_page: 3, source_excerpt: "Standardized container builds across 45 microservices using buildx." },
      { skill_name: "React", category: "Frontend", confidence: 0.85, source_page: 3, source_excerpt: "Constructed operational monitoring dashboards in React and TypeScript." }
    ],
    evaluation: {
      id: "eval-002",
      overall_status: "supported",
      summary_notes: "All 5 criteria strongly supported with verbatim quotes in project narratives.",
      metrics: {
        total_criteria: 5,
        supported_count: 5,
        ambiguous_count: 0,
        not_found_count: 0
      },
      criteria_evidence: [
        {
          id: "ce-101",
          job_criterion_name: "Python",
          job_criterion_category: "required",
          ai_status: "supported",
          ai_confidence: 0.99,
          ai_reasoning: "Architected Python orchestration engine handling 10M events daily.",
          verification_state: "human_verified",
          source_page: 1,
          source_excerpt: "Engineered core Python orchestration daemon for automated cluster scaling with asyncio."
        },
        {
          id: "ce-102",
          job_criterion_name: "PostgreSQL",
          job_criterion_category: "required",
          ai_status: "supported",
          ai_confidence: 0.95,
          ai_reasoning: "Proven 12TB zero-downtime migration.",
          verification_state: "human_verified",
          source_page: 2,
          source_excerpt: "Managed zero-downtime PostgreSQL 14 to 16 major version upgrade for 12TB database."
        },
        {
          id: "ce-103",
          job_criterion_name: "Kubernetes",
          job_criterion_category: "required",
          ai_status: "supported",
          ai_confidence: 0.97,
          ai_reasoning: "Enterprise multi-region Kubernetes control plane architecture.",
          verification_state: "human_verified",
          source_page: 2,
          source_excerpt: "Architected enterprise Kubernetes control plane migration across 3 AWS regions."
        },
        {
          id: "ce-104",
          job_criterion_name: "Docker",
          job_criterion_category: "preferred",
          ai_status: "supported",
          ai_confidence: 0.96,
          ai_reasoning: "Standardized multi-stage CI pipeline for 45 services.",
          verification_state: "human_verified",
          source_page: 3,
          source_excerpt: "Standardized container builds across 45 microservices using buildx."
        },
        {
          id: "ce-105",
          job_criterion_name: "React",
          job_criterion_category: "preferred",
          ai_status: "supported",
          ai_confidence: 0.85,
          ai_reasoning: "Operational dashboard engineering in React.",
          verification_state: "human_verified",
          source_page: 3,
          source_excerpt: "Constructed operational monitoring dashboards in React and TypeScript."
        }
      ]
    }
  },
  {
    id: "a3333333-3333-4333-8333-333333333333",
    name: "Jordan Reed",
    email: "jordan.reed@example.com",
    role: "Junior Associate Developer",
    resume_file: "jordan_reed_resume.pdf",
    page_count: 1,
    scenario: "Keyword Stuffing / Unsubstantiated Claims",
    description: "Jordan lists buzzwords in a skills footer ('Python, Kubernetes, Postgres, React') without demonstrable job or project experience. ClearHire marks evidence as ambiguous/unsubstantiated.",
    skills: [
      { skill_name: "Python", category: "Language", confidence: 0.65, source_page: 1, source_excerpt: "Skills list: Python, Django, Flask, Java" },
      { skill_name: "Kubernetes", category: "Infrastructure", confidence: 0.45, source_page: 1, source_excerpt: "Familiar with: Kubernetes, AWS, Docker" }
    ],
    evaluation: {
      id: "eval-003",
      overall_status: "ambiguous",
      summary_notes: "Buzzwords detected in skill summary but lacking source grounding in responsibilities or project bodies.",
      metrics: {
        total_criteria: 5,
        supported_count: 1,
        ambiguous_count: 2,
        not_found_count: 2
      },
      criteria_evidence: [
        {
          id: "ce-201",
          job_criterion_name: "Python",
          job_criterion_category: "required",
          ai_status: "ambiguous",
          ai_confidence: 0.62,
          ai_reasoning: "Listed in isolated skill list; no production backend duties cite Python usage.",
          verification_state: "unverified",
          source_page: 1,
          source_excerpt: "Technical Proficiencies: Python, Django, Flask"
        },
        {
          id: "ce-202",
          job_criterion_name: "Kubernetes",
          job_criterion_category: "required",
          ai_status: "ambiguous",
          ai_confidence: 0.45,
          ai_reasoning: "Only listed under 'Familiar with'; zero production cluster experience described.",
          verification_state: "human_rejected",
          source_page: 1,
          source_excerpt: "Tools: Kubernetes, Docker, Linux"
        }
      ]
    }
  }
];

export const MOCK_REVIEW_FLAGS = [
  {
    id: "flag-001",
    application_id: "app-marcus-001",
    candidate_name: "Marcus Vance",
    job_title: "Senior Cloud Backend Engineer",
    criterion_name: "Kubernetes",
    flag_type: "ambiguous_evidence",
    priority: "high",
    status: "pending",
    ai_status: "ambiguous",
    verification_state: "candidate_clarified",
    reason: "Candidate uses acronym 'K8s' in resume. Requires reviewer confirmation that candidate demonstrated Kubernetes production expertise.",
    source_page: 2,
    source_excerpt: "Maintained 14-node production K8s cluster on AWS EKS; authored Custom Resource Definitions (CRDs).",
    candidate_statement: "In my previous role at CloudScale Systems, 'K8s' is our internal standard term for Kubernetes. I maintained 14 production Kubernetes nodes on AWS EKS, configured Ingress-NGINX controllers, and wrote Helm charts for 20+ microservices.",
    created_at: "2026-10-28T14:22:10Z"
  },
  {
    id: "flag-002",
    application_id: "app-jordan-002",
    candidate_name: "Jordan Reed",
    job_title: "Senior Cloud Backend Engineer",
    criterion_name: "Python",
    flag_type: "unsubstantiated_claim",
    priority: "normal",
    status: "under_review",
    ai_status: "ambiguous",
    verification_state: "unverified",
    reason: "Skill listed without descriptive project or work experience context.",
    source_page: 1,
    source_excerpt: "Technical Proficiencies: Python, Django, Flask",
    candidate_statement: null,
    created_at: "2026-10-29T10:15:00Z"
  }
];

export const MOCK_AUDIT_CHAIN = [
  {
    id: "audit-001",
    sequence_number: 1,
    timestamp: "2026-10-28T14:20:00Z",
    actor_id: "system",
    actor_role: "system",
    action: "create_job_requisition",
    resource_type: "job",
    resource_id: "j1000000-0000-0000-0000-000000000001",
    entity_version: 1,
    previous_hash: "0000000000000000000000000000000000000000000000000000000000000000",
    event_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    is_verified: true,
    details: { title: "Senior Cloud Backend Engineer", criteria_count: 5 }
  },
  {
    id: "audit-002",
    sequence_number: 2,
    timestamp: "2026-10-28T14:21:05Z",
    actor_id: "a1111111-1111-4111-8111-111111111111",
    actor_role: "candidate",
    action: "submit_application",
    resource_type: "application",
    resource_id: "app-marcus-001",
    entity_version: 1,
    previous_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    event_hash: "5d41402abc4b2a76b9719d911017c592b02008f8702b854e4ff682669389f46b",
    is_verified: true,
    details: { candidate: "Marcus Vance", document_hash: "sha256-a9f82bc7190d" }
  },
  {
    id: "audit-003",
    sequence_number: 3,
    timestamp: "2026-10-28T14:22:10Z",
    actor_id: "ai_evaluation_engine",
    actor_role: "system",
    action: "evaluate_evidence",
    resource_type: "evaluation",
    resource_id: "eval-001",
    entity_version: 1,
    previous_hash: "5d41402abc4b2a76b9719d911017c592b02008f8702b854e4ff682669389f46b",
    event_hash: "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca7",
    is_verified: true,
    details: { supported: 3, ambiguous: 1, not_found: 1 }
  },
  {
    id: "audit-004",
    sequence_number: 4,
    timestamp: "2026-10-28T15:05:42Z",
    actor_id: "a1111111-1111-4111-8111-111111111111",
    actor_role: "candidate",
    action: "submit_clarification",
    resource_type: "correction_request",
    resource_id: "cr-001",
    entity_version: 1,
    previous_hash: "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca7",
    event_hash: "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    is_verified: true,
    details: { criterion: "Kubernetes", candidate_notes: "K8s abbreviation clarification provided" }
  }
];

export const MOCK_BENCHMARK_REPORT = {
  benchmark_timestamp: "2026-10-30T22:30:00Z",
  dataset: "Labelled Ground-Truth Synthetic Talent Screening Cohort (n=120)",
  metrics: {
    false_rejections_prevented: 42,
    recall_improvement_percent: 38.5,
    synonym_detection_accuracy: 96.2,
    grounding_hallucination_rate: 0.0,
    human_oversight_turnaround_hrs: 1.4
  },
  methodology_comparison: [
    {
      feature: "Synonym Recognition (e.g. K8s $\\to$ Kubernetes)",
      traditional: "Fails (Exact string match required)",
      clearhire: "Passes with verifiable page grounding"
    },
    {
      feature: "Project-Narrative Evidence",
      traditional: "Silently ignored (Not in standalone skill list)",
      clearhire: "Extracted and mapped with exact page number"
    },
    {
      feature: "Keyword Stuffing / Buzzword Spam",
      traditional: "False Positive (High fit score)",
      clearhire: "Flagged as Ambiguous / Unsubstantiated"
    },
    {
      feature: "Decision Authority",
      traditional: "Opaque algorithmic black box rejection",
      clearhire: "Transparent human review with mandatory rationale"
    },
    {
      feature: "Auditability & Legal Compliance",
      traditional: "Non-reproducible / ephemeral logs",
      clearhire: "Cryptographically chained SHA-256 ledger"
    }
  ]
};
