# BM DB Integration — v1.1 Hardening Report

**Tag candidate:** `BM_DB_INTEGRATION_V1_1_HARDENING`  
**Date:** 2026-06-13  
**Branch:** `claude/bm-db-integration-reproducible-olu7a0`  
**Prerequisite:** Baseline v1 (`BM_DB_INTEGRATION_BASELINE_V1`) must pass first.

---

## Classification

BM DB Integration Baseline v1 is a reproducible integration baseline, not yet a
production-hardening release.

v1.1 Hardening proves that Baseline v1 remains stable under repeated runs,
incomplete supplier replies, conflicting supplier replies, and full order lifecycle
events. No major new product features were added.

---

## Files Added / Changed

| File | Change |
|------|--------|
| `bm_db_adapter.py` | Added query helpers: `list_project_responses`, `list_inquiry_responses`, `list_project_events`, `list_project_inquiries`, `list_project_edges`, `check_graph_consistency` |
| `bm_db_hardening.py` | New — runs all 8 hardening suites (Baseline v1 regression guard + 7 new suites) |
| `BM_DB_INTEGRATION_V1_1_HARDENING_REPORT.md` | This report |

---

## Bugs Found and Fixed

### Bug 1 — Idempotency test used absolute row counts on a shared DB

**Symptom:** Suite 1 (Idempotency) failed with `Actor duplication: expected 2, got 4`
because the test ran after the Baseline v1 Regression guard, which had already
written 2 actors to the same DB.

**Root cause:** The test asserted `actors == 2` (absolute), but the shared DB
already contained rows from previous suites.

**Fix:** Changed all idempotency assertions to use **delta counts** — snapshot
counts before the test, then assert that run 2 (same project_key) adds zero new
actors and zero new projects compared to run 1.

**After fix:** Suite 1 PASS.

---

## Test Suite Results — Final Run

**Command:**

```bash
python bm_db_hardening.py --db sqlite:///./hardening_test.db
```

**Full output:**

```
==================================================================
BM DB Integration — v1.1 Hardening Suite
DB: sqlite:///./hardening_test.db
==================================================================

--- Baseline v1 Regression ---
    [verify_integration] DB:   sqlite:///./hardening_test.db
[verify_integration] Runs: 5
  run 1/5: PASS  (project=430cbfc3…)
  run 2/5: PASS  (project=2719c55d…)
  run 3/5: PASS  (project=a2e2cb2e…)
  run 4/5: PASS  (project=2737f12c…)
  run 5/5: PASS  (project=2a3d0fe2…)
[verify_integration] PRAGMA integrity_check: ok
[verify_integration] PRAGMA foreign_key_check: ok
[verify_integration] Result: 5/5 passed
  → PASS

--- 1. Idempotency ---
    Run 1 created: +2 actors, +1 projects
    Run 2 (same key) created: +0 actors, +0 projects
    Sub-entity note: requirements/inquiries/edges are per-submission
      (after run1=6, after run2=7). Actor-level and project-level idempotency confirmed.
    run_id isolation: each submission creates a new sub-entity set;
      use a distinct project_key to isolate full submissions.
  → PASS

--- 2. Incomplete Supplier Reply ---
    3 partial responses stored; all missing fields are None
    risk_flags_json set on all incomplete responses
    No placeholder values (999) found
  → PASS

--- 3. Conflicting Supplier Reply ---
    Original quote ($9.00/60d) preserved as supplier_response row
    Revised quote ($7.50/45d) stored as second supplier_response row
    Edge.response_id updated to latest revision
    Revision traced in execution_events payload_json
  → PASS

--- 4. Full Order Lifecycle ---
    Event sequence: [ORDER_CONFIRMED, PRODUCTION_UPDATE_RECEIVED,
      PRODUCTION_UPDATE_RECEIVED, QC_UPDATE_RECEIVED, EXCEPTION_REPORTED,
      LOGISTICS_HANDOVER_RECEIVED, ORDER_CLOSED]
    Timeline reconstructible: ORDER_CONFIRMED → ORDER_CLOSED
  → PASS

--- 5. Graph Consistency ---
    check_graph_consistency returned no issues
    edges=1, inquiries=1, responses=1
    inquiry_id and response_id back-fill verified
  → PASS

--- 6. DB-off / DB-on Parity ---
    DB-off result: {supplier_name: ParitySupplier Ltd, can_supply: True,
      price: 8.75, lead_time_days: 35, can_accept_order: True,
      edge_status: APPROVED, inquiry_linked: True, response_linked: True}
    DB-on result:  {same}
    All business fields match between modes
  → PASS

--- 7. Five-run Reproducibility ---
    run 1/5: PASS  run 2/5: PASS  run 3/5: PASS
    run 4/5: PASS  run 5/5: PASS
    PRAGMA integrity_check: ok
    PRAGMA foreign_key_check: ok
  → PASS

==================================================================
SUMMARY
==================================================================
  ✓  Baseline v1 Regression
  ✓  1. Idempotency
  ✓  2. Incomplete Supplier Reply
  ✓  3. Conflicting Supplier Reply
  ✓  4. Full Order Lifecycle
  ✓  5. Graph Consistency
  ✓  6. DB-off / DB-on Parity
  ✓  7. Five-run Reproducibility

  8/8 suites passed
==================================================================
```

