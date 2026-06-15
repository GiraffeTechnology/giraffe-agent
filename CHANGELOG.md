# Changelog

All notable changes to Giraffe Agent / AIVAN are recorded here.

---

## [0.1.0-clawhub] — 2026-06-15

### Tag candidate
`v0.1.0`

### Classification
First ClawHub-ready release of the AIVAN OpenClaw plugin bridge.
AIVAN (AI trade salesperson) is the public-facing product name for Giraffe Agent's
trade salesperson workflow, published as the first Giraffe Technology OpenClaw
ecosystem release.

### Added
- `integrations/openclaw-aivan-plugin/package.json` — ClawHub code plugin package
  metadata (`@giraffetechnology/openclaw-aivan v0.1.0`) with OpenClaw compatibility
  fields (`pluginApi`, `openclawVersion`, `extensions`)
- `integrations/openclaw-aivan-plugin/index.ts` — thin OpenClaw plugin bridge
  implementing `aivan.health`, `aivan.forwardEvent`, `aivan.openDashboard`,
  `aivan.getPendingDrafts`, `aivan.approveDraft`, `aivan.rejectDraft`; fails safely
  when AIVAN is not running; never logs secrets; never bypasses approval gate
- `integrations/openclaw-aivan-plugin/README.md` — installation, environment
  variables, mock mode, human approval gate, local data boundary, test and
  publication instructions
- `integrations/openclaw-aivan-plugin/SECURITY.md` — credential policy, approval gate,
  anti-bot boundaries, local data boundary, risk screening scope
- `skills/aivan-trade-salesperson/SKILL.md` — lightweight ClawHub skill listing that
  teaches OpenClaw when to route trade-salesperson workflows to the AIVAN plugin
- `scripts/validate_clawhub_aivan_plugin.py` — pre-publication validator: checks
  package metadata, OpenClaw compatibility fields, env-var documentation, skill
  listing, and absence of hardcoded secrets
- `scripts/run_aivan_openclaw_plugin_smoke_test.py` — smoke test: missing
  `AIVAN_BASE_URL` fails safely; health, event forwarding, pending drafts, and
  approve/reject round-trip verified; approval gate not bypassable
- `api/main.py` — new AIVAN/OpenClaw endpoints:
  - `POST /api/openclaw/events` — normalized event intake for the plugin bridge
  - `GET /api/openclaw/drafts/pending` — list drafts awaiting human approval
  - `POST /api/openclaw/drafts/{draft_id}/approve` — human approval action
  - `POST /api/openclaw/drafts/{draft_id}/reject` — rejection action
- `.env.example` — safe environment variable template (no real credentials)
- `SECURITY.md` — root security policy covering credential storage, approval gate,
  anti-bot rules, local data boundary, LLM key optionality, and risk screening scope
- README.md `## ClawHub / OpenClaw Plugin Publication` section with dry-run and
  publish commands for both the code plugin and the optional skill listing

### Security
- No credentials stored in plugin or service
- Human approval required for all outbound trade messages
- Mock mode confirmed working without any external API keys
- No direct IM/channel connections from AIVAN

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
