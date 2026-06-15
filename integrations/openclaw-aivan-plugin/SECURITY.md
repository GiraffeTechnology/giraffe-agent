# Security Policy — @giraffetechnology/openclaw-aivan

This document describes the security properties and operating boundaries of the AIVAN OpenClaw plugin bridge.

---

## No Credential Storage

This plugin does **not** store, cache, or transmit:

- IM platform credentials (WeChat tokens, WhatsApp Business API keys, etc.)
- Email server passwords or OAuth tokens
- Marketplace session cookies or authentication tokens
- Payment or banking credentials
- Any secrets beyond `AIVAN_API_KEY`, which is read from the environment and never logged

`AIVAN_API_KEY` is an optional API key for authenticating to the local AIVAN service. It is passed via the `X-AIVAN-API-Key` HTTP header and is never printed to logs, error messages, or console output.

---

## No Outbound Message Without Human Approval

This plugin **never** sends a trade message to a supplier, buyer, or any external party without AIVAN's human approval gate being satisfied.

The flow is:
1. The plugin forwards a normalized event to AIVAN.
2. AIVAN generates a draft and holds it in `pending_approval` state.
3. A human reviews and explicitly approves the draft.
4. Only then does OpenClaw dispatch the message through the channel.

The plugin has no code path to bypass step 3. It can only call `POST /api/openclaw/drafts/{id}/approve` or `POST /api/openclaw/drafts/{id}/reject` — both of which require the draft to already exist in AIVAN's local store.

---

## No Bypassing Anti-Bot or Platform Rules

This plugin does not:
- Automate login or authentication flows on any IM or marketplace platform
- Solve or bypass CAPTCHAs
- Simulate human interaction to circumvent rate limits
- Scrape, crawl, or harvest data from any platform in ways that violate their terms of service
- Act as a bot impersonating a human user on any channel

All channel access is handled by the OpenClaw channel runtime, which operates within documented platform APIs and rate limits.

---

## Local SQLite Data Boundary

All procurement state managed by AIVAN is stored locally:

- Message drafts: `data/message_drafts/*.json`
- Buyer workspaces: `data/b_side_workspaces/*.json`
- Supplier workspaces: `data/m_side_workspaces/*.json`
- SQLite database: `giraffe_agent.db` (when DB mode is enabled)

No procurement data, draft content, or conversation history is transmitted to any external server unless a human explicitly initiates that action.

---

## External LLM Keys Are Optional

AIVAN uses a Qwen (Alibaba DashScope) LLM integration for AI-assisted drafting. This is **optional**:

- If `DASHSCOPE_API_KEY` or `QWEN_API_KEY` is not set, AIVAN runs in mock mode using rule-based responses.
- When set, message text from OpenClaw events may be sent to the Qwen API for processing.
- Users should review Qwen's data processing terms before enabling this feature in production.

No other external LLM, cloud AI, or third-party API is called by AIVAN without explicit configuration.

---

## Risk Screening Is Decision Support Only

AIVAN may include trade risk indicators (sanctions lists, supplier risk signals, delivery feasibility estimates) as **decision support** for human trade professionals.

AIVAN does **not**:
- Make legally binding compliance decisions
- Issue sanctions clearances or denials
- Replace human legal judgment on export controls, trade compliance, or credit risk
- Provide financial, legal, or regulatory advice

All risk indicators are informational. Human users and their legal entities retain full responsibility for compliance decisions.

---

## Reporting Security Issues

To report a security vulnerability in this plugin or in Giraffe Agent, contact:

```
mich@giraffe.technology
```

Please include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact

We will acknowledge receipt within 5 business days.

---

## Scope of This Document

This policy covers:
- `@giraffetechnology/openclaw-aivan` (this plugin)
- The Giraffe Agent service that AIVAN is built on

It does not cover the OpenClaw channel runtime or ClawHub platform, which have their own security policies.
