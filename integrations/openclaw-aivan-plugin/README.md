# @giraffetechnology/openclaw-aivan

OpenClaw plugin bridge for **AIVAN** — a local-first AI trade salesperson assistant by [Giraffe Technology](https://giraffe.technology).

---

## What Is AIVAN?

AIVAN is an AI trade salesperson assistant built on Giraffe Agent. It runs locally on your machine and helps trading companies manage:

- Buyer inquiries received through IM channels (WeChat, WhatsApp, email, etc.)
- Supplier outreach and quotation collection
- Delivery feasibility analysis
- Order execution tracking
- Human-approved outbound message drafts

AIVAN is **local-first**: all procurement data, conversation bindings, and message drafts stay on your machine in a local SQLite database. No data is sent to any third-party cloud without your explicit action.

---

## What Does This Plugin Do?

This plugin is a **thin bridge** between the OpenClaw channel runtime and your locally-running AIVAN service.

It does **not**:
- Duplicate AIVAN's core procurement logic
- Store IM credentials, channel tokens, or platform passwords
- Send messages directly to any channel without AIVAN's approval gate
- Bypass login, CAPTCHA, anti-bot systems, access controls, or rate limits
- Make legal, credit, sanctions, or compliance decisions

It **does**:
- Receive normalized OpenClaw channel events (WeChat, WhatsApp, email, etc.)
- Forward trade-related events to your local AIVAN instance via its REST API
- Expose helper commands to check AIVAN health, open the dashboard, and manage draft approvals
- Return structured JSON results for every action
- Fail safely and return a clear error if AIVAN is not running

---

## How OpenClaw Connects to AIVAN

```
OpenClaw channel runtime (WeChat / WhatsApp / email / web)
  │
  │  normalized channel event
  ▼
@giraffetechnology/openclaw-aivan  (this plugin)
  │
  │  POST ${AIVAN_BASE_URL}/api/openclaw/events
  ▼
AIVAN local service (Giraffe Agent — http://localhost:8000)
  │
  ├─ routes event to B-side (buyer) or M-side (supplier) workflow
  ├─ generates reply draft
  └─ queues draft for human approval
         │
         │  human reviews draft in AIVAN dashboard
         │  POST /api/openclaw/drafts/{id}/approve   (via plugin or dashboard)
         ▼
      OpenClaw dispatches approved message through channel
```

AIVAN never receives raw IM tokens or platform credentials. OpenClaw owns all channel connections. AIVAN only sees normalized event payloads.

---

## Install

```bash
# Install from ClawHub
clawhub package install @giraffetechnology/openclaw-aivan

# Or install from source
npm install
```

### Prerequisites

- OpenClaw >= 5.0
- Node.js >= 18
- A running AIVAN service (see [Starting AIVAN](#starting-aivan))

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `AIVAN_BASE_URL` | No | `http://localhost:8000` | Base URL of your local AIVAN service |
| `AIVAN_API_KEY` | No | — | Optional API key for AIVAN (never logged by the plugin) |

Set these in your OpenClaw environment or `.env` file:

```bash
AIVAN_BASE_URL=http://localhost:8000
# AIVAN_API_KEY=your-optional-key-here
```

---

## Starting AIVAN

```bash
# Clone Giraffe Agent (the AIVAN backend)
git clone https://github.com/GiraffeTechnology/giraffe-agent
cd giraffe-agent

# Install dependencies (requires uv)
uv sync

# Copy environment template
cp .env.example .env
# Edit .env to add optional LLM credentials

# Start AIVAN in mock mode (no external API keys required)
uv run uvicorn api.main:app --reload

# AIVAN is now running at http://localhost:8000
# Dashboard / API docs: http://localhost:8000/docs
```

---

## Mock Mode

AIVAN runs in **mock mode by default** — no external API credentials are required. All LLM calls use rule-based mock responses. Mock mode is suitable for:

- Local development
- Integration testing
- Demo environments
- ClawHub plugin dry-runs

To enable real LLM responses, set `DASHSCOPE_API_KEY` (Qwen) in your `.env` file.

---

## Human Approval Gate

AIVAN **never** sends a message to a supplier or buyer without explicit human approval. Every outbound message goes through this gate:

1. AIVAN generates a reply draft based on the incoming event
2. The draft is stored locally with status `pending_approval`
3. A human reviews the draft in the AIVAN dashboard (`http://localhost:8000/docs`)
4. The human approves or rejects via:
   - AIVAN dashboard UI
   - `aivan.approveDraft` / `aivan.rejectDraft` plugin commands
   - `POST /api/openclaw/drafts/{id}/approve` REST endpoint
5. Only approved drafts are returned to OpenClaw for dispatch

The plugin enforces this gate by only calling AIVAN's approval API — it has no mechanism to send messages directly.

---

## Local-First Data Boundary

All procurement data is stored locally:

- `data/message_drafts/` — pending, approved, and rejected drafts
- `data/b_side_workspaces/` — buyer requirement workspaces
- `data/m_side_workspaces/` — supplier response workspaces
- SQLite database (when DB mode is enabled)

No procurement data, draft text, or conversation content is sent to any cloud service without your action.

---

## How to Test

### 1. Start AIVAN

```bash
cd giraffe-agent
uv run uvicorn api.main:app --reload
```

### 2. Run the smoke test

```bash
uv run python scripts/run_aivan_openclaw_plugin_smoke_test.py
```

### 3. Run plugin metadata validation

```bash
uv run python scripts/validate_clawhub_aivan_plugin.py
```

### 4. Run the full test suite

```bash
uv run pytest
```

---

## How to Dry-Run ClawHub Publication

```bash
# Install ClawHub CLI
npm i -g clawhub

# Log in
clawhub login
clawhub whoami

# Dry-run plugin publication
clawhub package publish integrations/openclaw-aivan-plugin --family code-plugin --dry-run
```

---

## Plugin Commands Reference

| Command | Description |
|---|---|
| `aivan.health` | Check whether AIVAN is running |
| `aivan.forwardEvent` | Forward an OpenClaw trade event to AIVAN |
| `aivan.openDashboard` | Open the AIVAN dashboard in a browser |
| `aivan.getPendingDrafts` | List message drafts awaiting approval |
| `aivan.approveDraft` | Approve a draft (human sign-off required) |
| `aivan.rejectDraft` | Reject a draft |

---

## License

Apache-2.0 — see [LICENSE](../../LICENSE)

Patent notice — see [PATENT_NOTICE.md](../../PATENT_NOTICE.md)
