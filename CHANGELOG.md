# Changelog

All notable changes to Giraffe Agent are recorded here.

---

## [BM_DB_INTEGRATION_V1_3_TRUST_BOUNDARY] — 2026-06-13

### Tag candidate
`BM_DB_INTEGRATION_V1_3_TRUST_BOUNDARY`

### Classification
v1.3 adds the trust boundary and rule integrity layer.  No new product features.

### Summary
8/8 trust suites pass, including regression guards for all prior layers (v1.0 baseline,
v1.1 hardening, v1.2 replay/decision packet) and 5 new trust-specific suites.

### Added
- `rule_packet_registry.py` — immutable, SHA-256-hashed rule packets for 7 lifecycle phases; fails closed on missing/deprecated/hash-mismatch
- `evidence_guard.py` — validates supplier response fields against source evidence; flags placeholders, ai_inferred without risk flags, missing fields; writes `AI_OUTPUT_EVIDENCE_GAP` events
- `human_confirmation.py` — manages `HUMAN_CONFIRMATION_REQUIRED`, `HUMAN_CONFIRMATION_RECEIVED`, `HUMAN_OVERRIDE_DETECTED` execution events; gates edge APPROVED
- `bm_db_v13_trust_test.py` — 8-suite trust runner (v1.0/v1.1/v1.2 regression + 5 new suites)
- `BM_DB_INTEGRATION_V1_3_TRUST_BOUNDARY_REPORT.md` — full trust report
- Sample artifacts: `sample_rule_packet.json`, `sample_human_confirmation_event.json`, `sample_override_detection_event.json`, `sample_decision_packet_with_evidence.md`

### Verified (all 8 suites)

| Suite | Result |
|-------|--------|
| Baseline v1.0 Regression (verify_integration --runs 5) | PASS |
| v1.1 Hardening Regression (bm_db_hardening) | PASS |
| v1.2 Replay + Decision Packet Regression | PASS |
| T1. Rule Packet Registry | PASS |
| T2. Evidence Guard | PASS |
| T3. Human Confirmation & Override Detection | PASS |
| T4. Rule Packet + Evidence Guard Integration | PASS |
| T5. Five-run Reproducibility (v1.3 full stack) | PASS |

---

## [BM_DB_INTEGRATION_V1_2_REPLAY_DECISION_PACKET] — 2026-06-13

### Tag candidate
`BM_DB_INTEGRATION_V1_2_REPLAY_DECISION_PACKET`

### Classification
v1.2 adds the first buyer-facing output layer.  No new product features.

### Summary
4/4 suites pass on a fresh DB, including 5-run reproducibility.  Baseline v1 and v1.1
hardening both pass as regression guards inside the v1.3 suite.

### Added
- `execution_graph_replay.py` — `replay_project(db_url, project_id) → dict`; reconstructs full B/M-side execution graph with event timeline; CLI with `--format json|md`
- `decision_packet_generator.py` — `generate_packet(db_url, project_id) → dict`; buyer-facing decision packet with evidence links; `human_confirmation_required=True` always; CLI with `--output file.json|md`
- `bm_db_v12_replay_test.py` — 4-suite test runner
- `BM_DB_INTEGRATION_V1_2_REPLAY_DECISION_PACKET_REPORT.md` — full v1.2 report
- Sample artifacts: `sample_execution_graph.json`, `sample_execution_graph.md`, `sample_decision_packet.json`, `sample_decision_packet.md`

### Verified (all 4 suites)

| Suite | Result |
|-------|--------|
| 1. Execution Graph Replay — Output Shape | PASS |
| 2. Decision Packet — Output Shape + Evidence Rules | PASS |
| 3. Markdown Rendering | PASS |
| 4. Five-run Reproducibility | PASS |

---

## [BM_DB_INTEGRATION_V1_1_HARDENING] — 2026-06-13

### Tag candidate
`BM_DB_INTEGRATION_V1_1_HARDENING`

### Classification
BM DB Integration Baseline v1 is a reproducible integration baseline, not yet a
production-hardening release.  v1.1 adds targeted stability proofs — no new
product features.

### Summary
8/8 hardening suites pass, including a Baseline v1 regression guard that runs
`verify_integration.py --runs 5` as a sub-process before each hardening run.
One bug was found and fixed (see below).

### Added
- `bm_db_hardening.py` — 8-suite hardening runner (Baseline v1 regression guard
  + 7 new suites)
- `bm_db_adapter.py` — new query helpers: `list_project_responses`,
  `list_inquiry_responses`, `list_project_events`, `list_project_inquiries`,
  `list_project_edges`, `check_graph_consistency`
- `BM_DB_INTEGRATION_V1_1_HARDENING_REPORT.md` — full hardening report

### Fixed
- **Idempotency test used absolute counts on shared DB**: Suite 1 initially
  failed because it asserted `actors == 2` (absolute) against a DB that already
  had rows from the Baseline v1 Regression guard.  Fixed by switching to delta
  counts (snapshot before test, assert zero growth on second same-key run).

