# Giraffe Agent — Architecture

## Overview

Giraffe Agent is a **project-aware, role-switching procurement execution agent**
built for SME industrial supply chains. It provides two AI-assisted execution
layers:

```
AI Buyer        = pre-confirmation decision support   (B-side)
AI Merchandiser = post-confirmation execution support (M-side)
```

Together they form the **Industrial Execution Graph v0.1** — an event-sourced,
project-aware graph that records what *actually happened* in the supply chain.

---

## Core Principle: Neutral Actor Model

> **Do not treat B-side and M-side as fixed identities.**

An actor's role is determined by *context* — the project edge and counterparty —
not by a static actor type. The same manufacturer is simultaneously:

- `MAIN_M_SIDE` — main supplier to the original buyer
- `UPSTREAM_B_SIDE` — buyer to its own fabric/material/subcontract suppliers

```
Buyer B  →  Manufacturer M   (M is MAIN_M_SIDE to B)
Manufacturer M  →  Fabric Supplier F1   (M is UPSTREAM_B_SIDE to F1)
```

Role resolution is implemented in `src/actors/role_resolver.py`.

---

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ IM / OpenClaw Layer                                                 │
│   OpenClaw skill manifest · WeChat / WhatsApp / Web adapters        │
├─────────────────────────────────────────────────────────────────────┤
│ Conversation Orchestration Layer                                    │
│   Session resolution · Role-aware IM router · Intent routing        │
├─────────────────────────────────────────────────────────────────────┤
│ B-side — AI Buyer (pre-confirmation)                                │
│   Requirement structurer · Inquiry drafter · Feasibility engine     │
│   Supplier response intake · Delivery path ranking                  │
├─────────────────────────────────────────────────────────────────────┤
│ B+M Bridge                                                          │
│   Inquiry dispatcher · Response bridge · Order creation             │
├─────────────────────────────────────────────────────────────────────┤
│ M-side — AI Merchandiser (post-confirmation)                        │
│   Workspace management · Response normalizer · Order acknowledger   │
│   Production updates · QC updates · Logistics handover              │
│   Upstream inquiry · Role-switch state machine                      │
├─────────────────────────────────────────────────────────────────────┤
│ Industrial Execution Graph                                          │
│   Event sourcing (JSONL) · Project graph · Supplier memory          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Monorepo Structure

```
giraffe-agent/
├── apps/
│   ├── bside/                  B-side app — AI Buyer
│   │   ├── tests/              B-side pytest suite (222 tests)
│   │   ├── pyproject.toml
│   │   └── run_tests.py        Integration test runner (33 tests)
│   └── mside/                  M-side app — AI Merchandiser
│       ├── tests/              M-side pytest suite (177 tests)
│       ├── pyproject.toml
│       └── run_tests.py
├── src/                        Shared source code
│   ├── b_side/                 B-side core modules
│   ├── m_side/                 M-side core modules
│   ├── bm_bridge/              B↔M bridge
│   ├── actors/                 Neutral actor model
│   ├── channels/               IM channel adapters
│   ├── core_schema/            Shared Pydantic models
│   ├── db/                     SQLAlchemy models + repositories
│   ├── integrations/           External service integrations
│   ├── legal/                  Patent and legal notice handling
│   ├── logistics/              Logistics tracking
│   ├── merchandiser/           Merchandiser state machine
│   ├── openclaw_skill/         OpenClaw skill manifest
│   └── projects/               Project graph models
├── api/                        FastAPI application
├── docs/                       Documentation
├── scripts/                    Development and demo scripts
├── data/                       Runtime JSON file store (gitignored at runtime)
└── alembic/                    Database migrations
```

---

## Data Flow

### B-side (Pre-Confirmation)

```
1. Buyer sends IM message
2. B-side: structure_requirement() → BuyerRequirement
3. B-side: draft_supplier_inquiry() → SupplierInquiryDraft (EN + ZH)
4. B+M Bridge: dispatch_supplier_inquiry() → MSideWorkspace × N
5. M-side: normalize_supplier_response_text() → SupplierResponsePacket
6. B+M Bridge: push_supplier_response_to_b_side() → SupplierResponseRecord
7. B-side: run_feasibility_simulation() → FeasibilityReport (ranked paths)
8. Buyer selects path → order creation
```

### M-side (Post-Confirmation)

```
1. B+M Bridge: create_order_execution_from_selected_path() → OrderExecutionContext
2. M-side: acknowledge_order() → milestone: order_acknowledgement = completed
3. M-side: submit_production_update() → milestone progress
4. M-side: submit_qc_update() → QC confirmation
5. M-side: submit_logistics_update() → shipment created
6. Logistics: tracking events via webhook/IM/API polling
7. Buyer sign-off → order closed → supplier memory updated
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Flat JSON file storage | No external dependencies for MVP |
| Deterministic regex parsing | No LLM required for structured field extraction |
| JSONL event log | Append-only audit trail; survives crashes |
| Pydantic v2 everywhere | Strong validation; clean serialization |
| Bilingual (EN + ZH) | Target market is cross-border industrial procurement |
| OpenClaw skill adapter | Future integration with WeChat mini-program orchestration |

---

## Known Limitations (MVP)

1. **Unknown supplier dispatch** returns HTTP 200 with `ok=true` and `dispatched=0`
   instead of a 404/422 with `missing_supplier_ids`. Fix planned for v0.2.0.
2. **No authentication** on the API server. Do not expose to the internet.
3. **Single-node JSON storage** — not suitable for concurrent multi-user access.
4. **No LLM integration** — all parsing is deterministic regex. LLM layer is
   planned for v0.2.0.

See `docs/ROADMAP.md` for the full plan.
