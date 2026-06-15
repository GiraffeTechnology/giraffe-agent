# User Manual — Giraffe Agent v1.0

**Apparel & Textile Industry Edition**

---

## Chapter 1: Introduction

Giraffe Agent is a C2M (Customer-to-Manufacturer) order execution platform for the apparel and textile industry. It coordinates buyer inquiries, supplier matching, RFQ, production monitoring, quality control, and logistics through a structured workflow with human approval gates at every critical decision point.

---

## Chapter 2: Getting Started

### 2.1 Account Registration

```http
POST /api/auth/register
{"email": "buyer@company.com", "password": "YourPassword123!"}
```

### 2.2 Login

```http
POST /api/auth/login
username=buyer@company.com&password=YourPassword123!
```

Returns an `access_token`. Include it in all subsequent requests:

```
Authorization: Bearer <token>
```

### 2.3 View Your Profile

```http
GET /api/auth/me
```

---

## Chapter 3: Participant Management

Participants represent factories, suppliers, logistics providers, and QC inspectors in your supply chain.

### 3.1 Register a Participant

```http
POST /api/participants
{"name": "Shenzhen Garment Co.", "country": "CN"}
```

### 3.2 Assign a Role

```http
POST /api/participants/{id}/roles
{"role_name": "MANUFACTURER"}
```

Available roles: `MANUFACTURER`, `FABRIC_SUPPLIER`, `TRIM_SUPPLIER`, `PACKAGING_SUPPLIER`, `LOGISTICS_PROVIDER`, `QC_INSPECTOR`, `BUYER`, `AGENT`

### 3.3 Update Participant Profile

```http
PATCH /api/participants/{id}
{"profile": {"moq_pcs": 500, "lead_time_days": 45}}
```

### 3.4 View Quality Ledger

```http
GET /api/participants/{id}/quality-ledger
```

---

## Chapter 4: Project and Buyer Inquiry

### 4.1 Create a Project

```http
POST /api/projects
{"title": "Summer 2026 T-Shirt Collection"}
```

### 4.2 Submit Buyer Inquiry

```http
POST /api/projects/{id}/buyer-inquiries
{"raw_text": "10,000 white cotton T-shirts, FOB Shenzhen, 60 days delivery"}
```

### 4.3 Generate Dynamic Form

The platform generates a structured form from your inquiry:

```http
POST /api/projects/{id}/dynamic-forms
{"inquiry_id": "<inquiry_id>"}
```

### 4.4 Lock the Form

Lock the form before creating RFQs:

```http
POST /api/dynamic-forms/{form_id}/lock
```

---

## Chapter 5: Participant Matching

Run the matching engine to score all participants against your project requirements:

```http
POST /api/projects/{id}/run-participant-matching
```

Returns a scored list with 12-dimension breakdowns and risk flags.

---

## Chapter 6: RFQ Workflow

### 6.1 Create an RFQ

```http
POST /api/projects/{id}/rfqs
{
  "form_version_id": "<version_id>",
  "recipient_participant_ids": ["<participant_id>"]
}
```

Returns an `rfq` and `approval_request_id`.

### 6.2 Approve the RFQ

```http
POST /api/approval-requests/{approval_id}/approve
{"review_notes": "Approved"}
```

### 6.3 Send the RFQ

```http
POST /api/rfqs/{rfq_id}/send
{"approval_id": "<approval_id>"}
```

### 6.4 Record Supplier Response

```http
POST /api/rfqs/{rfq_id}/responses
{
  "participant_id": "<pid>",
  "raw_response_text": "Unit price $8.50, lead time 52 days..."
}
```

---

## Chapter 7: Decision Packets and Order Creation

### 7.1 Generate Decision Packet

```http
POST /api/projects/{id}/decision-packets
{"rfq_id": "<rfq_id>"}
```

### 7.2 Approve the Packet

```http
POST /api/approval-requests/{approval_id}/approve
{"review_notes": "Approved"}
```

