# PR #12 — Qwen QC Intelligence Layer Implementation Report

**Branch:** `claude/qwen-qc-intelligence-layer-pr12`
**Date:** 2026-06-14
**Base branch:** `claude/ai-merchandiser-logistics-wy93i7`

---

## Summary

PR #12 builds a complete QC intelligence layer on top of the Qwen LLM provider established in PR #11.
It fixes three bugs from PR #11 and delivers a reference image store, process card management, video frame sampler,
QC result store, feedback generator, and policy engine — all integrated with existing merchandiser modules
and exposed via `/api/qc/...` endpoints.

---

## LLM Provider Status

| Item | Status |
|---|---|
| Default LLM provider | `qwen` |
| Default QC comparison provider | `qwen` |
| Real Qwen call tested | No — no API key in CI |
| Reason for no real call | `DASHSCOPE_API_KEY` / `QWEN_API_KEY` not set |
| Mock fallback tested | Yes — all 26 mock checks pass |
| Image comparison through Qwen interface | Yes (mock path verified) |
| Video-frame comparison through Qwen interface | Yes (mock path verified) |
| Production mode without key | Raises `RuntimeError` correctly |
| `QC_ALLOW_EXTERNAL_LLM` default | `false` |
| `QC_ALLOW_CAD_TO_LLM` default | `false` |
| `QC_ALLOW_BOM_TO_LLM` default | `false` |

---

## Bug Fixes

### Bug 4.1 — `buyer_actor_id` in Order Bridge

**File:** `src/bm_bridge/order_bridge.py`

**Problem:** `buyer_actor_id` was always set to `b_workspace_id`, not the actual buyer actor ID from the project.

**Fix:** After resolving `project_id` from disk, the code now also reads `original_buyer_actor_id` from the project JSON
and uses it as `buyer_actor_id` when calling `create_post_confirmation_execution()`. Falls back to `b_workspace_id`
if no project file is found (backwards compatible).

### Bug 4.2 — Media Upload Does Not Update Milestone Status

**File:** `src/merchandiser/media_confirmation.py`

**Problem:** `upload_media_evidence()` wrote `MediaEvidence` records but the milestone remained at `PENDING` or `REQUESTED`.

**Fix:** Added `update_milestone_status: bool = True` parameter. When `True` (default), after uploading media evidence,
calls `update_milestone_status(milestone_id, project_id, "UPLOADED", metadata={"media_ids": [...], "uploaded_by": ...})`.
Uses `try/except FileNotFoundError` so it never breaks if the milestone doesn't exist in the milestone manager store
(the two stores are decoupled).

### Bug 4.3 — Buyer Signoff Does Not Close Order

**File:** `src/merchandiser/b_side/b_signoff.py`

**Problem:** `receive_buyer_signoff()` only logged an event but did not update the order execution context status
or trigger order closure.

**Fix:** When `response == "confirmed"`:
1. Resolves `order_id` from the merchandiser execution plan (if not provided explicitly)
2. Calls `get_order_execution(order_id)` and updates `order.status = "ORDER_CLOSED"`
3. Calls `transition_order_state(project_id, "BUYER_SIGNED_OFF", ...)` on the state machine
4. Returns `"status": "order_closed"` instead of `"signoff_received"`
5. Both E2E scripts updated to accept both `"signoff_received"` and `"order_closed"`

---

## New QC Intelligence Layer Modules

### `src/merchandiser/qc/qc_reference_store.py`
- `add_reference_image()` — store golden sample / approved sample images per project+milestone
- `get_reference_images()` — retrieve active reference images, optionally filtered by `milestone_type`
- `deactivate_reference_image()` — soft-delete a reference image
- Persisted under `data/merchandiser/qc/reference_images/`

### `src/merchandiser/qc/qc_process_card.py`
- `create_process_card()` — create supplier process card with material, color, size, finish, defect criteria
- `get_process_card()` — retrieve most recent active card for a project
- `render_process_card_for_llm()` — render safe text representation for LLM (pricing/contact never included)
- `redact_process_card_for_llm()` — return redacted dict (unit_price, supplier_contact, contract_terms stripped)
- Security: material_spec gated by `QC_ALLOW_CAD_TO_LLM`; size_spec by `QC_ALLOW_BOM_TO_LLM`
- Persisted under `data/merchandiser/qc/process_cards/`

### `src/merchandiser/qc/qc_video_sampler.py`
- `sample_video_frames()` — MVP: directory → sorted PNG/JPG frames; file → single-frame list
- `normalize_video_input_to_frames()` — normalize pre-extracted frames or sample from a path

### `src/merchandiser/qc/qc_result_store.py`
- `save_qc_report()` — persist QCComparisonReport as JSON, returns `report_id`
- `get_qc_report()` — retrieve by `report_id`
- `get_qc_reports_for_project()` — list all reports for a project (sorted by `saved_at`)
- `get_latest_qc_report_for_milestone()` — latest report for project+milestone combo
- Persisted under `data/merchandiser/qc/reports/`

