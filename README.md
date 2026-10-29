# ClearHire — Hiring Evidence Transparency Platform (Backend)

Built for **SAP Hackfest 2026**, ClearHire prevents relevant candidate evidence from being silently missed during hiring screening. ClearHire maps verifiable candidate evidence to explicit, versioned job criteria with provenance, human reviewer rationales, and candidate clarification workflows.

ClearHire **never makes hiring decisions** and **never guarantees outcome reversals**. It empowers human decision-makers with transparent, source-grounded evidence.

---

## 1. Architecture Overview

ClearHire Backend follows a **modular monolith** design built on Python 3.12, FastAPI, PostgreSQL, and SQLAlchemy 2.x Async.

```
backend/
├── app/
│   ├── main.py                     # FastAPI application factory & lifespan
│   ├── core/
│   │   ├── config.py               # Pydantic-settings environment configuration
│   │   ├── logging.py              # Structured JSON / human-readable logging
│   │   ├── exceptions.py           # Domain exceptions & error response envelopes
│   │   └── security.py             # RBAC roles & JWT verification interface
│   ├── api/
│   │   ├── router.py               # Root router (/api)
│   │   └── v1/
│   │       ├── router.py           # Versioned router (/api/v1)
│   │       └── endpoints/
│   │           └── health.py       # Health, liveness, and database readiness endpoints
│   ├── db/
│   │   ├── base.py                 # DeclarativeBase with explicit constraint naming
│   │   ├── session.py              # Async SQLAlchemy engine & request session lifecycle
│   │   └── models/
│   │       ├── base.py             # UUID v4 and UTC timestamp mixins
│   │       └── audit.py            # Append-only AuditEvent persistence model
│   ├── schemas/
│   │   ├── common.py               # Standardized ErrorEnvelope & SuccessEnvelope
│   │   └── health.py               # System health and readiness schemas
│   ├── repositories/
│   │   ├── base.py                 # Generic async repository pattern
│   │   └── audit.py                # Append-only audit trail repository
│   ├── services/
│   │   └── health.py               # Liveness and PostgreSQL connectivity service
│   ├── workers/
│   │   ├── base.py                 # Background document processing job contracts
│   │   └── local.py                # In-memory asyncio background worker queue
│   ├── integrations/
│   │   ├── llm/
│   │   │   ├── base.py             # Provider-neutral LLM extraction interface
│   │   │   ├── fake.py             # Deterministic mock provider for tests/offline
│   │   │   └── schemas.py          # Structured claims & page-referenced source quotes
│   │   └── successfactors/
│   │       └── client.py           # Interface stub for SAP SuccessFactors Recruiting API
│   └── utils/
│       ├── document.py             # PDF page-preserving parser & magic-byte validation
│       └── text.py                 # Source excerpt grounding & hallucination checker
├── tests/
│   ├── conftest.py                 # Async test fixtures, test DB, and ASGI client
│   ├── unit/                       # Config, exceptions, LLM, grounding, worker tests
│   └── integration/                # Database sessions, health endpoints, DB failure tests
├── alembic/                        # Async database migrations
├── storage/                        # Document upload directory (local storage)
├── Dockerfile                      # Multi-stage production container
├── docker-compose.yml              # Local PostgreSQL 16 & API container definitions
├── pyproject.toml                  # Python package metadata, ruff & pytest configs
└── .env.example                    # Environment variable template
```

---

## 2. Key Architectural Guarantees

1. **Explicit DB Constraint Naming**: All primary keys, foreign keys, unique constraints, and indexes use consistent prefix patterns (`pk_`, `fk_`, `uq_`, `ix_`) to prevent migration drift across database engines.
2. **Strict Grounding Validation**: LLM extraction results must pass `validate_excerpt_in_text()` against the raw PDF text before becoming verified evidence. Hallucinated quotes are rejected.
3. **Non-Blocking Background Tasks**: Heavy document parsing and AI calls are offloaded to `BaseBackgroundWorker` and do not block the HTTP request/response cycle.
4. **Resilient Health Probes**:
   - `GET /api/v1/health/live`: Probes process health only (returns `200` independently of external dependencies).
   - `GET /api/v1/health/ready`: Performs `SELECT 1` on PostgreSQL. If unreachable, returns `503 Service Unavailable`.
5. **Secure Error Envelopes**: Production responses never expose internal stack traces, connection strings, or database credentials.

---

## 3. Local Development Setup

### Prerequisites
- Python 3.12 (`python3.12 --version`)
- PostgreSQL 15+ (or Docker Compose)

### Step 1: Create Virtual Environment & Install Dependencies
```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

### Step 2: Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### Step 3: Start PostgreSQL
**Option A: Using Docker Compose**
```bash
docker compose up -d db
```

**Option B: Using Local PostgreSQL**
Ensure PostgreSQL is running on port `5432` with the database `clearhire_db` and user `clearhire_user` matching your `.env` file.

### Step 4: Run Database Migrations
```bash
alembic upgrade head
```

### Step 5: Start Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative API Documentation: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- OpenAPI Specification: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 4. Verification & Testing

### Run Automated Tests
```bash
pytest -v
```

### Run Linter & Formatter Checks
```bash
# Lint checks
ruff check .

# Format checks
ruff format --check .

# Auto-format
ruff format .
```

---

## 5. API Endpoints (Foundation)

| Method | Endpoint | Description | Expected Status |
|---|---|---|---|
| `GET` | `/api/v1/health` | Application status, service name, version, and server timestamp | `200 OK` |
| `GET` | `/api/v1/health/live` | Process liveness probe for orchestrators (Kubernetes/container) | `200 OK` |
| `GET` | `/api/v1/health/ready` | Dependency readiness probe (tests PostgreSQL `SELECT 1`) | `200 OK` or `503 Service Unavailable` |

---

## 6. Phase 1 Implementation Status & Known Limitations

### Implemented & Verified
- [x] FastAPI modular application structure and lifespan manager.
- [x] Async SQLAlchemy 2.x engine, connection pooling, and request session lifecycle (`get_db_session`).
- [x] MetaData constraint naming conventions and async Alembic migrations.
- [x] Immutable `audit_events` model, migration `0001_initial_audit_events.py`, and repository.
- [x] Provider-neutral LLM interface (`BaseLLMProvider`) and deterministic `FakeLLMProvider`.
- [x] Verifiable text grounding utility (`validate_excerpt_in_text`) rejecting ungrounded quotes.
- [x] Page-preserving PDF text extraction (`extract_text_by_page`) and magic-byte validation (`%PDF-`).
- [x] Background worker abstraction (`BaseBackgroundWorker`) with local async worker queue (`LocalAsyncWorker`).
- [x] Health, liveness, and database readiness endpoints with HTTP 503 failure handling.
- [x] Comprehensive test suite (21 unit and integration tests passing).
- [x] Multi-stage `Dockerfile` and `docker-compose.yml`.

### Extension Points & Placeholders for Next Phase
- **Authentication**: Phase 1 includes JWT validation, token creation, and RBAC role dependencies (`require_roles`). Full OIDC/SAML integration with SAP Cloud Identity Services is reserved for Phase 2. Client role spoofing is strictly prohibited.
- **SAP SuccessFactors Integration**: `SuccessFactorsClient` provides interface stubs for Job Requisition and Application OData synchronization.
- **Domain Entities**: Phase 1 established the foundation with `audit_events`. Subsequent phases will migrate `users`, `documents`, `jobs`, `job_criteria`, `evaluations`, and `review_decisions`.
