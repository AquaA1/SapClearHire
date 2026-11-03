# ClearHire Backend — SAP HANA Cloud Integration

ClearHire is an evidence transparency platform designed to prevent relevant candidate evidence from being silently missed during hiring screening. This backend is built on **FastAPI**, **SQLAlchemy 2.x**, and integrates directly with **SAP HANA Cloud** via `hdbcli` and `sqlalchemy-hana`.

---

## 1. Architecture & Multi-Database Support

The ClearHire backend provides a modular enterprise architecture supporting multiple database engines via configuration:
- **SAP HANA Cloud**: Enterprise-grade in-memory database with schema isolation (`HACKFEST0328`), SSL/TLS encryption, and connection pooling.
- **SQLite (aiosqlite)**: Zero-configuration local development and rapid integration testing.
- **PostgreSQL (asyncpg)**: Traditional relational deployment option.

```
backend/
├── app/
│   ├── main.py                     # FastAPI application factory, lifespan, & CORS
│   ├── core/
│   │   ├── config.py               # Pydantic Settings supporting HANA/SQLite/Postgres
│   │   ├── logging.py              # Structured logging
│   │   ├── security.py             # JWT token handling & RBAC role checks
│   │   └── exceptions.py           # Domain exception handlers
│   ├── api/v1/endpoints/           # REST endpoints
│   │   ├── auth.py                 # Multi-role authentication & JWT issuance
│   │   ├── candidates.py           # Candidate profile, dossier, and evidence view
│   │   ├── criteria.py             # Job criteria definition & rubrics
│   │   ├── documents.py            # PDF upload, OCR, and page text extraction
│   │   ├── evaluations.py          # Grounded scoring & evidence mapping
│   │   ├── reviews.py              # Human reviewer workflows & decisions
│   │   ├── coaching.py             # Transcript analysis & coaching feedback
│   │   ├── audit.py                # Cryptographic SHA-256 audit log inspection
│   │   └── health.py               # Live & database readiness health probes
│   ├── db/
│   │   ├── session.py              # Multi-engine DB factory (HANA, SQLite, PostgreSQL)
│   │   ├── base.py                 # DeclarativeBase with explicit constraint naming
│   │   └── models/                 # SQLAlchemy ORM models (Audit, User, Job, Evaluation, etc.)
│   ├── integrations/
│   │   └── llm/                    # Provider-neutral LLM grounding & claims extraction
│   └── utils/
│       ├── text.py                 # Verifiable excerpt text grounding validator
│       └── document.py             # PDF parser & magic-byte validator
├── alembic/                        # Async database migrations (HANA & SQLite compatible)
├── scripts/                        # Database initialization, seeding, and verification
│   ├── init_hana_schema.py         # Dedicated HANA schema creator & smoke-tester
│   ├── seed_all_workflows.py       # Comprehensive end-to-end multi-role data seeder
│   └── verify_hana_workflows.py    # Automated verification of all HANA tables & foreign keys
├── tests/                          # Automated test suite (210 passing tests)
└── pyproject.toml                  # Dependencies including hdbcli & sqlalchemy-hana
```

---

## 2. SAP HANA Cloud Setup & Configuration

### Prerequisites
- Python 3.12+
- SAP HANA Cloud instance credentials
- Direct cloud connectivity on port `443`

### Environment Configuration
Copy `.env.example` to `.env` in the `backend/` directory:
```bash
cp .env.example .env
```

Configure the SAP HANA Cloud variables:
```env
DATABASE_BACKEND=hana
HANA_HOST=64e8c26b-3e07-47e9-b246-617058b0306e.hna3.prod-eu10.hanacloud.ondemand.com
HANA_PORT=443
HANA_USER=Hackfest0328
HANA_PASSWORD=<your_hana_password>
HANA_SCHEMA=HACKFEST0328
HANA_ENCRYPT=true
HANA_SSL_VALIDATE_CERTIFICATE=true
HANA_POOL_SIZE=10
HANA_MAX_OVERFLOW=15
HANA_POOL_RECYCLE=300
HANA_POOL_TIMEOUT=15
```

---

## 3. Installation & Database Initialization

### Step 1: Install Dependencies
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

### Step 2: Initialize SAP HANA Cloud Schema & Tables
Run the automated schema initializer:
```bash
python scripts/init_hana_schema.py
```
Or run Alembic migrations:
```bash
alembic upgrade head
```

### Step 3: Seed Demonstration Workflows
Seed full candidate screening data, evaluation rubrics, documents, review decisions, and audit events:
```bash
python scripts/seed_all_workflows.py
```

### Step 4: Verify Schema & Workflows
Verify that all tables exist, contain seeded records, and validate relational foreign key integrity:
```bash
python scripts/verify_hana_workflows.py
```

---

## 4. Running the Backend Server

Start the FastAPI application with Uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative Documentation (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health & Readiness Probe**: [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready)

---

## 5. Running Automated Tests

Run the full pytest suite:
```bash
pytest tests/
```
All **210 tests** validate:
- Authentication & JWT RBAC security
- Candidate dossiers & evidence scoring
- Reviewer workflows & mandatory justification requirements
- Audit trail integrity & cryptographic chain hashing
- Text grounding validators (preventing hallucinated quotations)
- Health check endpoints across database engines

---

## 6. Switching to Local SQLite Development

To run locally without an external internet connection or cloud database:
1. In `backend/.env`, set:
   ```env
   DATABASE_BACKEND=sqlite
   DATABASE_URL=sqlite+aiosqlite:///./clearhire.db
   ```
2. Run migrations:
   ```bash
   alembic upgrade head
   ```
3. Restart the backend server.
