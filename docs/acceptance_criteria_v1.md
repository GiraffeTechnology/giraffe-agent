# V1.0 Acceptance Criteria — Giraffe Apparel & Textile Platform

## Scope

These criteria define the minimum bar for V1.0 release of the Giraffe Agent apparel & textile C2M order execution platform.

---

## Functional Acceptance Criteria

### AC-1: User Authentication
- Users can register with email + password
- Users can log in and receive a JWT token
- All non-health API routes require a valid JWT

### AC-2: Participant Management
- Participants can be registered with name and country
- Roles can be assigned (MANUFACTURER, FABRIC_SUPPLIER, TRIM_SUPPLIER, PACKAGING_SUPPLIER, LOGISTICS_PROVIDER, QC_INSPECTOR, BUYER, AGENT)
- Participant profiles can be updated

### AC-3: Buyer Inquiry and Dynamic Form
- Buyer inquiries can be submitted as free text
- Dynamic forms are generated from inquiry text (LLM-assisted or stub)
- Forms can be locked before RFQ creation

### AC-4: Participant Matching
- 12-dimension matching scores are computed for all participants
- Risk flags are computed from supplier memory
- Matching results require human approval

### AC-5: RFQ Workflow
- RFQs can be created (auto-draft via LLM or stub)
- RFQ creation triggers an approval gate (RFQ_SEND)
- RFQs can only be sent after approval
- RFQ state machine: DRAFT → PENDING_APPROVAL → APPROVED_TO_SEND → SENT → RECEIVED/PARTIAL/COMPLETE

### AC-6: Supplier Response and Decision Packet
- Supplier responses can be recorded with raw text
- Responses are normalized (lead time extraction, price extraction)
- Decision packets compare up to 3 options (best/fastest/cheapest)
- Decision packet approval gates are enforced

### AC-7: Order State Machine
- Orders created from approved quotes enter DRAFT_FROM_APPROVED_QUOTE
- Order confirmation transitions through PENDING_BUYER_CONFIRMATION → CONFIRMED → IN_PRODUCTION
- Full 12-state machine with valid transitions enforced

### AC-8: Production Monitoring
- 12 milestones created at order creation with planned dates
- Milestone status can be updated (PENDING/IN_PROGRESS/COMPLETED/DELAYED)
- Predicted date > planned date auto-triggers DELAYED status
- Delay prediction computes ON_TRACK/LOW/MEDIUM/HIGH/CRITICAL risk levels
- HIGH/CRITICAL risk triggers expedite alert (requires approval before sending)

### AC-9: Quality Control
- QC standards can be created per order
- QC records are evaluated against standards
- QC_PASSED → order transitions to READY_TO_SHIP
- QC_FAILED → creates QualityIncident (if responsible participant given)
- 3 quality incidents trigger a ReplacementAlert

### AC-10: Logistics and Delivery
- Shipments can only be created for READY_TO_SHIP orders
- Tracking events can be added to shipments
- DELIVERED tracking event transitions order to DELIVERED
- Buyer sign-off transitions order to BUYER_SIGNED_OFF and updates SupplierMemory

### AC-11: Industrial Execution Graph
- All major platform events are recorded as immutable ExecutionEvents
- Events can be queried by project, order, or participant
- Events are returned in chronological order

### AC-12: Approval Gate Pattern
- No external action is executed without a prior PENDING ApprovalRequest
- Approval must reach APPROVED status before action is executed
- Rejection creates an audit trail

---

## Non-Functional Acceptance Criteria

### AC-NF1: Test Coverage
- All 98 automated tests pass (unit + API)
- Test scope covers all major workflows end-to-end

### AC-NF2: Security
- No secrets hardcoded in source code
- JWT authentication on all protected routes
- RBAC enforced at route and service level
- No tenant_id / user_id cross-contamination

### AC-NF3: Data Integrity
- Alembic migrations run cleanly on a fresh database
- No orphaned records created on failure paths
- Append-only audit trail (ExecutionEvent) is never deleted

### AC-NF4: Acceptance Script
- `scripts/run_v1_acceptance_apparel_order.py` completes all 22 steps with output: `GIRAFFE APPAREL & TEXTILE V1 ACCEPTANCE: PASS`
- `scripts/verify_v1_product_readiness_5x.py` achieves 5/5 PASS

---

## Out of Scope for V1.0

- Real-time messaging / WebSocket notifications
- Multi-tenant admin dashboard UI
- Payment processing integration
- CAD/BOM file management
- Logistics carrier API integration (tracking via webhook)
