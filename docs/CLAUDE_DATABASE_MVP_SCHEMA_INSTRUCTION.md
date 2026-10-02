# CLAUDE CODE INSTRUCTION — Giraffe Agent MVP Database Generation File

This retained reference describes the earlier physical database implementation. Current delivery uses the hot-swappable private data contract: both business history and ongoing process records are authoritative in the selected DB. SQLite/PostgreSQL and these local table layouts are implementation details, not mandatory provider identity. Business text is standard English after giraffe-language-skill translation; only enterprise/user profile information may retain non-English values. Legacy field names such as raw_text are preserved protocol identifiers, not permission to store non-English business content.
# Version: MVP Database v1.0
# Purpose: Generate the database layer required for the full Giraffe Agent MVP

## 0. Mission

Create the database layer for Giraffe Agent MVP.

The database must support the complete MVP scope:

1. B-side OpenClaw-compatible AI Buyer skill.
2. B-side IM workflow via WeChat / WhatsApp / OpenClaw / web fallback.
3. M-side role-switching procurement agent.
4. Recursive B-to-M execution graph.
5. Upstream / subcontractor inquiry loop.
6. M-side Professional Free CAD-to-CNC / machining center capability matching.
7. Embedded MachinaCheck-like mock capability evidence.
8. Supplier Response Rollup back to B-side workspace.
9. Industrial Execution Graph v0.1.
10. Dynamic self-learning database fields.
11. Professional Free file policy without encryption or Enterprise CAP.
12. Future portability to PostgreSQL.

This task is database-focused. Do not build the full application logic unless required for database smoke tests.

---

## 1. Database Philosophy

Giraffe Agent is not a simple CRM, ERP, RFQ tool, or static order database.

It is a **project-aware procurement execution graph**.

The core rule:

> Do not hard-code Buyer and Supplier as fixed identities.

A company / person / factory must be stored as a neutral `Actor`.

The actor's role is determined by:

- Project
- Procurement edge
- Counterparty
- Current inquiry
- Current workspace
- RoleContext

Example:

```text
Buyer B → Manufacturer M
Manufacturer M is MAIN_M_SIDE to Buyer B.

Manufacturer M → Fabric Supplier F1
Manufacturer M is UPSTREAM_B_SIDE to Fabric Supplier F1.
Fabric Supplier F1 is UPSTREAM_M_SIDE to Manufacturer M.
```

Therefore, the database must support:

```text
Actor + Project + ProcurementEdge + RoleContext + Message + Requirement + Response + Rollup + Capability Evidence + ExecutionEvent
= Industrial Execution Graph v0.1
```

---

## 2. Required Tech Stack

Use:

```text
Python 3.11+
SQLAlchemy 2.x
Alembic
Pydantic v2
SQLite for local deterministic MVP
PostgreSQL-compatible schema design
JSON columns for flexible MVP data
```

The schema must be portable to PostgreSQL later.

For PostgreSQL migration, JSON columns should map to JSONB.

Do not depend on PostgreSQL-only features in local MVP.

Optional future layer:

```text
pgvector / vector DB
ClickHouse / event warehouse
Neo4j / graph DB
S3 / MinIO object storage
```

Do not implement these optional systems in this MVP unless lightweight placeholders are needed.

---

## 3. Required File Structure

Create or update:

```text
src/db/
  __init__.py
  base.py
  session.py
  config.py
  enums.py
  mixins.py

src/db/models/
  __init__.py
  actor.py
  project.py
  procurement_edge.py
  role_context.py
  requirement.py
  inquiry.py
  response.py
  upstream.py
  approval.py
  rollup.py
  cad_cnc.py
  capability.py
  im_message.py
  artifact.py
  execution_event.py
  dynamic_schema.py
  supplier_memory.py
  legal_notice.py

src/db/repositories/
  __init__.py
  actor_repo.py
  project_repo.py
  graph_repo.py
  role_repo.py
  requirement_repo.py
  inquiry_repo.py
  response_repo.py
  rollup_repo.py
  cad_cnc_repo.py
  execution_event_repo.py
  dynamic_schema_repo.py

src/db/schemas/
  __init__.py
  actor_schema.py
  project_schema.py
  graph_schema.py
  requirement_schema.py
  response_schema.py
  rollup_schema.py
  cad_cnc_schema.py
  dynamic_schema_schema.py

alembic/
  env.py
  versions/

scripts/
  init_db.py
  reset_db.py
  seed_mvp_data.py
  run_db_smoke_test.py
  run_role_switching_db_test.py
  run_professional_free_db_test.py
  run_dynamic_schema_learning_test.py

tests/db/
  test_actor_role_context.py
  test_procurement_graph.py
  test_upstream_rollup.py
  test_cad_cnc_schema.py
  test_execution_events.py
  test_dynamic_schema.py
```

---

## 4. Database Configuration

Create:

