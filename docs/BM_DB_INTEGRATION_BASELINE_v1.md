# B/M-side DB Integration — Baseline v1

This is a historical implementation baseline. Current data ownership and acceptance follow the source-aligned PRD and the selected private DB contract. Existing fixtures and compatibility code are retained.

**Status:** Baseline v1 — first reproducible result  
**Date:** 2026-06-13  
**Branch:** `claude/bm-db-integration-reproducible-olu7a0`

---

## Summary

This document records the first reproducible end-to-end B/M-side DB integration
baseline for Giraffe Agent.  Prior to this baseline the integration package did
not exist in a runnable form; the five specific failure modes listed below were
identified and resolved.

**Reproducible integration baseline passed; ready for next-stage hardening and
broader scenario testing.**

---

## Failures Resolved

| # | Failure | Resolution |
|---|---------|-----------|
| 1 | `ModuleNotFoundError: pydantic_stub` in `verify_integration.py` | Created `pydantic_stub.py` as a re-export shim for pydantic symbols |
| 2 | `ModuleNotFoundError: src` in `run_bm_e2e_with_db.py` (both modes) | Added explicit `sys.path` fixup at script top; no reliance on caller's working directory |
| 3 | `build_schema.py` used a hard-coded absolute migration path | Rewrote to use `--url` arg or `GIRAFFE_DB_URL` env var; no local paths anywhere |
| 4 | `verify_integration.py` wrote raw SQLite rows, bypassing `bm_db_adapter.py` | Verifier now exercises `BMDbAdapter` exclusively; no direct sqlite3 calls |
| 5 | DB-off mode broken: `bm_db_adapter.py` imported `src.db.*` at module load time | All `src.db.*` imports are lazy — inside `if self._mode == "on":` branches only |

---

## Files Introduced

| File | Purpose |
|------|---------|
| `pydantic_stub.py` | Re-exports `BaseModel`, `Field`, `validator`, `model_validator` from pydantic; provides minimal fallback when pydantic is absent |
| `build_schema.py` | Creates the full DB schema via SQLAlchemy `create_all`; reads URL from `--url` / `GIRAFFE_DB_URL`; no-ops in DB-off mode |
| `bm_db_adapter.py` | Unified adapter: `_mode=on` uses real repositories; `_mode=off` uses `_MemStore` (pure in-memory); all `src.db.*` imports are lazy; provides `get_or_create_actor`, `get_or_create_project` for idempotency; `update_edge` back-fills `inquiry_id`, `response_id`, `status` |
| `run_bm_e2e_with_db.py` | End-to-end runner; handles both DB modes; auto-creates schema in on-mode |
| `verify_integration.py` | Reproducibility verifier; `--db` and `--runs` args; asserts row counts for 8 tables; checks edge FK linkage and edge status; runs PRAGMA checks |

---

## Test Modes

### DB-off mode

This historical fixture mode requires no DB installation and runs in memory. It remains a retained isolated-test utility. It does not satisfy the current requirement that business history and process records use the selected replaceable private DB, and must not be reported as durable product acceptance.
`src.db` is never imported.

```bash
GIRAFFE_DB_MODE=off python run_bm_e2e_with_db.py
```

**Result: PASS**

```
[run_bm_e2e_with_db] mode=off
  actors: buyer=…  supplier=…
  project: …
  counts: {'actors': 2, 'projects': 1, 'structured_requirements': 1,
           'supplier_inquiries': 1, 'supplier_responses': 1,
           'supplier_response_rollups': 1, 'procurement_edges': 1,
           'execution_events': 4}
[run_bm_e2e_with_db] PASS
```

### DB-on mode

Uses real SQLAlchemy repositories backed by SQLite.

```bash
GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db python run_bm_e2e_with_db.py
```

**Result: PASS**

```
[run_bm_e2e_with_db] mode=on
[run_bm_e2e] Schema ready at: sqlite:///./test.db
  actors: buyer=…  supplier=…
  project: …
  counts: {'actors': 2, 'projects': 1, 'structured_requirements': 1,
           'supplier_inquiries': 1, 'supplier_responses': 1,
           'supplier_response_rollups': 1, 'procurement_edges': 1,
           'execution_events': 4}
[run_bm_e2e_with_db] PASS
```

---

## Reproducibility Verification — 5/5 Passes

### Command

```bash
python verify_integration.py --db sqlite:///./test.db --runs 5
```

### Output

