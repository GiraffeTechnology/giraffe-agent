# CLAUDE CODE INSTRUCTION — M-side MVP Role-Switching Procurement Agent v2

## 0. Executive Summary

Build the M-side MVP for Giraffe Agent as a **project-aware role-switching procurement agent**.

The core requirement is:

> The M-side agent must automatically identify the actor's role within each project, and then roll up information obtained from upstream suppliers and subcontractors into a structured response back to the buyer.

Example:

- Buyer B orders 100 shirts from Manufacturer M.
- Manufacturer M is M-side to Buyer B.
- To answer Buyer B credibly, Manufacturer M must ask multiple fabric suppliers, trim suppliers, packaging suppliers, subcontractors, QC providers, and logistics providers.
- In these upstream inquiries, Manufacturer M becomes B-side.
- Fabric suppliers and subcontractors become M-side to Manufacturer M.
- Giraffe Agent collects and structures upstream responses, compares 1–3 feasible options, obtains human approval or authorized agent approval, and merges the approved information into Manufacturer M's final buyer-facing response.

This is the core product logic of the M-side MVP.

---

## 1. Non-negotiable Product Principle

Do not treat B-side and M-side as fixed identities.

An actor's role is contextual.

The same company may be:

- M-side supplier to its buyer.
- B-side buyer to its upstream material suppliers.
- B-side buyer to its subcontractors.
- B-side buyer to packaging, QC, or logistics providers.

Therefore, every workflow must be project-aware and edge-aware.

---

## 1A. Patent Rights, Licensing and Open Source Boundary

### 1A.1 Patent Notice

Certain workflows, business methods, system designs, data structures, role-based participant coordination mechanisms, dynamic form generation mechanisms, production monitoring mechanisms, quality inspection mechanisms, participant matching mechanisms, and multi-party C2M / order execution workflows implemented or referenced by this project may be covered by patents owned by Giraffe Technology Holding Limited.

The relevant patent family includes, without limitation:

- China invention patent: **ZL 2023 1 1645939.9**, publication / grant number **CN 117670482 B**, titled **“基于多方配合的C2M模式的纺织品及服装定制运营平台系统”**.
- Japan patent: **P7644545 / 特許第7644545号**, application number **P2024-57581**, titled **“協働型C2Mモデルに基づく繊維及びアパレルカスタマイズ運用プラットフォームシステム”**.

The patent owner is **Giraffe Technology Holding Limited**.

### 1A.2 Global Free Patent License Scope

Giraffe Technology Holding Limited grants a free patent license, to the extent it is legally able to do so, for compliant use of the relevant patented workflows and system logic by the following users worldwide:

1. **Individuals**  
   Individual developers, independent operators, freelancers, researchers, students, and personal users.

2. **Small and Medium-sized Enterprises (SMEs)**  
   SMEs using, deploying, adapting, localizing, or contributing to Giraffe Agent for their own procurement, production coordination, supplier communication, sourcing, order execution, or internal business workflows.

3. **Educational Institutions**  
   Schools, universities, colleges, vocational schools, teaching labs, student projects, and academic training programs using Giraffe Agent for learning, teaching, curriculum design, demonstrations, or non-commercial educational deployment.

4. **Research Institutions**  
   Universities, public research institutes, nonprofit research organizations, academic labs, industrial research labs, and independent research groups using Giraffe Agent for research, experiments, publications, prototypes, benchmark studies, open innovation, or non-commercial research collaboration.

This free patent license is intended to support global open-source adoption, SME digitization, developer contribution, education, research, localization, and workflow experimentation.

### 1A.3 Permitted Uses under the Global Free License

The above users may, on a free-of-charge patent-license basis:

- use the software for their own operations;
- deploy the system internally;
- modify and localize the workflows;
- build connectors, adapters, templates, and industry knowledge packs;
- test the role-switching procurement workflow;
- run buyer-side and M-side order execution workflows;
- use the system for teaching, research, prototyping, and non-commercial experiments;
- publish academic or technical findings, provided that Giraffe Technology’s patent notice and attribution are preserved;
- contribute code, documentation, workflow templates, and localization materials back to the open-source project.