```text
src/db/config.py
```

Support:

```text
DATABASE_URL=sqlite:///./giraffe_mvp.db
DATABASE_ECHO=false
DB_MODE=local_mvp
```

For PostgreSQL compatibility:

```text
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/giraffe
```

---

## 5. Base Model Rules

All tables must use string UUID primary keys.

Use timezone-aware timestamps.

Create mixins:

```python
UUIDPrimaryKeyMixin
TimestampMixin
SoftDeleteMixin
MetadataJSONMixin
```

Standard fields:

```python
id: str
created_at: datetime
updated_at: datetime
deleted_at: datetime | None
metadata_json: dict
```

Use `metadata_json` instead of `metadata` to avoid SQLAlchemy conflicts.

---

## 6. Enumerations

Create:

```text
src/db/enums.py
```

Required enums:

```python
ActorType:
- buyer
- manufacturer
- trading_company
- material_supplier
- fabric_supplier
- trim_supplier
- component_supplier
- subcontractor
- qc_provider
- packaging_supplier
- logistics_provider
- education_research
- unknown

RoleType:
- ORIGINAL_BUYER
- MAIN_M_SIDE
- UPSTREAM_B_SIDE
- UPSTREAM_M_SIDE
- QC_SIDE
- LOGISTICS_SIDE
- SYSTEM
- UNKNOWN

ProjectStatus:
- CREATED
- B_INQUIRY_STRUCTURED
- MAIN_SUPPLIER_RECEIVED
- UPSTREAM_DEPENDENCY_PLANNED
- UPSTREAM_INQUIRIES_SENT
- UPSTREAM_RESPONSES_RECEIVED
- UPSTREAM_OPTIONS_READY
- UPSTREAM_OPTION_APPROVED
- SUPPLIER_RESPONSE_ROLLED_UP
- SUPPLIER_RESPONSE_SUBMITTED_TO_BUYER
- ORDER_CONFIRMED
- IN_EXECUTION
- CLOSED
- CANCELLED

EdgeType:
- BUYER_TO_MAIN_SUPPLIER
- MAIN_SUPPLIER_TO_MATERIAL_SUPPLIER
- MAIN_SUPPLIER_TO_FABRIC_SUPPLIER
- MAIN_SUPPLIER_TO_TRIM_SUPPLIER
- MAIN_SUPPLIER_TO_COMPONENT_SUPPLIER
- MAIN_SUPPLIER_TO_SUBCONTRACTOR
- MAIN_SUPPLIER_TO_PACKAGING_SUPPLIER
- MAIN_SUPPLIER_TO_QC_PROVIDER
- MAIN_SUPPLIER_TO_LOGISTICS_PROVIDER

EdgeStatus:
- DRAFT
- SENT
- RESPONDED
- OPTIONS_READY
- APPROVED
- ROLLED_UP
- REJECTED
- CLOSED

ChannelType:
- openclaw
- wechat
- whatsapp
- line
- email
- web_fallback
- mock

ArtifactType:
- cad
- step
- pdf
- bom
- image
- video
- spreadsheet
- manual_text
- other

ProductTier:
- free
- professional_free
- plus
- pro
- enterprise_cap

ApprovalMode:
- human
- authorized_agent
- automatic_low_risk

ApprovalStatus:
- PENDING
- APPROVED
- REJECTED
- EXPIRED

DynamicFieldStatus:
- observed
- proposed
- approved
- rejected
- deprecated
- promoted

ExecutionEventType:
- ROLE_CONTEXT_RESOLVED
- ROLE_SWITCH_OCCURRED
- B_INQUIRY_CREATED
- M_SIDE_RECEIVED_BUYER_INQUIRY
- UPSTREAM_DEPENDENCY_PLANNED
- UPSTREAM_INQUIRY_CREATED
- UPSTREAM_INQUIRY_DISPATCHED
- UPSTREAM_RESPONSE_RECEIVED
- UPSTREAM_RESPONSE_PARSED
- UPSTREAM_OPTIONS_GENERATED
- UPSTREAM_OPTION_APPROVAL_REQUESTED
- UPSTREAM_OPTION_APPROVED
- SUPPLIER_RESPONSE_ROLLUP_GENERATED
- SUPPLIER_RESPONSE_ROLLUP_SUBMITTED_TO_B_SIDE
- CAD_REQUIREMENT_PACKET_CREATED
- CAD_FEATURES_EXTRACTED
- SHOP_CAPABILITY_PROFILE_LOADED
- CAD_CNC_MATCH_STARTED
- CAD_CNC_MATCH_COMPLETED
- MACHINE_PARAMETER_MATCHED
- MACHINE_PARAMETER_GAP_FOUND
- CAPABILITY_FIT_REPORT_CREATED
- DEPENDENCY_CREATED_FROM_CAD_CNC_MATCH
- PROFESSIONAL_FREE_FILE_WARNING_SHOWN
- PROFESSIONAL_FREE_CAP_LIMITATION_ACKNOWLEDGED
- CAPABILITY_CONNECTOR_REGISTERED
- CAPABILITY_CHECK_REQUESTED
- MACHINACHECK_LIKE_ASSESSMENT_STARTED
- MACHINACHECK_LIKE_ASSESSMENT_COMPLETED
- CAPABILITY_EVIDENCE_ATTACHED
- CAPABILITY_RISK_FLAGGED
- CAPABILITY_CONFIDENCE_SCORE_UPDATED
- ORDER_CONFIRMED
- PRODUCTION_UPDATE_RECEIVED
- QC_UPDATE_RECEIVED
- EXCEPTION_REPORTED
- LOGISTICS_HANDOVER_RECEIVED
- ORDER_CLOSED
```

