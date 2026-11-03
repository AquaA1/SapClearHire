# ClearHire — Hiring Evidence Transparency Platform

Built for **SAP Hackfest 2026**, ClearHire prevents relevant candidate evidence from being silently missed during hiring screening. ClearHire maps verifiable candidate evidence to explicit, versioned job criteria with provenance, human reviewer rationales, and candidate clarification workflows.

ClearHire **never makes hiring decisions** and **never guarantees outcome reversals**. It empowers human decision-makers with transparent, source-grounded evidence.

---

## 1. System Architecture

ClearHire is composed of a modern full-stack architecture designed for enterprise reliability and zero-configuration local development:

```
SapClearHire/
├── backend/                        # FastAPI asynchronous backend
│   ├── app/                        # Application factory, endpoints, and domain models
│   ├── alembic/                    # Database migrations
│   ├── scripts/                    # Workflow seeders & verification tools
│   ├── tests/                      # Automated test suite (210 passing tests)
│   ├── pyproject.toml              # Dependencies & build configuration
│   └── .env.example                # Local environment template
├── frontend/                       # Vite + React 18 enterprise web console
│   ├── src/
│   │   ├── pages/                  # Candidate, Employer, Reviewer, and Auditor consoles
│   │   ├── components/             # Reusable UI widgets, badges, cards, navigation
│   │   ├── context/                # Authentication, theme, and toast state
│   │   └── services/               # API client connectors
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

### Core Technologies
- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.0 (Async), Pydantic v2, Alembic
- **Database**: SQLite with `aiosqlite` (Default local development with zero external dependencies) or PostgreSQL
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons, Manrope typography
- **Document Processing**: PyPDF page-level extraction, bounding-box provenance, grounded quote verification
- **Security & Audit**: Argon2id password hashing, JWT RBAC, append-only cryptographic SHA-256 audit trail

---

## 2. Quickstart Guide (Local Development)

### Prerequisites
- Python 3.12+ (`python3 --version`)
- Node.js 18+ & npm (`node --version`)

---

### Step 1: Set Up Backend

```bash
cd backend

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -e ".[dev]"

# Configure environment (Defaults to zero-config SQLite)
cp .env.example .env

# Run database migrations
alembic upgrade head

# Seed initial demonstration data
python scripts/seed_all_workflows.py

# Start backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative Documentation (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Readiness Check**: [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready)

---

### Step 2: Set Up Frontend

In a separate terminal:

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 3. Demo Login Credentials (Pre-seeded)

| Role | Email | Password | Primary Capabilities |
| :--- | :--- | :--- | :--- |
| **Candidate** | `alex.morgan@test.com` | `ValidPassword123!` | View screening evidence, review criterion ratings, submit clarifications |
| **Employer** | `employer.admin@clearhire.dev` | `AdminPassword123!` | Create requisitions, review evidence breakdown, inspect candidate ledger |
| **Reviewer** | `senior.reviewer@clearhire.dev` | `ReviewerPass123!` | Review ambiguous claims with mandatory justifications in Decision Studio |
| **Auditor** | `auditor@clearhire.dev` | `AuditorPass123!` | Verify cryptographic audit trail, SHA-256 chain integrity, inspect tenant dossiers |

---

## 4. Key Platform Features

1. **Candidate Transparency Dossier**:
   Candidates inspect exactly which lines and pages of their resumes were matched against required and preferred criteria.
2. **Clarification Submission & Contestation**:
   Allows candidates to submit verifiable documentation and contextual clarifications when relevant qualifications were missed.
3. **Decision Studio with Mandatory Justifications**:
   Human reviewers can accept or modify AI claim suggestions, but must provide recorded, auditable justifications for any rating override.
4. **Append-Only Cryptographic Audit Trail**:
   Every score generation, upload, reviewer decision, and status transition is recorded in an immutable audit ledger with SHA-256 hash chaining.
5. **Interview Transcript Coaching**:
   Analyzes interview transcripts against evidence rubrics and generates constructive coaching recommendations without black-box rejections.
6. **Accessible High-Readability Typography**:
   Built with scalable Manrope typography and high-contrast status badges to ensure accessibility across desktop and mobile displays.

---

## 5. Automated Testing & Quality Assurance

Run the test suite from the `backend/` directory:

```bash
cd backend
source venv/bin/activate
pytest tests/
```

- **Total Tests**: 210 unit and integration tests.
- **Pass Rate**: 100%.
- **Coverage**: Grounding verification, claim extraction, JWT authorization, tamper-evident audit trails, and PDF extraction.

---

## 6. Enterprise Branches

- **`main`**: Zero-configuration baseline supporting local SQLite development and standard PostgreSQL.
- **`sap-hana-database`**: Enterprise branch featuring native **SAP HANA Cloud** database integration via `hdbcli` and `sqlalchemy-hana`, custom schema partitioning (`HACKFEST0328`), and cloud health telemetry.
