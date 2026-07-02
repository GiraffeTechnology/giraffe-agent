# Giraffe Agent

> Open-core industrial execution infrastructure for private-domain procurement, cross-border trade execution, supplier coordination, QC evidence, and auditable order orchestration.
>
> Industrial Execution Graph + Neutral Actor Model + giraffe-language-skill + giraffe-db facts + GPM/GLTG feasibility models + OpenClaw-compatible channel runtime + human approval.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-ready-green)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-purple)](https://docs.pydantic.dev/)
[![uv](https://img.shields.io/badge/uv-supported-black)](https://docs.astral.sh/uv/)
[![License](https://img.shields.io/badge/license-Apache--2.0-lightgrey)](LICENSE)

---

## What Is Giraffe Agent?

Giraffe Agent is the open-core orchestration reference implementation for the Giraffe industrial AI system.

It converts fragmented trade communication into structured, auditable, human-confirmable execution state. It is designed for apparel and textile procurement, cross-border supplier coordination, RFQ execution, quotation comparison, lead-time feasibility, order follow-up, QC evidence handling, logistics tracking, and private-domain business memory.

Giraffe Agent is not a generic chatbot, CRM, ERP, supplier directory, marketplace, or one-off demo.

It is an industrial execution infrastructure layer that sits between:

```text
communication channels
language canonicalization
private-domain business facts
deterministic feasibility models
LLM-assisted reasoning and drafting
human approval
append-only execution records
```

The core output is an **Industrial Execution Graph**: an append-only record of requirements, supplier inquiries, quotations, delivery assumptions, approvals, production events, QC evidence, logistics updates, exceptions, and sign-off decisions.

---

## Current Repository Status

```text
package: giraffe-agent
version: 0.1.0
python: >=3.11
runtime: FastAPI / SQLAlchemy / Pydantic v2 / httpx
role: open-core orchestration reference
```

Current local validation recorded in this repository:

```text
unit tests: 525 passed
B-side independent flow: PASS
M-side independent flow: PASS
B/M E2E: PASS
AI Merchandiser post-confirmation: PASS
Logistics ingestion: PASS
QC Intelligence interface: PASS
QC mock fallback: PASS
OpenClaw IM simulated events: PASS
DB-off mode: PASS
DB-on mode: PASS
3x clean-state validation: PASS
```

Repository-local verdict:

```text
PASS WITH GAPS
```

Internal mock paths and repository interfaces pass. Production integrations still require live OpenClaw, model providers, giraffe-db, GLTG, and channel credentials.

---

## Ecosystem Boundary

| Component | Responsibility | Repository / boundary |
|---|---|---|
| **giraffe-language-skill** | P0 canonical English language boundary and localized output rendering | `GiraffeTechnology/giraffe-language-skill` |
| **giraffe-db** | Private business facts, evidence, behavior snapshots, lead-time observations, GLTG/GPM context | `GiraffeTechnology/giraffe-db` |
| **GLTG** | Lead-time simulation, P50/P80/P90 quantiles, behavioral/statistical lead-time adjustment, fallback/manual-review flags | `GiraffeTechnology/GLTG` |
| **GPM** | Procurement graph reasoning, known-suppliers-first planning, fallback procurement logic | Model/service boundary |
| **AIVAN** | Standalone AI trade execution worker for private-domain RFQ execution | `GiraffeTechnology/aivan` |
| **giraffe-agent** | Open-core orchestration reference, Neutral Actor Model, B/M workflows, Industrial Execution Graph | This repository |
| **abcdYi** | Apparel/textile B2M industry edition | `GiraffeTechnology/abcdYi` |
| **Giraffe-JP** | Merchant-owned C-B-M backend deployment package | `GiraffeTechnology/Giraffe-JP` |
| **giraffe-qc-model** | Visual QC training, rule learning, sample learning, readiness gates, Pad/Server QC runtime | `GiraffeTechnology/giraffe-qc-model` |
| **OpenClaw** | Channel/account runtime and normalized event bridge | OpenClaw / Giraffe fork boundary |

Strict product split:

```text
language normalization lives in giraffe-language-skill
facts live in giraffe-db
simulation lives in GLTG / GPM
execution lives in AIVAN and giraffe-agent workflows
connectivity lives in OpenClaw or compatible runtime
legal/commercial responsibility remains human
```

---

## P0 Language Boundary

Standard English is the only internal working language across Giraffe products.

All raw multilingual user, operator, buyer, supplier, QC, IM, email, and marketplace input must pass through `giraffe-language-skill` before product workflow code extracts business fields, routes suppliers, runs GLTG, writes graph data, creates QC test points, generates decision packets, or creates outbound drafts.

Allowed path:

```text
raw multilingual input
-> giraffe-language-skill
-> canonical English packet
-> Giraffe Agent workflow
-> giraffe-db / GPM / GLTG / QC integration
-> localized user-facing output
```

Prohibited in this repository:

```text
internal RFQ translation prompts
multilingual city / destination / product / SKU / material / quality alias maps
raw non-English field extraction paths
LLM extraction directly from raw non-English business text
```

If language-skill cannot produce a valid canonical packet, the workflow must block or ask for operator confirmation. It must not guess fields.

---

## Core Execution Chain

```text
User IM / Email / Marketplace input
-> OpenClaw or compatible channel runtime
-> normalized event
-> language boundary check
-> canonical English packet
-> Giraffe Agent workflow router
-> role-aware requirement structuring
-> giraffe-db private-domain lookup
-> GPM procurement-path reasoning
-> GLTG lead-time / delivery-feasibility simulation
-> buyer option generation / supplier inquiry drafting
-> human approval gate
-> authorized outbound execution
-> order execution state
-> AI Merchandiser follow-up
-> QC evidence ingestion / QC service call
-> logistics / exception tracking
-> buyer sign-off
-> Supplier Memory / giraffe-db update
-> append-only Industrial Execution Graph
```

The LLM may classify, summarize, explain, and draft. It must not become the fact source, language boundary, lead-time calculator, QC judge, or legal decision-maker.

---

## Neutral Actor Model

Do not treat B-side and M-side as permanent identities.

An actor's role is contextual. It depends on the project, procurement edge, and counterparty.

| Role | Meaning |
|---|---|
| `MAIN_M_SIDE` | Main supplier to the original buyer |
| `UPSTREAM_B_SIDE` | Same manufacturer acting as buyer to upstream suppliers |

Example:

```text
Buyer B -> Manufacturer M
M is MAIN_M_SIDE to B.

Manufacturer M -> Fabric Supplier F1
M is UPSTREAM_B_SIDE to F1.
```

Every workflow is project-aware and edge-aware.

---

## GLTG Integration Status

GLTG is a standalone service:

```text
https://github.com/GiraffeTechnology/GLTG
```

Current giraffe-agent integration:

```text
src/integrations/gltg_client.py
src/integrations/gltg_leadtime.py
```

Current v1 environment:

```bash
GLTG_API_BASE_URL=http://localhost:8090
GLTG_API_TIMEOUT_SECONDS=30
```

Current v1 client endpoints:

```text
GET  /health
GET  /version
POST /v1/lead-time/estimate
POST /v1/paths/enumerate
POST /v1/reforecast
```

Current contract:

```text
giraffe-agent builds payloads only
GLTG service owns lead-time math
giraffe-agent does not calculate lead time locally
giraffe-agent does not silently fall back when GLTG fails
P80 is the conservative feasibility basis
```

---

## GLTG v2 Porting Target

The active GLTG iteration upgrades the model into a behavior-aware, statistically calibrated lead-time forecast.

Target:

```text
model_version: gltg-hybrid-v0.1.0
rule_version: behavior-rules-v0.1.0
```

Target v2 endpoints:

```text
POST /v2/lead-time/simulate
POST /v2/paths/enumerate
POST /v2/reforecast
```

Future giraffe-agent changes should map:

```text
gltg_run_id
model_version
rule_version
p50_days
p80_days
p90_days
supplier_response_buffer_days
supplier_uncertainty_buffer_days
buyer_decision_buffer_days
deadline_risk_level
fallback_supplier_required
manual_review_required
explanation_json
source_observation_ids
```

Release gate:

```text
v1 regression tests pass
v2 DTOs exist
v2 mock transport tests exist
source observation IDs are preserved
no local lead-time math is added
no silent fallback is added
no LLM-generated lead-time replacement is added
```

---

## giraffe-db Boundary

giraffe-db stores canonical private-domain business facts and evidence.

Giraffe Agent should query giraffe-db through explicit adapters or APIs. It must not reconstruct facts from general LLM knowledge.

Important data classes:

```text
customers / buyers
suppliers
RFQs
quotes
orders
leadtime observations
supplier capacity snapshots
communication events
behavior observations
buyer / supplier behavior snapshots
buyer-supplier pair metrics
execution events
GLTG simulation runs
GPM decision packets
audit records
```

Synthetic data must remain clearly labeled synthetic.

---

## QC Boundary

QC capability belongs to `giraffe-qc-model`.

Giraffe Agent may ingest QC evidence, request QC inspection, record QC reports, route corrective feedback, and append QC events. It must not fake QC pass/fail results.

QC requirement text in non-English must also pass through `giraffe-language-skill` before detection points, rule proposals, or decision packets are created.

---

## AIVAN Boundary

AIVAN is the standalone AI trade execution worker.

AIVAN owns:

```text
OpenClaw Gateway / WeChat bot bridge
private-domain RFQ intake
buyer inquiry parsing
giraffe-language-skill enforcement
giraffe-db lookup
GLTG call orchestration
supplier inquiry drafts
human approval prompts
approved outbound execution
AIVAN-specific deployment status
```

Stable AIVAN capabilities can later be ported into this repository as framework patterns.

---

## Install

```bash
git clone https://github.com/GiraffeTechnology/giraffe-agent.git
cd giraffe-agent
python -m pip install -e .
```

With `uv`:

```bash
uv sync
```

Environment:

```bash
cp .env.example .env

GIRAFFE_DB_MODE=off
GLTG_API_BASE_URL=http://localhost:8090
GLTG_API_TIMEOUT_SECONDS=30
# GIRAFFE_LANGUAGE_SKILL_BASE_URL=http://localhost:8780
```

Channel credentials belong to OpenClaw or the relevant channel runtime, not this repository.

---

## Tests

```bash
pytest
```

GLTG-specific tests currently include:

```text
tests/test_gltg_client.py
tests/test_gltg_client_integration.py
tests/test_feasibility_uses_gltg_api.py
tests/test_aivan_buyer_options_use_gltg.py
```

Required future language-boundary tests:

```text
non-English input calls giraffe-language-skill first
non-English input without valid canonical packet is blocked
local LLM never receives raw non-English business text
deterministic fallback does not canonicalize raw non-English fields
localized output is separate from canonical English state
static guards reject multilingual alias maps inside giraffe-agent
```

---

## Commercial / IP Positioning

Giraffe Agent is part of Giraffe Technology's industrial procurement and cross-border supply-chain AI infrastructure.

The broader company scope includes:

```text
industrial procurement execution
cross-border supply-chain AI infrastructure
high-quality data cleaning
data asset management
computing-power operation
private deployment
```

---

## License

See `LICENSE`.