---

## 7. Core Tables

### 7.1 actors

Model file:

```text
src/db/models/actor.py
```

Fields:

```python
actor_id: str primary key
name: str
actor_type: str
default_language: str | None
contact_channels_json: dict
capabilities_json: dict
profile_json: dict
is_active: bool
created_at
updated_at
```

Notes:

- `actor_type` describes the nature of the actor.
- It must not determine the actor's project role.
- Role is resolved through `role_contexts`.

---

### 7.2 projects

Model file:

```text
src/db/models/project.py
```

Fields:

```python
project_id: str primary key
original_buyer_actor_id: str FK actors.actor_id
main_supplier_actor_id: str | None FK actors.actor_id
category: str | None
product_summary: str | None
quantity: int | None
status: ProjectStatus
product_tier: ProductTier
created_by_channel: ChannelType | None
created_at
updated_at
metadata_json: dict
```

Indexes:

```text
original_buyer_actor_id
main_supplier_actor_id
status
category
created_at
```

---

### 7.3 procurement_edges

Model file:

```text
src/db/models/procurement_edge.py
```

Fields:

```python
edge_id: str primary key
project_id: str FK projects.project_id
from_actor_id: str FK actors.actor_id
to_actor_id: str FK actors.actor_id
edge_type: EdgeType
parent_edge_id: str | None FK procurement_edges.edge_id
inquiry_id: str | None
response_id: str | None
status: EdgeStatus
created_at
updated_at
metadata_json: dict
```

Purpose:

- Represents buyer-to-supplier and supplier-to-upstream relationships.
- Enables role switching and recursive procurement graph.

Indexes:

```text
project_id
from_actor_id
to_actor_id
parent_edge_id
edge_type
status
```

---

### 7.4 role_contexts

Model file:

```text
src/db/models/role_context.py
```

Fields:

```python
role_context_id: str primary key
project_id: str FK projects.project_id
edge_id: str | None FK procurement_edges.edge_id
actor_id: str FK actors.actor_id
counterparty_actor_id: str | None FK actors.actor_id
role: RoleType
role_reason: str
permissions_json: dict
can_create_upstream_inquiry: bool
can_approve_upstream_option: bool
can_submit_response_to_buyer: bool
created_at
metadata_json: dict
```

Acceptance:

- Same actor can have multiple role contexts in one project.
- Example: Manufacturer M is MAIN_M_SIDE to Buyer B and UPSTREAM_B_SIDE to Fabric Supplier F1.

---

## 8. B-side Tables

### 8.1 structured_requirements

Model file:

```text
src/db/models/requirement.py
```

Fields:

```python
requirement_id: str primary key
project_id: str FK projects.project_id
source_actor_id: str FK actors.actor_id
source_message_id: str | None
raw_input_refs_json: dict
category: str | None
quantity: int | None
material: str | None
specs_json: dict
deadline: str | None
destination: str | None
missing_fields_json: dict
confidence_score: float
created_at
updated_at
```

---

### 8.2 supplier_inquiries

Model file:

```text
src/db/models/inquiry.py
```

Fields:

```python
inquiry_id: str primary key
project_id: str FK projects.project_id
edge_id: str FK procurement_edges.edge_id
from_actor_id: str FK actors.actor_id
to_actor_id: str FK actors.actor_id
requirement_id: str | None FK structured_requirements.requirement_id
message_text_en: str | None
message_text_zh: str | None
message_text_local: str | None
requested_fields_json: dict
required_reply_schema_json: dict
status: str
created_at
updated_at
```

---

### 8.3 supplier_responses

Model file:

```text
src/db/models/response.py
```

Fields:

```python
response_id: str primary key
project_id: str FK projects.project_id
edge_id: str FK procurement_edges.edge_id
inquiry_id: str | None FK supplier_inquiries.inquiry_id
from_actor_id: str FK actors.actor_id
to_actor_id: str FK actors.actor_id
can_supply: bool | None
price: float | None
currency: str | None
moq: float | None
available_quantity: float | None
lead_time_days: int | None
earliest_dispatch_date: str | None
capacity_basis_json: dict
material_basis_json: dict
subcontract_basis_json: dict
qc_basis_json: dict
logistics_basis_json: dict
risk_flags_json: dict
raw_message: str | None
parsed_json: dict
confidence_score: float
completeness_score: float
created_at
updated_at
```