### 7.3 Approve an Option

```http
POST /api/decision-packets/{packet_id}/approve-option
{"option_id": "<option_id>", "approval_id": "<approval_id>"}
```

### 7.4 Create Order

```http
POST /api/projects/{id}/orders/from-approved-option
{
  "packet_id": "<packet_id>",
  "option_id": "<option_id>",
  "approval_id": "<approval_id>"
}
```

### 7.5 Confirm Order

```http
POST /api/orders/{id}/confirm
```

The order moves from `DRAFT_FROM_APPROVED_QUOTE` → `IN_PRODUCTION`.

---

## Chapter 8: Production Monitoring

### 8.1 View Production Monitoring

```http
GET /api/orders/{id}/production-monitoring
```

Returns all 12 milestones with status, planned dates, and predicted dates.

### 8.2 Update a Milestone

```http
PATCH /api/milestones/{id}
{"status": "IN_PROGRESS", "predicted_date": "2026-07-01T00:00:00Z"}
```

A `predicted_date` after the `planned_date` auto-sets status to `DELAYED`.

### 8.3 Run Delay Prediction

```http
POST /api/orders/{id}/run-delay-prediction
```

Returns `delay_risk_level` (ON_TRACK/LOW/MEDIUM/HIGH/CRITICAL) and `expedite_alert_required`.

### 8.4 Add Production Update

```http
POST /api/orders/{id}/production-updates
{"update_text": "Fabric arrived. Cutting started."}
```

---

## Chapter 9: Quality Control

### 9.1 Create QC Standard

```http
POST /api/orders/{id}/qc-standards
{"form_version_id": "<version_id>"}
```

### 9.2 Submit QC Record

```http
POST /api/orders/{id}/qc-records
{
  "label_compliance": true,
  "packaging_compliance": true,
  "fabric_defects": {"pin_holes": 0}
}
```

QC_PASSED → order moves to READY_TO_SHIP.
QC_FAILED → creates a QualityIncident.

### 9.3 List QC Records

```http
GET /api/orders/{id}/qc-records
```

---

## Chapter 10: Logistics

### 10.1 Create Shipment

```http
POST /api/orders/{id}/shipments
{
  "carrier": "COSCO",
  "tracking_number": "COSU123456",
  "trade_term": "FOB",
  "origin": "Shenzhen",
  "destination": "Hamburg"
}
```

Only available when order status is `READY_TO_SHIP`.

### 10.2 Add Tracking Event

```http
POST /api/shipments/{id}/tracking-events
{
  "event_type": "DELIVERED",
  "location": "Hamburg",
  "description": "Delivered to warehouse",
  "occurred_at": "2026-07-15T10:00:00Z"
}
```

A `DELIVERED` event transitions the order to `DELIVERED`.

### 10.3 View Shipment

```http
GET /api/shipments/{id}
```

---

## Chapter 11: Buyer Sign-Off

After delivery is confirmed:

```http
POST /api/orders/{id}/buyer-sign-off
```

Transitions order to `BUYER_SIGNED_OFF` and updates supplier memory for future matching.

---

## Chapter 12: Approval Management

### 12.1 List Pending Approvals

```http
GET /api/approval-requests?status=PENDING
```

### 12.2 View Approval

```http
GET /api/approval-requests/{id}
```

### 12.3 Approve

```http
POST /api/approval-requests/{id}/approve
{"review_notes": "Approved"}
```

### 12.4 Reject

```http
POST /api/approval-requests/{id}/reject
{"review_notes": "Rejected — price too high"}
```

---

## Chapter 13: Industrial Execution Graph

View the complete audit trail for any project, order, or participant:

```http
GET /api/execution-graph/projects/{id}
GET /api/execution-graph/orders/{id}
GET /api/execution-graph/participants/{id}
GET /api/execution-graph/events/{event_id}
```

Events are returned in chronological order and are immutable (append-only).
