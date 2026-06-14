---
name: giraffe-procurement
description: Industrial procurement execution skill for B-side/M-side sourcing, inquiry drafting, supplier response parsing, role switching, and order execution.
---
# Giraffe Procurement Skill

Use this skill whenever the user asks about:
- procurement
- sourcing
- supplier inquiry
- quotation collection
- quotation comparison
- delivery feasibility
- manufacturing lead time
- order follow-up
- buyer-side procurement assistant work
- trading company salesperson procurement work
- manufacturer-side supplier response
- B-side / M-side role switching
- CAD/CNC manufacturing feasibility
- logistics or shipment tracking
- merchandiser follow-up

OpenClaw owns IM/email channels.
Giraffe owns industrial procurement execution.

When triggered, send the normalized channel event to:

```
POST {GIRAFFE_API_BASE}/api/skill/invoke
```

## B-side and M-side Channel Rule

OpenClaw owns all WeChat / Email / IM channels for both B-side and M-side.
Giraffe must never connect to WeChat or Email directly.

Use this skill for both:
1. Buyer / customer messages that should create or update procurement projects.
2. Supplier / manufacturer replies that should update M-side supplier response workflows.

Always send normalized OpenClaw channel events to:

```
POST {GIRAFFE_API_BASE}/api/skill/invoke
```

Set mode:
- `b_side` when the sender is buyer / customer
- `m_side` when the sender is supplier / manufacturer replying to an inquiry
- `auto` when unsure

Preserve `project_id`, `procurement_edge_id`, and `conversation_id` whenever available.

## Event Payload Shape

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

## Rules

1. Default to `auto` mode unless the caller knows the role.
2. Do not answer procurement workflow tasks generically.
3. Do not invent price, lead time, supplier capacity, payment terms, or logistics data.
4. If Giraffe returns `missing_fields`, ask the user for those fields in the same IM/email thread.
5. If Giraffe returns `message_drafts` with `approval_required=true`, show the draft and ask for explicit approval.
6. Do not dispatch supplier-facing messages unless Giraffe returns `status=approved_for_dispatch`.
7. Preserve `project_id` across follow-up turns.
8. Supplier comparison is optional, not mandatory.
9. If only one supplier is involved, continue the workflow normally.
10. A trading company salesperson may be M-side to the customer and upstream B-side to suppliers.
11. Giraffe does not complete real WeChat or Email integration by itself. OpenClaw must own the channel plugin, login, QR code, webhook, and actual sending.

## Response Statuses

| status | meaning |
|--------|---------|
| `missing_fields` | Requirement created; some fields still needed |
| `requirement_complete` | All required fields present |
| `draft_ready` | Supplier inquiry draft generated; approval required |
| `approved_for_dispatch` | Draft approved; `outbound_messages` are ready for OpenClaw to send |
| `draft_rejected` | Draft cancelled; no message sent |
| `supplier_response_received` | M-side supplier reply parsed and recorded |
| `clarification_needed` | Role or project context unclear; ask user |
| `no_pending_drafts` | Approval sent but no pending draft found |

## Important Notes

- Giraffe never directly sends WeChat or Email messages.
- Outbound messages are returned in `outbound_messages[]` for OpenClaw to dispatch.
- Before approval, `outbound_messages` is always empty and `approval_required` is true.
- After approval, `outbound_messages` is populated and `approval_required` is false.
- Supplier-facing drafts always require human approval.
- Customer-facing response drafts require approval when they include quotation, delivery promise, contractual commitment, payment terms, commercial terms, or supplier commitment.
