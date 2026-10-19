# M-side Professional Free MVP v4
# CAD-to-CNC / Machining Center Parameter Matching with Embedded MachinaCheck-like Capability

## 0. Executive Summary

Build the M-side Professional Free MVP for Giraffe Agent with an embedded MachinaCheck-like capability module.

The goal is:

> B-side CAD / STEP / PDF / BOM inputs must be converted into a manufacturability requirement packet and compared against M-side CNC / machining center / shop-floor capability parameters.

This Professional Free MVP should allow an SME manufacturer to receive a buyer inquiry, inspect the buyer's CAD or engineering requirement, compare it against its own machining capability, identify gaps, and decide whether to respond directly, ask upstream / subcontractors, or request clarification.

This is not an Enterprise CAP build.

Professional Free MVP must not provide file encryption, dynamic watermarking, secure no-download room, VPC deployment, or full confidential artifact protection.

It may provide basic file upload, file reference, audit log, local test storage, deletion, and user warning only.

---

## 1. Product Positioning

### 1.1 What This Is

M-side Professional Free is a free professional-grade MVP for SME manufacturers.

It helps manufacturers:

1. Receive B-side engineering inquiry.
2. Read or ingest CAD / STEP / PDF / BOM references.
3. Convert buyer file requirements into a structured manufacturing requirement packet.
4. Compare those requirements with CNC / machining center parameters.
5. Identify machine fit, work envelope fit, material fit, tolerance fit, tooling fit, process fit, QC fit, and schedule risk.
6. Generate capability evidence.
7. Decide whether to:
   - respond to buyer directly;
   - ask material suppliers;
   - ask subcontractors;
   - ask QC providers;
   - ask logistics providers;
   - request more information from buyer.
8. Roll the evidence into Supplier Response Rollup.

### 1.2 What This Is Not

This is not Enterprise CAP.

Do not implement:

- file encryption
- dynamic watermarking
- secure viewer
- no-download enforcement
- VPC
- enterprise permission room
- full confidentiality workflow
- production-grade CAD security
- external file vault

Add clear user warning:

> Professional Free does not provide encrypted file protection. Do not upload highly confidential CAD / STEP / BOM files unless you accept this limitation. Enterprise CAP is required for high-confidentiality engineering files.

---

## 2. Core Workflow

The workflow must run like this:

```text
Buyer B uploads / sends CAD, STEP, PDF, BOM, or engineering requirement
→ Giraffe creates CAD Requirement Packet
→ Manufacturer M receives inquiry as M-side
→ M-side Professional Free runs embedded MachinaCheck-like assessment
→ CAD Requirement Packet is compared with CNC / machining center capability profile
→ System produces Capability Fit Report
→ If gaps exist, M-side Agent generates upstream / subcontractor inquiries
→ M receives upstream responses
→ System generates 1–3 feasible options
→ Human or authorized agent approval
→ Supplier Response Rollup is sent back to B-side workspace
```

---

## 3. Required New Modules

Create the following modules:

```text
src/m_side/professional_free/
  __init__.py
  product_flags.py
  file_policy.py
  cad_requirement_packet.py
  machine_profile.py
  cad_cnc_matcher.py
  capability_fit_report.py
  professional_free_workflow.py

src/integrations/machinacheck_embedded/
  __init__.py
  embedded_assessor.py
  feature_extractor.py
  mock_cad_parser.py
  mock_step_parser.py
  mock_bom_parser.py

src/m_side/capability_profiles/
  cnc_machine_profile.py
  machining_center_profile.py
  qc_equipment_profile.py
  tooling_inventory_profile.py
  shop_capability_profile.py

tests/fixtures/cad_cnc_matching/
  cnc_part_simple_step_metadata.json
  cnc_part_tight_tolerance_metadata.json
  machining_center_profile_3axis.json
  machining_center_profile_5axis.json
  tooling_inventory_basic.json
  qc_equipment_basic.json
  cad_cnc_match_success.json
  cad_cnc_match_gap_external_qc_required.json
  cad_cnc_match_gap_subcontract_required.json

scripts/run_mside_professional_free_cad_cnc_mvp.py
```

---

