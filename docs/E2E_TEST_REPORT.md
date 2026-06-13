# E2E Test Report — Giraffe Agent B-side v9-patched + M-side v8

**Date:** 2026-06-13
**B-side version:** v9-patched
**M-side version:** v8
**Report type:** MVP baseline acceptance

---

## Summary

| Test Suite | Result | Tests |
|------------|--------|-------|
| B-side run_tests.py | ✅ PASSED | 33/33 |
| B-side pytest | ✅ PASSED | 222/222 |
| M-side pytest | ✅ PASSED | 177/177 |
| HTTP E2E (3 consecutive runs) | ✅ PASSED | 3/3 |

All baseline acceptance criteria met.

---

## Test Environment

- Python: 3.11.x
- OS: Linux (Ubuntu 22.04)
- Storage: Flat JSON file store (no external DB)
- LLM: None (deterministic regex parsing only)
- Channel: Mock adapter (no live IM connections)

---

## B-side Test Coverage

### run_tests.py (33/33 scenarios)

Integration scenarios covering:
- Workspace lifecycle (create → persist → load)
- Requirement structuring (CNC, apparel, packaging, partial)
- Bilingual inquiry drafting (EN + ZH)
- Supplier response intake and deduplication
- Feasibility simulation and ranking
- Full end-to-end B-side flow
- Role resolution (ORIGINAL_BUYER, MAIN_M_SIDE, UPSTREAM_B_SIDE, UPSTREAM_M_SIDE)
- Edge cases (missing workspace, no can-make responses)

### pytest (222/222 tests)

Module coverage:
- `test_b_side_types.py` — Pydantic model validation (35 tests)
- `test_requirement_structurer.py` — Deterministic parser (47 tests)
- `test_inquiry_drafter.py` — Bilingual message generation (30 tests)
- `test_feasibility_engine.py` — Scoring and ranking (33 tests)
- `test_supplier_response_intake.py` — Response intake and dedup (8 tests)
- `test_workspace.py` — JSON file persistence (16 tests)
- `test_actors.py` — Role resolution (11 tests)
- `test_bm_bridge.py` — B+M bridge integration (12 tests)
- `test_extra_coverage.py` — Edge cases and extended scenarios (30 tests)

---

## M-side Test Coverage

### pytest (177/177 tests)

Module coverage:
- `test_m_side_types.py` — Pydantic model validation (45 tests)
- `test_response_normalizer.py` — Regex-based normalization (35 tests)
- `test_quote_builder.py` — Quote field extraction (16 tests)
- `test_supplier_profile.py` — Profile CRUD (13 tests)
- `test_order_acknowledger.py` — Order acknowledgement (13 tests)
- `test_m_event_logger.py` — JSONL event logging (19 tests)
- `test_supplier_workspace.py` — Workspace CRUD (16 tests)
- `test_logistics.py` — Shipment and event models (20 tests)

---

## HTTP E2E Test Results

**3 consecutive runs via `scripts/run_bm_e2e_mvp.py`**

Each run exercised:
1. B-side workspace creation
2. Requirement structuring
3. Supplier inquiry drafting
4. Dispatch to 3 mock suppliers
5. Supplier response simulation (1 can_make=True, 2 can_make=False)
6. Response normalization
7. Response push to B-side
8. Feasibility simulation
9. Top delivery path selection

**Run 1:** PASSED — Top path: supplier rank 1, lead_time=30d, confidence=0.91
**Run 2:** PASSED — Top path: supplier rank 1, lead_time=30d, confidence=0.91
**Run 3:** PASSED — Top path: supplier rank 1, lead_time=30d, confidence=0.91

All 3 runs produced identical deterministic results (no randomness in core logic).

---

## Known Issue Documented

> **Unknown supplier dispatch returns incorrect HTTP 200**
>
> When `dispatch-inquiry` is called with `supplier_ids` that don't exist in
> the supplier registry, the API currently returns:
> ```json
> {"ok": true, "dispatched": 0}
> ```
> instead of:
> ```json
> HTTP 422
> {"ok": false, "dispatched": 0, "missing_supplier_ids": ["sup_unknown"]}
> ```
>
> This is a known issue. Fix is planned for v0.2.0.
> See `docs/ROADMAP.md`.

---

## Conclusion

The v0.1.0-mvp release meets the MVP baseline acceptance criteria:
- All 222 B-side unit tests pass
- All 177 M-side unit tests pass
- All 33 B-side integration scenarios pass
- HTTP E2E: 3/3 consecutive runs passed
- One known issue documented with a clear fix path

This release is suitable as:
- An MVP baseline reference implementation
- A developer preview for integration testing
- An open-core starting point for production development

It is **not** production-ready (no auth, flat file storage, no LLM).
