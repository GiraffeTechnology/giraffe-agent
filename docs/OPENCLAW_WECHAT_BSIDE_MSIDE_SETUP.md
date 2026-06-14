# OpenClaw + Giraffe B-side / M-side Setup Guide

## Overview

This guide explains how to connect OpenClaw WeChat and Email channels to the
Giraffe procurement execution skill. OpenClaw owns all IM / Email / WeChat /
WhatsApp / Telegram channels. Giraffe owns procurement execution logic.

**Giraffe never directly connects to WeChat, Email, WhatsApp, or any IM platform.**

---

## Architecture

```
Customer WeChat / Email
  → OpenClaw channel plugin
  → OpenClaw normalized event
  → POST {GIRAFFE_API_BASE}/api/skill/invoke
  → Giraffe B-side procurement workflow
  → reply_text / missing_fields / message_drafts
  → OpenClaw sends customer reply

Supplier WeChat / Email
  → OpenClaw channel plugin
  → OpenClaw normalized event
  → POST {GIRAFFE_API_BASE}/api/skill/invoke
  → Giraffe M-side supplier response workflow
  → supplier_response_received / identified_fields / missing_fields
  → OpenClaw sends reply if needed
```

---

## Step 1: Install the Giraffe Procurement Skill

Copy the skill definition to your OpenClaw workspace:

```bash
mkdir -p ~/.openclaw/workspace/skills/giraffe-procurement
cp openclaw/skills/giraffe-procurement/SKILL.md \
   ~/.openclaw/workspace/skills/giraffe-procurement/SKILL.md
```

Set the Giraffe API base URL in your OpenClaw configuration:

```bash
export GIRAFFE_API_BASE=http://localhost:8000
```

Or add to `~/.openclaw/config.yaml`:

```yaml
skills:
  giraffe-procurement:
    api_base: http://localhost:8000
```

Restart the OpenClaw gateway:

```bash
openclaw gateway restart
```

---

## Step 2: Start the Giraffe Agent

```bash
cd /path/to/giraffe-agent
uv run uvicorn api.main:app --reload --port 8000
```

Verify the API is running:

```bash
curl http://localhost:8000/health
# {"status": "ok", "service": "giraffe-agent"}
```

---

## Step 3: Configure OpenClaw Channels

### WeChat / Weixin Channel

> **IMPORTANT:** Real WeChat integration is complete only after the OpenClaw
> Weixin plugin is installed, logged in by QR code, and tested against a real
> WeChat message. The steps below configure the routing — they do not complete
> WeChat integration by themselves.

In OpenClaw, configure the Weixin channel plugin and point it to the
Giraffe skill endpoint. When a WeChat message arrives, OpenClaw should:

1. Normalize it into an OpenClaw event payload.
2. POST to `{GIRAFFE_API_BASE}/api/skill/invoke`.
3. Read `reply_text` from the Giraffe response.
4. Send `reply_text` back to the WeChat conversation.
5. If `approval_required=true`, show `message_drafts` to the salesperson
   and wait for approval before dispatching.
6. If `status=approved_for_dispatch`, dispatch all messages in `outbound_messages`.

### Email Channel

> **IMPORTANT:** Real Email integration is complete only after the OpenClaw
> Email channel is configured and tested against real inbound and outbound
> email. The steps below configure the routing — they do not complete Email
> integration by themselves.

Configure OpenClaw Email channel similarly. Inbound emails are normalized
into OpenClaw events and sent to Giraffe. Giraffe returns structured replies
that OpenClaw sends via SMTP or the configured email provider.

---

## Step 4: Verify Both Flows

### B-side Flow (Customer → Giraffe → Supplier Draft)

```bash
# Simulate a customer WeChat message
uv run python scripts/test_openclaw_bside_invoke.py
```

This test covers:
1. Buyer sends procurement request
2. Giraffe creates B-side project and identifies missing fields
3. Buyer provides missing fields
4. Giraffe generates supplier inquiry draft
5. Draft requires human approval
6. Salesperson approves — outbound payload returned to OpenClaw
7. OpenClaw sends supplier inquiry

### M-side Flow (Supplier Reply → Giraffe → Response Parsed)

```bash
# Simulate a supplier email reply
uv run python scripts/test_openclaw_mside_invoke.py
```

This test covers:
1. Supplier replies via OpenClaw email
2. Giraffe receives M-side event
3. Supplier response is parsed (price, lead time, fabric weight, etc.)
4. Missing fields are identified
5. No direct sending occurs — Giraffe only returns structured data

---

## API Reference: `/api/skill/invoke`

### OpenClaw Event Payload

