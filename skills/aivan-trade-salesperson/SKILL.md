# AIVAN Trade Salesperson Skill

```yaml
name: aivan-trade-salesperson
version: 0.1.0
description: >
  Routes trade salesperson workflows — buyer inquiries, supplier outreach,
  quotation collection, and order execution — to a locally-running AIVAN
  service via the @giraffetechnology/openclaw-aivan plugin bridge.
  All outbound messages require human approval. No credentials are stored.

metadata:
  openclaw:
    requires:
      pluginApi: ">=1.0"
      plugins:
        - "@giraffetechnology/openclaw-aivan"
  clawhub:
    slug: aivan-trade-salesperson
    family: skill
    tags:
      - trade
      - procurement
      - salesperson
      - b2b
      - local-first
      - human-in-the-loop
```

---

## Purpose

This skill teaches OpenClaw when to route trade salesperson conversations and workflows to the AIVAN plugin bridge.

AIVAN handles:
- Buyer inquiry intake from IM channels (WeChat, WhatsApp, email, web)
- Structured requirement extraction from informal trade messages
- Bilingual supplier inquiry drafting (Chinese / English)
- Delivery feasibility simulation
- Supplier quotation normalization
- Order execution tracking
- Human-approved outbound message dispatch

This skill does **not** contain trade business logic. All logic runs inside the local AIVAN service.

---

## Required Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `AIVAN_BASE_URL` | Yes | — | Base URL of the local AIVAN service (e.g. `http://localhost:8000`) |
| `AIVAN_API_KEY` | No | — | Optional API key for authenticating to AIVAN (never logged) |

---

## When to Use This Skill

Use this skill when a user or OpenClaw channel event matches any of the following:

- A buyer sends an IM message that looks like a product inquiry, procurement request, or sourcing question
- A supplier sends a quotation, delivery confirmation, or production update via a trade channel
- A user asks to draft a supplier inquiry, check quotation status, or track an order
- A user wants to review or approve a pending outbound trade message
- A user asks about delivery feasibility, lead times, or upstream dependencies

Do **not** use this skill for:
- Consumer retail purchases
- Non-trade IM conversations (personal messages, support tickets, etc.)
- Automated actions without a human in the loop
- Any action that would bypass the AIVAN approval gate

---

## Operating Boundaries

### Human Approval Required
Every outbound trade message (to suppliers, buyers, logistics partners) must be explicitly approved by a human before dispatch. AIVAN queues drafts for review. This skill does not circumvent that gate.

### Local-First Data
All trade data, conversation bindings, and message drafts are stored locally by AIVAN. This skill does not route trade data to external cloud services.

### No Credential Handling
This skill does not handle, request, or store IM platform credentials, marketplace passwords, or payment information.

### No Legal or Compliance Decisions
AIVAN provides trade workflow assistance and risk indicators as decision support. It does not make legally binding compliance, sanctions, credit, or regulatory decisions.

---

## Example Invocation

When an OpenClaw trade channel event arrives:

```json
{
  "source": "openclaw",
  "channel": "openclaw-weixin",
  "conversation_id": "conv_abc123",
  "sender_id": "wechat_user_xyz",
  "message_text": "你好，我需要采购1000件棉质T恤，能否提供报价？",
  "project_id": "proj_456"
}
```

The skill routes this to the AIVAN plugin:

```
aivan.forwardEvent(event)
  → POST http://localhost:8000/api/openclaw/events
  → AIVAN structures requirement, drafts supplier inquiry
  → Draft queued for human approval
  → Human approves via dashboard or aivan.approveDraft
  → OpenClaw dispatches approved message
```

---

## How to Test

```bash
# Start AIVAN
uv run uvicorn api.main:app --reload

# Check AIVAN is running
curl http://localhost:8000/health

# Run the smoke test
uv run python scripts/run_aivan_openclaw_plugin_smoke_test.py

# Run full validation
uv run python scripts/validate_clawhub_aivan_plugin.py
```

---

## ClawHub Publication

```bash
# Publish skill listing
clawhub skill publish skills/aivan-trade-salesperson \
  --slug aivan-trade-salesperson \
  --name "AIVAN Trade Salesperson" \
  --version 0.1.0 \
  --changelog "Initial AIVAN ClawHub skill listing"
```

---

## License

Apache-2.0 — see [LICENSE](../../LICENSE)

Patent notice — see [PATENT_NOTICE.md](../../PATENT_NOTICE.md)
