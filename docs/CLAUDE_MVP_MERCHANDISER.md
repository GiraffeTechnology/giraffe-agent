# CLAUDE CODE INSTRUCTION — Integrated MVP Addendum
# M-side Send/Receive Role Switching + AI Merchandiser + Cainiao-like Logistics API
# Version: Integrated Addendum v1.0

## 0. Mission

Integrate three missing post-confirmation and M-side execution capabilities into the Giraffe Agent MVP:

1. **M-side Send / Receive Role Switching**
   - M is not only switching business roles; M is also switching communication direction.
   - M receives buyer inquiries, sends upstream inquiries, receives upstream replies, and sends a rollup response back to the buyer.
   - Every message must be routed by project, procurement edge, role context, direction, purpose, thread, and correlation token.

2. **AI Merchandiser Module**
   - Must be deployed on both B-side and M-side.
   - B-side AI Merchandiser supports buyer status tracking, milestone review, exception choices, logistics updates, and sign-off.
   - M-side AI Merchandiser supports supplier execution, production reminders, media upload, upstream / subcontractor follow-up, QC updates, logistics handover, and exception reporting.

3. **Automatic Logistics Data Ingestion**
   - Logistics data should primarily be read through Cainiao-like logistics aggregator APIs.
   - Manual entry and mock provider are fallback modes.
   - Tracking data must update the order execution state and Industrial Execution Graph.

This integrated addendum must work with:

- B-side OpenClaw-compatible AI Buyer skill.
- M-side role-switching procurement agent.
- Upstream / subcontractor inquiry loop.
- Supplier Response Rollup.
- Professional Free CAD-to-CNC matching.
- Dynamic self-learning database layer.
- Industrial Execution Graph v0.1.

---

## 1. Core Product Principle

Giraffe Agent has two major execution phases:

```text
AI Buyer = pre-confirmation decision support
AI Merchandiser = post-confirmation execution support
```

AI Buyer handles:

```text
buyer input
→ requirement structuring
→ supplier inquiry
→ supplier response
→ delivery feasibility simulation
→ Top 3 delivery paths
```

AI Merchandiser handles:

```text
order confirmation
→ supplier acceptance
→ production milestones
→ upstream follow-up
→ QC / media confirmation
→ exception handling
→ logistics handover
→ logistics tracking
→ delivery
→ buyer sign-off
→ supplier memory update
```

M-side role switching is the bridge between the two phases.

The M-side actor may be:

```text
1. MAIN_M_SIDE / INBOUND
   Receives inquiry from Buyer B.

2. UPSTREAM_B_SIDE / OUTBOUND
   Sends inquiries to fabric / material / subcontractor / QC / logistics providers.

3. UPSTREAM_B_SIDE / INBOUND
   Receives upstream supplier replies.

4. MAIN_M_SIDE / OUTBOUND
   Sends Supplier Response Rollup back to Buyer B.

5. MAIN_M_SIDE / EXECUTION
   Executes confirmed order and coordinates production, QC, logistics and exceptions.
```

The system must never confuse:

- buyer inquiry messages;
- upstream inquiry messages;
- upstream supplier replies;
- internal approval messages;
- buyer-facing rollup messages;
- progress update messages;
- media upload messages;
- logistics handover messages;
- buyer sign-off messages.

---

## 2. Required New File Structure

Create or update:

```text
src/m_side/communication/
  __init__.py
  direction.py
  role_switch_frame.py
  thread_context.py
  send_receive_state_machine.py
  message_router.py
  outbox_manager.py
  inbox_manager.py
  correlation.py

src/merchandiser/
  __init__.py
  merchandiser_engine.py
  merchandiser_state_machine.py
  task_planner.py
  reminder_scheduler.py
  milestone_manager.py
  media_confirmation.py
  exception_manager.py
  side_router.py
  message_templates.py

src/merchandiser/b_side/
  __init__.py
  b_merchandiser_service.py
  b_status_summary.py
  b_milestone_confirmation.py
  b_exception_options.py
  b_logistics_updates.py
  b_signoff.py

src/merchandiser/m_side/
  __init__.py
  m_merchandiser_service.py
  m_execution_plan.py
  m_progress_check.py
  m_media_request.py
  m_upstream_followup.py
  m_qc_followup.py
  m_logistics_handover.py

src/logistics/
  __init__.py
  logistics_models.py
  tracking_parser.py
  logistics_event_normalizer.py
  logistics_ingestion_service.py
  logistics_state_mapper.py
  logistics_message_parser.py
  logistics_webhook_service.py

src/logistics/providers/
  __init__.py
  base_provider.py
  cainiao_like_provider.py
  cainiao_like_models.py
  mock_provider.py
  provider_registry.py
  provider_config.py
  carrier_mapping.py

scripts/
  run_mside_send_receive_role_switch_test.py
  run_merchandiser_e2e_mvp.py
  run_logistics_cainiao_like_api_mvp.py
  run_integrated_post_confirmation_mvp.py
```

---

# PART A — M-side Send / Receive Role Switching

## 3. Communication Direction Model

Create:

```text
src/m_side/communication/direction.py
```

Define:

```python
CommunicationDirection = Literal[
    "INBOUND",
    "OUTBOUND",
    "INTERNAL"
]
```

Define:

```python
MessagePurpose = Literal[
    "buyer_inquiry_received",
    "main_supplier_clarification_to_buyer",
    "upstream_inquiry_to_supplier",
    "upstream_response_received",
    "upstream_option_approval_request",
    "supplier_response_rollup_to_buyer",
    "buyer_rollup_confirmation",
    "production_progress_update",
    "media_upload_request",
    "qc_update",
    "logistics_handover",
    "tracking_update",
    "buyer_signoff_request",
    "buyer_signoff_response",
    "exception_report",
    "system_reminder",
    "unknown"
]
```

---

## 4. RoleSwitchFrame

Create:

```text
src/m_side/communication/role_switch_frame.py
```

Define:

```python
RoleSwitchFrame
- frame_id: str
- project_id: str
- actor_id: str
- counterparty_actor_id: str | None
- edge_id: str | None
- role_context_id: str
- business_role: Literal[
    "ORIGINAL_BUYER",
    "MAIN_M_SIDE",
    "UPSTREAM_B_SIDE",
    "UPSTREAM_M_SIDE",
    "QC_SIDE",
    "LOGISTICS_SIDE",
    "SYSTEM",
    "UNKNOWN"
  ]
- communication_direction: Literal["INBOUND", "OUTBOUND", "INTERNAL"]
- message_purpose: str
- conversation_thread_id: str | None
- parent_frame_id: str | None
- created_at: str
```

