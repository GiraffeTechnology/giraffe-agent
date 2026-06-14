# Giraffe Agent

> **OpenClaw-compatible AI-native industrial order execution agent.**
> AI Buyer + AI Merchandiser + QC Intelligence + Industrial Execution Graph.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/pydantic-v2-orange.svg)](https://docs.pydantic.dev/)
[![uv](https://img.shields.io/badge/package_manager-uv-purple.svg)](https://docs.astral.sh/uv/)

---

## What Is Giraffe Agent?

Giraffe Agent is the **missing execution layer** between IM/email-based industrial procurement and structured order delivery. It is *not* a CRM, ERP, marketplace, or chatbot.

It is an **OpenClaw-compatible skill layer** that turns buyer/supplier conversations, production updates, QC evidence, logistics events, and buyer sign-off into a structured **Industrial Execution Graph**.

Four main capabilities:

1. **AI Buyer** — structures buyer requirements, drafts supplier inquiries, compares supplier responses, and ranks delivery paths.
2. **Role-switching M-side** — lets a manufacturer act as supplier to the buyer *and* buyer to its own upstream suppliers in the same project.
3. **AI Merchandiser** — handles post-confirmation execution: acceptance, milestones, QC evidence, exceptions, logistics, and buyer sign-off.
4. **QC Intelligence** — compares supplier images/video frames against reference images and process cards, generates Chinese-first M-side feedback, and escalates serious issues to buyer/human review. Uses Qwen as the default LLM provider with mock fallback when no key is available.

```
AI Buyer        = pre-confirmation decision support
AI Merchandiser = post-confirmation execution support
QC Intelligence = evidence-based quality verification
```

Together they form the **Industrial Execution Graph v0.1** — a project-aware, event-sourced graph that records what *actually happened* in the supply chain, not what was promised.

---

## Current Validation Status

Latest main branch validation:

- Unit tests: `525 passed`
- B-side independent flow: PASS
- M-side independent flow: PASS
- B/M E2E: PASS
- AI Merchandiser post-confirmation: PASS
- Logistics ingestion: PASS
- QC Qwen interface: PASS
- QC mock fallback: PASS
- OpenClaw IM simulated events: PASS
- DB-off mode: PASS
- DB-on mode: PASS
- 3x clean-state validation: PASS

External-service status:

- Real Qwen call: SKIPPED unless `DASHSCOPE_API_KEY` / `QWEN_API_KEY` is configured.
- Real OpenClaw IM bridge: SKIPPED unless live OpenClaw channel credentials are configured.

Verdict: **PASS WITH GAPS** — all internal interfaces and mock paths pass; external production calls require credentials.

See [`MAIN_3X_VALIDATION_REPORT.md`](MAIN_3X_VALIDATION_REPORT.md).

---

## Core Concept: Neutral Actor Model

> **Do not treat B-side and M-side as fixed identities.**

An actor's role is contextual — it depends on the project, the procurement edge, and the counterparty. The same company can be:

- `MAIN_M_SIDE` — main supplier to the original buyer
- `UPSTREAM_B_SIDE` — same manufacturer acting as buyer to its own upstream suppliers

**Example — 100-shirt project:**
```
Buyer B  →  Manufacturer M   (M is MAIN_M_SIDE to B)
Manufacturer M  →  Fabric Supplier F1   (M is UPSTREAM_B_SIDE to F1)
```

Every workflow is **project-aware** and **edge-aware**.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Channel Runtime Layer                                                       │
│   OpenClaw / compatible IM-email runtime                                    │
│   WeChat · WhatsApp · DingTalk · LINE · Email · Web · and other IM channels  │
│   Giraffe does not store IM platform credentials directly                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ OpenClaw Skill Layer                                                        │
│   /api/skill/invoke                                                         │
│   normalized event adapter · role-aware router · B/M action dispatcher      │
├─────────────────────────────────────────────────────────────────────────────┤
│ Workflow Layer                                                              │
│   B-side: AI Buyer                                                          │
│   M-side: Supplier Response Agent + Role-Switching Agent                    │
│   M-side: Professional Free CAD↔CNC matching                                │
│   AI Merchandiser: milestones · media · exceptions · logistics              │
│   QC Intelligence: image/video/process-card comparison (Qwen-requested)     │
│   Cainiao-like logistics ingestion                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ LLM / Intelligence Layer                                                    │
│   Default requested provider: Qwen / Tongyi Qianwen                         │
│   Mock fallback for local/CI                                                │
│   Provider registry: Qwen · Mock · OpenAI · Anthropic · DeepSeek            │
├─────────────────────────────────────────────────────────────────────────────┤
│ Bridge Layer                                                                │
│   Inquiry Dispatcher · Response Bridge · Order Bridge                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Persistence Layer                                                           │
│   JSON runtime stores · SQLite local · PostgreSQL-portable ORM              │
│   Actors · Projects · Edges · RoleContexts · Requirements                   │
│   Inquiries · Responses · Rollups · Milestones · QC Reports · Shipments     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Industrial Execution Graph v0.1                                             │
│   Append-only ExecutionEvent log + procurement_edges                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**End-to-end flow:**

```mermaid
flowchart TD
    A[Buyer IM / WeChat / WhatsApp / DingTalk / Email] --> O[OpenClaw Channel Runtime]
    O --> S[/api/skill/invoke]
    S --> B[B-side AI Buyer Workspace]
    B --> C[Structured Requirement]
    C --> D{Missing fields?}
    D -- yes --> E[Clarification via IM] --> C
    D -- no --> F[Bilingual Supplier Inquiry Draft]
    F --> G[Dispatch to Suppliers]
    G --> H[M-side Workspace]
    H --> I{Need upstream suppliers?}
    I -- yes --> J[Role Switch: M becomes UPSTREAM_B_SIDE]
    J --> K[Upstream Inquiry + Rollup]
    I -- no --> L[SupplierResponsePacket]
    K --> M[SupplierResponseRollup]
    L --> N[B-side Feasibility Report]
    M --> N
    N --> P[Buyer Confirms Order]
    P --> Q[AI Merchandiser Execution Plan]
    Q --> R[Production Milestones]
    R --> QC[QC Intelligence Layer]
    QC --> QC1[Compare image/video frames vs reference + process card]
    QC1 --> QC2[M-side Chinese Feedback]
    QC1 --> QC3{Serious issue?}
    QC3 -- yes --> QC4[Buyer/Human Review]
    QC3 -- no --> T[Logistics Handover]
    T --> U[Cainiao-like Tracking]
    U --> V[Buyer Sign-off]
    V --> W[Supplier Memory + Industrial Execution Graph]
```

---

## Modules

| # | Module | Phase |
|---|--------|-------|
| 1 | **OpenClaw Skill Layer** — normalized IM/email event intake through `/api/skill/invoke`; compatible with WeChat, WhatsApp, DingTalk, LINE, email, and other channels | Channel / Runtime |
| 2 | **AI Buyer** — structures requirements, drafts bilingual supplier inquiries, runs delivery feasibility simulation | Pre-confirmation |
| 3 | **Supplier Response Agent** — M-side intake, normalization, SupplierResponsePacket | Pre-confirmation |
| 4 | **Role-Switching Procurement Agent** — recursive UPSTREAM_B_SIDE logic, upstream inquiry builder, option engine, approval gate | Pre-confirmation |
| 5 | **Professional Free CAD↔CNC Matching** — CAD Requirement Packet, Capability Fit Report, machine profile matching | Pre-confirmation |
| 6 | **AI Merchandiser** — post-confirmation milestones, production/QC/exception updates, logistics handover, buyer sign-off | Post-confirmation |
| 7 | **QC Intelligence Layer** — image/video-frame comparison against reference images and process cards; M-side feedback and buyer escalation; Qwen is the default requested provider with mock fallback | Post-confirmation |
| 8 | **Send/Receive Role Switching** — M-side send/receive mode transitions | Post-confirmation |
| 9 | **Cainiao-like Logistics Ingestion** — carrier API normalization, shipment tracking ingestion | Post-confirmation |
| 10 | **LLM Provider Layer** — Qwen default provider, mock fallback, optional OpenAI/Anthropic/DeepSeek providers | Cross-cutting |
| 11 | **Database Layer** — SQLAlchemy models, Alembic migrations, SQLite→PostgreSQL portable | Cross-cutting |
| 12 | **Dynamic Self-Learning Schema** — AI observes and proposes new fields without altering physical tables at runtime | Cross-cutting |
| 13 | **Industrial Execution Graph v0.1** — append-only event log for every state transition across all actors | Cross-cutting |

---

## Quick Start

### Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) package manager

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/GiraffeTechnology/giraffe-agent.git
cd giraffe-agent

# 2. Install dependencies
uv sync

# 3. Initialize the database (SQLite)
uv run python scripts/init_db.py

# 4. Seed MVP reference data
uv run python scripts/seed_mvp_data.py

# 5. Start the API server
uv run uvicorn api.main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

---

## LLM Configuration

Giraffe Agent uses **Qwen / Tongyi Qianwen** as the default requested LLM provider.

Local and CI behavior:

```bash
LLM_PROVIDER=qwen
QC_AUTO_COMPARE_PROVIDER=qwen
LLM_ENABLE_REAL_CALLS=false
QC_ALLOW_EXTERNAL_LLM=false
```

When no Qwen API key is available, the provider registry falls back to the deterministic mock provider. Reports still record:

```json
{
  "requested_provider": "qwen",
  "provider_name": "mock",
  "fallback_used": true
}
```

To enable real Qwen calls:

```bash
export DASHSCOPE_API_KEY="..."
# or
export QWEN_API_KEY="..."
export LLM_ENABLE_REAL_CALLS=true
export QC_ALLOW_EXTERNAL_LLM=true
export LLM_PROVIDER=qwen
export QC_AUTO_COMPARE_PROVIDER=qwen
```

Safety defaults:

```bash
QC_ALLOW_EXTERNAL_LLM=false
QC_ALLOW_CAD_TO_LLM=false
QC_ALLOW_BOM_TO_LLM=false
QC_REDACT_PROCESS_CARD=true
```

By default, confidential CAD/BOM/contract/pricing information is not sent to external LLMs.

---

## QC Intelligence Layer

The QC Intelligence Layer compares supplier-submitted production/QC evidence against approved references and process cards. It uses Qwen / Tongyi Qianwen as the default requested LLM provider and falls back to the deterministic mock provider when no API key is configured.

**Inputs:**
- Supplier production image
- Supplier QC image
- Sample/reference/golden image
- Video frames
- Process card / 工艺卡
- Order requirements

**Outputs:**
- `QCComparisonReport`
- Chinese-first M-side feedback
- English summary
- Severity classification
- Buyer escalation decision
- Human review flag
- Industrial Execution Graph event

**Typical flow:**

```text
M-side uploads QC image/video
→ Giraffe loads reference image + process card
→ Qwen provider is requested
→ Mock fallback is used if no key is configured
→ QCComparisonReport is generated
→ M-side receives corrective feedback
→ buyer review is triggered only for serious issues
```

Run QC validation:

```bash
uv run python scripts/run_qc_llm_comparison_mvp.py
uv run python scripts/run_qwen_qc_smoke_test.py
```

Expected local behavior without Qwen key:

```
QC LLM COMPARISON MVP COMPLETE: 26 passed, 0 failed
QWEN REAL CALL SKIPPED: missing API key
```

---

## OpenClaw / IM Integration

Giraffe Agent is designed as an **OpenClaw-compatible skill layer**.

The channel architecture is:

```text
WeChat / WhatsApp / DingTalk / LINE / Email / Web / other IM channels
→ OpenClaw or compatible channel runtime
→ normalized event
→ POST /api/skill/invoke
→ OpenClaw event adapter
→ Giraffe B-side / M-side / QC / logistics workflow
```

Giraffe Agent **does not directly store IM platform credentials**. IM account control, message sending, and message receiving are expected to be handled by OpenClaw or a compatible runtime. This applies to all supported channels (WeChat, WhatsApp, DingTalk, LINE, email, and others).

The OpenClaw event adapter supports simulated IM events through normalized payload fields such as:

```json
{
  "source": "openclaw",
  "channel": "wechat",
  "channel_account_id": "wechat-account-test",
  "conversation_id": "wechat-conv-buyer-test",
  "sender_id": "wechat-user-buyer-001",
  "sender_display_name": "Buyer WeChat Test",
  "message_text": "I need 100 cotton polo shirts within 45 days.",
  "message_type": "text",
  "attachments": [],
  "mode": "b_side"
}
```

Run OpenClaw validation:

```bash
uv run pytest tests/test_openclaw_integration.py
```

Real IM bridge validation (any channel) requires live OpenClaw channel credentials and is not enabled by default.

---

## E2E Verification

Each script verifies a complete workflow end-to-end. Run them after setup to confirm everything is wired correctly.

### B/M-side DB Integration — Baseline v1 ✓

**Tag:** `BM_DB_INTEGRATION_BASELINE_V1` (2026-06-13)

The core B/M-side DB integration is reproducible from a clean checkout.
BM DB Integration Baseline v1 is a reproducible integration baseline, not yet a
production-hardening release.

Full test report: [`docs/BM_DB_INTEGRATION_BASELINE_v1.md`](docs/BM_DB_INTEGRATION_BASELINE_v1.md)
Machine-readable result record: [`TEST_RESULT.md`](TEST_RESULT.md)
Changelog entry: [`CHANGELOG.md`](CHANGELOG.md)

```bash
# DB-off mode (no database required — pure in-memory)
GIRAFFE_DB_MODE=off python run_bm_e2e_with_db.py

# DB-on mode (real SQLite repositories)
GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db python build_schema.py
GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db python run_bm_e2e_with_db.py

# Reproducibility verifier — runs the full lifecycle 5 times, asserts all tables
python verify_integration.py --db sqlite:///./test.db --runs 5
```

Result (tag `BM_DB_INTEGRATION_BASELINE_V1`, 2026-06-13):

```
run 1/5: PASS  run 2/5: PASS  run 3/5: PASS  run 4/5: PASS  run 5/5: PASS
PRAGMA integrity_check: ok
PRAGMA foreign_key_check: ok
Result: 5/5 passed
```

DB-off mode: PASS · DB-on mode: PASS · Reproducible integration baseline passed;
ready for next-stage hardening and broader scenario testing.

### Lead Time Path Model

The B-side feasibility engine uses the **canonical Lead Time Path Model** — a full path-based lead time calculation replacing simplified `lead_time_days` ranking.

**Key rules:**
- Material, trim, packaging-material, subcontract run in **PARALLEL** → use `max()`
- Production → QC → packaging → logistics run **SEQUENTIALLY** → use `sum()`
- Supplier-stated lead time is preserved as evidence but not trusted blindly
- Missing fields create `risk_flags`, never sentinel `999` values

Run the deterministic demo:

```bash
uv run python scripts/run_lead_time_model_demo.py
```

Expected output: `LEAD TIME MODEL DEMO: PASS`

### MVP E2E Scripts

| Script | What it verifies |
|--------|-----------------|
| `scripts/run_db_smoke_test.py` | Database models, migrations, seed data |
| `scripts/run_bm_e2e_mvp.py` | Full B+M minimum loop (18 steps) |
| `scripts/run_role_switching_mvp.py` | Role-Switching Agent (79 checks) |
| `scripts/run_mside_professional_free_cad_cnc_mvp.py` | CAD↔CNC matching (78 checks) |
| `scripts/run_mside_send_receive_role_switch_test.py` | M-side send/receive role switching |
| `scripts/run_merchandiser_e2e_mvp.py` | AI Merchandiser full flow |
| `scripts/run_logistics_cainiao_like_api_mvp.py` | Logistics ingestion and normalization |
| `scripts/run_integrated_post_confirmation_mvp.py` | Integrated post-confirmation (56 checks) |
| `scripts/run_lead_time_model_demo.py` | Lead Time Path Model deterministic verification |
| `scripts/run_qc_llm_comparison_mvp.py` | Qwen-requested QC comparison with mock fallback, reference image, process card, image/video-frame checks |
| `scripts/run_qwen_qc_smoke_test.py` | Real Qwen smoke test if key exists; safe skip if no key |

```bash
# Run all E2E scripts in sequence
uv run python scripts/run_db_smoke_test.py
uv run python scripts/run_bm_e2e_mvp.py
uv run python scripts/run_role_switching_mvp.py
uv run python scripts/run_mside_professional_free_cad_cnc_mvp.py
uv run python scripts/run_merchandiser_e2e_mvp.py
uv run python scripts/run_logistics_cainiao_like_api_mvp.py
uv run python scripts/run_integrated_post_confirmation_mvp.py
uv run python scripts/run_lead_time_model_demo.py
uv run python scripts/run_qc_llm_comparison_mvp.py
uv run python scripts/run_qwen_qc_smoke_test.py
```

### Unit Tests

```bash
uv run pytest
```

### Main Branch 3x Validation

Latest main has been validated with three clean-state runs.

Summary:
- Unit tests: `525 passed`
- B-side independent flow: PASS
- M-side independent flow: PASS
- B/M E2E: PASS
- AI Merchandiser: PASS
- Logistics: PASS
- QC Qwen interface: PASS
- OpenClaw IM simulated events: PASS
- DB-off: PASS
- DB-on: PASS

Verdict: `PASS WITH GAPS`

Gaps:
- Real Qwen call requires `DASHSCOPE_API_KEY` or `QWEN_API_KEY`
- Real OpenClaw IM bridge requires live OpenClaw channel credentials

See [`MAIN_3X_VALIDATION_REPORT.md`](MAIN_3X_VALIDATION_REPORT.md).

---

## API Overview

The FastAPI application entry point is `api.main:app`; the root `main.py` is only a lightweight helper for local developer guidance.

The FastAPI server exposes the following route groups:

| Prefix | Description |
|--------|-------------|
| `GET /health` | Health check |
| `POST /api/skill/invoke` | OpenClaw skill invocation for normalized IM/email events (WeChat, WhatsApp, DingTalk, LINE, email, and others) |
| `POST /api/b-side/workspaces` | Create a B-side Enquiry Workspace |
| `POST /api/b-side/workspaces/{id}/structure-requirement` | Structure raw buyer requirement |
| `POST /api/b-side/workspaces/{id}/draft-inquiry` | Draft bilingual supplier inquiry |
| `POST /api/b-side/workspaces/{id}/run-feasibility` | Run delivery feasibility simulation |
| `POST /api/m-side/suppliers` | Create supplier profile |
| `POST /api/bm/dispatch-inquiry` | Dispatch inquiry to supplier workspaces |
| `POST /api/bm/push-response-to-b-side` | Push M-side response back to B-side |
| `POST /api/bm/create-order-execution` | Create order execution from selected delivery path |
| `POST /api/m-side/orders/{id}/acknowledge` | Supplier order acknowledgement |
| `POST /api/m-side/orders/{id}/production-update` | Submit production update |
| `POST /api/m-side/orders/{id}/qc-update` | Submit QC confirmation |
| `POST /api/m-side/orders/{id}/logistics-update` | Submit logistics handover |
| `GET /api/qc/health` | QC module health check |
| `POST /api/qc/{project_id}/reference-images` | Add QC reference / golden sample image |
| `GET /api/qc/{project_id}/reference-images` | List QC reference images |
| `POST /api/qc/{project_id}/process-card` | Create process card / 工艺卡 |
| `GET /api/qc/{project_id}/process-card` | Get latest process card |
| `POST /api/qc/{project_id}/compare` | Run Qwen-requested QC comparison |
| `GET /api/qc/{project_id}/reports` | List QC reports |
| `GET /api/qc/reports/{report_id}` | Get QC report |
| `POST /api/qc/{project_id}/buyer-decision` | Record buyer QC decision |

Full interactive documentation available at `/docs` when the server is running.

---

## Repository Structure

```
giraffe-agent/
├── api/                        # FastAPI application
│   └── main.py
├── src/
│   ├── b_side/                 # AI Buyer: requirement structurer, inquiry drafter, feasibility engine
│   ├── m_side/                 # Supplier Response Agent, Role-Switching Agent, AI Merchandiser
│   │   ├── professional_free/  # CAD↔CNC matching (no Enterprise CAP)
│   │   ├── rollup/             # SupplierResponseRollup builder
│   │   └── upstream/           # Upstream inquiry builder, option engine, approval gate
│   ├── bm_bridge/              # Inquiry dispatcher, response bridge, order bridge
│   ├── channels/               # Optional local channel helpers; production IM is expected through OpenClaw
│   ├── llm/                    # Qwen-first provider layer, mock fallback, optional providers
│   ├── openclaw_skill/         # OpenClaw skill manifest, event adapter, skill router
│   ├── actors/                 # Neutral actor model, role resolver
│   ├── projects/               # Project graph
│   ├── core_schema/            # Pydantic types for B-side and M-side
│   ├── merchandiser/           # Post-confirmation execution engine
│   │   └── qc/                 # QC reference images, process cards, Qwen comparison, reports, policy
│   ├── logistics/              # Cainiao-like logistics ingestion
│   └── db/                     # SQLAlchemy models, mixins, Alembic config
├── scripts/                    # Setup, seed, and E2E verification scripts
├── alembic/                    # Database migrations
├── docs/                       # Product requirement documents (do not modify)
├── data/                       # Runtime workspace files and event log
├── PATENT_NOTICE.md
├── LICENSE_NOTICE.md
└── pyproject.toml
```

---

## How to Contribute

Giraffe Agent is an open MVP — there is a lot of room to improve and extend it. Here are good starting points:

**Backend / Core**
- Add real LLM calls to replace the rule-based stubs in `requirement_structurer.py` and `inquiry_drafter.py`
- Implement `dynamic_schema` observation and proposal logic in `src/db/models/dynamic_schema.py`
- Extend the Industrial Execution Graph with richer event types and replay/query APIs
- Improve Qwen real-call examples for image/video QC once production credentials are available
- Add richer QC report visualization and buyer review UI

**Channels**
- Build production OpenClaw channel connectors and deployment examples for WeChat, WhatsApp, DingTalk, LINE, email, and other IM runtimes
- Add real credential-based OpenClaw bridge smoke tests outside the default CI path

**Matching & Intelligence**
- Improve CAD↔CNC capability matching scoring in `src/m_side/professional_free/cad_cnc_matcher.py`
- Add supplier memory retrieval into the feasibility simulation

**Production / Ops**
- Migrate from SQLite to PostgreSQL (the models are already JSONB-portable)
- Add authentication middleware to the FastAPI app
- Build a simple buyer-facing or supplier-facing web UI

**Testing**
- Add unit tests for individual modules in `tests/`
- Add regression coverage for the role-switching edge cases

Before submitting a pull request, run the full E2E suite and make sure all scripts still pass.

---

## Design Constraints (Read Before Modifying)

These are non-negotiable product invariants — don't work around them:

- **Neutral Actor Model:** Never hardcode B-side/M-side as a fixed actor identity. Roles are contextual per `Project` + `ProcurementEdge`.
- **No Enterprise CAP in MVP:** The Professional Free tier explicitly has no file encryption, dynamic watermarking, secure viewer, or no-download rooms. Do not add these.
- **Dynamic Schema Rule:** AI may observe and propose new fields; it must not directly alter physical database table definitions at runtime.
- **No Faked Data:** If parsing is uncertain, surface a clarification question. Never invent data.
- **Append-Only Graph:** `execution_events` must never be updated or deleted — only appended to.
- **OpenClaw Boundary:** Giraffe Agent should receive normalized IM/email events from OpenClaw or compatible runtimes. It should not directly store IM platform credentials for any channel (WeChat, WhatsApp, DingTalk, LINE, or others).
- **AI Is Not a Legal Actor:** AI-generated recommendations, QC feedback, delivery paths, and supplier comparisons are decision-support artifacts. Human/legal entities remain responsible for acceptance and contractual decisions.
- **External LLM Safety:** External LLM calls are disabled by default. CAD, BOM, pricing, buyer identity, supplier contacts, and contract terms must not be sent externally unless explicitly enabled and redacted.
- **Mock Is Not Real Provider:** When Qwen credentials are absent, mock fallback is allowed for tests, but README and reports must say real Qwen call was skipped.

---

## Tech Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.11+ |
| API framework | FastAPI + Uvicorn |
| Data validation | Pydantic v2 |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Database (local) | SQLite |
| Database (production) | PostgreSQL |
| Package manager | `uv` |
| Default LLM provider | Qwen / Tongyi Qianwen |
| Local/CI fallback | Deterministic mock provider |
| Channel runtime | OpenClaw-compatible IM/email runtime |
| Primary channel integration | OpenClaw-compatible normalized events; WeChat/WhatsApp/DingTalk/LINE/email and other IM channels handled by channel runtime |
| QC intelligence | Image/video-frame/process-card comparison |

---

## Patent Notice & License

Certain workflows, system logic, role-based participant coordination mechanisms, and multi-party C2M / order execution workflows in this project may be covered by patents owned by **Giraffe Technology Holding Limited**:

| Jurisdiction | Patent |
|---|---|
| China | ZL 2023 1 1645939.9 / CN 117670482 B |
| Japan | P7644545 / 特許第7644545号 |

**Global Free Patent License** — Giraffe Technology Holding Limited grants a free patent license to:
- Individuals (developers, researchers, students)
- SMEs (for own procurement, production coordination, and sourcing)
- Educational institutions (teaching, non-commercial use)
- Research institutions (non-commercial research)

**Separate written permission is required for:** enterprise deployment, platform/SaaS operation, high-volume commercial production use, third-party system integration, white-label/OEM/resale, Enterprise CAP, or use of Giraffe commercial assets (trademarks, supplier/buyer network data, order archives).

Access to this source code does **not** automatically grant patent rights beyond the free license scope.

See [`PATENT_NOTICE.md`](PATENT_NOTICE.md) and [`LICENSE_NOTICE.md`](LICENSE_NOTICE.md) for the full terms.

**Authorization contact:** mich@giraffe.technology