---

## 9. M-side Upstream Tables

### 9.1 dependency_needs

Model file:

```text
src/db/models/upstream.py
```

Fields:

```python
dependency_id: str primary key
project_id: str FK projects.project_id
created_by_actor_id: str FK actors.actor_id
dependency_type: str
description: str
required_specs_json: dict
quantity_required: float | None
required_by_date: str | None
risk_level: str
why_needed: str
candidate_actor_ids_json: dict
source: str
status: str
created_at
updated_at
```

Dependency types include:

```text
fabric
trim
raw_material
component
subcontract_process
surface_treatment
heat_treatment
qc_testing
packaging
logistics
tooling
fixture
capacity
```

---

### 9.2 upstream_inquiries

Fields:

```python
upstream_inquiry_id: str primary key
project_id: str FK projects.project_id
edge_id: str FK procurement_edges.edge_id
dependency_id: str FK dependency_needs.dependency_id
parent_main_supplier_actor_id: str FK actors.actor_id
upstream_actor_id: str FK actors.actor_id
message_text_en: str | None
message_text_zh: str | None
requested_fields_json: dict
required_reply_schema_json: dict
due_time: str | None
dispatch_channel: ChannelType | None
status: str
created_at
updated_at
```

---

### 9.3 upstream_responses

Fields:

```python
upstream_response_id: str primary key
project_id: str FK projects.project_id
edge_id: str FK procurement_edges.edge_id
upstream_inquiry_id: str FK upstream_inquiries.upstream_inquiry_id
dependency_id: str FK dependency_needs.dependency_id
from_actor_id: str FK actors.actor_id
can_supply: bool
matched_specs_json: dict
price: float | None
currency: str | None
moq: float | None
available_quantity: float | None
lead_time_days: int | None
earliest_dispatch_date: str | None
quality_notes: str | None
substitute_options_json: dict
risk_flags_json: dict
confidence_score: float
completeness_score: float
raw_message: str | None
created_at
updated_at
```

---

### 9.4 upstream_options

Fields:

```python
option_id: str primary key
project_id: str FK projects.project_id
dependency_id: str FK dependency_needs.dependency_id
upstream_actor_id: str FK actors.actor_id
option_label: str
price_summary: str | None
lead_time_summary: str | None
risk_summary: str | None
score: float
reason: str | None
response_ids_json: dict
status: str
created_at
updated_at
```

Option labels:

```text
BEST
FASTEST
SAFEST
LOWEST_COST
BACKUP
```

---

### 9.5 approval_requests

Model file:

```text
src/db/models/approval.py
```

Fields:

```python
approval_request_id: str primary key
project_id: str FK projects.project_id
dependency_id: str | None FK dependency_needs.dependency_id
requested_by_actor_id: str FK actors.actor_id
approval_mode: ApprovalMode
status: ApprovalStatus
options_json: dict
approved_option_id: str | None
approved_by_actor_id: str | None
approved_by_mode: str | None
created_at
updated_at
metadata_json: dict
```

---

## 10. Supplier Response Rollup

Model file:

```text
src/db/models/rollup.py
```

Table:

```text
supplier_response_rollups
```

Fields:

```python
rollup_id: str primary key
project_id: str FK projects.project_id
main_supplier_actor_id: str FK actors.actor_id
can_accept_order: bool | None
main_capacity_summary: str | None
approved_upstream_options_json: dict
material_basis_json: dict
trim_basis_json: dict
subcontract_basis_json: dict
qc_basis_json: dict
packaging_basis_json: dict
logistics_basis_json: dict
price_basis_json: dict
lead_time_basis_json: dict
unresolved_dependencies_json: dict
risk_flags_json: dict
completeness_score: float
confidence_score: float
recommended_response_to_buyer_en: str | None
recommended_response_to_buyer_zh: str | None

cad_requirement_packet_id: str | None
cad_cnc_match_id: str | None
capability_fit_report_id: str | None
cnc_parameter_match_summary_json: dict
can_make_in_house: bool | None
recommended_machine_ids_json: dict
capability_gaps_json: dict
upstream_dependency_basis_json: dict

created_at
updated_at
```

Purpose:

- Main supplier's final structured response back to B-side.
- Must include upstream evidence and optional CAD-to-CNC capability evidence.

---

## 11. CAD / CNC / MachinaCheck-like Tables

### 11.1 artifacts

Model file:

```text
src/db/models/artifact.py
```

Fields:

```python
artifact_id: str primary key
project_id: str | None FK projects.project_id
owner_actor_id: str | None FK actors.actor_id
artifact_type: ArtifactType
file_name: str | None
file_ref: str
file_hash: str | None
mime_type: str | None
size_bytes: int | None
metadata_json: dict
product_tier: ProductTier
cap_level: str | None
encryption_enabled: bool
dynamic_watermark_enabled: bool
secure_viewer_enabled: bool
warning_acknowledged: bool
created_at
updated_at
```

Professional Free rule:

```text
encryption_enabled = false
dynamic_watermark_enabled = false
secure_viewer_enabled = false
```

---

### 11.2 cad_requirement_packets

Model file:

```text
src/db/models/cad_cnc.py
```

Fields:

```python
packet_id: str primary key
project_id: str FK projects.project_id
original_buyer_actor_id: str FK actors.actor_id
main_supplier_actor_id: str | None FK actors.actor_id
file_refs_json: dict
source_types_json: dict
part_summary: str | None
material: str | None
quantity: int | None
dimensions_json: dict
tolerance_requirements_json: dict
surface_finish_requirements_json: dict
thread_requirements_json: dict
heat_treatment_requirements_json: dict
operation_requirements_json: dict
qc_requirements_json: dict
packaging_requirements_json: dict
delivery_deadline: str | None
missing_information_json: dict
extraction_confidence_score: float
created_at
updated_at
```

---

### 11.3 manufacturing_feature_sets

Fields:

```python
feature_set_id: str primary key
packet_id: str FK cad_requirement_packets.packet_id
project_id: str FK projects.project_id
required_processes_json: dict
required_machine_types_json: dict
min_axis_requirement: int | None
work_envelope_required_json: dict
material_required: str | None
tolerance_class: str | None
surface_finish_class: str | None
thread_or_hole_features_json: dict
heat_treatment_required: bool
external_process_likely_required: bool
qc_required_json: dict
risk_flags_json: dict
missing_information_json: dict
created_at
updated_at
```

---

### 11.4 shop_capability_profiles

Model file:

```text
src/db/models/capability.py
```

Fields:

```python
profile_id: str primary key
actor_id: str FK actors.actor_id
profile_name: str | None
machines_json: dict
tooling_inventory_json: dict
qc_equipment_json: dict
material_inventory_json: dict
in_house_processes_json: dict
outsourced_processes_json: dict
schedule_summary_json: dict
created_at
updated_at
```

---

### 11.5 cad_cnc_match_results

Fields:

```python
match_id: str primary key
project_id: str FK projects.project_id
actor_id: str FK actors.actor_id
cad_requirement_packet_id: str FK cad_requirement_packets.packet_id
shop_capability_profile_id: str FK shop_capability_profiles.profile_id
can_make_in_house: bool
recommended_machine_ids_json: dict
machine_fit_score: float
work_envelope_fit: str
material_fit: str
tolerance_fit: str
surface_finish_fit: str
tooling_fit: str
qc_fit: str
schedule_fit: str
required_upstream_dependencies_json: dict
required_subcontract_dependencies_json: dict
risk_flags_json: dict
missing_information_json: dict
confidence_score: float
explanation: str | None
created_at
updated_at
```

---

### 11.6 capability_fit_reports

Fields:

```python
report_id: str primary key
project_id: str FK projects.project_id
actor_id: str FK actors.actor_id
cad_cnc_match_id: str FK cad_cnc_match_results.match_id
buyer_facing_summary_en: str | None
buyer_facing_summary_zh: str | None
internal_summary: str | None
can_quote_now: bool
can_make_in_house: bool
recommended_next_actions_json: dict
required_upstream_inquiries_json: dict
required_subcontractor_inquiries_json: dict
risk_flags_json: dict
confidence_score: float
created_at
updated_at
```

---

## 12. IM / Messaging Tables

Model file:

```text
src/db/models/im_message.py
```

### 12.1 channel_sessions

Fields:

```python
session_id: str primary key
project_id: str | None FK projects.project_id
edge_id: str | None FK procurement_edges.edge_id
actor_id: str FK actors.actor_id
counterparty_actor_id: str | None FK actors.actor_id
channel_type: ChannelType
channel_user_id: str | None
state_json: dict
last_message_at: datetime | None
created_at
updated_at
```

---

### 12.2 messages

Fields:

```python
message_id: str primary key
session_id: str | None FK channel_sessions.session_id
project_id: str | None FK projects.project_id
edge_id: str | None FK procurement_edges.edge_id
role_context_id: str | None FK role_contexts.role_context_id
sender_actor_id: str | None FK actors.actor_id
receiver_actor_id: str | None FK actors.actor_id
channel_type: ChannelType
direction: str
raw_text: str | None
normalized_text: str | None
attachments_json: dict
parsed_intent: str | None
parsed_entities_json: dict
confidence_score: float | None
created_at
metadata_json: dict
```

Purpose:

- Store standard-English IM business records with safe translation/source references. Enterprise/user profile information is the only exception for non-English DB values. Do not store non-English business originals in raw/evidence/audit side fields.
- Preserve evidence for future learning.
- Source for dynamic schema observation.

---

## 13. Industrial Execution Graph v0.1

Model file:

```text
src/db/models/execution_event.py
```

Table:

```text
execution_events
```

Fields:

```python
event_id: str primary key
project_id: str | None FK projects.project_id
edge_id: str | None FK procurement_edges.edge_id
actor_id: str | None FK actors.actor_id
role_context_id: str | None FK role_contexts.role_context_id
event_type: ExecutionEventType
payload_json: dict
source_channel: ChannelType | None
source_message_id: str | None
confidence_score: float | None
created_at
metadata_json: dict
```

Rules:

- Every major workflow transition must write an ExecutionEvent.
- This table plus procurement_edges is Industrial Execution Graph v0.1.
- Do not skip event logging in smoke tests.

---

## 14. Dynamic Self-Learning Database Layer

The database must support self-learning field expansion.

Core principle:

> AI may observe and propose new fields, but it must not directly alter physical database tables during runtime.

Dynamic field lifecycle:

```text
Observe → Normalize → Propose → Approve → Use → Promote
```

### 14.1 schema_registry

Model file:

```text
src/db/models/dynamic_schema.py
```

Fields:

```python
schema_id: str primary key
industry: str
category: str
schema_version: str
status: str
created_at
updated_at
metadata_json: dict
```

Examples:

```text
apparel / shirt / v0.1
cnc / precision_part / v0.1
packaging / custom_box / v0.1
```

---

### 14.2 field_definitions

Fields:

```python
field_id: str primary key
schema_id: str FK schema_registry.schema_id
field_name: str
normalized_field_name: str
field_type: str
unit: str | None
description: str | None
required_level: str
validation_rule_json: dict
example_values_json: dict
source: str
status: DynamicFieldStatus
created_at
updated_at
```

Required levels:

```text
required
recommended
optional
learned
experimental
```

---

### 14.3 observed_fields

Fields:

```python
observed_field_id: str primary key
project_id: str | None FK projects.project_id
actor_id: str | None FK actors.actor_id
source_message_id: str | None FK messages.message_id
source_artifact_id: str | None FK artifacts.artifact_id
candidate_field_name: str
normalized_field_name: str | None
candidate_value: str | None
candidate_unit: str | None
normalized_value: str | None
confidence_score: float
evidence_text: str | None
created_at
metadata_json: dict
```

---

### 14.4 field_proposals

Fields:

```python
proposal_id: str primary key
schema_id: str FK schema_registry.schema_id
candidate_field_name: str
normalized_field_name: str
field_type: str
suggested_unit: str | None
business_reason: str | None
example_count: int
project_count: int
supplier_count: int
confidence_score: float
risk_level: str
status: DynamicFieldStatus
created_at
updated_at
metadata_json: dict
```

---

### 14.5 entity_dynamic_values

Fields:

```python
value_id: str primary key
entity_type: str
entity_id: str
field_id: str FK field_definitions.field_id
field_value: str
unit: str | None
confidence_score: float
source: str | None
source_message_id: str | None FK messages.message_id
source_artifact_id: str | None FK artifacts.artifact_id
created_at
metadata_json: dict
```

---

### 14.6 field_aliases

Fields:

```python
alias_id: str primary key
field_id: str FK field_definitions.field_id
alias_text: str
language: str | None
created_at
```

Examples:

```text
fabric_gsm aliases: fabric weight, gsm, g/m², fabric weight
surface_roughness_ra aliases: Ra, roughness, surface roughness
```

---

### 14.7 unit_dictionary

Fields:

```python
unit_id: str primary key
unit_name: str
unit_symbol: str
unit_type: str
conversion_rule_json: dict
created_at
```

---

### 14.8 field_promotion_decisions

Fields:

```python
decision_id: str primary key
proposal_id: str FK field_proposals.proposal_id
decision: str
decided_by: str
reason: str | None
created_at
metadata_json: dict
```

---

## 15. Dynamic Field Promotion Rules

Implement helper logic in:

```text
src/db/repositories/dynamic_schema_repo.py
```

A candidate field may be proposed when:

```text
1. It appears in at least 5 projects; or
2. It appears across at least 3 suppliers; or
3. It materially affects feasibility scoring; or
4. A human operator marks it as important; or
5. It is extracted from CAD / BOM / supplier responses with confidence score above 0.85.
```

A candidate field may be automatically approved only if:

```text
1. It is low-risk;
2. It does not affect price, legal commitment, delivery promise, quality guarantee, tolerance, safety or compliance;
3. It has a stable unit or controlled vocabulary;
4. It has at least 3 supporting examples.
```

Fields affecting price, delivery date, tolerance, QC, compliance, safety, or buyer-facing commitment must require human approval.

