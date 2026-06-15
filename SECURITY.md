# Security Policy — Giraffe Agent / AIVAN

---

## No Credential Storage

Giraffe Agent (the AIVAN backend service) does **not** store, cache, or transmit:

- IM platform credentials (WeChat, WhatsApp, DingTalk, LINE, email server passwords, etc.)
- Marketplace session tokens or authentication cookies
- Payment, banking, or financial credentials
- Buyer or supplier private keys

External LLM API keys (`DASHSCOPE_API_KEY`, `QWEN_API_KEY`) are read from environment variables and are never written to the database, log files, or workspace files.

---

## No Outbound Message Without Human Approval

All trade messages drafted by AIVAN (supplier inquiries, buyer replies, etc.) are held in a `pending_approval` queue until a human explicitly approves them.

- Drafts are stored locally in `data/message_drafts/`
- Approval is required via `POST /api/openclaw/drafts/{id}/approve`
- Rejection is available via `POST /api/openclaw/drafts/{id}/reject`
- No draft is dispatched to any channel without an explicit approval action

The approval gate cannot be bypassed through the plugin or the API in normal operation.

---

## No Bypassing Anti-Bot or Platform Rules

Giraffe Agent does **not**:
- Connect directly to WeChat, WhatsApp, DingTalk, LINE, or any IM platform
- Automate login, solve CAPTCHAs, or circumvent access controls on any platform
- Scrape marketplace data in violation of platform terms of service
- Simulate human interaction to evade rate limits

All IM channel access is handled exclusively by the OpenClaw channel runtime, which operates within documented platform APIs.

---

## Local SQLite Data Boundary

All procurement state is stored locally:

- `data/b_side_workspaces/` — buyer requirement and inquiry workspaces
- `data/m_side_workspaces/` — supplier response workspaces
- `data/message_drafts/` — pending, approved, and rejected message drafts
- `data/upstream/` — upstream dependency and approval records
- `giraffe_agent.db` — SQLite database (when `GIRAFFE_DB_MODE=on`)

No procurement data is transmitted to external servers without explicit user action.

---

## External LLM Keys Are Optional

The Qwen (DashScope) LLM integration is **optional**. Without API keys, AIVAN runs in mock mode using rule-based responses — no external API calls are made.

When LLM keys are set:
- Trade message text may be sent to the Qwen API for processing
- Users should review Qwen's data processing policies before use in production
- No other external LLM or cloud AI is used by default

---

## Risk Screening Is Decision Support Only

AIVAN may surface trade risk indicators (delivery feasibility, supplier history, etc.) as **decision support** for human trade professionals.

AIVAN does **not**:
- Make legally binding compliance decisions
- Issue sanctions clearances or export-control determinations
- Replace human judgment on credit risk or regulatory obligations
- Provide legal, financial, or regulatory advice

All risk indicators are informational. Human users and their organizations retain full legal responsibility for trade compliance decisions.

---

## Reporting Vulnerabilities

To report a security vulnerability, contact:

```
mich@giraffe.technology
```

Please include:
- A clear description of the vulnerability
- Steps to reproduce
- Estimated impact

We will acknowledge receipt within 5 business days.

---

## Scope

This policy covers the Giraffe Agent service and the `@giraffetechnology/openclaw-aivan` plugin bridge.

It does not cover the OpenClaw channel runtime, ClawHub platform, or third-party LLM providers, which have their own security policies.
