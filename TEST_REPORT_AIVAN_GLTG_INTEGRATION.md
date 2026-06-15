# AIVAN GLTG Integration Report

**Branch:** `feature/aivan-embed-gltg`  
**Scope:** Embed GLTG into AIVAN lead-time / feasibility path generation.

## Summary

This PR introduces an embedded GLTG layer for AIVAN.

Before this PR, AIVAN-facing delivery paths were generated directly by the deterministic `calculate_lead_time_path()` function through `src.lead_time.path_enumerator.enumerate_delivery_paths()`.

After this PR, AIVAN-facing path enumeration routes through `src.gltg.engine.calculate_gltg_lead_time_path()`. The existing deterministic calculator remains the component-level core, but GLTG now wraps it and attaches model provenance, P50/P80/P90 lead-time estimates, explicit P80 feasibility basis, fallback status, and GLTG evidence references.

## Files Changed

| File | Purpose |
|---|---|
| `src/gltg/__init__.py` | New GLTG package exports |
| `src/gltg/engine.py` | Embedded GLTG engine; wraps deterministic lead-time calculator and adds P50/P80/P90/provenance |
| `src/lead_time/models.py` | Adds GLTG fields to `LeadTimePath` |
| `src/lead_time/path_enumerator.py` | Routes AIVAN path enumeration through GLTG |
| `src/lead_time/__init__.py` | Exports GLTG calculation entry point |
| `tests/test_aivan_gltg_integration.py` | Regression tests proving AIVAN uses GLTG |

## Product Rules Added

1. AIVAN-facing delivery paths must expose `model_name == "GLTG"`.
2. AIVAN-facing delivery paths must expose `p50_lead_time_days`, `p80_lead_time_days`, and `p90_lead_time_days`.
3. P80 is the default buyer deadline feasibility basis.
4. GLTG fallback status must be explicit: `fallback_model_used` cannot be silently omitted.
5. GLTG must append an evidence reference so downstream buyer options can trace model provenance.

## Verification Expected

Run:

```bash
uv sync
uv run pytest tests/test_aivan_gltg_integration.py -q --tb=short
uv run pytest -q --tb=short
python -m compileall src scripts tests -q
```

The full CI should also run automatically on the PR.

## Notes

This is a local embedded GLTG implementation. It deliberately avoids external service calls and live credentials. A future dedicated GLTG service or separate GLTG package can replace the internal engine behind the same `calculate_gltg_lead_time_path()` interface.