Every inbound and outbound message must be attached to a RoleSwitchFrame.

---

## 5. Conversation Thread Model

Create:

```text
src/m_side/communication/thread_context.py
```

Define:

```python
ConversationThread
- thread_id: str
- project_id: str
- edge_id: str
- from_actor_id: str
- to_actor_id: str
- channel_type: Literal["wechat", "whatsapp", "openclaw", "line", "email", "web_fallback", "mock"]
- thread_type: Literal[
    "buyer_main_supplier",
    "main_supplier_upstream",
    "main_supplier_internal_approval",
    "buyer_rollup_review",
    "production_progress",
    "media_confirmation",
    "logistics_handover",
    "logistics_tracking_update",
    "exception_resolution",
    "buyer_signoff"
  ]
- active_role_context_id: str
- status: Literal["OPEN", "WAITING_FOR_REPLY", "REPLIED", "CLOSED", "ESCALATED"]
- correlation_token: str | None
- created_at: str
- updated_at: str
```

A thread must be created for each edge-level conversation.

Example:

```text
Thread 1: Buyer B → Manufacturer M
thread_type = buyer_main_supplier

Thread 2: Manufacturer M → Fabric Supplier F1
thread_type = main_supplier_upstream

Thread 3: Manufacturer M → Fabric Supplier F2
thread_type = main_supplier_upstream

Thread 4: Manufacturer M internal approval
thread_type = main_supplier_internal_approval

Thread 5: Manufacturer M → Buyer B
thread_type = buyer_rollup_review

Thread 6: Manufacturer M logistics handover
thread_type = logistics_handover

Thread 7: Buyer B delivery sign-off
thread_type = buyer_signoff
```

---

## 6. M-side Send / Receive State Machine

Create:

```text
src/m_side/communication/send_receive_state_machine.py
```

Define states:

```python
MSideSendReceiveState = Literal[
    "WAITING_FOR_BUYER_INQUIRY",
    "BUYER_INQUIRY_RECEIVED",
    "PREPARING_UPSTREAM_INQUIRIES",
    "AWAITING_MAIN_SUPPLIER_SEND_APPROVAL",
    "SENDING_UPSTREAM_INQUIRIES",
    "WAITING_FOR_UPSTREAM_RESPONSES",
    "UPSTREAM_RESPONSES_RECEIVED",
    "PREPARING_UPSTREAM_OPTIONS",
    "AWAITING_OPTION_APPROVAL",
    "GENERATING_BUYER_ROLLUP",
    "AWAITING_ROLLUP_APPROVAL",
    "SENDING_ROLLUP_TO_BUYER",
    "WAITING_FOR_BUYER_CONFIRMATION",
    "ORDER_CONFIRMED",
    "EXECUTION_IN_PROGRESS",
    "LOGISTICS_HANDOVER_PENDING",
    "LOGISTICS_TRACKING_ACTIVE",
    "BUYER_SIGNOFF_PENDING",
    "CLOSED",
    "EXCEPTION"
]
```

Expected transition:

```text
WAITING_FOR_BUYER_INQUIRY
→ BUYER_INQUIRY_RECEIVED
→ PREPARING_UPSTREAM_INQUIRIES
→ AWAITING_MAIN_SUPPLIER_SEND_APPROVAL
→ SENDING_UPSTREAM_INQUIRIES
→ WAITING_FOR_UPSTREAM_RESPONSES
→ UPSTREAM_RESPONSES_RECEIVED
→ PREPARING_UPSTREAM_OPTIONS
→ AWAITING_OPTION_APPROVAL
→ GENERATING_BUYER_ROLLUP
→ AWAITING_ROLLUP_APPROVAL
→ SENDING_ROLLUP_TO_BUYER
→ WAITING_FOR_BUYER_CONFIRMATION
→ ORDER_CONFIRMED
→ EXECUTION_IN_PROGRESS
→ LOGISTICS_HANDOVER_PENDING
→ LOGISTICS_TRACKING_ACTIVE
→ BUYER_SIGNOFF_PENDING
→ CLOSED
```

---

## 7. Message Router Rules

Create:

```text
src/m_side/communication/message_router.py
```

Implement:

```python
route_incoming_message(raw_message, channel_context) -> RoutedMessageContext
```

Define:

```python
RoutedMessageContext
- project_id: str
- edge_id: str | None
- actor_id: str
- counterparty_actor_id: str | None
- thread_id: str | None
- role_context_id: str
- business_role: str
- communication_direction: Literal["INBOUND", "OUTBOUND", "INTERNAL"]
- message_purpose: str
- parser_target: Literal[
    "buyer_requirement_parser",
    "buyer_confirmation_parser",
    "upstream_response_parser",
    "approval_parser",
    "progress_update_parser",
    "media_parser",
    "logistics_parser",
    "buyer_signoff_parser",
    "exception_parser",
    "unknown"
  ]
- confidence_score: float
```

Routing rules:

1. If message arrives from original buyer thread:
   - M business role = MAIN_M_SIDE
   - direction = INBOUND
   - parser target = buyer_requirement_parser or buyer_confirmation_parser

2. If message arrives from upstream supplier thread:
   - M business role = UPSTREAM_B_SIDE
   - direction = INBOUND
   - parser target = upstream_response_parser

3. If message is internal approval from M:
   - direction = INTERNAL
   - parser target = approval_parser

4. If message includes tracking number from M-side execution thread:
   - business role = MAIN_M_SIDE
   - parser target = logistics_parser

5. If message is buyer delivery confirmation:
   - business role = ORIGINAL_BUYER
   - parser target = buyer_signoff_parser

6. If confidence is low:
   - create clarification task
   - do not update buyer-facing response automatically

---

## 8. Outbox Manager

Create:

```text
src/m_side/communication/outbox_manager.py
```

Implement:

```python
create_outbound_message(
    project_id: str,
    from_actor_id: str,
    to_actor_id: str,
    edge_id: str,
    role_context_id: str,
    message_purpose: str,
    body: str,
    channel_type: str
) -> OutboundMessage
```

Define:

```python
OutboundMessage
- outbound_message_id: str
- project_id: str
- edge_id: str
- from_actor_id: str
- to_actor_id: str
- role_context_id: str
- thread_id: str
- message_purpose: str
- body: str
- channel_type: str
- status: Literal["DRAFT", "APPROVAL_REQUIRED", "READY_TO_SEND", "SENT", "FAILED"]
- requires_approval: bool
- created_at: str
- sent_at: str | None
```

Rules:

- Upstream inquiries require M approval by default.
- Buyer-facing rollup requires M approval.
- Low-risk production reminders may be sent automatically if allowed.
- Any price, lead time, material change, QC risk, or buyer-facing commitment requires approval.

---

## 9. Inbox Manager

Create:

```text
src/m_side/communication/inbox_manager.py
```

Implement:

```python
receive_inbound_message(raw_message, channel_context) -> InboundMessage
```

Define:

```python
InboundMessage
- inbound_message_id: str
- project_id: str | None
- edge_id: str | None
- from_actor_id: str | None
- to_actor_id: str | None
- thread_id: str | None
- role_switch_frame_id: str | None
- raw_message: str
- parsed_target: str
- parsed_result_json: dict
- confidence_score: float
- status: Literal["RECEIVED", "ROUTED", "PARSED", "NEEDS_CLARIFICATION", "FAILED"]
- created_at: str
```

---

## 10. Correlation Tokens

Create:

```text
src/m_side/communication/correlation.py
```

Implement:

```python
generate_correlation_token(project_id, edge_id, dependency_id) -> str
resolve_correlation_token(raw_message, channel_context) -> CorrelationResult
```

Every outbound upstream inquiry should include or store a correlation token.

Example:

```text
GFR-PROJ-shirt100-DEP-fabric-F1
```

Purpose:

- match upstream replies to the correct project;
- match replies to the correct dependency;
- avoid confusion across similar inquiries;
- support WeChat / WhatsApp free-text replies.

---

# PART B — AI Merchandiser Module

## 11. Order Execution State Machine

Create:

```text
src/merchandiser/merchandiser_state_machine.py
```

Define:

```python
OrderExecutionState = Literal[
    "ORDER_CONFIRMED",
    "SUPPLIER_ACCEPTANCE_PENDING",
    "SUPPLIER_ACCEPTED",
    "PRODUCTION_PLAN_CREATED",
    "MATERIAL_CONFIRMATION_PENDING",
    "MATERIAL_CONFIRMED",
    "PRODUCTION_STARTED",
    "MILESTONE_PENDING",
    "MILESTONE_MEDIA_REQUESTED",
    "MILESTONE_MEDIA_UPLOADED",
    "MILESTONE_BUYER_REVIEW_PENDING",
    "MILESTONE_CONFIRMED",
    "QC_PENDING",
    "QC_CONFIRMED",
    "PACKAGING_PENDING",
    "PACKAGING_CONFIRMED",
    "LOGISTICS_HANDOVER_PENDING",
    "LOGISTICS_HANDOVER_RECEIVED",
    "IN_TRANSIT",
    "CUSTOMS",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "BUYER_SIGNOFF_PENDING",
    "BUYER_SIGNED_OFF",
    "ORDER_CLOSED",
    "EXCEPTION_RAISED",
    "EXCEPTION_RESOLUTION_PENDING",
    "EXCEPTION_RESOLVED",
    "CANCELLED"
]
```

State transition drivers:

- buyer action;
- supplier action;
- upstream response;
- media upload;
- QC update;
- logistics handover;
- logistics API event;
- timeout;
- exception event;
- human review;
- authorized agent action.

---

## 12. Merchandiser Task Model

Create:

```text
src/merchandiser/task_planner.py
```

Define:

```python
MerchandiserTask
- task_id: str
- project_id: str
- order_id: str | None
- assigned_side: Literal["B_SIDE", "M_SIDE", "UPSTREAM_M_SIDE", "SYSTEM"]
- assigned_actor_id: str | None
- role_context_id: str | None
- task_type: Literal[
    "supplier_acceptance",
    "material_confirmation",
    "production_start",
    "milestone_media_upload",
    "buyer_milestone_review",
    "qc_update",
    "packaging_update",
    "logistics_handover",
    "tracking_update",
    "exception_resolution",
    "buyer_signoff",
    "supplier_memory_update"
  ]
- due_at: str | None
- status: Literal["PENDING", "IN_PROGRESS", "DONE", "OVERDUE", "CANCELLED"]
- priority: Literal["low", "medium", "high"]
- payload: dict
- created_at: str
- updated_at: str
```

Task planner must create tasks after order confirmation.

---

## 13. B-side AI Merchandiser

Create:

```text
src/merchandiser/b_side/b_merchandiser_service.py
src/merchandiser/b_side/b_status_summary.py
src/merchandiser/b_side/b_milestone_confirmation.py
src/merchandiser/b_side/b_exception_options.py
src/merchandiser/b_side/b_logistics_updates.py
src/merchandiser/b_side/b_signoff.py
```

B-side responsibilities:

1. Receive order status summaries.
2. Track production milestones.
3. Receive media confirmation requests.
4. Ask buyer to confirm or reject milestone evidence.
5. Explain exceptions and available options.
6. Notify buyer of material, QC, production, or logistics risks.
7. Read logistics events and push delivery updates.
8. Ask buyer for delivery sign-off after logistics delivered status.
9. Update buyer-facing project timeline.

Example B-side messages:

```text
Your order is now in production. The supplier has confirmed fabric arrival and cutting is scheduled for tomorrow.
```

```text
Milestone confirmation required:
The supplier uploaded 3 photos for the cutting stage.
Reply:
A. Confirm
B. Request more photos
C. Raise issue
```

```text
Logistics update:
Tracking number SF123456789 is in transit. Latest event: departed Shenzhen sorting center. Estimated delivery: 2026-06-18.
```

```text
The shipment has been delivered according to logistics data. Please confirm receipt:
A. Confirm received
B. Not received
C. Received with issue
```

---

## 14. M-side AI Merchandiser

Create:

```text
src/merchandiser/m_side/m_merchandiser_service.py
src/merchandiser/m_side/m_execution_plan.py
src/merchandiser/m_side/m_progress_check.py
src/merchandiser/m_side/m_media_request.py
src/merchandiser/m_side/m_upstream_followup.py
src/merchandiser/m_side/m_qc_followup.py
src/merchandiser/m_side/m_logistics_handover.py
```

