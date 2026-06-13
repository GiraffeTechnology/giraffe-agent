# Test Results

## BM DB Integration — Baseline v1

**Tag:** `BM_DB_INTEGRATION_BASELINE_V1`  
**Date:** 2026-06-13  
**Branch:** `claude/bm-db-integration-reproducible-olu7a0`  
**Commits:** `2ed3d00` (integration package) → `78e37e1` (docs)

---

### Classification

BM DB Integration Baseline v1 is a reproducible integration baseline, not yet a
production-hardening release.

---

### Test Command

```bash
python verify_integration.py --db sqlite:///./test.db --runs 5
```

### Result

```
[verify_integration] DB:   sqlite:///./test.db
[verify_integration] Runs: 5
  run 1/5: PASS  (project=3c3e4942…)
  run 2/5: PASS  (project=ed0665f8…)
  run 3/5: PASS  (project=ac86f21c…)
  run 4/5: PASS  (project=096888a5…)
  run 5/5: PASS  (project=bc7c3460…)
[verify_integration] PRAGMA integrity_check: ok
[verify_integration] PRAGMA foreign_key_check: ok
[verify_integration] Result: 5/5 passed
```

| Run | Result |
|-----|--------|
| 1/5 | PASS |
| 2/5 | PASS |
| 3/5 | PASS |
| 4/5 | PASS |
| 5/5 | PASS |
| PRAGMA integrity_check | ok |
| PRAGMA foreign_key_check | ok |
| **Overall** | **5/5 passed** |

---

### DB Mode Coverage

| Mode | Command | Result |
|------|---------|--------|
| DB-off (in-memory, no giraffe_db) | `GIRAFFE_DB_MODE=off python run_bm_e2e_with_db.py` | PASS |
| DB-on (real SQLAlchemy + SQLite) | `GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db python run_bm_e2e_with_db.py` | PASS |

---

### Touched Tables — Row Counts After 5 Runs

Actors and supplier actors are idempotent (same buyer and supplier reused across
all runs). Every other table adds one row per run.

| Table | Rows | Growth pattern |
|-------|-----:|----------------|
| `actors` | 2 | Fixed — idempotent get-or-create |
| `projects` | 5 | +1 per run |
| `structured_requirements` | 5 | +1 per run |
| `supplier_inquiries` | 5 | +1 per run |
| `supplier_responses` | 5 | +1 per run |
| `supplier_response_rollups` | 5 | +1 per run |
| `procurement_edges` | 5 | +1 per run; each carries `inquiry_id` + `response_id` |
| `execution_events` | 20 | +4 per run (`ORDER_CONFIRMED`, `PRODUCTION_UPDATE_RECEIVED`, `QC_UPDATE_RECEIVED`, `LOGISTICS_HANDOVER_RECEIVED`) |

---

### Additional Syntax Check

```bash
python -m py_compile pydantic_stub.py build_schema.py bm_db_adapter.py \
    run_bm_e2e_with_db.py verify_integration.py
```

Result: **PASS** (no syntax errors)

---

### Scope

This baseline covers the **core happy path only**:

- Single buyer actor + single main supplier actor
- Idempotent actor and project creation
- Full inquiry → response → rollup → order confirmation → execution event chain
- `procurement_edges.inquiry_id` and `procurement_edges.response_id` back-filled and verified
- Edge status `APPROVED` (order confirmed)
- PRAGMA integrity and foreign-key checks

Not yet covered in this baseline:

- Upstream dependency chains (M → fabric/trim/subcontract suppliers)
- Role-switching within the verifier loop
- CAD/CNC rollup assertions
- PostgreSQL backend
- Concurrent-session or stress scenarios