---

## 16. Supplier Memory Tables

Model file:

```text
src/db/models/supplier_memory.py
```

### 16.1 supplier_score_snapshots

Fields:

```python
snapshot_id: str primary key
actor_id: str FK actors.actor_id
project_id: str | None FK projects.project_id
response_speed_score: float | None
acceptance_rate_score: float | None
on_time_delivery_score: float | None
media_cooperation_score: float | None
quality_score: float | None
lead_time_accuracy_score: float | None
quote_completeness_score: float | None
capability_confidence_score: float | None
risk_score: float | None
computed_from_json: dict
created_at
```

### 16.2 supplier_profile_updates

Fields:

```python
update_id: str primary key
actor_id: str FK actors.actor_id
project_id: str | None FK projects.project_id
update_type: str
previous_value_json: dict
new_value_json: dict
evidence_event_id: str | None FK execution_events.event_id
created_at
```

---

## 17. Legal / Patent Notice Table

Model file:

```text
src/db/models/legal_notice.py
```

Fields:

```python
notice_id: str primary key
notice_type: str
version: str
text_en: str
text_zh: str | None
effective_at: datetime
metadata_json: dict
created_at
```

Seed patent notice:

```text
China patent: ZL 2023 1 1645939.9 / CN 117670482 B.
Japan patent: P7644545 / Patent No. 7644545.
Patent owner: Giraffe Technology Holding Limited.
Free patent license applies globally to individuals, SMEs, educational institutions and research institutions for compliant use.
Enterprise deployment, platform operation, high-volume commercial production use, third-party system integration, white-label resale, Enterprise CAP, and use of Giraffe commercial assets require separate written permission.
Authorization contact: mich@giraffe.technology.
```

---

## 18. Seed Data Requirements

Create:

```text
scripts/seed_mvp_data.py
```

Seed the following:

### Actors

```text
buyer_b
manufacturer_m
fabric_supplier_f1
fabric_supplier_f2
fabric_supplier_f3
trim_supplier_t1
packaging_supplier_p1
qc_provider_q1
logistics_provider_l1
```

### Project

```text
shirt_100pcs_project
```

### CNC Project

```text
cnc_part_project
```

### Shop Capability Profile

```text
manufacturer_m_basic_shop_profile
```

Contains:

```text
3-axis CNC
limited 5-axis capability = false
supported material = aluminum 6061, steel, brass
typical tolerance = 0.05 mm
best tolerance = 0.02 mm
QC equipment = caliper, micrometer, basic inspection
CMM = false
surface treatment = outsourced
heat treatment = outsourced
schedule = limited
```

### Dynamic Schema

Seed:

```text
apparel / shirt / v0.1
cnc / precision_part / v0.1
packaging / custom_box / v0.1
```

Seed base fields for shirt:

```text
category
quantity
fabric_type
fabric_gsm
color
size_breakdown
trim_type
button_type
packaging_type
deadline
```

Seed base fields for CNC:

```text
material
quantity
tolerance
surface_finish
axis_count_required
work_envelope_x_mm
work_envelope_y_mm
work_envelope_z_mm
qc_method
heat_treatment_required
```

---

## 19. Smoke Test Requirements

### 19.1 run_db_smoke_test.py

Must:

1. Initialize database.
2. Create actors.
3. Create project.
4. Create buyer-to-main-supplier edge.
5. Resolve role contexts.
6. Write execution event.
7. Read data back.
8. Print success.

Command:

```bash
python scripts/run_db_smoke_test.py
```

---

### 19.2 run_role_switching_db_test.py

Must run:

```text
1. Buyer B creates shirt order project.
2. Manufacturer M receives buyer inquiry.
3. M is resolved as MAIN_M_SIDE.
4. Dependency needs are created: fabric, trim, packaging.
5. Procurement edges are created from M to fabric suppliers.
6. M is resolved as UPSTREAM_B_SIDE.
7. Fabric suppliers are resolved as UPSTREAM_M_SIDE.
8. Upstream inquiries and responses are created.
9. Options are created.
10. Approval request is approved.
11. Supplier Response Rollup is created.
12. Rollup is submitted back to B-side as SupplierResponse.
13. ExecutionEvents exist for all major transitions.
```

---

### 19.3 run_professional_free_db_test.py

Must run:

```text
1. Buyer B creates CNC project with CAD / STEP metadata.
2. Artifact record is created under Professional Free.
3. Warning event is recorded: Professional Free does not provide file encryption.
4. CADRequirementPacket is created.
5. ShopCapabilityProfile is loaded.
6. CADCNCMachiningMatchResult is created.
7. CapabilityFitReport is created.
8. Dependencies are created from match gaps.
9. SupplierResponseRollup includes CAD-to-CNC evidence.
10. ExecutionEvents exist for all steps.
```

---

### 19.4 run_dynamic_schema_learning_test.py

