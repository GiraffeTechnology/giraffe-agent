# GLTG Model Specification

## Overview

The Giraffe Lead-Time Graph (GLTG) engine computes a probabilistic, evidence-weighted delivery feasibility assessment for apparel orders. Unlike a simple date calculator, GLTG constructs a directed acyclic graph (DAG) of workflow steps -- the Lead-Time Graph -- where each node represents a discrete production or logistics activity and each edge encodes a dependency relationship. Duration estimates are computed from a six-tier evidence hierarchy, and the engine enumerates up to three ranked delivery path options from participant combinations.

---

## What GLTG Computes

Given an `ApparelOrderInput`, the engine produces a `DeliveryFeasibilityPacket` that answers:

1. **Can this order be delivered on time?** -- expressed as a `FeasibilityStatus`.
2. **By what date can we commit?** -- the `commitable_date` at the 90th-percentile confidence band.
3. **How many viable options exist?** -- zero to three ranked `DeliveryPathOption` objects.
4. **What is the critical path?** -- the sequence of nodes that determines the overall timeline.
5. **What risks exist?** -- a structured list of `RiskFlag` objects with severities and mitigations.

---

## DeliveryFeasibilityPacket -- 12 Output Fields

| Field | Type | Description |
|---|---|---|
| `order_id` | `str` | Echoes the input order identifier |
| `status` | `FeasibilityStatus` | Overall feasibility verdict (see status rules below) |
| `generated_at` | `datetime` | UTC timestamp of evaluation |
| `earliest_feasible_date` | `date \| None` | Best-case delivery date (p50 path, no slack) |
| `most_likely_date` | `date \| None` | Expected delivery date (p80 path) |
| `commitable_date` | `date \| None` | Date the engine will commit to (p90 path) |
| `risk_adjusted_latest_date` | `date \| None` | Worst-case date including identified risk buffers |
| `on_time_probability` | `float \| None` | Probability 0.0-1.0 of meeting `requested_delivery_date` |
| `options` | `list[DeliveryPathOption]` | Ranked delivery path options (0-3 items) |
| `critical_path` | `list[str]` | Ordered `node_id` list forming the critical path |
| `bottleneck_nodes` | `list[str]` | Nodes with the highest time-to-float ratio |
| `risk_flags` | `list[RiskFlag]` | Structured risk flags with severity and mitigation hints |
| `missing_fields` | `list[str]` | Order fields absent that would improve accuracy |
| `evidence_summary` | `list[EvidenceItem]` | Top evidence items used for date estimation |
| `recommended_action` | `str \| None` | Human-readable recommended next step |
| `human_review_required` | `bool` | True when automated decision is insufficient |

> Note: The Pydantic model defines 16 total fields including the above 12 plus `missing_fields`, `evidence_summary`, `recommended_action`, and `human_review_required` -- all are part of the output contract.

---

## Graph Node Model -- LeadTimeNode

Each node represents one workflow step. Fields:

| Field | Type | Description |
|---|---|---|
| `node_id` | `str` | Unique identifier within the graph (e.g. `"FACT-001_SEWING"`) |
| `node_type` | `ApparelNodeType` | One of the 28 apparel workflow node types |
| `label` | `str \| None` | Human-readable display name |
| `participant_id` | `str \| None` | Which participant executes this step |
| `required_inputs` | `list[str]` | Logical resource names that must be ready before this node starts |
| `outputs` | `list[str]` | Logical resource names produced by this node |
| `duration_estimate` | `DurationEstimate \| None` | Probabilistic duration with evidence |
| `earliest_start` | `date \| None` | Earliest calendar date the node can begin |
| `earliest_finish` | `date \| None` | Earliest calendar date (p50 duration from earliest start) |
| `most_likely_finish` | `date \| None` | Expected finish (p80 duration) |
| `commitable_finish` | `date \| None` | Committed finish date (p90 duration) |
| `risk_adjusted_finish` | `date \| None` | Finish date including identified risk buffers |
| `confidence_level` | `ConfidenceLevel` | HIGH / MEDIUM / LOW / VERY_LOW |
| `risk_flags` | `list[RiskFlag]` | Node-level risks |
| `evidence` | `list[EvidenceItem]` | Evidence items supporting this node's estimate |
| `status` | `NodeStatus` | PENDING / IN_PROGRESS / COMPLETED / BLOCKED / SKIPPED |
| `is_critical` | `bool` | True if this node lies on the critical path |
| `metadata` | `dict` | Engine-internal state (not for external consumption) |

---

## Graph Edge Model -- LeadTimeEdge

Edges encode dependencies between nodes. Fields:

| Field | Type | Description |
|---|---|---|
| `edge_id` | `str` | Unique edge identifier |
| `from_node_id` | `str` | Source node |
| `to_node_id` | `str` | Target node |
| `dependency_type` | `DependencyType` | The nature of the dependency (see below) |
| `lag_days` | `int` | Additional calendar days added between predecessor finish and successor start |
| `is_hard_dependency` | `bool` | If True, the successor cannot start until the predecessor completes |
| `condition` | `str \| None` | Optional logical condition under which this edge is active |

### Dependency Types

| Value | Meaning |
|---|---|
| `FINISH_TO_START` | Successor starts only after predecessor finishes (default) |
| `START_TO_START` | Successor may start when predecessor starts |
| `FINISH_TO_FINISH` | Successor finishes when predecessor finishes |
| `MATERIAL_READY_BEFORE_START` | Successor requires physical material to be at location |
| `APPROVAL_READY_BEFORE_START` | Successor requires a documented approval event |
| `CAPACITY_SLOT_REQUIRED` | Successor requires a confirmed production slot |
| `OPTIONAL` | Edge exists for tracking but does not constrain scheduling |
| `CONDITIONAL` | Edge is active only when `condition` evaluates true |