### 1A.4 Uses Requiring Separate Written Permission

The global free patent license does not automatically cover the following use cases. Prior written permission from Giraffe Technology Holding Limited is required for:

1. **Enterprise Deployment**  
   Deployment by large enterprises, multinational corporations, listed companies, industrial groups, large trading platforms, or enterprise procurement organizations.

2. **Platform Operation**  
   Operating a marketplace, SaaS platform, cloud service, procurement platform, manufacturing network, supplier network, B2B trading platform, or order execution platform based on the patented workflow.

3. **High-volume Commercial Production Use**  
   High-frequency, large-scale, multi-client, revenue-generating, or production-grade commercial operation beyond ordinary SME self-use.

4. **System Integration for Third Parties**  
   Commercial integration, customization, deployment, or managed service provision for third-party clients.

5. **White-label / OEM / Resale**  
   Repackaging, reselling, white-labeling, sublicensing, or embedding the patented workflow into another commercial platform or product.

6. **Enterprise CAP / Confidential Engineering File Services**  
   Use involving enterprise-grade confidential artifact protection, CAD / STEP / BOM protection, secure engineering data rooms, VPC deployment, no-download rooms, dynamic watermarking, or enterprise-grade file governance.

7. **Use of Giraffe Commercial Assets**  
   Use of Giraffe’s trademarks, brand, supplier network, buyer network, commercial operating rights, transaction data, supplier profile data, buyer data, order archives, Industrial Execution Graph data, or proprietary business data.

Any request for enterprise deployment, platform operation, high-volume commercial use, third-party system integration, white-label / OEM / resale, Enterprise CAP, or other use outside the global free patent license scope should be directed to:

Authorization contact: **mich@giraffe.technology**


### 1A.5 Open Source Boundary

The source code may be released under open-source licenses as specified in the repository. However, access to the source code does not automatically grant any additional rights to:

- Giraffe patents outside the free license scope stated above;
- Giraffe trademarks or brand assets;
- supplier network data;
- buyer data;
- transaction records;
- order archives;
- Industrial Execution Graph data;
- commercial operating rights;
- enterprise deployment rights;
- platform operating rights;
- sublicensing rights.

Open-source code access and patent permission are separate legal layers.

### 1A.6 Patent Notice Files Required

Claude Code must create or update the following files:

```text
README.md
LICENSE_NOTICE.md
PATENT_NOTICE.md
src/legal/patent_notice.py
```

The patent notice must clearly state:

- China patent: ZL 2023 1 1645939.9 / CN 117670482 B.
- Japan patent: P7644545 / 特許第7644545号.
- Patent owner: Giraffe Technology Holding Limited.
- Free patent license applies globally to individuals, SMEs, educational institutions, and research institutions for compliant use.
- Enterprise deployment, platform operation, large-scale commercial use, third-party system integration, white-label resale, Enterprise CAP, and use of Giraffe commercial assets require separate written permission.
- Open-source code access does not automatically grant rights outside the stated free patent license scope.
- Authorization contact: mich@giraffe.technology.

### 1A.7 Repository Notice Text

Use the following short notice in README and package metadata:

```text
Patent Notice:
Certain workflows and system logic in this project may be covered by patents owned by Giraffe Technology Holding Limited, including China patent ZL 2023 1 1645939.9 / CN 117670482 B and Japan patent P7644545.

Giraffe Technology Holding Limited grants a free patent license for compliant use by individuals, SMEs, educational institutions, and research institutions worldwide. Enterprise deployment, platform operation, high-volume commercial production use, third-party system integration, white-label resale, Enterprise CAP, and use of Giraffe commercial assets require separate written permission.

Open-source access to this repository does not automatically grant rights to Giraffe patents beyond the stated free license scope, nor does it grant rights to Giraffe trademarks, supplier network, buyer data, transaction data, order archives, Industrial Execution Graph data, or commercial operating rights.

For authorization outside the global free patent license scope, contact: mich@giraffe.technology.
```