M-side responsibilities:

1. Confirm supplier acceptance.
2. Create production milestone plan.
3. Remind supplier to start production.
4. Remind supplier to upload media evidence.
5. Ask supplier for progress updates.
6. Coordinate upstream / subcontractor dependencies.
7. Request QC updates.
8. Request packaging confirmation.
9. Request logistics handover data.
10. Parse supplier replies from IM.
11. Report delays, material shortages, QC problems, process changes, or shipment issues.
12. Update Supplier Memory after order completion.

Example M-side messages:

```text
Order SHIRT-100 is confirmed. Please confirm today whether the fabric has arrived at the warehouse:
A. Received at the warehouse
B. Not yet received
C. There is an issue; please explain
```

```text
Please upload three clear cutting-stage photos: front, back and detail, so the buyer can review them.
```

```text
The order is ready for logistics handover. Please provide the carrier and tracking number and upload a photo of the shipping label.
Example: Sent by SF Express, tracking number SF123456789, dispatched this afternoon.
```

---

## 15. Milestone Manager

Create:

```text
src/merchandiser/milestone_manager.py
```

Define:

```python
OrderMilestone
- milestone_id: str
- project_id: str
- order_id: str | None
- milestone_type: Literal[
    "material_arrival",
    "cutting",
    "machining",
    "surface_treatment",
    "assembly",
    "in_process_qc",
    "final_qc",
    "packaging",
    "logistics_handover",
    "delivery"
  ]
- sequence_no: int
- expected_at: str | None
- actual_at: str | None
- status: Literal["PENDING", "REQUESTED", "UPLOADED", "CONFIRMED", "REJECTED", "SKIPPED"]
- evidence_required: bool
- required_media_types: list[str]
- assigned_actor_id: str | None
- buyer_confirmation_required: bool
- metadata: dict
```

Milestone plan rules:

Apparel / shirt:

```text
material_arrival
cutting
assembly
in_process_qc
final_qc
packaging
logistics_handover
delivery
```

CNC / machining:

```text
material_confirmation
machining
surface_treatment if required
final_qc
packaging
logistics_handover
delivery
```

---

## 16. Media Confirmation

Create:

```text
src/merchandiser/media_confirmation.py
```

Define:

```python
MediaEvidence
- media_id: str
- project_id: str
- milestone_id: str
- uploaded_by_actor_id: str
- artifact_id: str | None
- media_type: Literal["image", "video", "document", "shipping_label"]
- description: str | None
- visibility_check_status: Literal["pass", "fail", "unknown"]
- completeness_check_status: Literal["pass", "fail", "unknown"]
- buyer_review_status: Literal["pending", "confirmed", "rejected", "not_required"]
- notes: str | None
- created_at: str
```

MVP media check:

- file exists;
- media type valid;
- required number of images exists;
- optional basic clarity flag;
- no advanced defect detection required.

---

## 17. Exception Manager

Create:

```text
src/merchandiser/exception_manager.py
```

Define:

```python
OrderException
- exception_id: str
- project_id: str
- order_id: str | None
- raised_by_actor_id: str | None
- exception_type: Literal[
    "material_shortage",
    "capacity_delay",
    "production_delay",
    "qc_issue",
    "quality_dispute",
    "media_missing",
    "logistics_delay",
    "lost_shipment",
    "address_issue",
    "customs_issue",
    "process_change",
    "price_change",
    "other"
  ]
- severity: Literal["low", "medium", "high"]
- description: str
- proposed_options: list[dict]
- buyer_confirmation_required: bool
- human_review_required: bool
- status: Literal["OPEN", "PENDING_CONFIRMATION", "RESOLVED", "ESCALATED", "CLOSED"]
- created_at: str
- updated_at: str
```

Autonomy rules:

- Low-risk reminders can be automatic.
- Material change, price change, delivery promise change, quality dispute, cancellation, refund, or buyer-facing commitment requires buyer confirmation or human review.
- M-side can propose resolution options, but buyer-impacting changes must be confirmed by B-side.

---

## 18. Side Router

Create:

```text
src/merchandiser/side_router.py
```

Implement:

```python
route_merchandiser_message(project_id, actor_id, event_or_task) -> MerchandiserMessage
```

The same event may generate different messages for B-side and M-side.

Example:

Event:

```text
material_delay_reported
```

B-side message:

```text
The supplier reported a fabric delay. Two options are available: wait 3 extra days or switch to backup fabric.
```

M-side message:

```text
Please confirm whether to use the alternative fabric or wait for the original fabric. If delivery is affected, provide the revised expected completion time.
```

---

# PART C — Cainiao-like Logistics API Ingestion

## 19. Product Principle

The logistics module should be API-ingestion first.

Main production path:

```text
M-side supplier provides carrier + tracking number
→ Giraffe creates LogisticsShipment
→ Giraffe calls Cainiao-like logistics aggregator API
→ API returns tracking events
→ Giraffe normalizes events
→ Giraffe updates order state
→ Giraffe pushes B-side logistics updates
→ Giraffe records events into Industrial Execution Graph
```

Manual entry and mock provider are fallback modes.

Delivered status must not automatically equal buyer acceptance.  
Delivered status triggers buyer sign-off request.

---

## 20. Logistics Provider Abstraction

Create:

```text
src/logistics/providers/base_provider.py
```

Define:

```python
class LogisticsProviderBase:
    provider_name: str

    def create_or_bind_shipment(
        self,
        carrier_code: str | None,
        tracking_number: str,
        metadata: dict | None = None
    ) -> dict:
        ...

    def fetch_tracking_events(
        self,
        carrier_code: str | None,
        tracking_number: str
    ) -> list[dict]:
        ...

    def parse_webhook_payload(
        self,
        payload: dict,
        headers: dict | None = None
    ) -> list[dict]:
        ...

    def verify_webhook_signature(
        self,
        payload: bytes,
        headers: dict
    ) -> bool:
        ...

    def normalize_event(
        self,
        raw_event: dict
    ) -> dict:
        ...
```

---

## 21. Cainiao-like Provider

Create:

```text
src/logistics/providers/cainiao_like_provider.py
src/logistics/providers/cainiao_like_models.py
```

Implement:

```python
class CainiaoLikeProvider(LogisticsProviderBase):
    provider_name = "cainiao_like"
```

Provider must support:

