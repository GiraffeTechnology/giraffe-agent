# Giraffe Agent

> Open-core industrial agent infrastructure for private-domain procurement, trade execution, quality control, and auditable order orchestration.
>
> Industrial Execution Graph + Neutral Actor Model + GPM/GLTG feasibility reasoning + OpenClaw-compatible channel runtime.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-ready-green)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-purple)](https://docs.pydantic.dev/)
[![uv](https://img.shields.io/badge/uv-supported-black)](https://docs.astral.sh/uv/)
[![License](https://img.shields.io/badge/license-Apache--2.0-lightgrey)](LICENSE)

---

## What Is Giraffe Agent?

Giraffe Agent is the open-core orchestration layer of the Giraffe industrial AI system.

It is designed for industrial procurement, cross-border trade execution, supplier coordination, order follow-up, QC evidence handling, logistics tracking, and private-domain business memory. It converts fragmented real-world trade communication into structured, auditable, human-confirmable execution state.

Giraffe Agent is not a CRM, ERP, marketplace, supplier directory, generic chatbot, or single-purpose demo.

It is an **industrial execution infrastructure layer** that sits between communication channels, private-domain data, deterministic feasibility models, AI reasoning, human approval, and auditable order execution.

The core output is an **Industrial Execution Graph**: an append-only record of requirements, supplier inquiries, quotations, delivery assumptions, approvals, production events, QC evidence, logistics updates, exceptions, and sign-off decisions.

---

## Product Category

Classical procurement tools assume clean forms, known suppliers, stable master data, and formal RFQs.

Real industrial trade usually starts elsewhere:

- buyer requirements arrive as incomplete IM messages, emails, screenshots, drawings, spreadsheets, PDFs, photos, or voice notes;
- suppliers reply in inconsistent formats;
- a manufacturer can be the supplier in one edge and the buyer in another edge;
- upstream material, trim, subcontracting, packaging, QC, and logistics dependencies are often hidden;
- lead-time promises require evidence and simulation, not blind trust;
- quality inspection requires visual comparison against confirmed detection points, not general language guessing;
- humans and legal entities still carry commercial and legal responsibility.

Giraffe Agent creates the execution layer for this environment:

> **Industrial agentic AI for private-domain trade execution — turning communication into auditable workflow primitives, execution graphs, and reusable business data.**

---

## Ecosystem Map

Giraffe Agent is the orchestration repository. It should not be confused with every downstream product built on the Giraffe architecture.

| Component | Role in the Giraffe ecosystem | Repository / boundary |
|---|---|---|
| **giraffe-agent** | Open-core orchestration layer, workflow state, Neutral Actor Model, B/M-side execution, Industrial Execution Graph, OpenClaw-compatible skill interface | This repository |
| **AIVAN** | Standalone AI trade salesperson for private-domain RFQ execution: buyer inquiry intake, supplier sourcing, GLTG calls, draft creation, human approval, email-first outbound | [`GiraffeTechnology/aivan`](https://github.com/GiraffeTechnology/aivan) |
| **abcdYi** | Apparel and textile industry application layer aligned with the Giraffe C2M / order execution patent family | Separate application repository |
| **GPM** | Giraffe Procurement Model: broader procurement graph reasoning, supplier-set feasibility, procurement-path planning, role/edge reasoning | Model layer / callable service boundary |
| **GLTG** | Giraffe Lead-Time Graph: deterministic lead-time and delivery-feasibility simulation, including P50/P80/P90 estimates and fallback triggers | Model layer / library boundary |
| **Giraffe DB** | Private-domain source of truth for customers, suppliers, RFQs, quotations, lead-time history, approval history, and order/quote/procurement data | Should be treated as an independent data layer, not as LLM memory |
| **giraffe-qc-model** | AI-native QC inference system with Pad and Server editions; manages sample DB, standard photos, inspection requirements, detection points, and QC inference | [`GiraffeTechnology/giraffe-qc-model`](https://github.com/GiraffeTechnology/giraffe-qc-model) |

`giraffe-agent` coordinates these capabilities. It should not silently absorb every product's runtime, credentials, database ownership, or deployment policy.

---

## Repository Boundary

This repository owns or demonstrates:

- OpenClaw-compatible normalized event intake;
- B-side / M-side role-aware workflow orchestration;
- Neutral Actor Model and role switching;
- supplier inquiry and response packets;
- delivery-feasibility workflow hooks;
- AI Buyer and AI Merchandiser reference workflows;
- QC evidence ingestion and QC service interface;
- logistics ingestion patterns;
- append-only Industrial Execution Graph events;
- local development persistence and validation scripts;
- reference implementation of the industrial execution model.

This repository does **not** own:

- IM account login, cookies, session tokens, CAPTCHA bypass, or platform anti-bot bypass;
- AIVAN runtime and OpenClaw Gateway product fixes, which belong in `aivan` first;
- canonical order/quote/procurement business database ownership, which should live in Giraffe DB;
- QC model inference runtime ownership, which belongs in `giraffe-qc-model`;
- final legal, credit, sanctions, compliance, payment, or contractual decisions.

---

## Current Validation Status

Latest main-branch local validation:

- Unit tests: `525 passed`
- B-side independent flow: PASS
- M-side independent flow: PASS
- B/M E2E: PASS
- AI Merchandiser post-confirmation: PASS
- Logistics ingestion: PASS
- QC Intelligence interface: PASS
- QC mock fallback: PASS
- OpenClaw IM simulated events: PASS
- DB-off mode: PASS
- DB-on mode: PASS
- 3x clean-state validation: PASS

External-service status:

- Real Qwen call: SKIPPED unless `DASHSCOPE_API_KEY` / `QWEN_API_KEY` is configured.
- Real OpenClaw IM bridge inside this repository: SKIPPED unless live OpenClaw channel credentials are configured.

Repository-local verdict: **PASS WITH GAPS** — internal interfaces and mock paths pass; external production calls require credentials.

Important ecosystem distinction:

- AIVAN has its own standalone OpenClaw Gateway / WeChat bot bridge validation status in the `aivan` repository.
- `giraffe-qc-model` has its own QC runtime, sample DB, Android Pad, and Server edition validation status in the `giraffe-qc-model` repository.

See [`MAIN_3X_VALIDATION_REPORT.md`](MAIN_3X_VALIDATION_REPORT.md).

---

## Core Execution Chain

```text
User IM / Email / Marketplace input
-> OpenClaw or compatible channel runtime
-> normalized event
-> Giraffe Agent workflow router
-> role-aware requirement structuring
-> Giraffe DB private-domain lookup
-> GPM procurement-path reasoning
-> GLTG lead-time / delivery-feasibility simulation
-> draft inquiry / draft quote / draft response
-> human approval gate
-> authorized outbound execution
-> order execution state
-> AI Merchandiser follow-up
-> QC evidence ingestion / QC service call
-> logistics / exception tracking
-> buyer sign-off
-> Supplier Memory / Giraffe DB update
-> append-only Industrial Execution Graph
```

The system is designed so that private-domain facts come from the database, deterministic feasibility comes from GPM/GLTG, visual QC comes from the QC model, and the LLM provides controlled reasoning, summarization, classification, and drafting.

---

## Legal and Operating Boundary

Giraffe Agent does not replace the legal parties to a transaction.

It does not become the buyer, seller, manufacturer, freight forwarder, payment obligor, insurer, bank, customs declarant, or contracting party.

Human users and their legal entities remain responsible for:

- approving supplier inquiries;
- confirming quotations;
- selecting delivery paths;
- accepting production schedules;
- approving order commitments;
- releasing payments;
- signing contracts;
- accepting commercial, legal, credit, sanctions, logistics, and quality risk.

Giraffe Agent assists by producing:

- structured requirements;
- clarification questions;
- bilingual inquiry drafts;
- supplier response packets;
- private-domain context packets;
- delivery feasibility reports;
- ranked options and risk flags;
- production and QC milestone records;
- QC comparison reports and corrective feedback;
- logistics updates;
- exception reports;
- supplier memory updates;
- append-only execution events.

High-stake actions must remain human-confirmed.

---

## Core Product Principles

### 1. Conversation is the real interface

Industrial trade does not start in a clean SaaS form. It starts in WeChat, WhatsApp, DingTalk, LINE, email, phone notes, drawings, screenshots, PDFs, informal buyer messages, and supplier fragments.

Giraffe Agent works through an OpenClaw-compatible channel runtime and normalized event interface.

### 2. Private-domain data is the source of truth

The LLM must not invent supplier facts, customer history, historical prices, lead-time history, approval history, or user preference memory.

Those facts must come from Giraffe DB or from explicitly provided evidence. The LLM may reason over database context, but it is not the business fact source.

### 3. Deterministic models calculate feasibility

Lead-time and delivery feasibility should not be guessed by the LLM.

GPM and GLTG provide procurement-path reasoning and delivery-feasibility simulation. The LLM may explain their outputs, but it must not replace their calculations.

### 4. Roles are contextual, not fixed

The same company can be:

- a supplier to the original buyer;
- a buyer to its own upstream supplier;
- a coordinator for subcontracting, packaging, or logistics;
- a merchandiser after an order is confirmed.

Giraffe Agent uses the Neutral Actor Model instead of hardcoding B-side and M-side as permanent identities.

### 5. Evidence matters more than promises

Supplier-stated lead time is preserved as evidence but not trusted blindly.

Delivery feasibility must consider full path dependencies:

- material;
- trim;
- packaging material;
- subcontracting;
- production;
- QC;
- packaging;
- logistics.

Missing fields become risk flags, not fake certainty.

### 6. QC must inspect confirmed detection points

Quality control must compare actual visual evidence against approved standard photos, inspection requirements, and detection points.

The QC model must not infer pass/fail results from general language alone. If a detection point cannot be inspected with sufficient confidence, the result must be marked for review.

### 7. The execution record must be append-only

Industrial execution needs auditability.

Giraffe Agent records state transitions in an append-only Industrial Execution Graph. Events are appended, not rewritten.

---

## Core Concept: Neutral Actor Model

> Do not treat B-side and M-side as permanent identities.

An actor's role is contextual. It depends on the project, procurement edge, and counterparty.

| Role | Meaning |
|---|---|
| `MAIN_M_SIDE` | Main supplier to the original buyer |
| `UPSTREAM_B_SIDE` | Same manufacturer acting as buyer to its own upstream suppliers |

Example:

```text
Buyer B -> Manufacturer M
M is MAIN_M_SIDE to B.

Manufacturer M -> Fabric Supplier F1
M is UPSTREAM_B_SIDE to F1.
```

Every workflow is project-aware and edge-aware. This enables recursive supply-chain execution instead of a flat buyer-supplier form.

---

## GPM and GLTG

GPM and GLTG should be treated as related but distinct model layers.

### GPM — Giraffe Procurement Model

GPM is the broader procurement graph model. It is responsible for supplier-set reasoning, procurement-path planning, known-suppliers-first feasibility, fallback decisions, and role/edge-aware procurement logic.

GPM answers questions such as:

- Which known suppliers should be tried first?
- Which missing procurement edges create risk?
- When should the system trigger public bidding or external supplier search?
- How should upstream evidence roll up into a buyer-facing option?
- Which procurement path is feasible, risky, or blocked?

### GLTG — Giraffe Lead-Time Graph

GLTG is the lead-time and delivery-feasibility model. It estimates delivery paths using deterministic dependency logic and probability bands.

GLTG should support:

- P50 / P80 / P90 lead-time estimates;
- minimum feasible lead time;
- dependency-aware parallel and sequential calculations;
- known-suppliers-first feasibility;
- fallback trigger recommendations;
- fewer-than-three-supplier outputs without crashing;
- explicit risk flags for missing data.

The LLM may translate GPM/GLTG results into user-friendly language, but it must not invent lead-time values or supplier feasibility.

---

## Giraffe DB and Private-Domain Memory

Giraffe DB is the private-domain business memory layer.

It should store or expose:

- customer profiles and preferences;
- supplier profiles and relationships;
- historical RFQs;
- historical quotations;
- historical lead-time records;
- order/quote/procurement data;
- approval history;
- draft revision history;
- risk flags;
- project and execution memory.

Giraffe Agent should query Giraffe DB through explicit adapters or APIs. The LLM must never reconstruct these facts from general knowledge.

Data categories should remain structurally separated where appropriate:

- API-imported data;
- private customer data;
- system-generated historical data;
- QC sample / inspection data, which belongs to the QC system and should not be mixed into ordinary order/quote DB tables.

---

## AIVAN Boundary

AIVAN is a standalone AI trade salesperson product extracted from the broader Giraffe Agent architecture.

AIVAN owns the private-domain RFQ execution workflow:

```text
User IM command or customer email
-> OpenClaw Gateway
-> AIVAN event intake
-> LLM strategy interpretation
-> Giraffe DB private-domain lookup
-> GLTG lead-time simulation
-> RFQ/project creation
-> pending supplier inquiry email drafts
-> user IM summary / approval request
-> approved email sent through OpenClaw email integration
```

AIVAN should be developed and validated in its own repository first. Stable capabilities can later be ported or integrated into `abcdYi` and the broader `giraffe-agent` framework.

`giraffe-agent` should not become the active development home for AIVAN runtime fixes, OpenClaw Gateway fixes, ClawHub packaging details, or AIVAN-specific product state.

---

## QC Model Boundary

QC capability is moving into `giraffe-qc-model` as an AI-native QC inference system.

The QC model owns:

- sample DB;
- standard photos;
- inspection requirements;
- detection points;
- ROI definitions;
- Pad and Server runtime editions;
- Qwen3-VL-based visual inspection;
- local-first / fail-closed QC inference policy;
- QC result conventions.

Giraffe Agent should call QC capability as a service or integration boundary. It should ingest QC evidence, request inspection, record the returned QC report, route corrective feedback, and append events into the Industrial Execution Graph.

Giraffe Agent must not fake QC pass/fail results. If real QC inference is unavailable, the result must be marked as skipped, mock, pending, or `review_required` according to the execution context.

---

## OpenClaw / IM / Email Integration

Giraffe Agent is designed as an **OpenClaw-compatible skill layer**.

The channel architecture is:

```text
WeChat / WhatsApp / DingTalk / LINE / Email / Web / other channels
-> OpenClaw or compatible channel runtime
-> normalized event
-> POST /api/skill/invoke
-> OpenClaw event adapter
-> Giraffe workflow router
```

Giraffe Agent does not directly store IM platform credentials. IM account control, message sending, and message receiving are expected to be handled by OpenClaw or a compatible runtime.

### User-control IM vs counterparty outbound

WeChat, LINE, WhatsApp, DingTalk, and similar IM channels are primarily user-control channels in the current product boundary.

They may be used for:

- user commands;
- approval requests;
- customer email summaries;
- RFQ/project progress notifications;
- revision requests;
- internal status updates.

Current counterparty commercial outbound should be draft-first and human-approved. Email is the current default formal outbound execution channel unless another official, API-permitted, auditable, authorized channel is explicitly integrated.

Giraffe Agent and downstream products must not automatically send commercial messages to customers or suppliers through personal IM accounts without explicit human approval and proper channel authorization.

---

## Architecture

```text
+--------------------------------------------------------------------------------+
| Channel Runtime Layer                                                          |
|   OpenClaw / compatible IM-email runtime                                       |
|   WeChat / WhatsApp / DingTalk / LINE / Email / Web / marketplace channels     |
|   Giraffe does not store IM platform credentials directly                      |
+--------------------------------------------------------------------------------+
| OpenClaw-Compatible Skill Layer                                                |
|   /api/skill/invoke                                                            |
|   normalized event adapter  role-aware router  workflow dispatcher             |
+--------------------------------------------------------------------------------+
| Orchestration Layer                                                            |
|   AI Buyer  Supplier Response Agent  Role-Switching Procurement Agent          |
|   AI Merchandiser  Logistics ingestion  QC evidence routing                    |
+--------------------------------------------------------------------------------+
| Private-Domain Data and Model Layer                                            |
|   Giraffe DB adapter  GPM procurement graph reasoning  GLTG lead-time graph    |
|   Supplier Memory  approval history  RFQ/order/quote context                   |
+--------------------------------------------------------------------------------+
| Intelligence Layer                                                             |
|   Qwen / Tongyi Qianwen default requested provider                             |
|   Mock fallback for local/CI when no key is configured                         |
|   Optional provider registry: Qwen  Mock  OpenAI  Anthropic  DeepSeek          |
+--------------------------------------------------------------------------------+
| Service Boundaries                                                             |
|   AIVAN RFQ product  giraffe-qc-model QC inference  abcdYi industry app        |
+--------------------------------------------------------------------------------+
| Persistence / Execution Record                                                 |
|   Local JSON/SQLite reference stores  PostgreSQL-portable ORM                  |
|   Append-only Industrial Execution Graph + procurement_edges                   |
+--------------------------------------------------------------------------------+
```

---

## Main Modules

| # | Module | Purpose |
|---:|---|---|
| 1 | OpenClaw Skill Layer | Normalized IM/email event intake via `/api/skill/invoke` |
| 2 | Neutral Actor Model | Contextual B/M-side role resolution per project and procurement edge |
| 3 | AI Buyer | Requirement structuring, inquiry drafting, feasibility workflow initiation |
| 4 | Supplier Response Agent | M-side intake, normalization, `SupplierResponsePacket` generation |
| 5 | Role-Switching Procurement Agent | Recursive `UPSTREAM_B_SIDE` logic, upstream inquiry builder, option engine, approval gate |
| 6 | Professional Free CAD->CNC Matching | CAD Requirement Packet, Capability Fit Report, machine profile matching |
| 7 | AI Merchandiser | Production milestones, QC/media confirmation, exception reporting, logistics handover, buyer sign-off |
| 8 | GPM / GLTG Integration | Procurement graph reasoning and lead-time / delivery-feasibility simulation boundary |
| 9 | QC Service Interface | QC evidence ingestion, QC report handling, M-side corrective feedback, buyer escalation |
| 10 | Logistics Ingestion | Carrier API normalization and shipment tracking ingestion |
| 11 | LLM Provider Layer | Qwen default requested provider, deterministic mock fallback, optional providers |
| 12 | Database / Adapter Layer | SQLAlchemy local reference models, SQLite->PostgreSQL portability, future Giraffe DB adapter boundary |
| 13 | Dynamic Self-Learning Schema | AI observes and proposes new fields without altering physical tables at runtime |
| 14 | Industrial Execution Graph | Append-only event log for state transitions across actors and project edges |

---

## Quick Start

### Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) package manager

### Setup

```bash
git clone https://github.com/GiraffeTechnology/giraffe-agent.git
cd giraffe-agent

uv sync

uv run python scripts/init_db.py
uv run python scripts/seed_mvp_data.py

uv run uvicorn api.main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

---

## LLM Configuration

Giraffe Agent uses **Qwen / Tongyi Qianwen** as the default requested LLM provider.

Local and CI behavior uses safe defaults:

```bash
LLM_PROVIDER=qwen
QC_AUTO_COMPARE_PROVIDER=qwen
LLM_ENABLE_REAL_CALLS=false
QC_ALLOW_EXTERNAL_LLM=false
```

When no Qwen API key is available, the provider registry falls back to the deterministic mock provider. Reports must still record:

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

Data safety defaults:

```bash
QC_ALLOW_EXTERNAL_LLM=false
QC_ALLOW_CAD_TO_LLM=false
QC_ALLOW_BOM_TO_LLM=false
QC_REDACT_PROCESS_CARD=true
```

By default, confidential CAD, BOM, contract, pricing, customer, and supplier information is not sent to external LLMs.

---

## E2E Verification

Run the verification suite after setup.

### B/M-side DB Integration Baseline

```bash
GIRAFFE_DB_MODE=off uv run python run_bm_e2e_with_db.py

GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db uv run python build_schema.py
GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db uv run python run_bm_e2e_with_db.py

uv run python verify_integration.py --db sqlite:///./test.db --runs 5
```

Expected successful baseline:

```text
run 1/5: PASS  run 2/5: PASS  run 3/5: PASS  run 4/5: PASS  run 5/5: PASS
PRAGMA integrity_check: ok
PRAGMA foreign_key_check: ok
Result: 5/5 passed
```

### Lead-Time / Delivery-Feasibility Verification

The current repository includes a path-based lead-time calculation reference.

Key rules:

- Material, trim, packaging-material, and subcontract dependencies run in parallel, so use `max()`.
- Production, QC, packaging, and logistics run sequentially, so use `sum()`.
- Supplier-stated lead time is preserved as evidence but not trusted blindly.
- Missing fields create `risk_flags`; never use fake sentinel values such as `999`.

Run:

```bash
uv run python scripts/run_lead_time_model_demo.py
```

Expected output: `LEAD TIME MODEL DEMO: PASS`

### Main Branch 3x Validation

Latest main has been validated with three clean-state runs.

Summary:

- Unit tests: `525 passed`
- B-side independent flow: PASS
- M-side independent flow: PASS
- B/M E2E: PASS
- AI Merchandiser: PASS
- Logistics: PASS
- QC Intelligence interface: PASS
- OpenClaw IM simulated events: PASS
- DB-off: PASS
- DB-on: PASS

Verdict: `PASS WITH GAPS`

Gaps:

- Real Qwen call requires `DASHSCOPE_API_KEY` or `QWEN_API_KEY`.
- Real OpenClaw IM bridge requires live OpenClaw channel credentials.

See [`MAIN_3X_VALIDATION_REPORT.md`](MAIN_3X_VALIDATION_REPORT.md).

### Verification Scripts

| Script | What it verifies |
|---|---|
| `scripts/run_db_smoke_test.py` | Database models, migrations, seed data |
| `scripts/run_bm_e2e_mvp.py` | Full B+M minimum loop |
| `scripts/run_role_switching_mvp.py` | Role-Switching Agent |
| `scripts/run_mside_professional_free_cad_cnc_mvp.py` | CAD->CNC matching |
| `scripts/run_mside_send_receive_role_switch_test.py` | M-side send/receive role switching |
| `scripts/run_merchandiser_e2e_mvp.py` | AI Merchandiser full flow |
| `scripts/run_logistics_cainiao_like_api_mvp.py` | Logistics ingestion and normalization |
| `scripts/run_integrated_post_confirmation_mvp.py` | Integrated post-confirmation |
| `scripts/run_lead_time_model_demo.py` | Lead Time Path Model deterministic verification |
| `scripts/run_qc_llm_comparison_mvp.py` | QC comparison with Qwen-requested provider and mock fallback |
| `scripts/run_qwen_qc_smoke_test.py` | Real Qwen smoke test if key exists; safe skip if no key |

```bash
uv run pytest
```

---

## API Overview

The FastAPI application entry point is `api.main:app`.

The root `main.py` is only a lightweight helper for local developer guidance.

Primary route groups:

| Route | Purpose |
|---|---|
| `GET /health` | Health check |
| `POST /api/skill/invoke` | OpenClaw skill invocation for normalized IM/email events |
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

Full interactive documentation is available at `/docs` when the server is running.

---

## Repository Structure

```text
giraffe-agent/
+-- api/                        # FastAPI application
|   +-- main.py
+-- src/
|   +-- b_side/                 # AI Buyer: requirement structurer, inquiry drafter, feasibility workflow
|   +-- m_side/                 # Supplier Response Agent, Role-Switching Agent, AI Merchandiser
|   |   +-- professional_free/  # CAD->CNC matching
|   |   +-- rollup/             # SupplierResponseRollup builder
|   |   +-- upstream/           # Upstream inquiry builder, option engine, approval gate
|   +-- bm_bridge/              # Inquiry dispatcher, response bridge, order bridge
|   +-- channels/               # Optional local channel helpers; production IM through OpenClaw
|   +-- llm/                    # Qwen-first provider layer, mock fallback, optional providers
|   +-- openclaw_skill/         # OpenClaw skill manifest, event adapter, skill router
|   +-- actors/                 # Neutral actor model, role resolver
|   +-- projects/               # Project graph
|   +-- core_schema/            # Pydantic types for B-side and M-side
|   +-- merchandiser/           # Post-confirmation execution engine
|   |   +-- qc/                 # QC reference images, process cards, comparison, reports, policy
|   +-- logistics/              # Logistics ingestion
|   +-- db/                     # SQLAlchemy reference models, mixins, Alembic config
+-- scripts/                    # Setup, seed, and E2E verification scripts
+-- alembic/                    # Database migrations
+-- docs/                       # Product requirement documents
+-- data/                       # Runtime workspace files and event log
+-- openclaw/                   # OpenClaw skill packaging
+-- PATENT_NOTICE.md
+-- LICENSE_NOTICE.md
+-- LICENSE
+-- pyproject.toml
```

---

## Design Constraints

These invariants are non-negotiable.

### Neutral Actor Model

Never hardcode B-side or M-side as fixed actor identities. Roles are contextual per `Project` and `ProcurementEdge`.

### Human Confirmation

Giraffe Agent must not create commercial commitments without human approval. High-stake actions require explicit confirmation.

### No Faked Business Facts

If parsing is uncertain, surface a clarification question or risk flag.

Never invent supplier data, prices, dates, capacity, material availability, logistics status, CAD properties, customer preferences, approval history, or buyer approvals.

### No Faked QC Results

QC must inspect confirmed detection points against approved standard photos, inspection requirements, and evidence.

If inference is unavailable or insufficient, mark the result as skipped, mock, pending, or `review_required`. Do not convert uncertainty into pass/fail.

### Append-Only Execution Graph

`execution_events` must never be updated or deleted. State changes are appended.

### Dynamic Schema Rule

AI may observe and propose new fields. It must not directly alter physical database table definitions at runtime.

### OpenClaw Boundary

Giraffe Agent should receive normalized IM/email events from OpenClaw or compatible runtimes. It should not directly store IM platform credentials for any channel.

### AI Is Not a Legal Actor

AI-generated recommendations, QC feedback, delivery paths, and supplier comparisons are decision-support artifacts. Human/legal entities remain responsible for acceptance and contractual decisions.

### External LLM Safety

External LLM calls are disabled by default. CAD, BOM, pricing, buyer identity, supplier contacts, and contract terms must not be sent externally unless explicitly enabled and redacted.

### Mock Is Not Real Provider

When Qwen credentials are absent, mock fallback is allowed for tests, but README, reports, and audit records must say the real Qwen call was skipped.

---

## Tech Stack

| Component | Choice |
|---|---|
| Language | Python 3.11+ |
| API framework | FastAPI + Uvicorn |
| Data validation | Pydantic v2 |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Local database | SQLite |
| Production-portable database | PostgreSQL |
| Package manager | `uv` |
| Default LLM provider | Qwen / Tongyi Qianwen |
| Local/CI LLM fallback | Deterministic mock provider |
| Channel runtime | OpenClaw-compatible IM/email runtime |
| Private-domain memory | Giraffe DB adapter boundary |
| Procurement model | GPM boundary |
| Lead-time model | GLTG boundary |
| QC intelligence | `giraffe-qc-model` service boundary plus local reference interface |

---

## How to Contribute

Giraffe Agent is an open-core industrial AI infrastructure project.

Good contribution paths include:

### Industrial Execution Graph

- Add richer graph query and replay APIs.
- Improve event provenance and audit metadata.
- Add regression tests for state transitions and exception scenarios.

### GPM / GLTG

- Improve procurement-path reasoning.
- Add deterministic lead-time simulation adapters.
- Add P50/P80/P90 feasibility packets.
- Support fewer-than-three supplier options without failure.
- Improve fallback trigger logic and risk flags.

### Giraffe DB Integration

- Add explicit adapters for private-domain customer, supplier, RFQ, quotation, approval, and lead-time history.
- Keep API-imported data, private customer data, and system-generated historical data separable.
- Do not mix QC sample DB tables into ordinary order/quote DB tables.

### OpenClaw and Channels

- Build production OpenClaw deployment examples for WeChat, WhatsApp, DingTalk, LINE, email, and other channel runtimes.
- Add real credential-based OpenClaw bridge smoke tests outside the default CI path.
- Add channel-specific human confirmation flows.

### AIVAN Integration

- Keep AIVAN runtime fixes in `aivan` first.
- Add stable adapter contracts so AIVAN can call Giraffe DB, GPM, GLTG, and execution-graph services cleanly.
- Preserve email-first outbound and human approval.

### QC Integration

- Treat `giraffe-qc-model` as the QC inference boundary.
- Improve QC report ingestion, corrective feedback routing, and buyer escalation workflow.
- Preserve fail-closed / no-fake-result behavior.

### Production / Ops

- Add authentication middleware.
- Add tenant/project permission model.
- Add observability and audit logs.
- Add deployment packaging.
- Build buyer-facing and supplier-facing UI.

Before submitting a PR, run the E2E suite and make sure the relevant scripts still pass.

---

## Open-Core and Commercial Deployment Boundary

This repository is released as open-core software for development, research, learning, SME experimentation, and non-enterprise use within the license and patent notice terms.

Commercial deployment may include:

- private-domain deployment;
- VPC or on-premise deployment;
- enterprise permission model;
- audit logs and compliance controls;
- Giraffe DB integration;
- GPM / GLTG service integration;
- QC model integration;
- ERP / MES / WMS integration;
- supplier-network integration;
- SLA, maintenance, and support;
- high-volume workflow execution;
- token / API / workflow / execution-graph usage billing.

Separate written authorization may be required depending on use case, patent scope, commercial scale, and integration pattern.

---

## Patent Notice and License

This repository is released under the Apache-2.0 software license.

Certain workflows, system logic, role-based participant coordination mechanisms, multi-party C2M workflows, textile and apparel customization workflows, supplier coordination workflows, and order execution mechanisms in this project may be covered by patents owned by Giraffe Technology Holding Limited.

Patent family description:

> **Textile and Garment Customization Operation Platform System Based on a Multi-Party Coordinated C2M Model**  
> Chinese title: **基于多方配合的C2M模式的纺织品及服装定制运营平台系统**

| Jurisdiction | Patent |
|---|---|
| China | ZL 2023 1 1645939.9 / CN 117670482 B |
| Japan | P7644545 / 特許第7644545号 |

Giraffe Technology Holding Limited grants a Global Free Patent License to:

- individuals;
- developers;
- researchers;
- students;
- SMEs for their own procurement, production coordination, and sourcing;
- educational institutions for teaching and non-commercial use;
- research institutions for non-commercial research.

Separate written permission is required for:

- enterprise deployment;
- platform operation;
- high-volume commercial production use;
- third-party system integration;
- white-label, OEM, or resale;
- Enterprise CAP;
- use of Giraffe commercial assets, trademarks, supplier/buyer network data, or order archives.

Access to this source code does not automatically grant patent rights beyond the free license scope.

See:

- [`PATENT_NOTICE.md`](PATENT_NOTICE.md)
- [`LICENSE_NOTICE.md`](LICENSE_NOTICE.md)
- [`LICENSE`](LICENSE)

Authorization contact:

```text
mich@giraffe.technology
```

---

## Project Status

Giraffe Agent is an open-core reference implementation of the Giraffe industrial execution model.

The repository demonstrates the core execution chain:

```text
IM/email/marketplace input
-> OpenClaw-compatible channel runtime
-> normalized event
-> role-aware structured requirement
-> private-domain data lookup
-> GPM / GLTG feasibility reasoning
-> supplier inquiry
-> recursive upstream sourcing
-> human confirmation
-> order execution
-> AI Merchandiser
-> QC service interface
-> logistics / exception tracking
-> buyer sign-off
-> Supplier Memory / Giraffe DB update
-> Industrial Execution Graph
```

It is ready for developer contribution, technical review, scenario extension, model-layer integration, and deeper channel integration.

It is not yet a turnkey production enterprise deployment by itself. Production use requires explicit deployment architecture, credential handling, security hardening, permission model, observability, commercial authorization where applicable, and integration with the relevant Giraffe ecosystem services.