### 1A.8 Chinese Notice Text

Use the following Chinese notice where appropriate:

```text
专利提示：
本项目中的部分工作流、系统逻辑、参与者协同机制、动态表单机制、生产监控机制、质量检测机制、角色切换式采购执行流程及多方 C2M / 订单执行流程，可能涉及长颈鹿科技（控股）有限公司拥有的相关专利，包括中国发明专利 ZL 2023 1 1645939.9 / CN 117670482 B 及日本专利 P7644545 / 特許第7644545号。

长颈鹿科技（控股）有限公司向全球范围内的个人、中小企业（SME）、教育机构及科研机构，就合规使用相关专利工作流与系统逻辑授予免费专利许可。企业级部署、平台化运营、大规模商业生产使用、为第三方提供系统集成或托管服务、白标/OEM/转售、Enterprise CAP、以及使用长颈鹿商标、供应商网络、买方数据、交易数据、订单档案、Industrial Execution Graph 数据或商业运营权，须另行取得书面许可。

取得本项目开源代码，并不当然取得超出上述免费专利许可范围之外的任何专利权、商标权、商业运营权、数据权利或平台运营权。

如需申请超出全球免费专利许可范围之外的授权，请联系：mich@giraffe.technology。
```


## 2. Required Architecture

Implement a neutral actor model.

### 2.1 Actor

Create:

```text
src/actors/models.py
```

```python
Actor
- actor_id: str
- name: str
- actor_type: Literal[
    "buyer",
    "manufacturer",
    "trading_company",
    "material_supplier",
    "component_supplier",
    "subcontractor",
    "qc_provider",
    "packaging_supplier",
    "logistics_provider",
    "unknown"
  ]
- contact_channels: list[ContactChannel]
- capabilities: list[str]
- default_language: str
- metadata: dict
```

### 2.2 RoleContext

Create:

```text
src/actors/role_context.py
```

```python
RoleContext
- project_id: str
- actor_id: str
- counterparty_actor_id: str | None
- edge_id: str | None
- role: Literal[
    "ORIGINAL_BUYER",
    "MAIN_M_SIDE",
    "UPSTREAM_B_SIDE",
    "UPSTREAM_M_SIDE",
    "QC_SIDE",
    "LOGISTICS_SIDE",
    "UNKNOWN"
  ]
- role_reason: str
- can_create_upstream_inquiry: bool
- can_approve_upstream_option: bool
- can_submit_response_to_buyer: bool
```

Examples:

```json
{
  "actor_id": "manufacturer_m",
  "role": "MAIN_M_SIDE",
  "role_reason": "Manufacturer M received the original inquiry from Buyer B."
}
```

```json
{
  "actor_id": "manufacturer_m",
  "role": "UPSTREAM_B_SIDE",
  "role_reason": "Manufacturer M is asking fabric suppliers for material availability in order to respond to Buyer B."
}
```

```json
{
  "actor_id": "fabric_supplier_1",
  "role": "UPSTREAM_M_SIDE",
  "role_reason": "Fabric Supplier 1 received an upstream inquiry from Manufacturer M."
}
```

---

## 3. Role Resolver

Create:

```text
src/actors/role_resolver.py
```

Implement:

```python
resolve_role_context(project_id: str, actor_id: str, edge_id: str | None = None) -> RoleContext
```

The resolver must inspect:

- original buyer
- main supplier
- current inquiry sender
- current inquiry receiver
- upstream dependency edges
- current workspace type
- approval permissions
- order state

Acceptance requirement:

The same actor must be resolved as:

- `MAIN_M_SIDE` when responding to the original buyer.
- `UPSTREAM_B_SIDE` when asking upstream suppliers.
- Another supplier must be resolved as `UPSTREAM_M_SIDE` when responding to that upstream inquiry.

---

## 4. Project Graph

Create:

```text
src/projects/models.py
src/projects/project_graph.py
```