1. API authentication placeholder.
2. Request signing placeholder.
3. Tracking event polling.
4. Webhook payload parsing.
5. Carrier code mapping.
6. Status normalization.
7. Retry and timeout.
8. Idempotency handling.

Do not assume exact Cainiao API field names.  
Use adapter mapping config so real API fields can be added later.

Local MVP must use fixture data shaped like Cainiao-like logistics responses.

---

## 22. Environment Variables

Add:

```text
LOGISTICS_PROVIDER=mock
LOGISTICS_API_ENABLED=false

CAINIAO_LIKE_ENABLED=false
CAINIAO_LIKE_API_BASE_URL=
CAINIAO_LIKE_APP_KEY=
CAINIAO_LIKE_APP_SECRET=
CAINIAO_LIKE_ACCESS_TOKEN=
CAINIAO_LIKE_SIGNING_METHOD=hmac_sha256
CAINIAO_LIKE_TIMEOUT_SECONDS=10
CAINIAO_LIKE_MAX_RETRIES=3
CAINIAO_LIKE_WEBHOOK_SECRET=

LOGISTICS_POLL_INTERVAL_MINUTES=60
LOGISTICS_USE_WEBHOOKS=false
LOGISTICS_ENABLE_MANUAL_FALLBACK=true
```

Local MVP must run with:

```text
LOGISTICS_PROVIDER=mock
LOGISTICS_API_ENABLED=false
```

Production switch:

```text
LOGISTICS_PROVIDER=cainiao_like
LOGISTICS_API_ENABLED=true
CAINIAO_LIKE_ENABLED=true
```

---

## 23. Provider Registry

Create:

```text
src/logistics/providers/provider_registry.py
```

Implement:

```python
get_logistics_provider(provider_name: str | None = None) -> LogisticsProviderBase
```

Rules:

- If `LOGISTICS_PROVIDER=mock`, return MockProvider.
- If `LOGISTICS_PROVIDER=cainiao_like`, return CainiaoLikeProvider.
- If API config is missing, fall back to MockProvider only in local MVP mode.
- In production mode, missing config must raise clear error.

---

## 24. Carrier Mapping

Create:

```text
src/logistics/providers/carrier_mapping.py
```

Support configurable mapping:

```python
{
  "SF Express": "SF",
  "SF Express": "SF",
  "ZTO Express": "ZTO",
  "YTO Express": "YTO",
  "STO Express": "STO",
  "Yunda Express": "YD",
  "EMS": "EMS",
  "DHL": "DHL",
  "FedEx": "FEDEX",
  "UPS": "UPS"
}
```

Do not treat the above list as exhaustive.

---

## 25. Tracking Number Extraction from IM

Create or update:

```text
src/logistics/logistics_message_parser.py
```

Implement:

```python
extract_logistics_info_from_im(raw_message: str) -> LogisticsInfoExtract
```

Define:

```python
LogisticsInfoExtract
- carrier_name: str | None
- carrier_code: str | None
- tracking_number: str | None
- shipping_date_text: str | None
- confidence_score: float
- evidence_text: str
```

Examples:

```text
Sent by SF Express, tracking number SF123456789, dispatched this afternoon
```

Extract:

```json
{
  "carrier_name": "SF Express",
  "carrier_code": "SF",
  "tracking_number": "SF123456789"
}
```

```text
DHL shipped today, tracking no. 1234567890
```

Extract:

```json
{
  "carrier_name": "DHL",
  "carrier_code": "DHL",
  "tracking_number": "1234567890"
}
```

---

## 26. Logistics Models

Create:

```text
src/logistics/logistics_models.py
```

Define:

```python
LogisticsShipment
- shipment_id: str
- project_id: str
- order_id: str | None
- provider_name: str | None
- provider_shipment_id: str | None
- carrier_name: str | None
- carrier_code: str | None
- tracking_number: str
- sender_actor_id: str | None
- receiver_actor_id: str | None
- origin: str | None
- destination: str | None
- current_status: Literal[
    "label_created",
    "picked_up",
    "in_transit",
    "customs",
    "out_for_delivery",
    "delivered",
    "exception",
    "unknown"
  ]
- estimated_delivery_date: str | None
- actual_delivery_date: str | None
- last_event_at: str | None
- last_synced_at: str | None
- sync_status: str | None
- sync_error: str | None
- polling_enabled: bool
- webhook_enabled: bool
- created_at: str
- updated_at: str
```

```python
LogisticsEvent
- logistics_event_id: str
- shipment_id: str
- project_id: str
- provider_name: str | None
- provider_event_id: str | None
- carrier_name: str | None
- tracking_number: str
- event_time: str | None
- status: str
- raw_status_code: str | None
- normalized_status: str
- location: str | None
- description: str | None
- raw_payload: dict
- source: Literal["api", "webhook", "im_message", "uploaded_receipt", "mock", "manual"]
- event_hash: str
- is_duplicate: bool
- created_at: str
```

---

## 27. Logistics Ingestion Service

Create or update:

```text
src/logistics/logistics_ingestion_service.py
```

Implement:

```python
ingest_tracking_number(
    project_id: str,
    carrier_name: str | None,
    carrier_code: str | None,
    tracking_number: str,
    source: str,
    actor_id: str | None = None
) -> LogisticsShipment
```

Then:

```python
provider = get_logistics_provider()
raw_events = provider.fetch_tracking_events(carrier_code, tracking_number)
normalized_events = normalize_and_store_events(project_id, shipment_id, raw_events)
```

Also implement:

```python
sync_tracking_from_provider(shipment_id: str) -> list[LogisticsEvent]
sync_all_active_shipments() -> dict
ingest_logistics_from_im_message(project_id: str, raw_message: str, actor_id: str) -> LogisticsShipment | None
```

---

## 28. Logistics Webhook Service

Create:

```text
src/logistics/logistics_webhook_service.py
```

Implement:

```python
handle_logistics_webhook(provider_name: str, payload: dict, headers: dict | None = None) -> list[LogisticsEvent]
```

Rules:

- Provider must verify webhook signature in production.
- Signature bypass is allowed only in local MVP mock mode.
- Never bypass signature verification in production mode.

---

## 29. Status Normalization

Create or update:

```text
src/logistics/logistics_event_normalizer.py
```

Normalize all provider statuses into:

```text
label_created
picked_up
in_transit
customs
out_for_delivery
delivered
exception
unknown
```

