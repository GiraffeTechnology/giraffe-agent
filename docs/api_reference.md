# API Reference — Giraffe Agent v1.0

Base URL: `http://localhost:8000` (development)

All routes except `/health`, `/api/auth/register`, and `/api/auth/login` require:
```
Authorization: Bearer <jwt_token>
```

---

## Health

### GET /health
Returns platform health status.

**Response:** `{"status": "ok"}`

---

## Authentication

### POST /api/auth/register
Register a new user (creates a tenant).

**Body:** `{"email": "user@example.com", "password": "..."}`
**Response 201:** `{"id": "...", "email": "..."}`

### POST /api/auth/login
Login with email and password.

**Body (form):** `username=email&password=pass`
**Response 200:** `{"access_token": "...", "token_type": "bearer"}`

### GET /api/auth/me
Get current user profile.

**Response 200:** `{"id": "...", "email": "...", "tenant_id": "..."}`

---

## Participants

### POST /api/participants
Create a participant.

**Body:** `{"name": "...", "country": "CN"}`
**Response 201:** `ParticipantOut`

### GET /api/participants
List all participants in tenant.

**Response 200:** `[ParticipantOut]`

### GET /api/participants/{id}
Get a participant.

**Response 200:** `ParticipantOut`

### PATCH /api/participants/{id}
Update participant.

**Body:** `{"profile": {...}}`
**Response 200:** `ParticipantOut`

### POST /api/participants/{id}/roles
Assign a role to participant.

**Body:** `{"role_name": "MANUFACTURER"}`
**Response 201:** `RoleOut`

### GET /api/participants/{id}/quality-ledger
Get quality incidents for participant.

**Response 200:** `[QualityIncidentOut]`

---

## Projects

### POST /api/projects
Create a project.

**Body:** `{"title": "..."}`
**Response 201:** `ProjectOut`

### GET /api/projects
List all projects.

**Response 200:** `[ProjectOut]`

### GET /api/projects/{id}
Get a project.

**Response 200:** `ProjectOut`

### POST /api/projects/{id}/buyer-inquiries
Submit a buyer inquiry.

**Body:** `{"raw_text": "..."}`
**Response 201:** `BuyerInquiryOut`

### GET /api/projects/{id}/timeline
Get project timeline events.

---

## Dynamic Forms

### POST /api/projects/{id}/dynamic-forms
Generate a dynamic form from a buyer inquiry.

**Body:** `{"inquiry_id": "..."}`
**Response 201:** `DynamicFormVersionOut`

### PATCH /api/dynamic-forms/{form_id}
Update form fields.

**Response 200:** `DynamicFormVersionOut`

### POST /api/dynamic-forms/{form_id}/lock
Lock form (required before RFQ creation).

**Response 200:** `DynamicFormVersionOut`

### POST /api/dynamic-forms/{form_id}/clarification-questions
Generate clarification questions.

---

## Participant Matching

### POST /api/projects/{id}/run-participant-matching
Run 12-dimension matching for all participants.

**Response 200:** `[ParticipantMatchOut]`

---

## RFQ

### POST /api/projects/{id}/rfqs
Create an RFQ. Returns RFQ + approval request ID.

**Body:** `{"form_version_id": "...", "recipient_participant_ids": [...]}`
**Response 201:** `{"rfq": RFQOut, "approval_request_id": "..."}`

### GET /api/rfqs/{id}
Get an RFQ.

**Response 200:** `RFQOut`

### POST /api/rfqs/{id}/send
Send RFQ (requires prior approval).

**Body:** `{"approval_id": "..."}`
**Response 200:** `RFQOut`

### POST /api/rfqs/{id}/responses
Record a supplier response.

**Body:** `{"participant_id": "...", "raw_response_text": "..."}`
**Response 201:** `SupplierResponseOut`

### GET /api/rfqs/{id}/responses
List supplier responses for an RFQ.

---

## Approval Gates

### GET /api/approval-requests
List approval requests.

**Query:** `?status=PENDING` (default) or `?status=ALL`
**Response 200:** `[ApprovalRequestOut]`

### GET /api/approval-requests/{id}
Get an approval request.

### POST /api/approval-requests/{id}/approve
Approve a request.

**Body:** `{"review_notes": "..."}`
**Response 200:** `ApprovalRequestOut`

### POST /api/approval-requests/{id}/reject
Reject a request.

**Body:** `{"review_notes": "..."}`
**Response 200:** `ApprovalRequestOut`

---

## Decision Packets

### POST /api/projects/{id}/decision-packets
Generate a decision packet.

