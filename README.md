# Giraffe Agent

> Open-core industrial execution infrastructure for private-domain procurement, cross-border trade execution, supplier coordination, QC evidence, and auditable order orchestration.
>
> Industrial Execution Graph + Neutral Actor Model + Giraffe DB facts + GPM/GLTG feasibility models + OpenClaw-compatible channel runtime + human approval.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-ready-green)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-purple)](https://docs.pydantic.dev/)
[![uv](https://img.shields.io/badge/uv-supported-black)](https://docs.astral.sh/uv/)
[![License](https://img.shields.io/badge/license-Apache--2.0-lightgrey)](LICENSE)

---

## What Is Giraffe Agent?

Giraffe Agent is the open-core orchestration layer of the Giraffe industrial AI system.

It converts fragmented trade communication into structured, auditable, human-confirmable execution state. It is designed for apparel and textile procurement, cross-border supplier coordination, RFQ execution, quotation comparison, lead-time feasibility, order follow-up, QC evidence handling, logistics tracking, and private-domain business memory.

Giraffe Agent is not a generic chatbot, CRM, ERP, supplier directory, marketplace, or one-off demo.

It is an **industrial execution infrastructure layer** that sits between:

```text
communication channels
private-domain business facts
deterministic feasibility models
LLM-assisted reasoning and drafting
human approval
append-only execution records
```

The core output is an **Industrial Execution Graph**: an append-only record of requirements, supplier inquiries, quotations, delivery assumptions, approvals, production events, QC evidence, logistics updates, exceptions, and sign-off decisions.

---

## Current Repository Status

This repository is the **open-core orchestration reference implementation**.

Current package metadata:

```text
package: giraffe-agent
version: 0.1.0
python: >=3.11
runtime: FastAPI / SQLAlchemy / Pydantic v2 / httpx
```

Current local validation status recorded in this repository:

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

Meaning: internal interfaces and mock paths pass, but production integrations require live credentials, deployed services, and cross-repository validation.

---

## Ecosystem Boundary

Giraffe Agent coordinates the broader Giraffe industrial AI stack. It must not silently absorb every downstream product, runtime, database, or model.

| Component | Responsibility | Boundary |
|---|---|---|
| **giraffe-agent** | Open-core orchestration, Neutral Actor Model, B/M-side workflows, Industrial Execution Graph, reference adapters | This repository |
| **AIVAN** | Standalone AI trade salesperson for private-domain RFQ execution, OpenClaw Gateway intake, buyer/supplier workflow, draft generation, human approval | `GiraffeTechnology/aivan` |
| **giraffe-db** | Private-domain facts: RFQs, quotes, supplier history, buyer/supplier behavior snapshots, lead-time observations, execution evidence | `GiraffeTechnology/giraffe-db` |
| **GLTG** | Lead-time simulation, P50/P80/P90 quantiles, behavioral/statistical lead-time adjustment, fallback/manual-review flags | `GiraffeTechnology/GLTG` |
| **GPM** | Procurement graph reasoning, supplier-set feasibility, known-suppliers-first path logic, fallback planning | Model/service boundary |
| **abcdYi** | Apparel/textile application layer aligned with the Giraffe C2M patent family | Separate application repository |
| **giraffe-qc-model** | AI-native QC inference, standard photos, inspection requirements, detection points, Pad/Server runtime | `GiraffeTechnology/giraffe-qc-model` |

The product boundary should remain:

```text
facts live in giraffe-db
simulation lives in GLTG / GPM
execution lives in AIVAN and giraffe-agent workflows
connectivity lives in OpenClaw or compatible channel runtime
legal/commercial approval lives with humans and legal entities
```

---

## Core Execution Chain

```text
User IM / Email / Marketplace input
-> OpenClaw or compatible channel runtime
-> normalized event
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

The LLM is allowed to classify, summarize, explain, and draft. It must not become the fact source, the lead-time calculator, the QC judge, or the legal decision-maker.

---

## Product Principles

### 1. Conversation is the real interface

Industrial trade does not start in a clean SaaS form. It starts in WeChat, WhatsApp, DingTalk, LINE, email, voice notes, drawings, photos, PDFs, screenshots, spreadsheets, and informal buyer messages.

Giraffe Agent works through normalized channel events, not through fragile direct platform credential handling.

### 2. Private-domain data is the source of truth

The LLM must not invent supplier facts, customer history, historical prices, lead-time history, approval history, buyer behavior, supplier behavior, or user preference memory.

Those facts must come from `giraffe-db` or from explicitly provided evidence.

### 3. Deterministic models calculate feasibility

Lead-time, delivery feasibility, supplier path ranking, and risk buffers must not be guessed by the LLM.

GLTG and GPM own the calculations. The LLM may explain their outputs, but it must not replace them.

### 4. Roles are contextual, not fixed

A company can be a supplier in one edge and a buyer in another edge. Giraffe Agent uses the Neutral Actor Model instead of hardcoding permanent B-side and M-side identities.

### 5. Evidence matters more than promises

Supplier-stated lead time is preserved as evidence but not trusted blindly.

Delivery feasibility must consider material, trims, packaging, subcontracting, production, QC, logistics, supplier behavior, buyer behavior, and historical reliability.

### 6. QC must inspect confirmed detection points

QC must compare actual visual evidence against approved standards and inspection points. It must not infer pass/fail from general language alone.

### 7. Human approval is mandatory for high-stake actions

The system may draft, recommend, and route. It must not commit legally or commercially without human approval.

---

## Neutral Actor Model

> Do not treat B-side and M-side as permanent identities.

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

Every workflow is project-aware and edge-aware. This enables recursive supply-chain execution instead of a flat buyer/supplier form.

---

## GLTG Integration Status

GLTG is now a standalone service:

```text
https://github.com/GiraffeTechnology/GLTG
```

Current giraffe-agent integration:

```text
src/integrations/gltg_client.py
src/integrations/gltg_leadtime.py
```

Current environment variables:

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
giraffe-agent adapter builds payloads only
GLTG service owns lead-time math
giraffe-agent does not calculate lead time locally
giraffe-agent does not silently fall back when GLTG fails
GLTG failures surface as structured errors
P80 is the conservative feasibility basis
```

Current adapter behavior:

```text
v1 output p50_days -> LeadTimePath.p50_lead_time_days
v1 output p80_days -> LeadTimePath.p80_lead_time_days
v1 output p90_days -> LeadTimePath.p90_lead_time_days
v1 output warnings -> risk flags
v1 calculation_trace -> component evidence source
```

---

## GLTG Behavioral + Statistical Model Porting Target

The active GLTG iteration upgrades the model from deterministic v1 lead-time simulation into a behavior-aware, statistically calibrated model.

Target model version:

```text
gltg-hybrid-v0.1.0
```

Target rule version:

```text
behavior-rules-v0.1.0
```

Target v2 endpoints:

```text
POST /v2/lead-time/simulate
POST /v2/paths/enumerate
POST /v2/reforecast
```

This repository should port the same contract after AIVAN validates it first.

Required future changes in giraffe-agent:

```text
src/integrations/gltg_client.py
src/integrations/gltg_leadtime.py
src/b_side/feasibility_engine.py
src/m_side/rollup/supplier_response_rollup.py
buyer option generation tests
E2E trade salesperson flow tests
```

Required future test fixtures:

```text
tests/fixtures/gltg_v2_simulation_request.json
tests/fixtures/gltg_v2_simulation_response.json
```

v2 must preserve the same boundary:

```text
GLTG service owns simulation
giraffe-agent adapter owns mapping only
no local lead-time math
no silent fallback
no LLM-generated lead-time replacement
```

---

## Target GLTG v2 Data Contract

GLTG v2 should consume behavior-aware inputs from giraffe-db:

```text
communication_events
behavior_observations
buyer_behavior_feature_snapshots
supplier_behavior_feature_snapshots
buyer_supplier_behavior_metrics
leadtime_observations
rfq_outcomes
supplier_quotes
supplier_quote_line_items
```

GLTG v2 should return or persist:

```text
gltg_run_id
model_version
rule_version
calibration_version
quantiles.p50_days
quantiles.p80_days
quantiles.p90_days
components.base_production_days
components.base_procurement_days
components.supplier_response_buffer_days
components.supplier_uncertainty_buffer_days
components.buyer_decision_buffer_days
components.logistics_buffer_days
components.risk_buffer_days
risk.deadline_risk_level
risk.confidence_score
risk.fallback_supplier_required
risk.manual_review_required
risk.deadline_feasible
risk.selected_confidence_days
explanation_json
warnings
source_observation_ids
```

New fields to map into Giraffe Agent lead-time / option DTOs:

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

---

## Behavioral Signals for GLTG v2

GLTG v2 should not treat lead time as only:

```text
material days + production days + QC days + logistics days
```

It should adjust forecasts using behavior signals such as:

```text
supplier response delay ratio
business-hours delay ratio
quote completeness score
missing quote fields
quote revision count
lead-time revision count
upstream confirmation signal
supplier current load signal
historical on-time delivery rate
historical quoted-vs-actual error
buyer requirement change count
buyer requirement volatility
buyer decision delay score
buyer response delay ratio
buyer-supplier pair conversion rate
relationship strength score
recommended pairing score
```

Important interpretation rule:

```text
Behavior signals are risk signals, not hard facts.
```

For example, a slow supplier response may indicate low engagement, but it may also indicate upstream material confirmation, holiday, timezone mismatch, capacity pressure, or internal approval.

Therefore, GLTG v2 must explain high-impact adjustments instead of returning an opaque lead-time number.

---

## AIVAN Boundary

AIVAN is the standalone AI trade salesperson product extracted from the broader Giraffe Agent architecture.

AIVAN owns:

```text
OpenClaw Gateway / WeChat bot bridge
private-domain RFQ intake
buyer inquiry parsing
Giraffe DB lookup
GLTG call orchestration
supplier inquiry drafts
human approval prompts
approved outbound execution
AIVAN-specific runtime and deployment status
```

Giraffe Agent should not be the active home for AIVAN runtime fixes, OpenClaw Gateway fixes, ClawHub packaging details, or AIVAN product state.

Stable AIVAN capabilities can later be ported into this repository as framework patterns.

---

## giraffe-db Boundary

giraffe-db is the private-domain business fact layer.

It should store or expose:

```text
customers
buyers
suppliers
supplier products
historical RFQs
historical quotes
leadtime observations
supplier capacity snapshots
communication events
behavior observations
buyer behavior feature snapshots
supplier behavior feature snapshots
buyer-supplier behavior metrics
gltg simulation runs
gltg behavior inputs
pricing decision inputs
execution events
audit records
```

Giraffe Agent should query giraffe-db through explicit adapters or APIs. The LLM must never reconstruct these facts from general knowledge.

Synthetic records from `synthetic_private_v1` must remain clearly labeled as synthetic and must not be represented as real transaction history.

---

## GPM Boundary

GPM is the broader procurement graph model.

GPM answers:

```text
which known suppliers should be tried first
which missing procurement edges create risk
when public bidding or external supplier search is needed
how upstream evidence rolls up into a buyer-facing option
which procurement path is feasible, risky, or blocked
```

GLTG answers:

```text
how many days at P50 / P80 / P90
which behavior changed the forecast
which risk buffers were added
whether fallback supplier is required
whether manual review is required
```

GPM and GLTG are related, but they must not be collapsed into an LLM prompt.

---

## QC Model Boundary

QC capability belongs to `giraffe-qc-model`.

The QC model owns:

```text
sample DB
standard photos
inspection requirements
detection points
ROI definitions
Pad and Server runtime editions
Qwen3-VL-based visual inspection
local-first / fail-closed QC policy
QC result conventions
```

Giraffe Agent may ingest QC evidence, request QC inspection, record returned QC reports, route corrective feedback, and append QC events into the Industrial Execution Graph.

Giraffe Agent must not fake QC pass/fail results.

---

## OpenClaw / IM / Email Boundary

Giraffe Agent is designed as an OpenClaw-compatible skill layer.

```text
WeChat / WhatsApp / DingTalk / LINE / Email / Web / other channels
-> OpenClaw or compatible channel runtime
-> normalized event
-> POST /api/skill/invoke
-> OpenClaw event adapter
-> Giraffe workflow router
```

Giraffe Agent does not directly own IM account login, cookies, session tokens, CAPTCHA bypass, or platform anti-bot bypass.

OpenClaw or a compatible runtime owns channel connectivity. Giraffe Agent owns normalized workflow handling after the event arrives.

---

## Legal and Operating Boundary

Giraffe Agent does not replace the legal parties to a transaction.

It does not become the buyer, seller, manufacturer, freight forwarder, payment obligor, insurer, bank, customs declarant, or contracting party.

Human users and their legal entities remain responsible for:

```text
approving supplier inquiries
confirming quotations
selecting delivery paths
accepting production schedules
approving order commitments
releasing payments
signing contracts
accepting commercial, legal, credit, sanctions, logistics, and quality risk
```

High-stake actions must remain human-confirmed.

---

## Installation

```bash
git clone https://github.com/GiraffeTechnology/giraffe-agent.git
cd giraffe-agent
python -m pip install -e .
```

With development dependencies:

```bash
python -m pip install -e . pytest
```

With `uv`:

```bash
uv sync
```

---

## Environment

Copy the example file:

```bash
cp .env.example .env
```

Core settings:

```bash
GIRAFFE_DB_MODE=off
# GIRAFFE_DB_URL=sqlite:///./giraffe_agent.db

GLTG_API_BASE_URL=http://localhost:8090
GLTG_API_TIMEOUT_SECONDS=30

# DASHSCOPE_API_KEY=your-dashscope-api-key-here
# QWEN_API_KEY=your-qwen-api-key-here
```

Channel credentials should not be placed in this repository. IM/email credentials belong to OpenClaw or the relevant channel runtime.

---

## Running Tests

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

Future GLTG v2 tests should cover:

```text
v2 request builder includes case_context
v2 request builder includes behavior_features when available
v2 request builder includes source_observation_ids
v2 response maps quantiles into existing DTOs
v2 response maps risk and explanation fields
v1 compatibility remains intact
GLTG unavailability surfaces structured error
no local fallback calculation is used
```

---

## Current Known Limitations

1. This repository currently integrates GLTG through v1 HTTP endpoints.
2. GLTG v2 behavioral/statistical simulation is a porting target, not yet the default in this repository.
3. AIVAN production OpenClaw / WeChat bridge status belongs to the `aivan` repository.
4. Canonical private-domain data ownership belongs to `giraffe-db`, not this repository.
5. QC runtime ownership belongs to `giraffe-qc-model`.
6. Real Qwen calls require configured API credentials.
7. Real channel execution requires deployed OpenClaw or compatible runtime.

---

## Release Gate for GLTG v2 Port

Do not mark the GLTG v2 port complete in giraffe-agent until:

1. `GLTG_API_VERSION` is supported.
2. v2 request/response DTOs exist.
3. v2 mock transport tests exist.
4. v1 regression tests still pass.
5. behavior feature payloads are mapped when available.
6. source observation IDs are preserved.
7. P50/P80/P90, buffers, risk, fallback, manual review, and explanation JSON are mapped.
8. no local GLTG math is added.
9. no silent fallback is added.
10. cross-repository fixtures match AIVAN and GLTG.

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

Enterprise deployment, large-scale commercial use, platform operation, white-label resale, third-party system integration, commercial asset use, and sublicensing may require separate written authorization.

---

## License

See `LICENSE`.