```python
ProcurementProject
- project_id: str
- original_buyer_actor_id: str
- main_supplier_actor_id: str | None
- product_summary: str
- category: str
- quantity: int | None
- status: Literal[
    "CREATED",
    "MAIN_SUPPLIER_RECEIVED",
    "UPSTREAM_DEPENDENCY_PLANNED",
    "UPSTREAM_INQUIRIES_SENT",
    "UPSTREAM_RESPONSES_RECEIVED",
    "UPSTREAM_OPTIONS_READY",
    "UPSTREAM_OPTION_APPROVED",
    "SUPPLIER_RESPONSE_ROLLED_UP",
    "SUPPLIER_RESPONSE_SUBMITTED_TO_BUYER",
    "ORDER_CONFIRMED",
    "IN_EXECUTION",
    "CLOSED"
  ]
```

```python
ProcurementEdge
- edge_id: str
- project_id: str
- from_actor_id: str
- to_actor_id: str
- edge_type: Literal[
    "BUYER_TO_MAIN_SUPPLIER",
    "MAIN_SUPPLIER_TO_MATERIAL_SUPPLIER",
    "MAIN_SUPPLIER_TO_TRIM_SUPPLIER",
    "MAIN_SUPPLIER_TO_COMPONENT_SUPPLIER",
    "MAIN_SUPPLIER_TO_SUBCONTRACTOR",
    "MAIN_SUPPLIER_TO_PACKAGING_SUPPLIER",
    "MAIN_SUPPLIER_TO_QC_PROVIDER",
    "MAIN_SUPPLIER_TO_LOGISTICS_PROVIDER"
  ]
- inquiry_id: str | None
- response_id: str | None
- status: Literal[
    "DRAFT",
    "SENT",
    "RESPONDED",
    "OPTIONS_READY",
    "APPROVED",
    "ROLLED_UP"
  ]
```

---

## 5. Main Supplier Workflow

When Manufacturer M receives an inquiry from Buyer B, the M-side agent must:

1. Resolve Manufacturer M as `MAIN_M_SIDE`.
2. Parse the buyer requirement.
3. Determine whether M can answer internally.
4. Identify upstream dependencies.
5. Ask M whether to contact upstream / subcontractor suppliers.
6. Generate upstream inquiries.
7. Dispatch upstream inquiries.
8. Parse upstream responses.
9. Generate 1–3 upstream options.
10. Ask for human approval or authorized agent approval.
11. Roll approved options into a buyer-facing response.
12. Submit the response back to Buyer B.

---

## 6. Dependency Planner

Create:

```text
src/m_side/dependencies/dependency_planner.py
```

Implement:

```python
plan_upstream_dependencies(project, structured_requirement, main_supplier_actor_id) -> list[DependencyNeed]
```

```python
DependencyNeed
- dependency_id: str
- project_id: str
- dependency_type: Literal[
    "fabric",
    "trim",
    "raw_material",
    "component",
    "subcontract_process",
    "surface_treatment",
    "heat_treatment",
    "qc_testing",
    "packaging",
    "logistics"
  ]
- description: str
- required_specs: dict
- quantity_required: float | int | None
- required_by_date: str | None
- risk_level: Literal["low", "medium", "high"]
- why_needed: str
- candidate_actor_ids: list[str]
```

For the 100-shirt example, the system must identify at least:

- fabric
- trim / buttons
- packaging
- sewing capacity if outsourced
- QC if required
- logistics if destination or deadline affects feasibility

---

## 7. Upstream Inquiry Builder

Create:

```text
src/m_side/upstream/inquiry_builder.py
```

Implement:

```python
build_upstream_inquiry(project_id: str, dependency_id: str, upstream_actor_id: str) -> UpstreamInquiry
```

```python
UpstreamInquiry
- inquiry_id: str
- project_id: str
- parent_main_supplier_actor_id: str
- upstream_actor_id: str
- dependency_id: str
- message_text_en: str
- message_text_zh: str
- requested_fields: list[str]
- required_reply_schema: dict
- due_time: str | None
```