Chinese examples:

```text
picked up → picked_up
in transit → in_transit
customs clearance → customs
out for delivery → out_for_delivery
delivered → delivered
delivery exception → exception
```

English examples:

```text
picked up → picked_up
in transit → in_transit
customs clearance → customs
out for delivery → out_for_delivery
delivered → delivered
delivery exception → exception
```

---

## 30. Idempotency and Duplicate Events

A LogisticsEvent duplicate should be detected by:

```text
shipment_id
+ provider_name
+ tracking_number
+ normalized_status
+ event_time
+ location
+ description_hash
```

If duplicate:

- do not create another event;
- write `LOGISTICS_EVENT_DEDUPED`;
- still update shipment `last_synced_at` if relevant.

---

## 31. Logistics State Mapper

Create:

```text
src/logistics/logistics_state_mapper.py
```

Implement:

```python
map_logistics_status_to_order_state(normalized_status: str) -> OrderExecutionState | None
```

Rules:

```text
label_created → LOGISTICS_HANDOVER_RECEIVED
picked_up → IN_TRANSIT
in_transit → IN_TRANSIT
customs → CUSTOMS or IN_TRANSIT with customs note
out_for_delivery → OUT_FOR_DELIVERY
delivered → DELIVERED and BUYER_SIGNOFF_PENDING
exception → EXCEPTION_RAISED
```

---

# PART D — Database Additions

## 32. Required Tables

Update database models and migrations to include:

### 32.1 conversation_threads

```python
thread_id: str primary key
project_id: str FK projects.project_id
edge_id: str FK procurement_edges.edge_id
from_actor_id: str FK actors.actor_id
to_actor_id: str FK actors.actor_id
channel_type: str
thread_type: str
active_role_context_id: str FK role_contexts.role_context_id
status: str
correlation_token: str | None
created_at
updated_at
metadata_json: dict
```

### 32.2 role_switch_frames

```python
frame_id: str primary key
project_id: str FK projects.project_id
actor_id: str FK actors.actor_id
counterparty_actor_id: str | None FK actors.actor_id
edge_id: str | None FK procurement_edges.edge_id
role_context_id: str FK role_contexts.role_context_id
business_role: str
communication_direction: str
message_purpose: str
conversation_thread_id: str | None FK conversation_threads.thread_id
parent_frame_id: str | None FK role_switch_frames.frame_id
created_at
metadata_json: dict
```

### 32.3 outbound_messages

```python
outbound_message_id: str primary key
project_id: str FK projects.project_id
edge_id: str FK procurement_edges.edge_id
from_actor_id: str FK actors.actor_id
to_actor_id: str FK actors.actor_id
role_context_id: str FK role_contexts.role_context_id
thread_id: str FK conversation_threads.thread_id
message_purpose: str
body: str
channel_type: str
status: str
requires_approval: bool
created_at
sent_at: datetime | None
metadata_json: dict
```

### 32.4 inbound_messages

```python
inbound_message_id: str primary key
project_id: str | None FK projects.project_id
edge_id: str | None FK procurement_edges.edge_id
from_actor_id: str | None FK actors.actor_id
to_actor_id: str | None FK actors.actor_id
thread_id: str | None FK conversation_threads.thread_id
role_switch_frame_id: str | None FK role_switch_frames.frame_id
raw_message: str
parsed_target: str
parsed_result_json: dict
confidence_score: float | None
status: str
created_at
metadata_json: dict
```

### 32.5 merchandiser_tasks

```python
task_id: str primary key
project_id: str FK projects.project_id
order_id: str | None
assigned_side: str
assigned_actor_id: str | None FK actors.actor_id
role_context_id: str | None FK role_contexts.role_context_id
task_type: str
due_at: datetime | None
status: str
priority: str
payload_json: dict
created_at
updated_at
```

### 32.6 order_milestones

```python
milestone_id: str primary key
project_id: str FK projects.project_id
order_id: str | None
milestone_type: str
sequence_no: int
expected_at: datetime | None
actual_at: datetime | None
status: str
evidence_required: bool
required_media_types_json: dict
assigned_actor_id: str | None FK actors.actor_id
buyer_confirmation_required: bool
metadata_json: dict
created_at
updated_at
```

### 32.7 media_evidence

```python
media_id: str primary key
project_id: str FK projects.project_id
milestone_id: str | None FK order_milestones.milestone_id
uploaded_by_actor_id: str | None FK actors.actor_id
artifact_id: str | None FK artifacts.artifact_id
media_type: str
description: str | None
visibility_check_status: str
completeness_check_status: str
buyer_review_status: str
notes: str | None
created_at
updated_at
```

### 32.8 order_exceptions

```python
exception_id: str primary key
project_id: str FK projects.project_id
order_id: str | None
raised_by_actor_id: str | None FK actors.actor_id
exception_type: str
severity: str
description: str
proposed_options_json: dict
buyer_confirmation_required: bool
human_review_required: bool
status: str
created_at
updated_at
```

### 32.9 logistics_shipments

```python
shipment_id: str primary key
project_id: str FK projects.project_id
order_id: str | None
provider_name: str | None
provider_shipment_id: str | None
carrier_name: str | None
carrier_code: str | None
tracking_number: str
sender_actor_id: str | None FK actors.actor_id
receiver_actor_id: str | None FK actors.actor_id
origin: str | None
destination: str | None
current_status: str
estimated_delivery_date: datetime | None
actual_delivery_date: datetime | None
last_event_at: datetime | None
last_synced_at: datetime | None
sync_status: str | None
sync_error: str | None
polling_enabled: bool
webhook_enabled: bool
created_at
updated_at
metadata_json: dict
```

### 32.10 logistics_events

```python
logistics_event_id: str primary key
shipment_id: str FK logistics_shipments.shipment_id
project_id: str FK projects.project_id
provider_name: str | None
provider_event_id: str | None
carrier_name: str | None
tracking_number: str
event_time: datetime | None
status: str
raw_status_code: str | None
normalized_status: str
location: str | None
description: str | None
raw_payload_json: dict
source: str
event_hash: str
is_duplicate: bool
created_at
```

---

# PART E — Industrial Execution Graph Events

## 33. Add Event Types

Add or ensure these event types exist:

