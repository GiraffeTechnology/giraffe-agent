# 🦒 Giraffe Agent — Universal Order Execution Model

> Every industrial order should run a delivery feasibility simulation before confirmation.

[![License](https://img.shields.io/github/license/GiraffeTechnology/giraffe-agent)](LICENSE_NOTICE.md)
[![Issues](https://img.shields.io/github/issues/GiraffeTechnology/giraffe-agent)](https://github.com/GiraffeTechnology/giraffe-agent/issues)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/pydantic-v2-orange.svg)](https://docs.pydantic.dev/)

---

## Overview

Giraffe Agent is an open-core AI agent framework for industrial order execution. It converts messy B2B procurement requests into structured RFQs, supplier response packets, delivery feasibility simulations, ranked delivery paths, and human-approved execution plans.

It is not a chatbot, not a supplier directory, and not a generic workflow automation script.

---

## What Giraffe Agent Does

- converts incomplete buyer requests into structured order requirements
- detects missing commercial / production / logistics fields
- generates bilingual RFQs (English + Chinese) where applicable
- dispatches inquiries to multiple suppliers and manages M-side workspaces
- simulates supplier capacity, production timeline, QC capability, logistics terms, and risk flags
- enumerates and ranks delivery paths by risk-adjusted composite score
- generates Supplier Response Rollups aggregating upstream dependency responses
- creates AI Merchandiser execution plans covering milestones, QC, exceptions, and logistics handover
- records every state transition in an append-only Industrial Execution Graph

---

## Quickstart

**Prerequisites:** Python 3.11+, [`uv`](https://docs.astral.sh/uv/getting-started/installation/) or pip

```bash
# Clone and install
git clone https://github.com/GiraffeTechnology/giraffe-agent.git
cd giraffe-agent
pip install -e .

# Run the primary B+M end-to-end demo (18-step CNC order execution)
python scripts/run_bm_e2e_mvp.py

# Run the apparel / shirt order demo (role-switching, 79 checks)
python scripts/run_role_switching_mvp.py

# Run all E2E verification scripts
python scripts/run_merchandiser_e2e_mvp.py
python scripts/run_integrated_post_confirmation_mvp.py
```

> **Note:** The event logger emits SQLite warnings on first run because the `execution_events` table is not initialized by default. The demos complete successfully regardless. Run `python scripts/init_db.py` to silence the warnings.

---

## Current Public MVP

The primary public MVP consists of two executable end-to-end demonstration scripts.

### B+M E2E Demo (`scripts/run_bm_e2e_mvp.py`)

18-step procurement execution loop demonstrating the full AI Buyer + AI Merchandiser flow:

1. Buyer submits a messy natural-language procurement request
2. Giraffe Agent structures the requirement (category, quantity, material, specs, deadline, destination)
3. Missing field detection — clarification loop if required
4. Bilingual supplier inquiry generation (EN + ZH)
5. Inquiry dispatched to 3 suppliers; 3 M-side workspaces created
6. M-side normalizes each supplier reply into a `SupplierResponsePacket`
7. Responses pushed back to B-side workspace
8. Delivery feasibility simulation — all suppliers scored and ranked
9. Buyer selects Rank 1 supplier; order execution workspace created
10. Supplier acknowledges order, submits production update, QC update, logistics update
11. Events written to Industrial Execution Graph

**Artifacts written:**
- `data/b_side_workspaces/bw_<id>.json` — buyer workspace with RFQ, inquiry draft, supplier responses, feasibility report
- `data/m_side_workspaces/mw_<id>.json` — per-supplier M-side workspace
- `data/industrial_execution_graph/events.jsonl` — append-only execution event log

### Apparel Order / Role-Switching Demo (`scripts/run_role_switching_mvp.py`)

16-step role-switching test using a 100-shirt apparel order, demonstrating recursive B-side / M-side role switching:

- Buyer B → Manufacturer M (Manufacturer is `MAIN_M_SIDE`)
- Manufacturer M → Fabric / Trim / Packaging suppliers (Manufacturer switches to `UPSTREAM_B_SIDE`)
- Upstream supplier responses parsed, upstream options generated and approved
- Supplier Response Rollup submitted back to B-side
- B-side delivery feasibility simulation consumes rollup
- 79/79 checks pass

---

## Core Architectural Pillars

### 1. Order Feasibility Simulation

Before an order is confirmed, Giraffe Agent simulates whether the order can actually be delivered under real-world constraints. Supplier responses are evaluated against capacity, lead time, material availability, QC capability, logistics terms, and risk flags. Only suppliers with `can_make=True` are ranked.

### 2. Route Enumeration and Ranking

The system compares multiple supplier / production / logistics paths and ranks them by risk-adjusted composite score:

```
score = confidence / (1 + lead_time_days / 30) / (1 + red_flag_count × 0.1)
```

The top-ranked path is surfaced as the recommended delivery route. The buyer selects which path to execute.

### 3. Human-in-the-Loop Execution Gateway

The system prepares recommendations, RFQs, execution plans, and decision packets, but final pricing quotes, contractual commitments, and financial actions require explicit human approval. Upstream option approval gates (`src/m_side/upstream/approval_gate.py`) enforce this boundary before any commitment is rolled up to the buyer.

### 4. Circuit Breakers for Enterprise Risk Control

The system triggers human review when a proposed path exceeds predefined risk boundaries: abnormal pricing, deadline mismatch, supplier reliability concerns, logistics uncertainty, or missing critical order fields. Missing-field detection halts the flow and surfaces a clarification request rather than proceeding with incomplete data.

---

## Core Algorithms

All components currently in the repo are deterministic — no LLM calls are required to run the demos.

| Component | Location | What it does |
|-----------|----------|--------------|
| Requirement parser | `src/b_side/requirement_structurer.py` | Regex + keyword extraction of quantity, material, specs, deadline, destination; missing-field detection |
| Bilingual inquiry drafter | `src/b_side/inquiry_drafter.py` | Generates EN + ZH supplier inquiry from structured requirement |
| Delivery feasibility engine | `src/b_side/feasibility_engine.py` | Composite risk-adjusted scoring; builds ranked `DeliveryPath` list; writes `FeasibilityReport` |
| Upstream dependency planner | `src/m_side/dependencies/dependency_planner.py` | Identifies fabric / trim / packaging / QC / logistics dependencies for a given order category |
| Upstream option engine | `src/m_side/upstream/option_engine.py` | Generates 1–3 ranked upstream options from parsed supplier responses |
| Upstream approval gate | `src/m_side/upstream/approval_gate.py` | Human-in-the-loop approval step before upstream commitment |
| Supplier Response Rollup | `src/m_side/rollup/supplier_response_rollup.py` | Aggregates upstream responses into a single rollup submitted to B-side |
| AI Merchandiser | `src/merchandiser/` | Post-confirmation milestone tracking, QC follow-up, media confirmation, logistics handover, buyer sign-off |
| Industrial Execution Graph | `data/industrial_execution_graph/events.jsonl` | Append-only event log recording every state transition across all actors |
| Role resolver | `src/actors/role_resolver.py` | Resolves actor role (`MAIN_M_SIDE` / `UPSTREAM_B_SIDE` / `UPSTREAM_M_SIDE`) per project edge |

LLM integration stubs exist in `requirement_structurer.py` and `inquiry_drafter.py` — replacing the rule-based logic with real LLM calls is an identified contribution area.

---

## Validation and Test Status

> Tests run on: 2026-06-13

`pytest -q` finds **0 pytest test files** in the `tests/` directory. The integration coverage comes from the E2E verification scripts.

| Script | Result |
|--------|--------|
| `scripts/run_bm_e2e_mvp.py` | 18 steps — complete |
| `scripts/run_role_switching_mvp.py` | **79 / 79 checks passed** |
| `scripts/run_merchandiser_e2e_mvp.py` | **47 / 47 passed** |
| `scripts/run_integrated_post_confirmation_mvp.py` | **56 / 56 passed** |

The SQLite `execution_events` table is not initialized by default, so the event logger emits warnings during the B+M E2E demo. This does not affect the core workflow results. Run `python scripts/init_db.py` before the demo to resolve this.

---

## What Giraffe Agent Is Not

- a chatbot wrapper
- a supplier directory
- a static procurement form
- a generic workflow automation script
- a financial settlement system in the current public MVP

Trade finance workflow support is a long-term direction, not an implemented feature.

---

## Repository Structure

```
giraffe-agent/
├── api/                        # FastAPI application (health, skill invocation, B/M side routes)
│   └── main.py
├── src/
│   ├── b_side/                 # AI Buyer: requirement parser, inquiry drafter, feasibility engine
│   ├── m_side/                 # Supplier Response Agent, Role-Switching Agent, upstream logic
│   │   ├── upstream/           # Inquiry builder, dispatch, response parser, option engine, approval gate
│   │   ├── rollup/             # SupplierResponseRollup builder
│   │   ├── professional_free/  # CAD↔CNC matching (no Enterprise CAP)
│   │   └── dependencies/       # Upstream dependency planner
│   ├── bm_bridge/              # Inquiry dispatcher, response bridge, order bridge
│   ├── merchandiser/           # Post-confirmation execution engine
│   ├── actors/                 # Neutral actor model, role resolver
│   ├── projects/               # Project graph and procurement edges
│   ├── logistics/              # Logistics ingestion and normalization
│   ├── channels/               # WeChat / WhatsApp / Web adapters
│   ├── core_schema/            # Pydantic types for B-side and M-side
│   ├── db/                     # SQLAlchemy models, Alembic config
│   └── legal/                  # Patent notice module
├── scripts/                    # Setup, seed, and E2E verification scripts
├── alembic/                    # Database migrations
├── tests/fixtures/             # JSON fixtures for actors, projects, logistics, role switching
├── data/                       # Runtime workspace files and execution event log
├── PATENT_NOTICE.md
├── LICENSE_NOTICE.md
└── pyproject.toml
```

---

## Roadmap

- [ ] PostgreSQL persistence (SQLAlchemy models are already JSONB-portable)
- [ ] API authentication middleware
- [ ] Frontend visualization for delivery paths and Gantt-style execution plans
- [ ] Supplier Memory — persistent supplier performance history fed into feasibility scoring
- [ ] Real LLM calls replacing rule-based stubs in `requirement_structurer.py` and `inquiry_drafter.py`
- [ ] Logistics API ingestion (carrier webhook normalization)
- [ ] Private / self-hosted deployment packaging
- [ ] Trade document verification
- [ ] Trade finance workflow support (future extension)

---

## How to Contribute

Giraffe Agent is an open MVP. Good starting points:

**Core algorithms**
- Add real LLM calls to `src/b_side/requirement_structurer.py` and `src/b_side/inquiry_drafter.py`
- Extend the Industrial Execution Graph with richer event types and replay/query APIs
- Add pytest unit tests for individual modules in `tests/`

**Channels**
- Wire up real WeChat or WhatsApp webhook adapters in `src/channels/`

**Matching and intelligence**
- Improve CAD↔CNC capability matching scoring in `src/m_side/professional_free/cad_cnc_matcher.py`
- Add supplier memory retrieval into the feasibility simulation

**Production / ops**
- Migrate from SQLite to PostgreSQL
- Add authentication middleware to the FastAPI app
- Build a buyer-facing or supplier-facing web UI

Before submitting a pull request, run all E2E scripts and confirm they still pass.

---

## Design Constraints

Non-negotiable product invariants — do not work around them:

- **Neutral Actor Model:** Never hardcode B-side / M-side as a fixed actor identity. Roles are contextual per `Project` + `ProcurementEdge`.
- **No Enterprise CAP in MVP:** The Professional Free tier has no file encryption, dynamic watermarking, secure viewer, or no-download rooms.
- **Dynamic Schema Rule:** AI may observe and propose new fields; it must not directly alter physical database table definitions at runtime.
- **No Faked Data:** If parsing is uncertain, surface a clarification request. Never invent order fields.
- **Append-Only Graph:** `execution_events` must never be updated or deleted — only appended to.

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
| Database (target) | PostgreSQL |
| Package manager | `uv` (or pip) |

---

## Patent Notice and License

Certain workflows, role-based participant coordination mechanisms, and multi-party order execution workflows in this project may be covered by patents owned by **Giraffe Technology Holding Limited**:

| Jurisdiction | Patent |
|---|---|
| China | ZL 2023 1 1645939.9 / CN 117670482 B |
| Japan | P7644545 / 特許第7644545号 |

**Global Free Patent License** — Giraffe Technology Holding Limited grants a free patent license to:

- Individuals (developers, researchers, students)
- SMEs (for own procurement, production coordination, and sourcing)
- Educational institutions (teaching, non-commercial use)
- Research institutions (non-commercial research)

**Separate written permission is required for:** enterprise deployment, platform/SaaS operation, high-volume commercial production use, third-party system integration, white-label/OEM/resale, Enterprise CAP, or use of Giraffe commercial assets.

See [`PATENT_NOTICE.md`](PATENT_NOTICE.md) and [`LICENSE_NOTICE.md`](LICENSE_NOTICE.md) for full terms.

**Authorization contact:** mich@giraffe.technology