## 4. Product Flags

Create:

```text
src/m_side/professional_free/product_flags.py
```

Define:

```python
PROFESSIONAL_FREE_FEATURES = {
    "cad_requirement_packet": True,
    "machinacheck_embedded_mock": True,
    "cad_cnc_parameter_matching": True,
    "machine_profile_matching": True,
    "supplier_response_rollup": True,
    "role_switching_upstream_inquiry": True,
    "basic_audit_log": True,

    "file_encryption": False,
    "dynamic_watermark": False,
    "secure_viewer": False,
    "no_download_room": False,
    "vpc_deployment": False,
    "enterprise_cap": False
}
```

All tests must assert that Enterprise CAP functions are disabled in Professional Free.

---

## 5. File Policy for Professional Free

Create:

```text
src/m_side/professional_free/file_policy.py
```

Implement:

```python
get_professional_free_file_policy() -> FilePolicy
```

Define:

```python
FilePolicy
- product_tier: Literal["professional_free"]
- encryption_enabled: bool = False
- dynamic_watermark_enabled: bool = False
- secure_viewer_enabled: bool = False
- local_storage_allowed: bool = True
- mock_file_refs_allowed: bool = True
- audit_log_enabled: bool = True
- user_warning_required: bool = True
- warning_text: str
```

Warning text:

```text
Professional Free does not provide encrypted file protection or Enterprise CAP. Do not upload highly confidential CAD / STEP / BOM files. Use Enterprise CAP for confidential engineering documents.
```

Do not block local MVP file references.

Do create audit events:

- FILE_REFERENCE_CREATED
- PROFESSIONAL_FREE_FILE_WARNING_SHOWN
- CAD_REQUIREMENT_PACKET_CREATED

---

## 6. CAD Requirement Packet

Create:

```text
src/m_side/professional_free/cad_requirement_packet.py
```

Define:

```python
CADRequirementPacket
- packet_id: str
- project_id: str
- original_buyer_actor_id: str
- main_supplier_actor_id: str
- file_refs: list[str]
- source_types: list[Literal["cad", "step", "pdf", "bom", "image", "manual"]]
- part_summary: str | None
- material: str | None
- quantity: int | None
- dimensions: dict
- tolerance_requirements: dict
- surface_finish_requirements: dict
- thread_requirements: dict
- heat_treatment_requirements: dict
- operation_requirements: list[str]
- qc_requirements: dict
- packaging_requirements: dict
- delivery_deadline: str | None
- missing_information: list[str]
- extraction_confidence_score: float
```

Implement:

```python
create_cad_requirement_packet(project_id: str, buyer_input: dict) -> CADRequirementPacket
```

Local MVP may use fixture metadata and rule-based extraction. Do not require full CAD parsing.

---

## 7. Embedded MachinaCheck-like Feature Extractor

Create:

```text
src/integrations/machinacheck_embedded/feature_extractor.py
```

Implement:

```python
extract_manufacturing_features(packet: CADRequirementPacket) -> ManufacturingFeatureSet
```

Define:

```python
ManufacturingFeatureSet
- feature_set_id: str
- packet_id: str
- required_processes: list[str]
- required_machine_types: list[str]
- min_axis_requirement: int | None
- work_envelope_required: dict
- material_required: str | None
- tolerance_class: Literal["standard", "medium", "tight", "unknown"]
- surface_finish_class: Literal["standard", "fine", "mirror", "unknown"]
- thread_or_hole_features: list[dict]
- heat_treatment_required: bool
- external_process_likely_required: bool
- qc_required: list[str]
- risk_flags: list[str]
- missing_information: list[str]
```

For local MVP, use simple deterministic heuristics.

Examples:

- Tight tolerance → higher QC requirement.
- 5-axis feature flag → requires 5-axis machining center or subcontractor.
- Heat treatment required → external process dependency if not in shop profile.
- Material not in stock → upstream material inquiry.

---

## 8. CNC / Machining Center Profile

Create:

```text
src/m_side/capability_profiles/machining_center_profile.py
```

Define:

```python
MachiningCenterProfile
- machine_id: str
- actor_id: str
- machine_name: str
- machine_type: Literal["cnc_milling", "cnc_turning", "turn_mill", "5_axis_machining_center", "grinding", "edm", "other"]
- axis_count: int | None
- travel_x_mm: float | None
- travel_y_mm: float | None
- travel_z_mm: float | None
- max_part_weight_kg: float | None
- spindle_speed_rpm: int | None
- spindle_power_kw: float | None
- tool_magazine_capacity: int | None
- supported_materials: list[str]
- typical_tolerance_mm: float | None
- best_tolerance_mm: float | None
- surface_finish_capability: list[str]
- available_operations: list[str]
- schedule_status: Literal["available", "limited", "busy", "unknown"]
- earliest_start_date: str | None
```

Create:

```text
src/m_side/capability_profiles/shop_capability_profile.py
```

Define:

```python
ShopCapabilityProfile
- actor_id: str
- machines: list[MachiningCenterProfile]
- tooling_inventory: dict
- qc_equipment: list[dict]
- in_house_processes: list[str]
- outsourced_processes: list[str]
- material_inventory: dict
- schedule_summary: dict
```

---

## 9. CAD-to-CNC Matcher

Create:

```text
src/m_side/professional_free/cad_cnc_matcher.py
```

Implement:

```python
match_cad_to_cnc_capability(
    packet: CADRequirementPacket,
    feature_set: ManufacturingFeatureSet,
    shop_profile: ShopCapabilityProfile
) -> CADCNCMachiningMatchResult
```

Define:

```python
CADCNCMachiningMatchResult
- match_id: str
- project_id: str
- actor_id: str
- can_make_in_house: bool
- recommended_machine_ids: list[str]
- machine_fit_score: float
- work_envelope_fit: Literal["fit", "not_fit", "unknown"]
- material_fit: Literal["in_stock", "purchasable", "not_supported", "unknown"]
- tolerance_fit: Literal["fit", "marginal", "not_fit", "unknown"]
- surface_finish_fit: Literal["fit", "requires_external_process", "not_fit", "unknown"]
- tooling_fit: Literal["fit", "setup_required", "missing", "unknown"]
- qc_fit: Literal["fit", "external_qc_required", "missing", "unknown"]
- schedule_fit: Literal["fit", "limited", "not_fit", "unknown"]
- required_upstream_dependencies: list[str]
- required_subcontract_dependencies: list[str]
- risk_flags: list[str]
- missing_information: list[str]
- confidence_score: float
- explanation: str
```

Matching rules:

- If work envelope exceeds all machines → can_make_in_house = False and subcontract dependency required.
- If material not in stock but supported → material dependency required.
- If material unsupported → risk flag and alternative supplier / subcontractor required.
- If tolerance tighter than best_tolerance_mm → QC or subcontract dependency.
- If operation requires 5-axis but only 3-axis available → subcontract dependency.
- If heat treatment or surface treatment is required but outsourced → subcontract_process dependency.
- If QC requirement cannot be met in-house → QC provider dependency.
- If schedule_status is busy → capacity or subcontract dependency.

---

## 10. Capability Fit Report

Create:

```text
src/m_side/professional_free/capability_fit_report.py
```

Implement:

```python
generate_capability_fit_report(match_result: CADCNCMachiningMatchResult) -> CapabilityFitReport
```

Define:

```python
CapabilityFitReport
- report_id: str
- project_id: str
- actor_id: str
- buyer_facing_summary_en: str
- buyer_facing_summary_zh: str
- internal_summary: str
- can_quote_now: bool
- can_make_in_house: bool
- recommended_next_actions: list[str]
- required_upstream_inquiries: list[str]
- required_subcontractor_inquiries: list[str]
- risk_flags: list[str]
- confidence_score: float
```

The report must be readable by SME users.

---

## 11. Link to Role-Switching Upstream Inquiry

Update dependency planner:

```text
src/m_side/dependencies/dependency_planner.py
```

Add:

```python
plan_dependencies_from_cad_cnc_match(
    project_id: str,
    match_result: CADCNCMachiningMatchResult
) -> list[DependencyNeed]
```

Rules:

