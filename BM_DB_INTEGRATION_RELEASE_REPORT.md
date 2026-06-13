# BM DB Integration — Release Report

**Repository:** GiraffeTechnology/giraffe-agent  
**Baseline:** BM_DB_INTEGRATION_BASELINE_V1  
**Status:** Reproducible integration baseline  
**Date:** 2026-06-13

---

## Summary

BM DB Integration Baseline v1 is a reproducible integration baseline, not yet a
production-hardening release.

The integration package previously did not exist in a runnable form. Five distinct failure
modes were identified and resolved. The verifier now passes 5/5 runs with clean PRAGMA
checks against a fresh SQLite database.

---

## Test Results

### DB-off mode

```
GIRAFFE_DB_MODE=off python run_bm_e2e_with_db.py
```

**Result:** PASS

```
[run_bm_e2e_with_db] mode=off
  actors: buyer=ca03bbf6  supplier=c2d382ec
  project: a68ead4a
  counts: {actors: 2, projects: 1, structured_requirements: 1, supplier_inquiries: 1,
           supplier_responses: 1, supplier_response_rollups: 1, procurement_edges: 1,
           execution_events: 4}
[run_bm_e2e_with_db] PASS
```

### DB-on mode

```
GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db python build_schema.py
GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db python run_bm_e2e_with_db.py
```

**Result:** PASS

```
[build_schema] Schema applied to: sqlite:///./test.db
[run_bm_e2e] Schema ready at: sqlite:///./test.db
  actors: buyer=381544f4  supplier=54ea42f7
  project: a25122c8
  counts: {actors: 2, projects: 1, structured_requirements: 1, supplier_inquiries: 1,
           supplier_responses: 1, supplier_response_rollups: 1, procurement_edges: 1,
           execution_events: 4}
[run_bm_e2e_with_db] PASS
```

### Verifier — 5/5 reproducibility

```
python verify_integration.py --db sqlite:///./test.db --runs 5
```

**Result:** 5/5 PASS

```
[verify_integration] DB:   sqlite:///./test.db
[verify_integration] Runs: 5
  run 1/5: PASS  (project=88fba939…)
  run 2/5: PASS  (project=7a30846e…)
  run 3/5: PASS  (project=57a5b911…)
  run 4/5: PASS  (project=cc768450…)
  run 5/5: PASS  (project=a7e57c3b…)
[verify_integration] PRAGMA integrity_check: ok
[verify_integration] PRAGMA foreign_key_check: ok
[verify_integration] Result: 5/5 passed
```

### Unit tests (pytest)

```
uv run pytest tests/ -q
```

**Result:** 39 passed in 1.89s

---

## DB Tables Touched

| Table | Row count after 5 runs | Notes |
|-------|------------------------|-------|
| `actors` | ≥ 2 (+ cumulative) | buyer + supplier per run (idempotent by name+type) |
| `projects` | ≥ 1 (+ cumulative) | one per run (unique product_summary per run) |
| `structured_requirements` | ≥ 5 | one per run |
| `supplier_inquiries` | ≥ 5 | one per run |
| `supplier_responses` | ≥ 5 | one per run |
| `supplier_response_rollups` | ≥ 5 | one per run |
| `procurement_edges` | ≥ 5 | one per run; status=APPROVED |
| `execution_events` | ≥ 4 per run | ORDER_CONFIRMED + 3 production/logistics events |

---

## Latest main commit

`c9da565` — Merge pull request #1 from GiraffeTechnology/claude/giraffe-mvp-database-5cftvx

---

## Known Limitations

1. PostgreSQL not tested — all suites run against SQLite only
2. Concurrent write scenarios not covered — single-threaded sequential only
3. Execution graph replay not yet on main — implemented on dev branch (v1.2)
4. Decision packet not yet on main — implemented on dev branch (v1.2)
5. Trust boundary layer not yet on main — implemented on dev branch (v1.3)
6. CI does not run on tag push events — workflow only triggers on push to main and pull_request

---

## Next Milestones

- **v1.2** — Merge execution graph replay + decision packet (on dev branch `claude/bm-db-integration-reproducible-olu7a0`)
- **v1.3** — Merge trust boundary & rule integrity layer (same dev branch)
- **v1.4** — PostgreSQL compatibility testing + concurrent write scenarios
