# ClearHire Backend (Main Branch)

The ClearHire backend is a modular asynchronous service built on **Python 3.12**, **FastAPI**, and **SQLAlchemy 2.x**. It powers evidence transparency, document extraction, reviewer decisioning, and cryptographic audit tracking.

---

## 1. Architecture Overview

```
backend/
├── app/
│   ├── main.py                     # FastAPI application factory, CORS, and lifespan
│   ├── core/
│   │   ├── config.py               # Pydantic Settings (SQLite / PostgreSQL)
│   │   ├── logging.py              # Structured logging
│   │   ├── security.py             # Argon2id password hashing & JWT verification
│   │   └── exceptions.py           # Domain exception handlers & envelopes
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
│   │   ├── session.py              # Async SQLAlchemy engine & session factory
│   │   ├── base.py                 # DeclarativeBase with explicit constraint naming
│   │   └── models/                 # SQLAlchemy ORM models (Audit, User, Job, Evaluation, etc.)
│   ├── integrations/
│   │   └── llm/                    # Provider-neutral LLM grounding & claims extraction
│   └── utils/
│       ├── text.py                 # Verifiable excerpt text grounding validator
│       └── document.py             # PDF parser & magic-byte validator
├── alembic/                        # Async database migrations
├── scripts/                        # Database seeding & verification tools
│   ├── seed_all_workflows.py       # Comprehensive end-to-end multi-role data seeder
│   └── verify_all_workflows.py     # Live verification script
├── tests/                          # Automated test suite (210 passing tests)
└── pyproject.toml                  # Python package specifications
```

---

## 2. Database Engines & Configuration

The backend supports multiple database backends configured via `DATABASE_URL` in `.env`:

### Option A: SQLite (Default Local Development)
Requires zero configuration and zero external software:
```env
DATABASE_URL=sqlite+aiosqlite:///./clearhire.db
```

### Option B: PostgreSQL
For containerized or cloud deployments:
```env
DATABASE_URL=postgresql+asyncpg://clearhire_user:clearhire_secure_dev_password@localhost:5432/clearhire_db
```

---

## 3. Local Development Setup

### Step 1: Virtual Environment
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

### Step 2: Environment Variables
```bash
cp .env.example .env
```

### Step 3: Database Migrations
```bash
alembic upgrade head
```

### Step 4: Seed Data
```bash
python scripts/seed_all_workflows.py
```

### Step 5: Run the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Readiness Probe**: [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready)

---

## 4. Testing & Code Quality

Run tests:
```bash
pytest tests/
```
All **210 tests** pass (100% pass rate).

Run linter:
```bash
ruff check .
```

---

## 5. Enterprise Branches

For the SAP HANA Cloud database integration, see the `sap-hana-database` branch:
```bash
git checkout sap-hana-database
```