```json
{
  "source": "openclaw",
  "channel": "openclaw-weixin",
  "channel_account_id": "wechat_account_001",
  "conversation_id": "wechat_dm_or_email_thread_id",
  "sender_id": "external_peer_id",
  "sender_display_name": "optional display name",
  "message_text": "采购助理，帮我询价 10000 件白色纯棉衬衣，45 天内交温哥华。",
  "message_type": "text",
  "attachments": [],
  "timestamp": "2026-06-14T00:00:00Z",
  "project_id": null,
  "procurement_edge_id": null,
  "actor_id": null,
  "role_context": null,
  "mode": "auto"
}
```

### Mode Values

| mode | behavior |
|------|---------|
| `b_side` | Force B-side / customer-facing workflow |
| `m_side` | Force M-side / supplier response workflow |
| `auto` | Auto-detect from conversation binding, project context, and message intent |
| *(missing)* | Same as `auto` |

### Response Shape

```json
{
  "ok": true,
  "project_id": "RFQ-XXXXXXXX",
  "b_workspace_id": "bw_xxxx",
  "mode": "b_side",
  "status": "missing_fields",
  "reply_text": "已创建采购项目 ...",
  "missing_fields": ["size_ratio", "fabric_weight"],
  "approval_required": false,
  "message_drafts": [],
  "outbound_messages": [],
  "execution_event_id": "evt_xxxxxxxxxxxx"
}
```

---

## Conversation Binding

Giraffe automatically creates a conversation binding when a new procurement
project is started. Future messages from the same sender / thread
(`source + channel + channel_account_id + conversation_id + sender_id`)
will automatically continue the same project.

Bindings are stored in `data/conversation_bindings/`.

### Binding Fields

| field | description |
|-------|------------|
| `source` | always `openclaw` |
| `channel` | `openclaw-weixin`, `openclaw-email`, etc. |
| `channel_account_id` | the OpenClaw account receiving the message |
| `conversation_id` | WeChat DM ID or email thread ID |
| `sender_id` | sender's external peer ID |
| `project_id` | the bound Giraffe procurement project (RFQ ID) |
| `b_workspace_id` | the B-side workspace |
| `mode` | `b_side` or `m_side` |
| `counterparty_type` | `customer`, `supplier`, `manufacturer`, etc. |

---

## Human Approval Gate

Giraffe never sends supplier-facing or customer-facing commercial messages
automatically.

**Supplier-facing messages:**
- Always saved as drafts with `approval_status=pending_approval`
- Returned as `message_drafts` with `approval_required=true`
- `outbound_messages` is empty before approval

**To approve:** The salesperson sends `确认发送` (or `approve` / `send it` /
`yes send`) in the same conversation. Giraffe marks the draft as approved
and returns `outbound_messages` for OpenClaw to dispatch.

**To reject:** The salesperson sends `取消` (or `reject` / `do not send`).
Giraffe marks the draft as rejected. No message is sent.

**Customer-facing commercial responses** also require approval when they
include quotation, delivery promise, contractual commitment, payment terms,
commercial terms, or supplier commitment.

---

## Trading Company Salesperson (Variable-M Role)

A trading company salesperson operates in two contextual roles:

| facing | role | description |
|--------|------|-------------|
| Customer | `CUSTOMER_FACING_M_SIDE` | Receives buyer requirements, creates procurement projects |
| Supplier | `UPSTREAM_B_SIDE` | Drafts supplier inquiries, collects responses |
| Execution | `TRADE_MERCHANDISER` | Post-confirmation order follow-up |

The same salesperson can switch roles depending on the counterparty. This is
the **Neutral Actor Model** — B-side / M-side are contextual roles, not fixed
company identities.

---

## Supplier Count Behavior

Giraffe does not require a minimum number of suppliers:

| situation | Giraffe behavior |
|-----------|-----------------|
| No supplier reply yet | Returns inquiry draft or asks for missing fields |
| 1 supplier replies | Returns `single_supplier_option_ready` |
| 2–3 suppliers reply | Returns `available_supplier_options_ready` |
| More than 3 suppliers reply | Returns `ranked_delivery_paths_ready` |
| Specific supplier inquiry | Generates targeted draft with `target_peer_id` if known |

---

## Warning: Integration Is Not Complete Without Channel Plugins

> **Real WeChat integration is not complete unless:**
> - The OpenClaw Weixin plugin is installed
> - The plugin is logged in by QR code
> - The plugin has been tested against a real WeChat message
>
> **Real Email integration is not complete unless:**
> - The OpenClaw Email channel is configured with the correct IMAP/SMTP settings
> - Inbound email delivery has been tested with a real incoming email
> - Outbound email sending has been tested with a real sent email
>
> This guide configures the routing and logic only. Channel plugins and
> credentials are managed entirely by OpenClaw — not by Giraffe.
