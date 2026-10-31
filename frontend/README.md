# ClearHire — Frontend Application
**Hiring Evidence Transparency Platform (Built for SAP Hackfest 2026)**

ClearHire prevents relevant candidate evidence from being silently missed during screening by mapping verifiable resume excerpts directly to versioned job criteria with exact page references, human reviewer rationales, candidate clarification workflows, and a cryptographic SHA-256 audit ledger.

---

## 1. Quickstart & Local Development

The frontend is built using standard **HTML5**, **Vanilla CSS**, and **Modern JavaScript (ES Modules)**. No build step or heavy node_modules compilation is required.

### Option A: Using NPM / NPX (Port 3000)
```bash
cd frontend
npm run dev
```
Then open: [http://localhost:3000](http://localhost:3000)

### Option B: Using Python's Built-in HTTP Server
```bash
cd frontend
python -m http.server 3000
```
Then open: [http://localhost:3000](http://localhost:3000)

---

## 2. Page Breakdown & Features

| View | Target Persona | Backend Phase 1 Mapping | Capabilities |
|---|---|---|---|
| **1. Command Center** | All | `GET /api/v1/health/ready` | Live backend probe, quick KPI cards, persona switcher, workflow breakdown. |
| **2. Candidate Portal** | Candidate | `POST /documents`, `GET /profiles/{id}/skills` | Page-preserving PDF uploader, extracted skills inventory, factual criteria coverage breakdown, candidate clarification drawer. |
| **3. Human Review Desk** | Reviewer | `GET /reviews`, `POST /reviews/{id}/decision` | Review queue with priority filters, side-by-side criterion vs verbatim quote & page inspection, candidate clarification feed, decision console with **enforced mandatory written rationale**. |
| **4. Job & Criteria Studio** | Employer Admin | `POST /jobs`, `GET /jobs/{id}`, `/integrations/successfactors/feed` | Job requisition builder with versioned criteria, active requisition table, simulated SAP SuccessFactors applicant feed inspection and batch import. |
| **5. Fairness Benchmark Lab** | All | `GET /benchmark/run` | Interactive before/after benchmark runner comparing legacy literal-keyword ATS filters against ClearHire evidence matching on labelled ground truth. |
| **6. Cryptographic Ledger** | System Auditor | `GET /audit/verify`, `GET /audit/{id}` | Real-time SHA-256 hash-chain verification (`previous_hash` $\to$ `event_hash`), block-by-block visualizer, tamper-proof state guarantee. |
| **7. API Playground** | Developer / Tester | `GET /health`, Swagger Docs | Base URL configuration, live endpoint ping tester, active JWT role inspector. |

---

## 3. Seamless Phase 1 Backend Integration

Because ClearHire backend is currently in **Phase 1 testing**:
* When the FastAPI backend is running on `http://localhost:8000`, the frontend automatically sends live API requests and handles real responses.
* When the backend is offline or undergoing tests, the frontend automatically falls back to deterministic mock simulation mirroring the backend schemas and `fixtures.py` 1:1.
* The frontend allows instant switching between **Candidate**, **Reviewer**, **Employer Admin**, and **System Auditor** personas, automatically generating corresponding JWT authorization headers for testing.
