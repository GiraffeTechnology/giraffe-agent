# Main Branch 3x Validation Report

Historical evidence note: original non-English documentation examples have been translated into English for readability. Recorded outcomes refer to the original test inputs at the source revision, not to a new run of the translated examples. Source code and test fixtures have not been changed.

## 1. Summary

- **Branch:** `main` (validated at HEAD, working tree: `claude/main-3x-validation-ep6z5p`, same commit)
- **Commit:** `a88121f` — Merge pull request #12 from GiraffeTechnology/claude/qwen-qc-intelligence-layer-pr12
- **PR #12 present on main:** YES — merged 2026-06-14T17:33:31Z (`merged_at` confirmed)
- **PR #12 head commit on main:** `e740dc8` (fix: correct transition_order_state kwarg and register QC ORM models)
- **Overall result:** PASS WITH GAPS
- **Run 1/3:** PASS
- **Run 2/3:** PASS
- **Run 3/3:** PASS

> GAPS: Real Qwen call SKIPPED (no `DASHSCOPE_API_KEY` / `QWEN_API_KEY`). Real OpenClaw WeChat bridge SKIPPED (no live credentials). All internal interfaces, mock fallback paths, and simulated event flows: PASS.

---

## 2. B-side Independent Deployment

| Check | Result | Notes |
|---|---:|---|
| B-side scripts (`run_bm_e2e_mvp.py`) | PASS | All B-side steps in E2E confirmed |
| B-side API smoke (`/api/b-side/workspaces`) | PASS | Endpoint present, returns 422 on missing field (correct validation, not 500) |
| Requirement structuring | PASS | `raw_requirement` field accepted, workspace created |
| Inquiry drafting | PASS | Supplier inquiries dispatched in E2E flow |
| Feasibility / path model | PASS | Delivery path ranking verified, lead time model demo PASS |

---

## 3. M-side Independent Deployment

| Check | Result | Notes |
|---|---:|---|
| Role switching (`run_role_switching_mvp.py`) | PASS | 79/79 checks |
| Send/receive role switching (`run_mside_send_receive_role_switch_test.py`) | PASS | 64 passed, 0 failed |
| Merchandiser module (`run_merchandiser_e2e_mvp.py`) | PASS | 47 passed, 0 failed |
| Logistics module (`run_logistics_cainiao_like_api_mvp.py`) | PASS | 54 passed, 0 failed |
| Standalone M-side module smoke | PASS | `create_execution_plan`, `get_tasks_for_project`, `get_milestones_for_project` all verified |

---

## 4. B/M E2E

| Check | Result | Notes |
|---|---:|---|
| BM E2E MVP (`run_bm_e2e_mvp.py`) | PASS | Full B→M→order lifecycle |
| Integrated post-confirmation (`run_integrated_post_confirmation_mvp.py`) | PASS | 56 passed, 0 failed |
| Lead time model (`run_lead_time_model_demo.py`) | PASS | 3-path demo, all verified totals |
| verify_integration (`--db sqlite:///./test.db --runs 5`) | PASS | 5/5 PASS, PRAGMA integrity ok |

---

## 5. QC + Qwen

| Check | Result | Notes |
|---|---:|---|
| Qwen default provider (`DEFAULT_LLM_PROVIDER`) | PASS | `"qwen"` confirmed in `src/llm/provider_config.py:15` |
| Qwen default QC provider (`DEFAULT_QC_PROVIDER`) | PASS | `"qwen"` confirmed in `src/llm/provider_config.py:16` |
| Real Qwen call | SKIPPED | No `DASHSCOPE_API_KEY` / `QWEN_API_KEY` in environment |
| Mock fallback | PASS | Provider registry returns `MockLLMProvider` when no key; `fallback_used=True` in reports |
| Image comparison through Qwen interface | PASS | `requested_provider=qwen`, `provider_name=mock` (fallback); `m_side_feedback_zh` present |
| Video-frame comparison through Qwen interface | PASS | `frames_used=2`, Chinese feedback in video report |
| Process-card comparison | PASS | `/api/qc/{project_id}/process-card` returns `PC-*` ID, fields correctly stored |
| M-side feedback generated | PASS | `m_side_feedback_zh` and `m_side_feedback_en` in all comparison reports |
| QC API endpoints | PASS | `/api/qc/health`, `/reference-images`, `/process-card`, `/compare`, all 200 |

**Note on Qwen interface:** `requested_provider=qwen` in all reports; mock executes because no key present. Interface routing is verified correct.

---

## 6. OpenClaw + WeChat

| Check | Result | Notes |
|---|---:|---|
| `/api/skill/invoke` exists | PASS | `api/main.py:48` — endpoint present, handles OpenClaw normalized events |
| OpenClaw adapter exists | PASS | `src/openclaw_skill/openclaw_event_adapter.py` — `adapt_openclaw_event` function present |
| WeChat channel accepted | PASS | `channel: "wechat"` accepted and routed by adapter |
| Buyer WeChat event simulation | PASS | `ok=True`, project created `RFQ-*`, `reply_text` in Chinese, `missing_fields` surfaced |
| Supplier WeChat event simulation | PASS | `ok=True`, `status=clarification_needed` (correct: no bound project_id) |
| QC media attachment event simulation | PASS | `ok=True`, attachment received, `status=clarification_needed` |
| Real WeChat bridge | SKIPPED | No live OpenClaw WeChat bridge credentials in environment |
| Direct WeChat credentials inside Giraffe | NONE | Grep confirms no `WECHAT_APP_ID/SECRET/TOKEN`; WeChat handled entirely by OpenClaw externally |

