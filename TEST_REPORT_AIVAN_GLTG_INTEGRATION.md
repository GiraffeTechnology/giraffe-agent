# AIVAN × GLTG Integration Report

**Branch:** `feature/aivan-embed-gltg`
**Commit tested:** `8a5a921` (original) → hardened in this update
**Head after hardening:** see `git log --oneline -1`
**Scope:** Complete, validate, and harden GLTG as AIVAN lead-time / feasibility engine.

---

## 1. Architecture Change

Before this PR, AIVAN-facing delivery paths were generated directly by the deterministic `calculate_lead_time_path()` function through `src.lead_time.path_enumerator.enumerate_delivery_paths()`.

After this PR, all AIVAN-facing path enumeration routes through `src.gltg.engine.calculate_gltg_lead_time_path()`. The deterministic calculator remains the component-level core, but GLTG now wraps it and attaches:

- Model provenance (`model_name = "GLTG"`, `model_version`, `fallback_model_used`)
- Probabilistic percentile estimates (`p50_lead_time_days`, `p80_lead_time_days`, `p90_lead_time_days`)
- Explicit P80 feasibility basis (`feasibility_basis = "p80"`)
- GLTG evidence references on every path

The B-side feasibility engine (`run_feasibility_simulation`) now uses GLTG and surfaces all fields on `DeliveryPath` (buyer-facing options). The M-side rollup (`generate_supplier_response_rollup`) was also updated to use GLTG for its internal lead-time calculation.

---

## 2. Files Changed

| File | Purpose |
|---|---|
| `src/gltg/__init__.py` | GLTG package exports |
| `src/gltg/engine.py` | Embedded GLTG engine; wraps deterministic calculator; adds P50/P80/P90 and provenance |
| `src/lead_time/models.py` | GLTG fields added to `LeadTimePath` |
| `src/lead_time/path_enumerator.py` | Routes AIVAN path enumeration through GLTG; lazy-import to break circular dependency |
| `src/lead_time/__init__.py` | Removed GLTG re-export that caused circular import |
| `src/b_side/feasibility_engine.py` | Switched from `calculate_lead_time_path` to `calculate_gltg_lead_time_path`; passes GLTG fields to `DeliveryPath` |
| `src/core_schema/b_side_types.py` | Added GLTG provenance fields to `DeliveryPath` |
| `src/m_side/rollup/supplier_response_rollup.py` | Switched internal lead-time calculation to GLTG |
| `tests/test_aivan_gltg_integration.py` | Regression tests proving AIVAN uses GLTG |
| `tests/test_aivan_buyer_options_use_gltg.py` | New: buyer-facing DeliveryPath exposes GLTG fields |
| `tests/test_gltg_feasibility_basis.py` | New: all 5 GLTG functional rules verified |
| `tests/test_gltg_no_silent_fallback.py` | New: fallback is explicit, legacy default never used |

---

## 3. Bugs Fixed

### 3.1 Circular Import (Critical)

`src/lead_time/__init__.py` imported `calculate_gltg_lead_time_path` from `src.gltg.engine`, which itself imports from `src.lead_time.*`. This caused a `ImportError: cannot import name 'calculate_gltg_lead_time_path' from partially initialized module` that broke the entire test suite.

Fix applied (two-part):
1. Removed the GLTG re-export from `src/lead_time/__init__.py`.
2. Moved the `from src.gltg.engine import calculate_gltg_lead_time_path` in `path_enumerator.py` inside the function body (lazy import) to prevent the cycle even on direct sub-module imports.

### 3.2 B-side Feasibility Engine Bypassed GLTG

`run_feasibility_simulation()` in `src/b_side/feasibility_engine.py` called `calculate_lead_time_path()` directly. AIVAN-facing buyer options (`DeliveryPath`) had no GLTG provenance, P50/P80/P90, or feasibility basis.

Fix applied: switched to `calculate_gltg_lead_time_path()` and added GLTG fields to the `DeliveryPath` conversion.

### 3.3 DeliveryPath Missing GLTG Fields