- `material_fit == purchasable` → material supplier inquiry.
- `surface_finish_fit == requires_external_process` → surface treatment subcontractor inquiry.
- `qc_fit == external_qc_required` → QC provider inquiry.
- `schedule_fit == limited` → backup subcontractor inquiry.
- `work_envelope_fit == not_fit` → subcontractor inquiry.
- `tolerance_fit == marginal` → QC / process review inquiry.
- `tooling_fit == setup_required` → tooling supplier or setup confirmation.

---

## 12. Supplier Response Rollup Update

Update:

```text
src/m_side/rollup/supplier_response_rollup.py
```

Add fields:

```python
SupplierResponseRollup
- cad_requirement_packet_id: str | None
- cad_cnc_match_id: str | None
- capability_fit_report_id: str | None
- cnc_parameter_match_summary: dict
- can_make_in_house: bool | None
- recommended_machine_ids: list[str]
- capability_gaps: list[str]
- upstream_dependency_basis: dict
```

Buyer-facing response must include capability basis, for example:

```text
We can quote this part based on our current 3-axis CNC capability, but material confirmation and external surface treatment are required before final lead-time commitment. The CAD requirement fits our work envelope and typical tolerance range. QC is available in-house for standard inspection, while tighter inspection requires external QC confirmation.
```

---

## 13. B-side Feasibility Engine Update

The B-side feasibility engine must consume:

- SupplierResponseRollup
- CapabilityFitReport
- CADCNCMachiningMatchResult

And adjust:

- quote readiness score
- capability confidence score
- lead-time credibility score
- risk flags
- missing information list
- Top 3 supplier / delivery path ranking

Do not give a high score if:

- CAD data is incomplete.
- machine profile is missing.
- tolerance cannot be matched.
- material is unknown.
- unresolved upstream dependencies remain.
- Professional Free file warning was ignored.

---

## 14. APIs

Add:

```text
POST /api/m-side/professional-free/file-policy
POST /api/m-side/professional-free/cad-requirement-packet
POST /api/m-side/professional-free/extract-features
POST /api/m-side/professional-free/shop-profile
POST /api/m-side/professional-free/cad-cnc-match
POST /api/m-side/professional-free/capability-fit-report
POST /api/m-side/professional-free/plan-dependencies-from-match
```

---

## 15. IM Interaction Flow

### 15.1 B-side inquiry received by M

```text
Giraffe Agent:
Buyer B has sent a CNC / machining inquiry with CAD / STEP / BOM references.

Your role in this project:
M-side supplier to Buyer B.

Professional Free can compare the buyer's CAD requirements with your CNC / machining center capability.

Important:
Professional Free does not provide encrypted file protection. Do not upload highly confidential engineering files. Use Enterprise CAP for confidential CAD / STEP / BOM.

Proceed with CAD-to-CNC capability matching?

A. Proceed
B. Enter requirements manually
C. Skip and reply manually
```

### 15.2 Capability matching result

```text
Giraffe Agent:
CAD-to-CNC matching complete.

Result:
- Work envelope: fit
- Machine fit: 3-axis CNC available
- Material: not in stock, supplier confirmation required
- Tolerance: marginal, QC review required
- Surface treatment: external process required
- Schedule: limited capacity next week

Recommended actions:
1. Ask material suppliers
2. Ask surface treatment subcontractors
3. Ask QC provider
4. Prepare buyer-facing response after confirmations
```

### 15.3 Rollup to buyer

```text
Giraffe Agent:
Buyer-facing response is ready.

It includes:
- CAD-to-CNC matching basis
- machine capability evidence
- approved material option
- approved subcontractor option
- QC condition
- estimated lead time
- unresolved risks

Approve submission to Buyer B?
```

---

## 16. Industrial Execution Graph Events

Add:

```text
PROFESSIONAL_FREE_FILE_WARNING_SHOWN
CAD_REQUIREMENT_PACKET_CREATED
CAD_FEATURES_EXTRACTED
SHOP_CAPABILITY_PROFILE_LOADED
CAD_CNC_MATCH_STARTED
CAD_CNC_MATCH_COMPLETED
MACHINE_PARAMETER_MATCHED
MACHINE_PARAMETER_GAP_FOUND
CAPABILITY_FIT_REPORT_CREATED
DEPENDENCY_CREATED_FROM_CAD_CNC_MATCH
PROFESSIONAL_FREE_CAP_LIMITATION_ACKNOWLEDGED
```