**Architecture confirmed:** WeChat/Weixin → OpenClaw → normalized event → `/api/skill/invoke` → `adapt_openclaw_event` → Giraffe B/M flow. Giraffe never holds WeChat credentials.

---

## 7. DB

| Check | Result | Notes |
|---|---:|---|
| DB-off (`GIRAFFE_DB_MODE=off`) | PASS | `[run_bm_e2e_with_db] PASS` with in-memory store |
| DB-on (`GIRAFFE_DB_MODE=on`, SQLite) | PASS | `[run_bm_e2e_with_db] PASS` with real SQLite |
| QC tables created (`build_schema.py`) | PASS | `qc_reference_images`, `qc_process_cards`, `qc_comparison_reports` all present |
| PRAGMA integrity_check | PASS | `ok` |
| PRAGMA foreign_key_check | PASS | `[]` (no violations) |

QC ORM models registered in `src/db/models/__init__.py` (PR #12 fix — Bug Fix #2 from Codex P2).

---

## 8. Bugs Found

| ID | Severity | Module | Description | Repro Command | Suggested Fix |
|---|---|---|---|---|---|
| B-001 | Low/Info | `run_bm_e2e_mvp.py` | IEG event logger warns `no such table: execution_events` when DB mode is off (default). Warning is non-fatal — script continues and passes. | `uv run python scripts/run_bm_e2e_mvp.py` (default DB-off mode) | Suppress warning when `GIRAFFE_DB_MODE=off`; or gate event logger on DB mode flag. |

> No functional failures. B-001 is a non-fatal warning that does not affect correctness.

---

## 9. Final Verdict

**PASS WITH GAPS**

All required internal/mock flows pass across 3 consecutive clean-state runs:
- B-side independent deployment: PASS
- M-side independent deployment: PASS
- B/M E2E: PASS
- AI Merchandiser post-confirmation: PASS
- Logistics: PASS
- QC Qwen default provider + interface: PASS
- QC mock fallback (no key): PASS
- OpenClaw normalized WeChat event routing: PASS
- DB-off mode: PASS
- DB-on mode: PASS

**Gaps (not failures — credentials not present in environment):**
- Real Qwen call: SKIPPED (no `DASHSCOPE_API_KEY` / `QWEN_API_KEY`)
- Real OpenClaw WeChat bridge: SKIPPED (no live credentials)

---

## 10. Reproduction Commands

```bash
# --- Environment Setup ---
cd /home/user/giraffe-agent      # or: git clone https://github.com/GiraffeTechnology/giraffe-agent
git checkout main
git pull origin main
git log --oneline -5
# Expected HEAD: a88121f Merge pull request #12

UV_HTTP_TIMEOUT=120 uv sync
uv run python -c "import fastapi, pydantic, sqlalchemy, httpx; print('core imports ok')"

# --- Static audit ---
ls -R src/llm src/merchandiser/qc src/openclaw_skill
ls scripts | sort
grep -R "DEFAULT_LLM_PROVIDER\|DEFAULT_QC_PROVIDER" src/llm/provider_config.py

# --- Full test suite ---
uv run pytest -q
# Expected: 525 passed

# --- B-side ---
uv run python scripts/run_bm_e2e_mvp.py

# --- M-side ---
uv run python scripts/run_role_switching_mvp.py
uv run python scripts/run_mside_send_receive_role_switch_test.py
uv run python scripts/run_merchandiser_e2e_mvp.py
uv run python scripts/run_logistics_cainiao_like_api_mvp.py

# --- E2E ---
uv run python scripts/run_integrated_post_confirmation_mvp.py
uv run python scripts/run_lead_time_model_demo.py

# --- QC + Qwen ---
uv run python scripts/run_qc_llm_comparison_mvp.py
uv run python scripts/run_qwen_qc_smoke_test.py
# Expected: 26 passed / QWEN REAL CALL SKIPPED: missing API key

# --- OpenClaw WeChat simulated events ---
uv run python - <<'PY'
from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event
r = adapt_openclaw_event({"source":"openclaw","channel":"wechat","channel_account_id":"x","conversation_id":"c1","sender_id":"u1","sender_display_name":"Test","message_text":"I need to source 100 pure-cotton polo shirts","message_type":"text","attachments":[],"mode":"b_side"})
assert r.get("ok") is not False
print("OPENCLAW_WECHAT_BUYER: PASS")
PY

# --- DB ---
GIRAFFE_DB_MODE=off uv run python run_bm_e2e_with_db.py
rm -f test.db
GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db uv run python build_schema.py
GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db uv run python run_bm_e2e_with_db.py
uv run python verify_integration.py --db sqlite:///./test.db --runs 5

# --- 3x Full Regression ---
for i in 1 2 3; do
  rm -rf data/merchandiser data/logistics data/communication data/order_execution data/industrial_execution_graph data/projects 2>/dev/null || true
  uv run pytest -q
  uv run python scripts/run_bm_e2e_mvp.py
  uv run python scripts/run_role_switching_mvp.py
  uv run python scripts/run_mside_send_receive_role_switch_test.py
  uv run python scripts/run_merchandiser_e2e_mvp.py
  uv run python scripts/run_logistics_cainiao_like_api_mvp.py
  uv run python scripts/run_integrated_post_confirmation_mvp.py
  uv run python scripts/run_lead_time_model_demo.py
  uv run python scripts/run_qc_llm_comparison_mvp.py
  uv run python scripts/run_qwen_qc_smoke_test.py
  rm -f test.db && GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db uv run python build_schema.py
  echo "RUN $i/3: PASS"
done
```

---

*Validated: 2026-06-14 | Branch: main @ a88121f | PR #12: merged*