`DeliveryPath` in `src/core_schema/b_side_types.py` had no GLTG provenance fields. Buyer options could not expose `lead_time_model`, P50/P80/P90, `feasibility_basis`, or `fallback_model_used`.

Fix applied: added six new optional fields to `DeliveryPath` with `None`/`False` defaults for backward compatibility.

### 3.4 M-side Rollup Used Legacy Calculator

`generate_supplier_response_rollup()` called `calculate_lead_time_path()` directly. Fixed to use `calculate_gltg_lead_time_path()`.

---

## 4. GLTG Integration Confirmed

### 4.1 AIVAN-facing Path Enumeration Uses GLTG

`enumerate_delivery_paths()` calls `calculate_gltg_lead_time_path()` (lazy import), not the legacy function. All returned `LeadTimePath` objects have:

```
path.model_name == "GLTG"
path.model_version == "0.1.0-local"
path.p50_lead_time_days <= path.p80_lead_time_days <= path.p90_lead_time_days
path.feasibility_basis == "p80"
path.fallback_model_used is False
path.evidence_refs contains GLTG provenance ref
```

### 4.2 Buyer Options Preserve GLTG Metadata

`run_feasibility_simulation()` routes through GLTG and the converter `_path_to_delivery_path()` now maps all GLTG fields to `DeliveryPath`:

```
path.lead_time_model == "GLTG"
path.p50_lead_time_days is not None
path.p80_lead_time_days is not None
path.p90_lead_time_days is not None
path.feasibility_basis == "p80"
path.fallback_model_used is False
```

### 4.3 P80 is the Default Feasibility Basis

`_apply_gltg_envelope()` sets `slack_days = deadline_days - p80_lead_time_days` and `feasible_before_deadline = slack_days >= 0`. All infeasibility risk flags reference `gltg_p80_deadline_infeasible`.

### 4.4 Human Approval Gate Unchanged

The human approval gate (`src/openclaw_skill/message_draft_store.py`, `src/m_side/upstream/approval_gate.py`) was not modified. All drafts still require explicit approval. E2E scripts confirm `Approval gate: ENFORCED`.

### 4.5 GLTG Evidence References

Every GLTG path carries a reference of the form:
```
type:ai_calculated|src:GLTG|note:version:0.1.0-local;p50:N;p80:N;p90:N;basis:p80
```

---

## 5. GLTG Functional Rules Verified

| Rule | Status |
|---|---|
| P80 is default deadline feasibility basis | PASS — `feasibility_basis == "p80"`, slack = deadline − P80 |
| Supplier-stated lead time is evidence, not truth | PASS — 1-day claim for 10k units produces flagged multi-day path |
| GLTG must preserve audit trail | PASS — `evidence_refs` contain GLTG provenance on every path |
| Fallback cannot be silent | PASS — `fallback_model_used is False`; field always present |
| Risk affects P90 | PASS — risky path P90 ≥ clean path P90 |
| Larger order ≥ smaller order lead time | PASS — `large.p80 >= small.p80` for equal capacity |

---

## 6. Test Commands Run

```bash
# Fix verification
uv run pytest tests/test_aivan_gltg_integration.py -q --tb=short
uv run pytest -q --tb=short
python -m compileall src scripts tests -q

# New test files
uv run pytest tests/test_aivan_buyer_options_use_gltg.py tests/test_gltg_feasibility_basis.py tests/test_gltg_no_silent_fallback.py -v --tb=short

# E2E scripts
GIRAFFE_DB_MODE=off uv run python scripts/run_aivan_e2e.py
GIRAFFE_DB_MODE=off uv run python scripts/run_aivan_marketplace_e2e.py
GIRAFFE_DB_MODE=off uv run python scripts/run_aivan_unknown_supplier_risk_e2e.py
GIRAFFE_DB_MODE=off uv run python scripts/run_aivan_platform_whitelist_e2e.py

# Plugin validation
uv run python scripts/validate_clawhub_aivan_plugin.py
uv run python scripts/run_aivan_openclaw_plugin_smoke_test.py --offline

# TypeScript check
cd integrations/openclaw-aivan-plugin && npm install && npx tsc --noEmit

# Unicode / BIDI / line-ending check
python - << 'EOF'
import os, re, sys
BIDI = re.compile('[​-‏‪-‮⁠-⁩﻿]')
bad = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ('.git', '.venv', '__pycache__', 'node_modules', 'dist')]
    for f in files:
        if not any(f.endswith(e) for e in ('.py', '.ts', '.md', '.json', '.yml', '.yaml', '.sh')):
            continue
        path = os.path.join(root, f)
        raw = open(path, 'rb').read()
        issues = []
        if b'\r\n' in raw:
            issues.append('CRLF')
        if raw.startswith(b'\xef\xbb\xbf'):
            issues.append('BOM')
        if BIDI.search(raw.decode('utf-8', errors='replace')):
            issues.append('BIDI')
        if issues:
            bad.append(f"{','.join(issues)}: {path}")
if bad:
    print('\n'.join(bad))
    sys.exit(1)
print('No encoding issues found.')
EOF
```

