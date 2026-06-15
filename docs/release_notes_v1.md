# Release Notes — Giraffe Agent v1.0.0

**Release Date:** 2026-06-15
**Codename:** Apparel & Textile Industry Edition

---

## Overview

Giraffe Agent v1.0.0 is the first production-ready release of the C2M (Customer-to-Manufacturer) apparel and textile order execution platform. This release implements the full order lifecycle from buyer inquiry to buyer sign-off, with an append-only Industrial Execution Graph audit trail throughout.

---

## What's New in v1.0.0

### Core Order Lifecycle (Iter 5)
- 12-state order state machine from `DRAFT_FROM_APPROVED_QUOTE` to `BUYER_SIGNED_OFF`
- Order creation from approved supplier quotes
- Order confirmation and production kickoff
- Parallel + sequential lead time calculation (no sentinel values)
- Decision packets with up to 3 comparison options (best/fastest/cheapest)
- Risk flag detection for deadlines, pricing, and capacity

### Participant Matching Engine (Iter 4)
- 12-dimension scoring: category fit, fabric capability, quantity, MOQ, capacity, lead time, location, trade terms, quality history, on-time delivery, response quality, risk penalty
- Supplier memory integration (QC pass rate, on-time delivery, quality issue count)
- Risk flags: no history, low QC pass rate, late delivery history, approaching replacement threshold, incomplete profile
- RFQ workflow with approval gates (9-state RFQ state machine)

### Production Monitoring (Iter 6)
- 12-milestone production tracking (SAMPLE_CONFIRMATION through BUYER_SIGN_OFF)
- Delay predictor: ON_TRACK / LOW / MEDIUM / HIGH / CRITICAL risk levels
- Expedite alert creation on HIGH/CRITICAL — requires human approval before sending
- Production monitoring view with all milestone details

### Quality Control (Iter 6)
- QC standards per order (linked to locked dynamic form)
- QC record evaluation: defects, label compliance, packaging compliance, size deviation, color difference
- QC_PASSED → READY_TO_SHIP transition
- QC_FAILED → QualityIncident creation
- Replacement alert at 3 quality incidents (REPLACEMENT_THRESHOLD)

### Logistics and Delivery (Iter 6)
- Shipment creation (enforces READY_TO_SHIP status)
- Tracking events: DEPARTED, IN_TRANSIT, ARRIVED, DELIVERED, etc.
- DELIVERED event → order transitions to DELIVERED
- Buyer sign-off → BUYER_SIGNED_OFF + SupplierMemory update

### Industrial Execution Graph (Iter 7)
- 31 event types covering all platform actions
- Append-only audit trail (no updates/deletes)
- Query API: by project, order, participant, or event ID
- Chronological ordering guaranteed

---

## API Routes Added in v1.0.0

| Method | Path | Description |
|---|---|---|
| GET | `/api/execution-graph/projects/{id}` | Project events |
| GET | `/api/execution-graph/orders/{id}` | Order events |
| GET | `/api/execution-graph/participants/{id}` | Participant events |
| GET | `/api/execution-graph/events/{id}` | Single event |
| PATCH | `/api/milestones/{id}` | Update milestone |
| POST | `/api/orders/{id}/run-delay-prediction` | Run delay prediction |
| GET | `/api/orders/{id}/production-monitoring` | Production monitoring view |
| POST | `/api/orders/{id}/production-updates` | Add production update |
| POST | `/api/orders/{id}/qc-standards` | Create QC standard |
| POST | `/api/orders/{id}/qc-records` | Submit QC record |
| GET | `/api/orders/{id}/qc-records` | List QC records |
| POST | `/api/orders/{id}/shipments` | Create shipment |
| POST | `/api/shipments/{id}/tracking-events` | Add tracking event |
| GET | `/api/shipments/{id}` | Get shipment with events |
| POST | `/api/orders/{id}/buyer-sign-off` | Buyer sign-off |

---

## Test Results

- 98/98 automated tests pass (API + unit)
- 7 test files covering all platform modules

---

## Known Limitations

- LLM provider defaults to `LocalStub` (no real LLM calls without API key)
- No real-time WebSocket notifications
- Single-tenant per registration (no admin tenant management UI)
- Tracking event delivery detection is based on event_type strings only

---

## Upgrade Notes

This is the initial release. No migration from a previous version is required.

Run `alembic upgrade head` after cloning to initialize the database schema.

---

## Patents

This software may be covered by patents held by Giraffe Technology Holding Limited. See `PATENT_NOTICE.md` for the global free patent license terms.

CN ZL 2023 1 1645939.9 / CN 117670482 B
JP P7644545 / 特許第7644545号
