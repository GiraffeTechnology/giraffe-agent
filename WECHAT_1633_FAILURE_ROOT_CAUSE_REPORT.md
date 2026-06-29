# WeChat 16:33 Failure — Root Cause Report

Debug of the real mobile WeChat failure (bot **WeixinClawBot**, ~16:33 local).
Investigation done from a build sandbox (code + local reproduction). The live
production server is not reachable from the sandbox, so the 16:33 server-side
logs could not be read directly; the root cause was established from the deploy
configuration, the deployed code, and a local reproduction of the exact messages.

## 1. Real-test evidence acknowledged
Yes — a real mobile WeChat test against **WeixinClawBot** at ~16:33. No new
physical WeChat test was requested.

## 2. Exact real messages
```
帮我询价，1000件纯棉T恤，交加拿大
询价5000件格子衬衫，45天交东京，高品质
```

## 3. Exact observed WeChat failure reply
```
⚠️ Agent couldn't generate a response. Please try again.
```

## 4. Deployed artifact
`.github/workflows/deploy-server.yml` deploys **this `giraffe-agent` repo** as the
production "AIVAN": systemd `aivan.service` runs `uvicorn api.main:app` from
`/opt/giraffe/giraffe-agent` on **:8000**, and the OpenClaw gateway is pointed at
`AIVAN_BASE_URL=http://localhost:8000`. Deployed code was at `main` (`96d2052`),
the commit *before* any fail-soft handling.

## 5. Was the fail-soft fix deployed?
**No.** The fail-soft envelope had been merged only into the sibling `aivan` repo
(its PR #16). Production runs `giraffe-agent`, whose `api/main.py` had **no global
exception handler** and **no `reply_text`/`output` error envelope**:
- `/api/skill/invoke` and `/api/openclaw/events` returned `adapt_openclaw_event(...)` directly with no error wrapping.

## 6. Did OpenClaw receive the messages?
**Yes** — OpenClaw emitted "Agent couldn't generate a response", which is its own
message for an empty/failed agent result; it could only do so after receiving the
WeChat message and invoking the skill.

## 7. Did the bridge call AIVAN?
**Yes** (the bridge's only action is to POST the event to AIVAN). The exact HTTP
outcome is not in the sandbox's reach.

## 8. Which AIVAN endpoint?
`POST {AIVAN_BASE_URL}/api/openclaw/events` (and/or `/api/skill/invoke`) on
`http://localhost:8000`.

## 9. HTTP status from AIVAN
Not directly observed (no server logs). Structural + reproduction evidence points
to **HTTP 500** (uncaught dependency error, no fail-soft handler) as the dominant
case; a **401** is possible on the auth-guarded `/api/openclaw/events` if the
gateway's API key did not match.

## 10. AIVAN response body
Before the fix: a raw FastAPI 500 (or 401 JSON), no skill envelope. After the fix
(reproduced locally on real `api.main:app`): HTTP 200 with
`{"status","output","reply_text"}` for both exact 16:33 messages.

## 11/12. reply_text / output present?
Before: **No** on the error path. After: **Yes** for both.

## 13. Did the bridge return visible text to OpenClaw?
**No** — an OpenClaw bridge turns a non-2xx / unreachable AIVAN into an empty
agent result, which is exactly the generic WeChat error. Fixing AIVAN to always
return a 200 envelope removes the trigger.

## 14. Primary root cause
**A — Deployed server was not running the fail-soft fix.** Production serves
`giraffe-agent` `api.main:app` @ `96d2052`, which had no global fail-soft handler;
a backend-dependency error (GLTG `:8766` not started, giraffe-db, or LLM) became a
**raw HTTP 500** (mechanism **F**), which the OpenClaw bridge converted into an
empty agent result (mechanism **E**). Process cause: the fix had landed in the
`aivan` repo while production deploys `giraffe-agent`.

## 15. Fix applied
**Applied in this PR (giraffe-agent).** `api/main.py`:
- Global `@app.exception_handler(Exception)` that fails soft for the skill paths
  (`/invoke`, `/api/skill/invoke`, `/api/openclaw/events`) → HTTP 200
  `{status:"error", output, reply_text}`; other routes keep 500 semantics.
- `_skill_envelope()` guarantees `status`/`output`/`reply_text` on skill responses.
- `GET /healthz` and `POST /invoke` registered on the root app; `/invoke`
  normalizes OpenClaw-standard, WeChat-webhook, and native-event bodies.
- Regression tests in `tests/test_openclaw_skill_failsoft.py` (the exact 16:33
  messages, forced dependency error, /healthz, /invoke).

Verification (local, real `api.main:app` on :8000):
- `GET /healthz` → 200.
- `POST /api/skill/invoke` (both 16:33 messages) → 200, `status:ok`, meaningful reply.
- `POST /invoke` (WeChat-webhook shape) → 200, extracts 产品/数量/目的地.
- Forced dependency error → 200 `status:error` with the degraded reply (never 500).
- Suite: 643 passed, 2 skipped, 1 pre-existing GLTG-infra E2E failure unrelated to this change.

## 16. Remaining manual acceptance step
Merge + deploy this PR, ensure GLTG/giraffe-db/LLM are up and the WeChat device
pairing/scope is approved, then re-send the message from the phone for a final
meaningful reply.

---

ROOT CAUSE FOUND — CODE PR REQUIRED