---

## 7. Test Results

| Test Suite | Result |
|---|---|
| `tests/test_aivan_gltg_integration.py` | 3/3 PASS |
| `tests/test_aivan_buyer_options_use_gltg.py` | 7/7 PASS |
| `tests/test_gltg_feasibility_basis.py` | 9/9 PASS |
| `tests/test_gltg_no_silent_fallback.py` | 7/7 PASS |
| Full pytest suite | **730/730 PASS** |
| `run_aivan_e2e.py` | PASS — `Approval gate: ENFORCED` |
| `run_aivan_marketplace_e2e.py` | PASS |
| `run_aivan_unknown_supplier_risk_e2e.py` | PASS |
| `run_aivan_platform_whitelist_e2e.py` | PASS |
| `validate_clawhub_aivan_plugin.py` | PASS |
| `run_aivan_openclaw_plugin_smoke_test.py --offline` | PASS |
| TypeScript (`npx tsc --noEmit`) | PASS |
| Unicode / BIDI / line-ending check | PASS — No issues found |

---

## 8. CI Result

The original `8a5a921` commit failed CI (`AIVAN ClawHub Plugin` job) due to the circular import bug.
After hardening, all issues are resolved. CI will re-run on the new push.

Required CI jobs and expected outcomes:
- B-side Tests: success
- AIVAN ClawHub Plugin: success (circular import fixed)
- BM DB Integration: success
- M-side Role-Switching Tests: success
- Lead Time Path Model: success

---

## 9. Remaining Limitations

1. **GLTG is embedded local-only.** The embedded engine uses a deterministic uncertainty formula (confidence gap × 10% + risk flags × 0.5d + buffer × 50%). A future external GLTG service would replace this behind the same `calculate_gltg_lead_time_path()` interface.
2. **P50/P80/P90 are deterministic, not statistical.** They are derived from a formula, not from historical outcome data. They model uncertainty conservatively without requiring runtime data.
3. **`SupplierResponseRollup` does not expose P50/P80/P90.** The rollup is an internal M-side artifact; buyer-facing GLTG fields live on `DeliveryPath` (the AIVAN-facing output).

---

## 10. Final Recommendation

**SAFE TO MERGE**

All definition-of-done criteria are met:
- `src.gltg.engine.calculate_gltg_lead_time_path()` exists and is non-circular ✓
- AIVAN path enumeration calls GLTG ✓
- AIVAN buyer option generation does not bypass GLTG ✓
- `LeadTimePath` exposes GLTG metadata ✓
- `DeliveryPath` (buyer options) exposes GLTG metadata ✓
- P50/P80/P90 present on AIVAN-facing paths ✓
- P80 is used for default deadline feasibility ✓
- Fallback status is explicit (`fallback_model_used is False`) ✓
- GLTG evidence refs exist on every path ✓
- Human approval gate untouched and enforced ✓
- Full pytest (730 tests) passes ✓
- All four AIVAN E2E scripts pass ✓
- Plugin validation passes ✓
- TypeScript check passes ✓
- Unicode/BIDI check passes ✓