```text
M_ROLE_SEND_RECEIVE_STATE_CHANGED
M_INBOUND_BUYER_INQUIRY_ROUTED
M_OUTBOUND_UPSTREAM_INQUIRY_CREATED
M_OUTBOUND_UPSTREAM_INQUIRY_APPROVED
M_OUTBOUND_UPSTREAM_INQUIRY_SENT
M_INBOUND_UPSTREAM_RESPONSE_ROUTED
M_UPSTREAM_RESPONSE_ATTACHED_TO_DEPENDENCY
M_INTERNAL_OPTION_APPROVAL_RECEIVED
M_BUYER_ROLLUP_APPROVAL_REQUESTED
M_BUYER_ROLLUP_APPROVED
M_OUTBOUND_BUYER_ROLLUP_SENT
MESSAGE_CORRELATION_TOKEN_CREATED
MESSAGE_CORRELATION_TOKEN_RESOLVED
MESSAGE_ROUTING_LOW_CONFIDENCE

MERCHANDISER_TASK_CREATED
MERCHANDISER_TASK_COMPLETED
ORDER_MILESTONE_CREATED
ORDER_MILESTONE_REQUESTED
ORDER_MILESTONE_MEDIA_UPLOADED
ORDER_MILESTONE_BUYER_CONFIRMED
ORDER_MILESTONE_REJECTED
M_SIDE_PROGRESS_CHECK_REQUESTED
M_SIDE_PROGRESS_UPDATE_RECEIVED
B_SIDE_STATUS_UPDATE_SENT
EXCEPTION_OPTION_GENERATED
EXCEPTION_BUYER_CONFIRMATION_REQUESTED
EXCEPTION_RESOLVED
LOGISTICS_HANDOVER_REQUESTED
LOGISTICS_HANDOVER_RECEIVED

TRACKING_NUMBER_INGESTED
LOGISTICS_PROVIDER_SELECTED
LOGISTICS_PROVIDER_API_CALLED
LOGISTICS_PROVIDER_API_ERROR
LOGISTICS_PROVIDER_WEBHOOK_RECEIVED
LOGISTICS_WEBHOOK_SIGNATURE_VERIFIED
LOGISTICS_EVENT_INGESTED
LOGISTICS_EVENT_DEDUPED
LOGISTICS_STATUS_NORMALIZED
ORDER_STATE_UPDATED_FROM_LOGISTICS
B_SIDE_LOGISTICS_UPDATE_SENT
BUYER_SIGNOFF_REQUESTED
BUYER_SIGNOFF_RECEIVED
SUPPLIER_MEMORY_UPDATED_FROM_ORDER
```

Every major send / receive switch, merchandiser task, milestone action, exception, logistics event, and order state update must write an ExecutionEvent.

---

# PART F — API Routes

## 34. M-side Send / Receive Routes

Add:

```text
POST /api/m-side/{project_id}/route-message
POST /api/m-side/{project_id}/outbox
POST /api/m-side/outbox/{outbound_message_id}/approve
POST /api/m-side/outbox/{outbound_message_id}/send
POST /api/m-side/inbox
GET  /api/m-side/{project_id}/threads
GET  /api/m-side/{project_id}/role-switch-frames
```

---

## 35. Merchandiser Routes

Add:

```text
POST /api/merchandiser/{project_id}/create-execution-plan
POST /api/merchandiser/{project_id}/create-tasks
GET  /api/merchandiser/{project_id}/tasks
POST /api/merchandiser/tasks/{task_id}/complete

POST /api/merchandiser/{project_id}/milestones
GET  /api/merchandiser/{project_id}/milestones
POST /api/merchandiser/milestones/{milestone_id}/media
POST /api/merchandiser/milestones/{milestone_id}/buyer-confirm
POST /api/merchandiser/milestones/{milestone_id}/reject

POST /api/merchandiser/{project_id}/exceptions
POST /api/merchandiser/exceptions/{exception_id}/resolve
POST /api/merchandiser/{project_id}/buyer-signoff
```

---

## 36. Logistics Routes

Add:

```text
POST /api/logistics/{project_id}/tracking-number
POST /api/logistics/{project_id}/tracking-number/sync
POST /api/logistics/shipments/{shipment_id}/sync
POST /api/logistics/sync-active
POST /api/logistics/webhook/{provider_name}
POST /api/logistics/from-im-message
GET  /api/logistics/shipments/{shipment_id}/events
GET  /api/logistics/{project_id}/shipments
GET  /api/logistics/providers
```

---

# PART G — Test Fixtures and E2E Scripts

## 37. Fixtures

Create:

```text
tests/fixtures/role_switching/shirt_100pcs_send_receive_flow.json
tests/fixtures/role_switching/fabric_supplier_replies.json

tests/fixtures/merchandiser/shirt_order_execution_plan.json
tests/fixtures/merchandiser/cnc_order_execution_plan.json
tests/fixtures/merchandiser/milestone_media_upload.json
tests/fixtures/merchandiser/material_delay_exception.json

tests/fixtures/logistics/cainiao_like_tracking_response_normal.json
tests/fixtures/logistics/cainiao_like_tracking_response_delivered.json
tests/fixtures/logistics/cainiao_like_tracking_response_exception.json
tests/fixtures/logistics/cainiao_like_webhook_payload_delivered.json
tests/fixtures/logistics/cainiao_like_duplicate_events.json
tests/fixtures/logistics/im_shipping_message_sf_zh.json
tests/fixtures/logistics/im_shipping_message_dhl_en.json
```

---

## 38. E2E Script 1 — M-side Send / Receive Role Switching

Create:

```text
scripts/run_mside_send_receive_role_switch_test.py
```

Must verify:

```text
1. Buyer B sends 100-shirt inquiry to Manufacturer M.
2. M receives as MAIN_M_SIDE / INBOUND.
3. M identifies fabric dependency.
4. M approves sending upstream inquiries.
5. M sends to Fabric Supplier F1 / F2 / F3 as UPSTREAM_B_SIDE / OUTBOUND.
6. F1 replies.
7. M receives reply as UPSTREAM_B_SIDE / INBOUND.
8. Reply is routed to upstream_response_parser.
9. Correlation token links reply to fabric dependency.
10. M generates options and approves one.
11. M generates buyer-facing rollup.
12. M sends rollup to Buyer B as MAIN_M_SIDE / OUTBOUND.
13. All messages have RoleSwitchFrame.
14. All messages are attached to the correct thread and edge.
15. Execution events are logged.
```

Command:

```bash
uv run python scripts/run_mside_send_receive_role_switch_test.py
```