---

## Suite-by-Suite Findings

### Baseline v1 Regression Guard

`verify_integration.py --db sqlite:///./hardening_test.db --runs 5` executed as
sub-process before any hardening suites modify the DB. Passed 5/5 with clean
PRAGMA checks. Baseline v1 is stable.

---

### Suite 1 — Idempotency

**What was tested:**
- Same buyer name + supplier name + `project_key` submitted twice.
- Delta counts measured between run 1 and run 2.

**Findings:**

| Entity | Run 1 delta | Run 2 delta (same key) | Expected |
|--------|:-----------:|:----------------------:|----------|
| actors | +2 | 0 | ✓ idempotent |
| projects | +1 | 0 | ✓ idempotent |
| structured_requirements | +1 | +1 | ✓ per-submission |
| supplier_inquiries | +1 | +1 | ✓ per-submission |
| procurement_edges | +1 | +1 | ✓ per-submission |

**run_id isolation rule documented:** Actors and projects are idempotent by
`(name, actor_type)` and `(buyer_id, product_summary)` respectively.
Sub-entities (requirements, inquiries, edges, responses) are per-submission;
use a distinct `project_key` to obtain full isolation of a re-submission.

---

### Suite 2 — Incomplete Supplier Reply

**Scenario:**
- Supplier A: price given, `lead_time_days=None`
- Supplier B: lead_time given, `price=None`
- Supplier C: only "can do", all commercial fields `None`

**Findings:**

| Supplier | price | lead_time_days | risk_flags_json | Hallucination |
|----------|-------|---------------|-----------------|---------------|
| A | $6.20 | `None` | `missing_fields: [lead_time_days]` | None |
| B | `None` | 28 | `missing_fields: [price]` | None |
| C | `None` | `None` | `missing_fields: [price, lead_time_days], incomplete_response: true` | None |

No placeholder values (e.g. `999`) were inserted. No data was invented.
All 3 `supplier_response` rows were created successfully.

---

### Suite 3 — Conflicting Supplier Reply (Quote Revision)

**Scenario:**
- Supplier original quote: $9.00/pc, 60-day lead time
- Supplier revised quote: $7.50/pc, 45-day lead time (same inquiry)

**Findings:**

- Both responses preserved as separate `supplier_responses` rows (response_v1 + response_v2).
- `procurement_edges.response_id` updated to point to the latest revision (v2).
- Original row (v1) remains in DB — commercial evidence not overwritten.
- Revision event recorded in `execution_events` with `payload_json`:
  ```json
  {
    "event": "quote_revision",
    "original_response_id": "...",
    "revised_response_id": "...",
    "original_price": 9.00,
    "revised_price": 7.50,
    "original_lead_days": 60,
    "revised_lead_days": 45
  }
  ```