For fabric suppliers, the inquiry must ask:

- fabric availability
- stock quantity
- MOQ
- price
- color availability
- quality / shrinkage risk
- substitute options
- earliest dispatch date
- whether buyer deadline can be supported

---

## 8. Upstream Dispatch

Create:

```text
src/m_side/upstream/dispatch_service.py
```

Implement:

```python
dispatch_upstream_inquiry(inquiry_id: str, channel: Literal["wechat", "whatsapp", "openclaw", "web_fallback", "mock"]) -> DispatchResult
```

The MVP must run locally with mock channels.

Real IM channels must be configurable later by environment variables.

```text
MOCK_CHANNELS=true
WECHAT_ENABLED=false
WHATSAPP_ENABLED=false
OPENCLAW_ENABLED=true
```

---

## 9. Upstream Response Parser

Create:

```text
src/m_side/upstream/response_parser.py
```

Implement:

```python
parse_upstream_response(raw_message: str, inquiry_id: str, upstream_actor_id: str) -> UpstreamResponse
```

```python
UpstreamResponse
- response_id: str
- inquiry_id: str
- project_id: str
- upstream_actor_id: str
- dependency_id: str
- can_supply: bool
- matched_specs: dict
- price: float | None
- currency: str | None
- moq: int | float | None
- available_quantity: int | float | None
- lead_time_days: int | None
- earliest_dispatch_date: str | None
- quality_notes: str | None
- substitute_options: list[dict]
- risk_flags: list[str]
- confidence_score: float
- completeness_score: float
- raw_message: str
```

---

## 10. Upstream Option Engine

Create:

```text
src/m_side/upstream/option_engine.py
```

Implement:

```python
generate_upstream_options(project_id: str, dependency_id: str) -> list[UpstreamOption]
```

```python
UpstreamOption
- option_id: str
- project_id: str
- dependency_id: str
- upstream_actor_id: str
- option_label: Literal["BEST", "FASTEST", "SAFEST", "LOWEST_COST", "BACKUP"]
- price_summary: str
- lead_time_summary: str
- risk_summary: str
- score: float
- reason: str
- response_ids: list[str]
```

For each dependency, generate 1–3 recommended options.

For the 100-shirt example:

- Fabric Option 1: Best overall
- Fabric Option 2: Fastest
- Fabric Option 3: Backup / safer alternative

---

## 11. Approval Gate

Create:

```text
src/m_side/upstream/approval_gate.py
```

Implement:

```python
request_upstream_option_approval(project_id: str, dependency_id: str, options: list[UpstreamOption]) -> ApprovalRequest
approve_upstream_option(approval_request_id: str, approved_option_id: str, approved_by: str, mode: Literal["human", "authorized_agent"]) -> ApprovalResult
```

Rules:

- Default approval mode is human approval.
- Authorized agent approval is allowed only if `AUTO_APPROVAL_ENABLED=true`.
- Medium or high risk options always require human approval.
- The system must not roll up unapproved upstream options into the buyer-facing response.

---

## 12. Supplier Response Rollup

Create:

```text
src/m_side/rollup/supplier_response_rollup.py
```

Implement:

```python
generate_supplier_response_rollup(project_id: str, main_supplier_actor_id: str) -> SupplierResponseRollup
```

```python
SupplierResponseRollup
- rollup_id: str
- project_id: str
- main_supplier_actor_id: str
- can_accept_order: bool
- main_capacity_summary: str
- approved_upstream_options: list[ApprovedDependencyOption]
- material_basis: dict
- trim_basis: dict
- subcontract_basis: dict
- qc_basis: dict
- packaging_basis: dict
- logistics_basis: dict
- price_basis: dict
- lead_time_basis: dict
- unresolved_dependencies: list[str]
- risk_flags: list[str]
- completeness_score: float
- confidence_score: float
- recommended_response_to_buyer_en: str
- recommended_response_to_buyer_zh: str
```

The rollup must state:

- what M can do internally
- which upstream dependencies were confirmed
- which option was approved
- which dependencies are unresolved
- what delivery promise can be credibly made to Buyer B
- what risks require buyer confirmation

Example buyer-facing response:

```text
We can support the 100-shirt order based on approved Fabric Option A and Trim Option B. Fabric can be dispatched in 3 days, MOQ fits the requested quantity, and sewing capacity is available from [date]. Estimated production lead time is 12–15 days after fabric arrival. Key risk: color confirmation is required before cutting. We recommend confirming Fabric Option A before final order acknowledgement.
```

---

## 13. Submit Rollup Back to B-side

Create:

```text
src/m_side/bridge/submit_rollup_to_b_side.py
```

Implement:

```python
submit_rollup_to_b_side(project_id: str, rollup_id: str) -> SubmitResult
```

The B-side feasibility engine must be able to consume the rollup as a supplier response with dependency evidence.

Map rollup fields into:

- can_supply
- price_basis
- lead_time_days
- capacity_basis
- material_basis
- subcontract_basis
- qc_basis
- logistics_basis
- risk_flags
- confidence_score
- completeness_score

---

## 14. IM Interaction Flow

### 14.1 M receives buyer inquiry

```text
Giraffe Agent:
Buyer B is asking whether you can produce 100 shirts.

Your role in this project:
M-side supplier to Buyer B.

To respond credibly, we need to confirm:
1. Fabric
2. Trims / buttons
3. Packaging
4. Sewing capacity
5. QC
6. Logistics

Would you like Giraffe to ask upstream suppliers now?

A. Ask selected upstream suppliers
B. Edit upstream supplier list
C. Reply based on internal estimate only
```

### 14.2 M becomes B-side to upstream suppliers

```text
Giraffe Agent:
You are now acting as B-side buyer to fabric suppliers for this project.

I will send the following inquiry to 3 fabric suppliers:
[message preview]

Approve sending?
```

### 14.3 Upstream options ready

```text
Giraffe Agent:
Fabric options are ready.

Option 1 — Best Overall
Supplier: F1
Price: ...
Lead time: ...
MOQ: ...
Risk: ...

Option 2 — Fastest
Supplier: F2
...

Option 3 — Backup
Supplier: F3
...

Approve one option, ask for more quotes, or edit assumptions?
```

### 14.4 Rollup ready

```text
Giraffe Agent:
Your buyer-facing response is ready.

It includes:
- internal capacity
- approved fabric option
- approved trim option
- packaging assumption
- estimated lead time
- unresolved risk
- recommended response

Approve submission to Buyer B?
```

---

## 15. APIs

Add these routes:

```text
POST /api/projects/{project_id}/resolve-role
POST /api/m-side/{project_id}/plan-dependencies
POST /api/m-side/{project_id}/upstream-inquiries
POST /api/m-side/upstream/{inquiry_id}/dispatch
POST /api/m-side/upstream/{inquiry_id}/responses
GET  /api/m-side/{project_id}/upstream-options
POST /api/m-side/{project_id}/approve-upstream-option
POST /api/m-side/{project_id}/rollup
POST /api/m-side/{project_id}/submit-rollup-to-b-side
```

---

## 16. Industrial Execution Graph Events

Add event types:

```text
ROLE_CONTEXT_RESOLVED
ROLE_SWITCH_OCCURRED
M_SIDE_RECEIVED_BUYER_INQUIRY
UPSTREAM_DEPENDENCY_PLANNED
UPSTREAM_INQUIRY_CREATED
UPSTREAM_INQUIRY_DISPATCHED
UPSTREAM_RESPONSE_RECEIVED
UPSTREAM_RESPONSE_PARSED
UPSTREAM_OPTIONS_GENERATED
UPSTREAM_OPTION_APPROVAL_REQUESTED
UPSTREAM_OPTION_APPROVED
SUPPLIER_RESPONSE_ROLLUP_GENERATED
SUPPLIER_RESPONSE_ROLLUP_SUBMITTED_TO_B_SIDE
```