Must run:

```text
1. Create observed fields from mock supplier messages:
   - fabric_gsm
   - shrinkage_rate
   - color_fastness_grade
   - surface_roughness_ra
   - cmm_required
2. Create field proposals when thresholds are met or manually triggered.
3. Approve a low-risk field.
4. Store entity_dynamic_values.
5. Verify no physical table migration is required.
6. Verify all fields are traceable to source messages or artifacts.
```

---

## 20. Repository Interfaces

Implement minimal repository methods.

### ActorRepo

```python
create_actor(...)
get_actor(actor_id)
list_actors(...)
```

### ProjectRepo

```python
create_project(...)
get_project(project_id)
update_project_status(...)
```

### GraphRepo

```python
create_edge(...)
get_project_edges(project_id)
get_child_edges(parent_edge_id)
```

### RoleRepo

```python
create_role_context(...)
resolve_role_context(project_id, actor_id, edge_id=None)
```

### ExecutionEventRepo

```python
log_event(...)
list_project_events(project_id)
```

### DynamicSchemaRepo

```python
observe_field(...)
propose_field(...)
approve_field(...)
store_dynamic_value(...)
list_schema_fields(...)
```

---

## 21. Index Requirements

Add indexes for:

```text
actors.actor_type
projects.status
projects.original_buyer_actor_id
projects.main_supplier_actor_id
procurement_edges.project_id
procurement_edges.from_actor_id
procurement_edges.to_actor_id
procurement_edges.parent_edge_id
role_contexts.project_id
role_contexts.actor_id
messages.project_id
messages.session_id
execution_events.project_id
execution_events.event_type
execution_events.created_at
observed_fields.normalized_field_name
field_definitions.normalized_field_name
entity_dynamic_values.entity_type, entity_dynamic_values.entity_id
supplier_response_rollups.project_id
cad_cnc_match_results.project_id
```

---

## 22. Professional Free File Policy

Database must enforce the following default values for `artifacts` when `product_tier = professional_free`:

```text
encryption_enabled = false
dynamic_watermark_enabled = false
secure_viewer_enabled = false
warning_acknowledged must be true before CADRequirementPacket is created
```

If warning is not acknowledged, creation of CADRequirementPacket should fail in repository helper or service-layer test.

Warning text:

```text
Professional Free does not provide encrypted file protection or Enterprise CAP. Do not upload highly confidential CAD / STEP / BOM files. Use Enterprise CAP for confidential engineering documents.
```

---

## 23. Acceptance Criteria

The task is complete only if:

1. Database initializes locally with SQLite.
2. Alembic migration can create all tables.
3. Seed script creates MVP actors, projects, dynamic schemas, and shop capability profile.
4. Same actor can be MAIN_M_SIDE and UPSTREAM_B_SIDE in the same project.
5. Procurement graph supports parent-child edges.
6. Upstream inquiries, responses, options, approvals, and rollups can be stored and retrieved.
7. CADRequirementPacket, ShopCapabilityProfile, CADCNCMachiningMatchResult, and CapabilityFitReport can be stored and retrieved.
8. Professional Free file policy disables encryption, watermarking, secure viewer and Enterprise CAP fields.
9. ExecutionEvents are written for all major workflow transitions.
10. Dynamic schema layer can observe, propose, approve and store new fields without altering physical tables.
11. Supplier memory tables can store score snapshots and profile updates.
12. Patent notice seed data includes global free license scope and authorization contact.
13. All smoke test scripts run deterministically.
14. The schema remains PostgreSQL-compatible.
15. No external API, WeChat, WhatsApp, OpenClaw, MachinaCheck, ERP, MES, QMS, S3, MinIO or encryption service is required for local MVP database tests.

---

## 24. Do Not Do

Do not:

- hard-code companies permanently as Buyer or Supplier;
- skip RoleContext;
- skip ProcurementEdge;
- store CAD / STEP / BOM binary files directly in database;
- implement Enterprise CAP in Professional Free;
- allow AI to directly alter physical database schema at runtime;
- create a graph database dependency for MVP;
- require real IM credentials for database tests;
- require real MachinaCheck / ERP / MES / QMS integrations for database tests;
- create untraceable dynamic fields;
- use learned fields for buyer-facing scoring unless approved or marked experimental.

---

## 25. Final Deliverable

After implementation, output:

```text
1. List of created database model files.
2. Alembic migration status.
3. Seed script output.
4. Smoke test output.
5. Role-switching DB test output.
6. Professional Free CAD-CNC DB test output.
7. Dynamic schema learning test output.
8. Any assumptions or skipped items.
```

The final database layer must be ready for B-side MVP, M-side MVP, role-switching procurement graph, upstream inquiry loop, CAD-to-CNC Professional Free matching, Supplier Response Rollup, Industrial Execution Graph v0.1, and dynamic self-learning schema.