### Verified (all 8 suites)

| Suite | Result |
|-------|--------|
| Baseline v1 Regression (verify_integration --runs 5) | PASS |
| 1. Idempotency | PASS |
| 2. Incomplete Supplier Reply | PASS |
| 3. Conflicting Supplier Reply | PASS |
| 4. Full Order Lifecycle | PASS |
| 5. Procurement Graph Consistency | PASS |
| 6. DB-off / DB-on Parity | PASS |
| 7. Five-run Reproducibility | PASS |

---

## [BM_DB_INTEGRATION_BASELINE_V1] — 2026-06-13

### Tag
`BM_DB_INTEGRATION_BASELINE_V1`

### Classification
BM DB Integration Baseline v1 is a reproducible integration baseline, not yet a
production-hardening release.

### Summary
First fully reproducible B/M-side DB integration baseline.  The integration
package previously did not exist in a runnable form; five distinct failure modes
were identified and resolved.  The verifier now passes 5/5 runs with clean
PRAGMA checks against a fresh SQLite database.

### Added
- `pydantic_stub.py` — re-export shim so `import pydantic_stub` resolves;
  provides a minimal `BaseModel` fallback when pydantic is absent
- `build_schema.py` — schema builder using `GIRAFFE_DB_URL` / `--url`; no
  hard-coded paths; `create_all` idempotent against an existing DB
- `bm_db_adapter.py` — unified adapter with lazy `src.db.*` imports;
  `_mode=off` uses `_MemStore` (pure in-memory); `_mode=on` uses real
  SQLAlchemy repositories; `get_or_create_actor` and `get_or_create_project`
  for idempotency; `update_edge` back-fills `inquiry_id`, `response_id`, status
- `run_bm_e2e_with_db.py` — end-to-end runner; adds `sys.path` fixup; handles
  both `GIRAFFE_DB_MODE=off` and `GIRAFFE_DB_MODE=on`; auto-creates schema in
  on-mode
- `verify_integration.py` — reproducibility verifier; `--db` and `--runs` args;
  runs full 11-step lifecycle per iteration; asserts row counts for 8 tables;
  checks `procurement_edges.inquiry_id` and `.response_id` linkage; asserts
  `edge.status == APPROVED`; runs `PRAGMA integrity_check` and
  `PRAGMA foreign_key_check` at end
- `docs/BM_DB_INTEGRATION_BASELINE_v1.md` — full test report
- `TEST_RESULT.md` — machine-readable test result record

### Fixed
- `ModuleNotFoundError: pydantic_stub` — module now exists
- `ModuleNotFoundError: src` in `run_bm_e2e_with_db.py` — explicit
  `sys.path` fixup at script top
- Hard-coded absolute migration path in `build_schema.py` — replaced with
  `--url` / `GIRAFFE_DB_URL`
- `verify_integration.py` bypassed `bm_db_adapter.py` and wrote raw sqlite
  rows — verifier now goes exclusively through `BMDbAdapter`
- DB-off mode broken by module-level `src.db.*` imports in
  `bm_db_adapter.py` — all such imports are now lazy

### Changed
- `README.md` — E2E Verification section now includes the B/M-side DB
  Integration Baseline v1 block with commands, result, and link to report

### Verified
| Check | Result |
|-------|--------|
| `python -m py_compile *.py` | PASS |
| `GIRAFFE_DB_MODE=off python run_bm_e2e_with_db.py` | PASS |
| `GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db python run_bm_e2e_with_db.py` | PASS |
| `python verify_integration.py --db sqlite:///./test.db --runs 5` | 5/5 PASS |
| `PRAGMA integrity_check` | ok |
| `PRAGMA foreign_key_check` | ok |

---

## [MVP v1.0] — 2026-05-26

Initial MVP release covering:

- AI Buyer (B-side): requirement structuring, bilingual inquiry drafting,
  delivery feasibility simulation
- Supplier Response Agent (M-side): intake, normalization,
  `SupplierResponsePacket`
- Role-Switching Procurement Agent: recursive `UPSTREAM_B_SIDE` logic,
  upstream inquiry builder, option engine, approval gate
- Professional Free CAD↔CNC Matching: `CADRequirementPacket`,
  `CapabilityFitReport`, machine profile matching (no encryption, no
  watermarking)
- AI Merchandiser: post-confirmation milestones, production/QC/exception
  updates, logistics handover, buyer sign-off
- Cainiao-like logistics ingestion: carrier API normalization, shipment
  tracking
- Database layer: SQLAlchemy 2.x models, Alembic, SQLite (local) /
  PostgreSQL-compatible schema
- Dynamic self-learning schema: observe → propose → approve field lifecycle
- Industrial Execution Graph v0.1: append-only `ExecutionEvent` log
- OpenClaw skill manifest, WeChat/WhatsApp/Web channel adapters