Each event must include:

```python
event_id
project_id
actor_id
role_context
edge_id
event_type
payload
created_at
```

---

## 17. Shirt Example Fixtures

Create fixtures:

```text
tests/fixtures/projects/shirt_100pcs_project.json
tests/fixtures/actors/buyer_b.json
tests/fixtures/actors/manufacturer_m.json
tests/fixtures/actors/fabric_suppliers.json
tests/fixtures/actors/trim_suppliers.json
tests/fixtures/actors/packaging_suppliers.json
tests/fixtures/upstream_responses/fabric_supplier_responses.json
tests/fixtures/upstream_responses/trim_supplier_responses.json
```

---

## 18. End-to-End Script

Create:

```text
scripts/run_role_switching_mvp.py
```

It must run:

```text
1. Buyer B creates project: 100 shirts.
2. Manufacturer M receives the inquiry.
3. Role resolver identifies Manufacturer M as MAIN_M_SIDE to Buyer B.
4. Dependency planner identifies fabric, trim, packaging, capacity, QC, and logistics dependencies.
5. Manufacturer M becomes UPSTREAM_B_SIDE to fabric suppliers.
6. Giraffe sends inquiries to 3 fabric suppliers.
7. Fabric suppliers reply.
8. Giraffe parses fabric supplier responses.
9. Giraffe generates 1–3 fabric options.
10. Human / authorized agent approval selects one fabric option.
11. Giraffe repeats or mocks trim and packaging dependency confirmation.
12. Giraffe generates Supplier Response Rollup.
13. Manufacturer M approves the rollup.
14. Rollup is submitted to Buyer B's B-side workspace.
15. B-side feasibility engine consumes the rollup.
16. Industrial Execution Graph records all role switching and dependency events.
```

Command:

```bash
uv run python scripts/run_role_switching_mvp.py
```

---

## 19. Acceptance Criteria

The task is complete only if:

Patent / licensing criteria:

0. README.md, LICENSE_NOTICE.md, PATENT_NOTICE.md and src/legal/patent_notice.py must be created or updated.
0.1 The patent notice must state that free patent license coverage extends globally to individuals, SMEs, educational institutions and research institutions for compliant use.
0.2 The patent notice must state that enterprise deployment, platform operation, high-volume commercial production use, third-party system integration, white-label resale, Enterprise CAP and use of Giraffe commercial assets require separate written permission.
0.3 The patent notice must state that open-source code access does not automatically grant rights beyond the stated free patent license scope.
0.4 The patent notice must include the authorization contact email: mich@giraffe.technology.



1. The same actor can be resolved as M-side to a buyer and B-side to upstream suppliers in the same project.
2. RoleContext is explainable.
3. M-side can detect upstream dependencies.
4. The system can generate upstream inquiries.
5. Upstream suppliers can respond through mock IM or web fallback.
6. Upstream responses are parsed into structured data.
7. The system can recommend 1–3 upstream options.
8. Human or authorized agent approval is required.
9. Approved upstream information is rolled up into a main supplier response.
10. The main supplier response is submitted back to the B-side workspace.
11. The B-side feasibility engine can consume the rollup.
12. Industrial Execution Graph logs all role switching and dependency events.
13. The E2E script runs deterministically with fixture data.
14. Patent notice files are generated and include China patent ZL 2023 1 1645939.9 and Japan patent P7644545.
15. README and LICENSE_NOTICE state that open-source access does not automatically grant separate commercial patent rights.

---

## 20. Strategic Rationale

This role-switching mechanism is central to Giraffe Agent.

Most procurement products treat buyer and supplier as fixed identities. Giraffe treats every participant as a node in a recursive procurement execution graph. A manufacturer may be a supplier in one relationship and a buyer in another.

The M-side agent must help the manufacturer ask upstream and subcontractor suppliers, structure their responses, compare feasible dependency options, secure approval, and generate a credible buyer-facing delivery response.

This is how Giraffe turns supplier replies into delivery feasibility simulation.