---

## Duration Estimate Model -- DurationEstimate

Probabilistic duration for a single node:

| Field | Type | Description |
|---|---|---|
| `p50_days` | `float` | Median estimate in working days |
| `p80_days` | `float` | 80th-percentile estimate (comfortable delivery buffer) |
| `p90_days` | `float` | 90th-percentile estimate (the committed date basis) |
| `min_days` | `float \| None` | Absolute minimum (best case) |
| `max_days` | `float \| None` | Absolute maximum (worst case) |
| `supplier_claim_days` | `float \| None` | Value stated by supplier in quote or response |
| `computed_days` | `float \| None` | Capacity-based calculation: `quantity / capacity_per_day` |
| `memory_adjusted_days` | `float \| None` | Estimate adjusted using historical memory records |
| `confidence` | `float` | Blended confidence score 0.0-1.0 |
| `evidence_summary` | `list[EvidenceItem]` | Evidence items contributing to this estimate |

---

## Evidence Hierarchy -- 6 Tiers

Evidence sources are ranked by authority. Higher weight = more trusted:

| Tier | `EvidenceSourceType` | Weight | Description |
|---|---|---|---|
| 1 | `ACTUAL_PROGRESS` | 1.00 | A progress event confirming actual completion or current state |
| 2 | `SUPPLIER_CONFIRMATION` | 0.85 | A formal `SupplierResponse` with confirmed lead days |
| 3 | `HISTORICAL_MEMORY` | 0.70 | A `SupplierMemoryRecord` from a prior order with the same participant |
| 4 | `SUPPLIER_QUOTE` | 0.55 | An informal supplier estimate or unconfirmed quote |
| 5 | `CATEGORY_BASELINE` | 0.40 | Industry-standard baseline for this node type and order volume |
| 6 | `AI_ESTIMATE` | 0.25 | AI-generated estimate when no other evidence is available |

The blended duration value is computed as:

```
blended_days = sum(days_i * weight_i * confidence_i) / sum(weight_i * confidence_i)
```

where `weight_i` is the evidence tier weight and `confidence_i` is the individual item confidence.

---

## Feasibility Status Rules

The engine determines `FeasibilityStatus` based on the number of feasible options after pruning:

| Options Count | Status | Extra Risk Flag |
|---|---|---|
| 0 | `NO_FEASIBLE_OPTION` | `NO_FEASIBLE_OPTION` (CRITICAL severity) |
| 1 | `LIMITED_OPTIONS` | `LIMITED_COMPETITION` (MEDIUM severity) |
| 2 | `LIMITED_OPTIONS` | `LIMITED_COMPARISON` (LOW severity) |
| 3+ | `FEASIBLE` | None |

If any of the top options has `REQUIRES_EXPEDITE` status and the overall status would otherwise be `FEASIBLE`, the packet status is elevated to `REQUIRES_EXPEDITE`.

---

## Apparel Workflow Sequence -- 28 Node Types

The canonical apparel order workflow proceeds through the following 28 `ApparelNodeType` values in dependency order. Optional nodes are skipped if the order configuration does not require them.

1. `BUYER_REQUIREMENT_CONFIRMATION` -- confirms buyer specs
2. `DESIGN_OR_TECH_PACK_CONFIRMATION` -- tech pack sign-off
3. `FABRIC_SELECTION` -- fabric choice and specification
4. `FABRIC_AVAILABILITY_CONFIRMATION` -- mill availability check
5. `FABRIC_ORDERING` -- fabric purchase order placed
6. `FABRIC_DYEING_OR_PRINTING` -- _(optional)_ color/print processing
7. `FABRIC_FINISHING` -- _(optional)_ calendering, coating, etc.
8. `FABRIC_TESTING` -- _(optional)_ lab test for compliance
9. `TRIM_SELECTION` -- buttons, zippers, labels selection
10. `TRIM_AVAILABILITY_CONFIRMATION` -- trim stock or lead-time check
11. `TRIM_ORDERING` -- trim purchase order placed
12. `PACKAGING_MATERIAL_CONFIRMATION` -- polybags, cartons confirmed
13. `SAMPLE_MAKING` -- proto or counter sample production
14. `SAMPLE_APPROVAL` -- buyer approves sample
15. `PP_SAMPLE_APPROVAL` -- _(optional)_ pre-production sample approval
16. `PRODUCTION_SLOT_BOOKING` -- factory confirms production window
17. `CUTTING` -- fabric cutting to pattern
18. `SEWING` -- assembly of cut panels (quantity-scaled duration)
19. `WASHING_OR_FINISHING` -- _(optional)_ garment wash or finish treatment
20. `INLINE_QC` -- _(optional)_ mid-production quality check
21. `FINAL_QC` -- end-of-line inspection (AQL-based)
22. `REWORK_IF_NEEDED` -- _(optional)_ remediation of QC failures
23. `PACKING` -- folding, tagging, bagging, cartoning
24. `LOGISTICS_BOOKING` -- freight booking and space reservation
25. `CUSTOMS_OR_EXPORT_DOCS` -- export license, packing list, B/L
26. `SHIPMENT` -- physical transit to destination
27. `BUYER_RECEIPT` -- goods received at buyer warehouse
28. `BUYER_SIGN_OFF` -- _(optional)_ final buyer acceptance