---

## 17. Test Fixtures

Create fixtures:

```text
tests/fixtures/cad_cnc_matching/cnc_part_simple_step_metadata.json
tests/fixtures/cad_cnc_matching/cnc_part_tight_tolerance_metadata.json
tests/fixtures/cad_cnc_matching/cnc_part_5axis_required_metadata.json
tests/fixtures/cad_cnc_matching/machining_center_profile_3axis.json
tests/fixtures/cad_cnc_matching/machining_center_profile_5axis.json
tests/fixtures/cad_cnc_matching/shop_profile_basic_sme.json
tests/fixtures/cad_cnc_matching/shop_profile_limited_capacity.json
tests/fixtures/cad_cnc_matching/cad_cnc_match_success.json
tests/fixtures/cad_cnc_matching/cad_cnc_match_gap_external_qc_required.json
tests/fixtures/cad_cnc_matching/cad_cnc_match_gap_subcontract_required.json
```

---

## 18. End-to-End Script

Create:

```text
scripts/run_mside_professional_free_cad_cnc_mvp.py
```

It must run:

```text
1. Buyer B submits CNC / machining inquiry with CAD / STEP / BOM metadata.
2. Manufacturer M receives inquiry.
3. Professional Free file policy warning is shown.
4. CAD Requirement Packet is created.
5. Embedded MachinaCheck-like feature extractor creates ManufacturingFeatureSet.
6. Manufacturer M's shop capability profile is loaded.
7. CAD-to-CNC matcher compares buyer requirement with machining center parameters.
8. Capability Fit Report is generated.
9. Dependency planner creates upstream material / subcontractor / QC inquiries based on match gaps.
10. Role resolver switches M from MAIN_M_SIDE to UPSTREAM_B_SIDE.
11. Upstream suppliers respond.
12. Options are generated and approved.
13. Supplier Response Rollup includes CAD-to-CNC matching basis.
14. Rollup is submitted back to B-side workspace.
15. B-side feasibility engine consumes the evidence-enhanced rollup.
16. Industrial Execution Graph records all file warning, matching, dependency, role switching and rollup events.
```

Command:

```bash
uv run python scripts/run_mside_professional_free_cad_cnc_mvp.py
```

---

## 19. Acceptance Criteria

The task is complete only if:

1. Professional Free explicitly disables file encryption and Enterprise CAP features.
2. Professional Free shows file confidentiality warning before CAD / STEP / BOM handling.
3. CAD Requirement Packet can be created from fixture CAD / STEP / BOM metadata.
4. Embedded MachinaCheck-like feature extractor produces ManufacturingFeatureSet.
5. ShopCapabilityProfile can represent CNC / machining center parameters.
6. CAD-to-CNC matcher compares buyer requirements with shop capability.
7. Matching result identifies machine fit, work envelope fit, material fit, tolerance fit, tooling fit, QC fit and schedule fit.
8. Match gaps generate upstream / subcontractor dependencies.
9. Role-switching inquiry flow can ask upstream / subcontractors.
10. Supplier Response Rollup includes CAD-to-CNC matching evidence.
11. B-side feasibility engine can consume the evidence.
12. Industrial Execution Graph logs all matching and role-switching events.
13. Local E2E script runs deterministically with mock data.
14. No real CAD parser, MachinaCheck API, ERP, MES, QMS or encryption service is required for MVP.

---

## 20. Strategic Rationale

M-side Professional Free should provide enough professional value for SME manufacturers to adopt Giraffe Agent.

The key value is not file security. The key value is:

> A manufacturer can compare a buyer's CAD / STEP / BOM requirements with its own CNC / machining center capability, identify capability gaps, ask upstream or subcontractors, and return a more credible response to the buyer.

Enterprise CAP remains a later paid / enterprise-grade layer for confidential engineering files.

Professional Free proves workflow adoption and manufacturing capability matching first.