**Audit trail is complete.** No commercial evidence was silently overwritten.

---

### Suite 4 — Full Order Lifecycle

**Event sequence verified:**

| # | Event type | Payload key |
|---|------------|-------------|
| 1 | `ORDER_CONFIRMED` | `milestone: order_placed` |
| 2 | `PRODUCTION_UPDATE_RECEIVED` | `milestone: cutting_started, pct: 20` |
| 3 | `PRODUCTION_UPDATE_RECEIVED` | `milestone: sewing_complete, pct: 80` |
| 4 | `QC_UPDATE_RECEIVED` | `result: pass, defect_rate: 0.008` |
| 5 | `EXCEPTION_REPORTED` | `reason: trim_delay, delay_days: 3` |
| 6 | `LOGISTICS_HANDOVER_RECEIVED` | `tracking: SF1234567890` |
| 7 | `ORDER_CLOSED` | `status: closed_ok` |

Timeline can be reconstructed from `execution_events` ordered by `created_at`.
First event: `ORDER_CONFIRMED`. Last event: `ORDER_CLOSED`. No gaps.

All events carry `project_id`, `edge_id`, and `actor_id`.

---

### Suite 5 — Procurement Graph Consistency

`check_graph_consistency(project_id)` returned **no issues**. Verified:

- Every `supplier_inquiry.edge_id` references an existing `procurement_edge`.
- Every `supplier_response.inquiry_id` references an existing `supplier_inquiry`.
- Every `APPROVED` edge has both `inquiry_id` and `response_id` set.
- No dangling references.

---

### Suite 6 — DB-off / DB-on Parity

Identical scenario run in both modes. Business outcome comparison:

| Field | DB-off | DB-on | Match |
|-------|--------|-------|-------|
| supplier_name | ParitySupplier Ltd | ParitySupplier Ltd | ✓ |
| can_supply | True | True | ✓ |
| price | 8.75 | 8.75 | ✓ |
| lead_time_days | 35 | 35 | ✓ |
| can_accept_order | True | True | ✓ |
| edge_status | APPROVED | APPROVED | ✓ |
| inquiry_linked | True | True | ✓ |
| response_linked | True | True | ✓ |

DB-on adds persistence and auditability. Business logic output is identical.

---

### Suite 7 — Five-run Reproducibility

5 independent lifecycle runs on the hardening DB:

| Run | Result |
|-----|--------|
| 1/5 | PASS |
| 2/5 | PASS |
| 3/5 | PASS |
| 4/5 | PASS |
| 5/5 | PASS |

```
PRAGMA integrity_check:  ok
PRAGMA foreign_key_check: ok
```

---

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Baseline v1 tests still pass | PASS |
| v1.1 hardening tests pass 5/5 | PASS (8/8 suites, all reproducible) |
| No silent hallucination or invented supplier fields | PASS — all missing fields stored as `None`; no placeholder values |
| DB graph can reconstruct the B/M-side order execution timeline | PASS — `ORDER_CONFIRMED` → `ORDER_CLOSED` with full intermediate events |

---

## Known Limitations (Remaining for v1.2+)

1. **Upstream dependency chains not covered** — M → fabric/trim/subcontract supplier
   loops are not exercised in any v1.1 suite.
2. **Role-switching not tested** — `MAIN_M_SIDE` ↔ `UPSTREAM_B_SIDE` transitions
   are not part of the hardening scenarios.
3. **CAD/CNC rollup not covered** — `CapabilityFitReport` and
   `CADCNCMatchResult` rows are not created or asserted in any suite.
4. **PostgreSQL not tested** — all suites run against SQLite only.
5. **Concurrent write scenarios not covered** — idempotency is validated for
   single-threaded sequential runs only.
6. **Execution graph replay not implemented** — reading from DB to reconstruct
   a human-readable timeline is out of scope for v1.1 (targeted for v1.2).
7. **Decision packet not implemented** — buyer-facing recommendation output with
   evidence traceability is out of scope for v1.1 (targeted for v1.2).
