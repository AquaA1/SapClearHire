# ClearHire — Hiring Evidence Transparency Platform

> **SAP Hackfest 2026** | **SAP HANA Cloud Integrated Edition** (`sap-hana-database` branch)

ClearHire ensures that verifiable candidate evidence is never silently missed during hiring screening. ClearHire maps candidate evidence to explicit, versioned job criteria with cryptographic provenance, human reviewer justifications, and candidate clarification workflows.

ClearHire **never makes automated hiring decisions** and **never guarantees outcome reversals**. It empowers human decision-makers with transparent, source-grounded evidence backed by enterprise cloud databases.

---

## 1. System Architecture

```
                               ┌───────────────────────────────────────────────────┐
                               │       ClearHire Frontend (React 18 + Vite)        │
                               │   Candidate Console | Employer Requisition Studio │
                               │     Reviewer Adjudication | Auditor Audit Log     │
                               └─────────────────────────┬─────────────────────────┘
                                                         │ HTTP / WebSocket (:3000)
                                                         ▼
                               ┌───────────────────────────────────────────────────┐
                               │           ClearHire Backend (FastAPI)             │
                               │   Auth & RBAC | Claim Extraction | Grounding Engine│
                               │   Audit Hash Chain | Interview Dialogue Coaching  │
                               └───────────┬───────────────────────────┬───────────┘
                                           │                           │
                   SQLAlchemy 2.0 Async    │                           │  Async / Local
                   (hana+aiohdbcli driver) │                           │  Background Queue
                                           ▼                           ▼
                         ┌───────────────────────────┐     ┌───────────────────────┐
                         │      SAP HANA Cloud       │     │ Local / S3 Document   │
                         │   Instance: Hackfest-DB   │     │ Storage Engine        │
                         │    Schema: HACKFEST0328   │     │ (PDFs & Transcripts)  │
                         │    17 Relational Tables   │     └───────────────────────┘
                         └───────────────────────────┘
```

### Tech Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.x Async, Pydantic v2, Alembic
- **Database Backend**: **SAP HANA Cloud** via official `hdbcli` (v2.30) and `sqlalchemy-hana` (v5.0) with native async support (`hana+aiohdbcli`)
- **Database Fallback**: SQLite (`sqlite+aiosqlite`) for offline/standalone development
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons
- **Security**: Argon2id password hashing, JWT RBAC, cryptographic SHA-256 audit chaining

---

## 2. SAP HANA Cloud Integration Highlights

On this branch (`sap-hana-database`), ClearHire is fully integrated with **SAP HANA Cloud**:

1. **High-Performance Asynchronous Driver**: Runtime FastAPI requests communicate with SAP HANA Cloud using the `hana+aiohdbcli` dialect over TLS v1.3 (`port 443`).
2. **Enterprise Schema Isolation**: Tenant schema `HACKFEST0328` encapsulates all 17 platform tables:
   - `USERS`, `JOBS`, `JOB_CRITERIA`, `APPLICATIONS`
   - `DOCUMENTS`, `EXTRACTION_RUNS`, `CANDIDATE_SKILLS`, `EVIDENCE_ITEMS`
   - `EVALUATIONS`, `CRITERION_EVIDENCE`, `REVIEW_FLAGS`, `CORRECTION_REQUESTS`, `REVIEW_DECISIONS`
   - `AUDIT_EVENTS` (tamper-evident hash chain)
   - `INTERVIEW_TRANSCRIPTS`, `TRANSCRIPT_QA_ITEMS`
   - `ALEMBIC_VERSION` (at head revision `0008`)
3. **Dialect-Aware Resiliency**:
   - Automatic detection of SAP HANA's index constraints (preventing redundant column indexing).
   - Universal health readiness probe using `SELECT 1 FROM DUMMY`.
   - Native mapping of `UUID`, `BOOLEAN`, `TIMESTAMP`, and `JSON` (via `NCLOB`).
4. **Seamless Dual-Database Switching**: Switch between SAP HANA Cloud and local SQLite via a single environment variable: `DATABASE_BACKEND=hana` vs `DATABASE_BACKEND=sqlite`.

---

## 3. Quick Start Guide

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- Access to SAP HANA Cloud instance (or offline SQLite)

### Step 1: Clone & Checkout Branch
```bash
git clone https://github.com/AquaA1/SapClearHire.git
cd SapClearHire
git checkout sap-hana-database
```

### Step 2: Configure Environment
```bash
cd backend
cp .env.example .env
```
Edit `backend/.env` with your SAP HANA Cloud credentials:
```env
DATABASE_BACKEND=hana
HANA_HOST=64e8c26b-3e07-47e9-b246-617058b0306e.hna3.prod-eu10.hanacloud.ondemand.com
HANA_PORT=443
HANA_USER=Hackfest0328
HANA_PASSWORD=YourPasswordHere
HANA_SCHEMA=HACKFEST0328
HANA_ENCRYPT=true
HANA_SSL_VALIDATE_CERTIFICATE=true
```

### Step 3: Install Backend Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

### Step 4: Verify Connectivity & Apply Migrations
```bash
# 1. Run read-only TLS connection check:
python scripts/test_hana_connection.py

# 2. Apply all Alembic migrations to SAP HANA Cloud:
alembic upgrade head

# 3. Seed demo accounts & sample job requisitions:
python -m app.db.seed

# 4. Verify end-to-end ORM workflows:
python scripts/verify_hana_workflows.py
```

### Step 5: Start Backend Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Probe: [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready)

### Step 6: Start Frontend Server
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 4. Demo Login Credentials (Seeded)

| Role | Email | Password | Primary Capabilities |
| :--- | :--- | :--- | :--- |
| **Candidate** | `alex.morgan@test.com` | `ValidPassword123!` | View screening evidence, upload documents, contest ratings with clarifications |
| **Employer** | `employer.admin@clearhire.dev` | `AdminPassword123!` | Create requisitions, review evidence breakdown, inspect candidate ledger |
| **Reviewer** | `senior.reviewer@clearhire.dev` | `ReviewerPass123!` | Review ambiguous claims with mandatory justifications in Decision Studio |
| **Auditor** | `auditor@clearhire.dev` | `AuditorPass123!` | Verify cryptographic audit trail, SHA-256 chain integrity, inspect tenant dossiers |

---

## 5. Switching Between SAP HANA Cloud and SQLite

- **To run on SAP HANA Cloud**:
  ```env
  DATABASE_BACKEND=hana
  ```
- **To switch to SQLite (local offline development)**:
  ```env
  DATABASE_BACKEND=sqlite
  DATABASE_URL=sqlite+aiosqlite:///./clearhire.db
  ```
Restarting the backend immediately connects to the selected database engine.

---

## 6. Testing & Quality Assurance

```bash
cd backend
source venv/bin/activate
pytest tests/
```
All **210 unit and integration tests** pass (100% pass rate) with zero regressions across core domain entities, authorization, grounding checks, and transcript coaching.