```
[verify_integration] DB:   sqlite:///./test.db
[verify_integration] Runs: 5
  run 1/5: PASS  (project=3c3e4942…)
  run 2/5: PASS  (project=ed0665f8…)
  run 3/5: PASS  (project=ac86f18c…)
  run 4/5: PASS  (project=096888a5…)
  run 5/5: PASS  (project=bc7c3460…)
[verify_integration] PRAGMA integrity_check: ok
[verify_integration] PRAGMA foreign_key_check: ok
[verify_integration] Result: 5/5 passed
```

---

## Final Row Counts (after 5 runs)

Actors and supplier actors are idempotent (get-or-create): the same buyer and
supplier are reused across all runs.  Every other table grows by one row per run.

| Table | Rows after 5 runs | Notes |
|-------|:-----------------:|-------|
| `actors` | **2** | Buyer + supplier; idempotent across runs |
| `projects` | **5** | One new project per run |
| `structured_requirements` | **5** | One per project |
| `supplier_inquiries` | **5** | One per project; each linked to its edge |
| `supplier_responses` | **5** | One per inquiry; each linked to its inquiry |
| `supplier_response_rollups` | **5** | One per project |
| `procurement_edges` | **5** | One per project; `inquiry_id` and `response_id` back-filled |
| `execution_events` | **20** | Four per run: `ORDER_CONFIRMED`, `PRODUCTION_UPDATE_RECEIVED`, `QC_UPDATE_RECEIVED`, `LOGISTICS_HANDOVER_RECEIVED` |

---

## Lifecycle Covered Per Run

Each of the five runs exercises the full B/M procurement lifecycle:

1. **Actors** — buyer + main supplier, idempotent `get_or_create_actor`
2. **Project** — unique per run, idempotent `get_or_create_project`
3. **Structured requirement** — category, quantity, material, specs, deadline
4. **Procurement edge** — `BUYER_TO_MAIN_SUPPLIER`, starts `DRAFT`
5. **Supplier inquiry** — linked to edge; `edge_id` FK satisfied before creation
6. **Edge back-fill** — `inquiry_id` written to edge; status advances to `SENT`
7. **Supplier response** — references `inquiry_id`; `can_supply`, price, lead time
8. **Edge back-fill** — `response_id` written to edge; status advances to `RESPONDED`
9. **Supplier response rollup** — aggregates capacity summary; `can_accept_order=True`
10. **Order confirmation** — edge status → `APPROVED`; project status → `ORDER_CONFIRMED`
11. **Execution events** — `ORDER_CONFIRMED`, `PRODUCTION_UPDATE_RECEIVED`, `QC_UPDATE_RECEIVED`, `LOGISTICS_HANDOVER_RECEIVED`

---

## Edge Status Semantics

Order confirmation is represented by `EdgeStatus.APPROVED` (from `src/db/enums.py`).
The term "confirmed" in product language maps to `APPROVED` in the DB enum.  No
new enum value was added; the existing semantics are correct.

---

## DB Integrity Checks

Both PRAGMA checks are run after every 5-run session:

```
PRAGMA integrity_check  → ok
PRAGMA foreign_key_check → ok  (no violations)
```

SQLite FK enforcement is enabled per-connection via `PRAGMA foreign_keys=ON`
(set in `BMDbAdapter._connect` through a SQLAlchemy engine connect event).

---

## Acceptance Criteria — All Met

| Criterion | Status |
|-----------|--------|
| `python -m py_compile *.py` | PASS |
| `GIRAFFE_DB_MODE=off python run_bm_e2e_with_db.py` (no giraffe_db installed) | PASS |
| `GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db python run_bm_e2e_with_db.py` | PASS |
| `python verify_integration.py --db sqlite:///./test.db --runs 5` → 5/5 | PASS |
| `PRAGMA integrity_check` returns `ok` | PASS |
| `PRAGMA foreign_key_check` returns no violations | PASS |

---

## Scope and Caveats

This baseline covers the **core happy path** only:

- Single buyer, single main supplier
- No upstream dependency chains
- No CAD/CNC matching integration
- No role-switching within the verification loop
- SQLite only (PostgreSQL path untested at this stage)

**Reproducible integration baseline passed; ready for next-stage hardening and
broader scenario testing.**

Suggested next steps for hardening:

- Add upstream dependency chain scenarios (M → fabric/trim suppliers)
- Add role-switching lifecycle tests (MAIN_M_SIDE ↔ UPSTREAM_B_SIDE)
- Extend verifier with CAD/CNC rollup assertions
- Run against PostgreSQL
- Add concurrent-session stress tests
- Wire into CI with `pytest` fixtures