---

## 39. E2E Script 2 — AI Merchandiser

Create:

```text
scripts/run_merchandiser_e2e_mvp.py
```

Must run:

```text
1. Buyer B confirms supplier selection.
2. System creates post-confirmation execution plan.
3. M-side AI Merchandiser creates supplier tasks.
4. B-side AI Merchandiser creates buyer review tasks.
5. M-side receives progress reminder.
6. M-side uploads milestone media.
7. B-side receives milestone review request.
8. Buyer confirms milestone.
9. M-side reports logistics handover with tracking number.
10. Logistics ingestion creates shipment and events.
11. Order state updates from logistics events.
12. B-side receives delivery update and sign-off request.
13. Buyer signs off.
14. Supplier Memory update is created.
15. Industrial Execution Graph records all events.
```

Command:

```bash
uv run python scripts/run_merchandiser_e2e_mvp.py
```

---

## 40. E2E Script 3 — Cainiao-like Logistics API

Create:

```text
scripts/run_logistics_cainiao_like_api_mvp.py
```

Must run:

```text
1. Create project and confirmed order.
2. M-side sends IM message: Sent by SF Express, tracking number SF123456789, dispatched this afternoon.
3. System extracts carrier and tracking number.
4. System creates LogisticsShipment.
5. Provider registry selects CainiaoLikeProvider in mock mode.
6. Cainiao-like mock API returns tracking events.
7. System normalizes events.
8. System deduplicates events.
9. System updates order state.
10. B-side receives logistics update.
11. Delivered event triggers buyer sign-off request.
12. Industrial Execution Graph records API call, ingestion, normalization, order update and buyer notification.
```

Command:

```bash
uv run python scripts/run_logistics_cainiao_like_api_mvp.py
```

---

## 41. E2E Script 4 — Integrated Post-confirmation MVP

Create:

```text
scripts/run_integrated_post_confirmation_mvp.py
```

Must run:

```text
1. Buyer B sends inquiry.
2. M receives inquiry and role-switch frame is created.
3. M sends upstream inquiry and receives response.
4. M generates Supplier Response Rollup.
5. Buyer confirms order.
6. AI Merchandiser execution plan is created.
7. M-side progress task is created.
8. M-side uploads milestone media.
9. B-side confirms milestone.
10. M-side sends logistics handover message.
11. Cainiao-like provider mock returns tracking events.
12. Order state reaches delivered.
13. B-side sign-off request is generated.
14. Buyer signs off.
15. Supplier Memory update is recorded.
16. Industrial Execution Graph contains role-switching, merchandiser and logistics events.
```

Command:

```bash
uv run python scripts/run_integrated_post_confirmation_mvp.py
```

---

# PART H — Acceptance Criteria

## 42. Integrated Acceptance Criteria

The task is complete only if:

### M-side send / receive role switching

1. Business role switching and communication direction switching are both implemented.
2. M can receive buyer inquiry as MAIN_M_SIDE / INBOUND.
3. M can send upstream inquiry as UPSTREAM_B_SIDE / OUTBOUND.
4. M can receive upstream reply as UPSTREAM_B_SIDE / INBOUND.
5. M can send rollup to buyer as MAIN_M_SIDE / OUTBOUND.
6. Buyer-facing messages and upstream messages are never mixed.
7. Internal approval messages are not sent externally.
8. Correlation tokens are generated and resolved.
9. RoleSwitchFrame exists for each major inbound / outbound message.

### AI Merchandiser

10. AI Merchandiser module exists and can run after order confirmation.
11. B-side and M-side services share the same core Merchandiser engine.
12. B-side receives milestone, exception, logistics and sign-off updates.
13. M-side receives production, QC, media, upstream and logistics handover tasks.
14. Order milestones can be created, updated, confirmed and rejected.
15. Media evidence can be linked to milestones.
16. Exceptions can be raised and resolved with autonomy rules.
17. Supplier Memory can be updated after order closure.

### Logistics API ingestion

18. Logistics module supports provider abstraction.
19. Cainiao-like provider class exists.
20. Mock Cainiao-like tracking response can be ingested.
21. IM text can extract carrier and tracking number.
22. Tracking API call path works in mock mode.
23. Provider registry can switch between mock and Cainiao-like provider.
24. Logistics events are normalized.
25. Duplicate logistics events are deduplicated.
26. Logistics status updates order state.
27. Delivered status triggers buyer sign-off request, not automatic acceptance.
28. API errors are recorded and do not crash workflow.
29. Webhook route exists and can parse mock webhook payload.
30. Signature verification placeholder exists and cannot be bypassed in production mode.

### Industrial Execution Graph

31. All major actions create ExecutionEvents.
32. Role-switching events are logged.
33. Merchandiser task and milestone events are logged.
34. Logistics API ingestion events are logged.
35. Order state updates from logistics are logged.

### Local MVP

36. All E2E scripts run locally without real logistics API, WeChat, WhatsApp, OpenClaw, ERP, MES, QMS, MachinaCheck, S3, or encryption service.
37. The implementation remains compatible with existing database models and does not remove prior MVP functionality.

---

## 43. Important Constraints

Do not:

- hard-code M as only a supplier;
- route messages only by actor_id;
- mix buyer-facing and upstream threads;
- send buyer-facing rollup without M approval;
- treat logistics delivered status as automatic buyer acceptance;
- require real Cainiao API credentials for local MVP;
- bypass webhook signature verification in production mode;
- expose confidential CAD / BOM / order documents to logistics provider;
- implement Enterprise CAP here;
- remove or break B-side AI Buyer, M-side role switching, CAD-to-CNC Professional Free, dynamic schema or database functions.

Only send logistics provider:

```text
carrier
tracking number
logistics-related reference
```

Do not send confidential engineering files to logistics providers.

---

## 44. Strategic Rationale

Giraffe Agent is not complete if it stops at supplier selection or feasibility simulation.

The buyer pays for execution confidence.  
The supplier needs help executing and communicating the order.  
The platform needs real execution data.

Therefore:

```text
AI Buyer = pre-confirmation decision support
AI Merchandiser = post-confirmation execution support
M-side send / receive role switching = recursive supply-chain communication control
Logistics API ingestion = objective execution signal
Industrial Execution Graph = memory of what actually happened
```

Together, these three modules turn Giraffe from an inquiry tool into an order execution agent.

