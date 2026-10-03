# English defaults and retained compatibility

This bounded change follows the owner's English working-language requirement. It does not restart a parallel product, remove multilingual recognition, rewrite repository history or change commercial approval rules.

## Changed defaults

- Order acknowledgement and supplier-response operator copy is English.
- Supplier clarification uses the existing English question map and an `en` language tag.
- The Qwen JSON-schema instruction and QC prompts are English. Canonical QC output populates `m_side_feedback_en`; the existing `m_side_feedback_zh` protocol field remains present and empty for new default output.
- Mock QC, logistics and embedded RFQ outputs use English. A supplied historical localized QC field remains unmodified; the formatter no longer invents a localized fallback.
- Escaped recognition vectors retain their runtime semantics. They are not proof that the reference parser itself implements a production translation boundary.

Relevant regression coverage is in `tests/test_canonical_english_defaults.py` and the existing operator-message, QC, Qwen, OpenClaw and model tests. These tests perform no real external model call or commercial send.

## What this change does not claim

The inventory at baseline `ad15fa661a36b878ed2363c7c13a85779e9c4551` covered 675 tracked text blobs and excluded two binary PNG fixtures. It found CJK text in 109 files: 27 source files, 12 scripts, 14 tests and 56 historical simulated-data files; no Markdown document contained CJK text. This is a bounded script scan, not proof that every Latin-script phrase is English.

The historical `data/b_side_workspaces` and `data/m_side_workspaces` snapshots are preserved. No historical business value is deleted or replaced merely to make a scan pass. Explicit multilingual fixtures and recognition dictionaries remain semantically intact. Remaining text has not been mislabeled as fully cleaned.

Several retained reference components still contain explicit localized compatibility fields and templates, including B-side/M-side inquiry builders, upstream inquiry/rollup builders, capability reports, and embedded Aivan response templates. Their protocol field names are not casually renamed or filled with English while still claiming to hold another language. This change does not certify these retained paths for canonical-only production persistence.

## Actual entry-point distinction

This repository's `api.main:app` mounts its reference `/invoke` and `/api/openclaw/events` adapter. Those routes are reachable if an operator independently runs that application; they are not described as unreachable files.

The separately released Aivan/MyAivan application uses `aivan.api.main:app` from the Aivan repository and does not mount this repository's `src.openclaw_skill` reference adapter. Its canonical language and commercial preview/approval changes are reviewed in that repository. Do not replace the selected application entry point with this reference app and assume those guarantees follow automatically.

Separately maintained application releases have their own entry points, workflow implementations and compatibility surfaces. Their release-specific findings belong in their own acceptance and deployment records. The current reference-repository tests do not certify another application merely because it retains a similar module name.

Deployment control must identify the actual configured service entry points and existing route exposure. This document changes neither deployment configuration nor network/security settings. Production acceptance exercises the selected Aivan and abcdYi native workflow, the compatible selected private DB and the real language-module contract; it does not silently substitute reference demonstration endpoints.

## Verification for this candidate

The full local suite passed: 665 tests, with two optional live-GLTG tests skipped. The subprocess E2E test used the existing repository CI GLTG fixture server on loopback; this is explicitly test-double evidence, not actual GLTG acceptance. Thirteen new default-language checks passed alongside existing security, approval and compatibility checks. Python compile and whitespace checks passed. Exact-head CI remains required before merge.

The standalone mock QC comparison script also passed all 26 assertions and now runs as a subprocess regression in the default-language suite. The real-Qwen smoke script was not exercised against a model: its existing missing-key guard reported SKIPPED. Its source assertions now require English canonical feedback and an empty legacy localized field.
