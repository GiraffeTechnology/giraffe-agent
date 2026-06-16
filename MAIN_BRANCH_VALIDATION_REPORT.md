# Main Branch Validation Report

## Metadata

| Field | Value |
|---|---|
| Commit SHA | `e56770e1ae67d89f314f895edfbf98b9146e0fd4` |
| Branch | `main` |
| Report date/time (UTC) | 2026-06-16T05:00:00Z |
| Reporter | Release hardening — local CI dry-run |

---

## Commands run and results

### 1. Python syntax check

```
uv run python -m compileall src api scripts tests -q
```

**Result:** PASS — no syntax errors across `src/`, `api/`, `scripts/`, `tests/`.

---

### 2. Full pytest suite

```
uv run pytest -q --tb=short
```

**Result:** PASS  
Tests passed: **734**  
Tests failed: 0  
Tests skipped: 0  

---

### 3. B/M E2E — DB-off

```
GIRAFFE_DB_MODE=off uv run python run_bm_e2e_with_db.py
```

**Result:** PASS — all B+M integration assertions pass in memory-only mode.

---

### 4. B/M E2E — DB-on (SQLite)

```
GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./ci_test.db uv run python build_schema.py
GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./ci_test.db uv run python run_bm_e2e_with_db.py
```

**Result:** PASS — schema built without errors; B/M E2E assertions pass against SQLite.

---

### 5. Integration verifier (5 runs)

```
uv run python verify_integration.py --db sqlite:///./ci_test.db --runs 5
```

**Result:** PASS — all 5 runs completed cleanly.

---

### 6. SQLite integrity checks

```python
import sqlite3
conn = sqlite3.connect("ci_test.db")
print(conn.execute("PRAGMA integrity_check").fetchone())
print(conn.execute("PRAGMA foreign_key_check").fetchall())
```

**PRAGMA integrity\_check:** `ok`  
**PRAGMA foreign\_key\_check:** `[]` (no violations)

---

### 7. BM E2E MVP script

```
uv run python scripts/run_bm_e2e_mvp.py
```

**Result:** PASS

---

### 8. Role switching MVP

```
uv run python scripts/run_role_switching_mvp.py
```

**Result:** PASS — 79 role-switching checks passed.

---

### 9. Lead time model demo

```
uv run python scripts/run_lead_time_model_demo.py
```

**Result:** PASS — `LEAD TIME MODEL DEMO: PASS`

---

### 10. QC LLM comparison MVP

```
uv run python scripts/run_qc_llm_comparison_mvp.py
```

**Result:** PASS — mock provider, reference image comparison, process card, and fallback path all verified.

---

### 11. Qwen QC smoke test

```
uv run python scripts/run_qwen_qc_smoke_test.py
```

**Result:** SKIPPED — `DASHSCOPE_API_KEY` / `QWEN_API_KEY` not configured. Real Qwen API call was not made. Mock fallback path verified only.

---

### 12. OpenClaw integration tests

```
uv run pytest tests/test_openclaw_integration.py -q --tb=short
```

**Result:** PASS

---

### 13. ClawHub plugin metadata validation

```
uv run python scripts/validate_clawhub_aivan_plugin.py
```

**Result:** PASS — all required metadata fields present and valid.

---

### 14. AIVAN OpenClaw plugin smoke test (mock server)

```
uv run uvicorn api.main:app --host 127.0.0.1 --port 8000 &
AIVAN_BASE_URL=http://127.0.0.1:8000 uv run python scripts/run_aivan_openclaw_plugin_smoke_test.py
```

**Result:** PASS — all skill endpoints reachable against local mock server.

---

### 15. TypeScript syntax check (plugin bridge)

```
cd integrations/openclaw-aivan-plugin && npm install && npx tsc --noEmit
```

**Result:** PASS — no TypeScript errors.

---

## External service status

| Service | Status | Reason |
|---|---|---|
| Real Qwen API call | **SKIPPED** | `DASHSCOPE_API_KEY` / `QWEN_API_KEY` not set |
| Real OpenClaw IM bridge | **SKIPPED** | Live OpenClaw channel credentials not configured |

These are not failures. All internal interfaces and mock paths pass. External calls require operator-supplied credentials and are explicitly gated.

---

## Final verdict

**PASS WITH GAPS**

- Full pytest suite passed: 734 tests.
- All E2E scripts pass.
- DB-off and DB-on modes both validated.
- SQLite integrity confirmed.
- Mock paths for all external integrations verified.
- Real Qwen call: SKIPPED (no key).
- Real OpenClaw IM bridge: SKIPPED (no live credentials).

This is **not a production-ready deployment**. It is a validated MVP that passes all internal contract tests and mock-mode E2E flows. Production deployment requires:
- PostgreSQL (not SQLite)
- Real IM channel credentials
- Real LLM provider keys
- Operator-managed approval workflows for outbound trade messages

See [`docs/PERSISTENCE_MODE.md`](docs/PERSISTENCE_MODE.md) for deployment mode details.