**Body:** `{"rfq_id": "..."}`
**Response 201:** `{"packet": DecisionPacketOut, "approval_request_id": "..."}`

### GET /api/decision-packets/{id}
Get a decision packet.

### POST /api/decision-packets/{id}/approve-option
Approve a specific supplier option.

**Body:** `{"option_id": "...", "approval_id": "..."}`
**Response 200:** `DecisionPacketOut`

---

## Orders

### POST /api/projects/{id}/orders/from-approved-option
Create order from approved quote.

**Body:** `{"packet_id": "...", "option_id": "...", "approval_id": "..."}`
**Response 201:** `OrderOut`

### GET /api/orders/{id}
Get an order.

**Response 200:** `OrderOut`

### POST /api/orders/{id}/confirm
Confirm order (transitions to IN_PRODUCTION).

**Response 200:** `OrderOut`

### POST /api/orders/{id}/buyer-sign-off
Buyer sign-off (order must be DELIVERED).

**Response 200:** `OrderOut`

---

## Production Monitoring

### GET /api/orders/{id}/production-monitoring
Get production monitoring view with all milestones.

**Response 200:** `{"milestones": [...], "order_id": "..."}`

### PATCH /api/milestones/{id}
Update a milestone.

**Body:** `{"status": "IN_PROGRESS", "predicted_date": "...", "notes": "..."}`
**Response 200:** `MilestoneOut`

### POST /api/orders/{id}/run-delay-prediction
Run delay prediction analysis.

**Response 200:** `{"delay_risk_level": "ON_TRACK", "expedite_alert_required": false, ...}`

### POST /api/orders/{id}/production-updates
Add a production update note.

**Body:** `{"update_text": "..."}`
**Response 201:** `ProductionUpdateOut`

---

## Quality Control

### POST /api/orders/{id}/qc-standards
Create a QC standard for an order.

**Body:** `{"form_version_id": "..."}`
**Response 201:** `QCStandardOut`

### POST /api/orders/{id}/qc-records
Submit a QC inspection record.

**Body:** `{"label_compliance": true, "packaging_compliance": true, "fabric_defects": {...}}`
**Response 201:** `QCRecordOut` — includes `result`: `QC_PASSED` or `QC_FAILED`

### GET /api/orders/{id}/qc-records
List QC records for an order.

**Response 200:** `[QCRecordOut]`

### POST /api/qc-records/{id}/mark-pass
Manually mark a QC record as passed.

### POST /api/qc-records/{id}/mark-fail
Manually mark a QC record as failed.

---

## Logistics

### POST /api/orders/{id}/shipments
Create a shipment. Order must be READY_TO_SHIP.

**Body:** `{"carrier": "COSCO", "tracking_number": "...", "trade_term": "FOB", "origin": "...", "destination": "..."}`
**Response 201:** `ShipmentOut`

### GET /api/shipments/{id}
Get a shipment with tracking events.

**Response 200:** `ShipmentOut` (includes `tracking_events`)

### POST /api/shipments/{id}/tracking-events
Add a tracking event.

**Body:** `{"event_type": "DELIVERED", "location": "...", "description": "...", "occurred_at": "..."}`
**Response 201:** `TrackingEventOut`

Event types: `DEPARTED`, `IN_TRANSIT`, `ARRIVED`, `CUSTOMS_CLEARED`, `DELIVERED`, `POD`, `PROOF_OF_DELIVERY`, `ARRIVAL`

---

## Industrial Execution Graph

### GET /api/execution-graph/projects/{id}
List all events for a project (chronological).

**Response 200:** `[ExecutionEventOut]`

### GET /api/execution-graph/orders/{id}
List all events for an order (chronological).

**Response 200:** `[ExecutionEventOut]`

### GET /api/execution-graph/participants/{id}
List all events for a participant (chronological).

**Response 200:** `[ExecutionEventOut]`

### GET /api/execution-graph/events/{id}
Get a single execution event by ID.

**Response 200:** `ExecutionEventOut`
**Response 404:** Event not found

---

## Response Schemas

### ExecutionEventOut
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "project_id": "uuid|null",
  "order_id": "uuid|null",
  "participant_id": "uuid|null",
  "event_type": "PROJECT_CREATED",
  "payload": {},
  "triggered_by_user_id": "uuid|null",
  "occurred_at": "2026-06-15T10:00:00Z"
}
```

### OrderOut
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "status": "IN_PRODUCTION",
  "locked_form_version_id": "uuid|null",
  "total_quantity": 10000,
  "currency": "USD",
  "unit_price": "8.50",
  "created_at": "2026-06-15T10:00:00Z"
}
```
