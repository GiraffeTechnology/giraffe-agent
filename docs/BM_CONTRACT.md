# B↔M Contract

This document defines the data contract between the B-side (AI Buyer) and
M-side (AI Merchandiser) through the B+M Bridge.

---

## Dispatch: B-side → M-side

When the B-side has a structured requirement and has drafted a supplier inquiry,
it dispatches to one or more suppliers via `dispatch_supplier_inquiry()`.

### Input: `BWWorkspace` (must have)

| Field | Type | Description |
|-------|------|-------------|
| `b_workspace_id` | str | Unique buyer workspace ID |
| `rfq_id` | str | RFQ identifier from `BuyerRequirement` |
| `supplier_inquiry_draft` | `SupplierInquiryDraft` | Must be set before dispatch |
| `buyer_requirement` | `BuyerRequirement` | Structured requirement |

### Output: `list[SupplierInquiryContext]`

One context per dispatched supplier:

| Field | Type | Description |
|-------|------|-------------|
| `m_workspace_id` | str | Unique M-side workspace ID (`mw_XXXX`) |
| `b_workspace_id` | str | Linked B-side workspace |
| `rfq_id` | str | Shared RFQ identifier |
| `inquiry_id` | str | Inquiry identifier |
| `supplier_id` | str | Target supplier |
| `invitation_token` | str | `GQ-XXXXXXXX` token for supplier identity |
| `inquiry_text_zh` | str | Mandarin inquiry message |
| `inquiry_text_en` | str | English inquiry message |

**Events logged:** `M_SUPPLIER_INQUIRY_DISPATCHED`

---

## Response: M-side → B-side

When a supplier responds and the M-side normalizes their message, it pushes
the structured response back to the B-side via `push_supplier_response_to_b_side()`.

### Input: `SupplierResponsePacket`

| Field | Type | Description |
|-------|------|-------------|
| `m_workspace_id` | str | Source M-side workspace |
| `b_workspace_id` | str | Target B-side workspace |
| `supplier_id` | str | Responding supplier |
| `capacity_signal.can_make` | bool\|None | Can produce the item |
| `schedule_signal.estimated_lead_time_days` | int\|None | Lead time in days |
| `quote.unit_price` | float\|None | Unit price |
| `quote.currency` | str\|None | Currency code |
| `completeness_score` | float | 0.0–1.0 response completeness |
| `confidence_score` | float | 0.0–1.0 overall confidence |
| `red_flags` | list[str] | Any identified issues |

### Output: dict

```json
{
  "ok": true,
  "supplier_id": "sup_001",
  "b_workspace_id": "bw_XXXX",
  "can_make": true
}
```

**Events logged:** `M_RESPONSE_ATTACHED_TO_B_WORKSPACE`

---

## Order Creation: B-side → M-side

After the buyer selects a delivery path, `create_order_execution_from_selected_path()`
creates an `OrderExecutionContext` that drives M-side execution.

### Input

| Parameter | Type | Description |
|-----------|------|-------------|
| `b_workspace_id` | str | Source B-side workspace |
| `selected_path_id` | str | Selected `DeliveryPath.path_id` |

### Output: `OrderExecutionContext`

| Field | Type | Description |
|-------|------|-------------|
| `order_execution_id` | str | Unique order ID (`ORD-XXXX`) |
| `status` | str | Initial: `order_acknowledgement_pending` |
| `milestones` | list | Category-specific production milestones |
| `supplier_id` | str | Assigned supplier |
| `m_workspace_id` | str | Linked M-side workspace |

---

## Invariants

1. `b_workspace_id` links a workspace across all stages.
2. `rfq_id` is immutable after `structure_requirement()` runs.
3. `can_make=True` is required for a supplier to appear in `FeasibilityReport.paths`.
4. `invitation_token` must start with `GQ-` and is supplier-specific.
5. M-side must not modify the B-side workspace directly; only `push_supplier_response_to_b_side()` may append to `supplier_responses`.

---

## Known Issue

> **M-side unknown supplier dispatch** currently returns HTTP 200 with
> `ok=true` and `dispatched=0` when `supplier_ids` contains unknown IDs.
> It should return HTTP 404 or 422 with:
> ```json
> {"ok": false, "dispatched": 0, "missing_supplier_ids": ["sup_unknown"]}
> ```
> This will be fixed in v0.2.0.