### `src/merchandiser/qc/qc_feedback_generator.py`
- `generate_m_side_qc_feedback()` — produces structured feedback dict with Chinese-first `feedback_zh` / `feedback_en`,
  `action_required`, `escalate_to_buyer`, `severity`, `overall_result`

### `src/merchandiser/qc/qc_policy.py`
- `decide_qc_action()` — decides next action from `QCComparisonReport`:
  - `auto_approve` (pass + score ≥ 0.85)
  - `request_rework` (needs_fix or medium/high severity)
  - `escalate_to_buyer` (buyer_confirmation_required or buyer_review_required result)
  - `reject` (reject result or critical severity)
  - `review` (unknown / fallback)

### `src/merchandiser/m_side/m_qc_followup.py`
- `request_qc_update()` — request QC evidence from supplier
- `send_qc_comparison_feedback_to_m_side()` — send AI QC feedback to M-side; auto-raises exception for critical findings

### `src/merchandiser/b_side/b_qc_review.py`
- `escalate_qc_to_buyer()` — escalate QC report to buyer for review
- `receive_buyer_qc_decision()` — record buyer approve/reject/rework_required decision

### `src/db/models/qc.py`
- `QCReferenceImageORM` — SQLAlchemy ORM for reference images
- `QCProcessCardORM` — SQLAlchemy ORM for process cards
- `QCComparisonReportORM` — SQLAlchemy ORM for QC comparison reports
- All active only when `GIRAFFE_DB_MODE=on` (dual persistence pattern)

---

## New API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/qc/health` | QC module health check |
| POST | `/api/qc/{project_id}/reference-images` | Add a reference image |
| GET | `/api/qc/{project_id}/reference-images` | List reference images (optional `?milestone_type=`) |
| POST | `/api/qc/{project_id}/process-card` | Create a process card |
| GET | `/api/qc/{project_id}/process-card` | Get most recent active process card |
| POST | `/api/qc/{project_id}/compare` | Run QC comparison (AI-assisted, default provider: qwen) |
| GET | `/api/qc/{project_id}/reports` | List saved QC reports for project |
| GET | `/api/qc/reports/{report_id}` | Get a specific QC report by ID |
| POST | `/api/qc/{project_id}/buyer-decision` | Record buyer QC decision |

The `/api/merchandiser/{project_id}/buyer-signoff` endpoint was also updated to accept optional `order_id` and `tracking_number` fields.

---

## Test Coverage

| Test File | Tests | Purpose |
|---|---|---|
| `tests/test_qc_reference_store.py` | 6 | Reference image CRUD, deactivation |
| `tests/test_qc_process_card.py` | 6 | Process card create/get, LLM redaction |
| `tests/test_qc_feedback_generator.py` | 6 | Feedback generation for all QC outcomes |
| `tests/test_qc_video_sampler.py` | 6 | Frame sampling, normalize function |
| `tests/test_qc_result_store.py` | 5 | Report save/retrieve/list |
| `tests/test_qc_policy.py` | 5 | Policy decisions for all outcomes |
| `tests/test_qc_m_side_followup.py` | 3 | M-side feedback send |
| `tests/test_b_qc_review.py` | 4 | B-side escalation and decision |
| `tests/test_order_bridge_buyer_actor_fix.py` | 3 | Bug 4.1 verification |
| `tests/test_media_upload_updates_milestone.py` | 3 | Bug 4.2 verification |
| `tests/test_buyer_signoff_order_closure_fix.py` | 5 | Bug 4.3 verification |
| `tests/test_qc_api_endpoints.py` | 8 | FastAPI QC endpoint tests |
| `tests/test_qwen_provider_config.py` | 9 | Provider config constants |

**Total new tests: 69 | Total tests in suite: 524**

---

## Regression Results (5/5 Pass)

| Script | Result |
|---|---|
| `uv run pytest` | ✅ 524 passed, 0 failed |
| `scripts/run_qc_llm_comparison_mvp.py` | ✅ 26/26 checks pass |
| `scripts/run_qwen_qc_smoke_test.py` | ✅ Skipped (no API key) — correct behavior |
| `scripts/run_merchandiser_e2e_mvp.py` | ✅ 47/47 checks pass |
| `scripts/run_integrated_post_confirmation_mvp.py` | ✅ 56/56 checks pass |

---

## Security Constraints Verified

- `unit_price`, `supplier_contact`, `contract_terms` never sent to LLM (redacted by `render_process_card_for_llm`)
- `material_spec` requires `QC_ALLOW_CAD_TO_LLM=true` (default: false)
- `size_spec` requires `QC_ALLOW_BOM_TO_LLM=true` (default: false)
- `QC_ALLOW_EXTERNAL_LLM` defaults to `false`
- No secrets logged, no API keys printed
- CI passes without Qwen API key (mock fallback)
- Production mode without key raises `RuntimeError` (not silent fallback)

---

## Known Limitations

- Real Qwen API call not tested in this PR (no API key in CI — expected and documented)
- Video sampling is frame-based (no FFmpeg dependency); native video input deferred to future PR
- `original_buyer_actor_id` lookup in Bug 4.1 fix uses filesystem glob — for high-scale, should use a DB index
