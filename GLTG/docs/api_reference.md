# GLTG API Reference

---

## LeadTimeGraphEngine

The main orchestrator class. Import from `gltg.engine` or `gltg` directly.

```python
from gltg import LeadTimeGraphEngine
engine = LeadTimeGraphEngine()
```

### Methods

| Method | Signature | Description |
|---|---|---|
| `build_graph` | `(order_input: ApparelOrderInput) -> LeadTimeGraph` | Builds the lead-time DAG, resolves dependency dates, and identifies the critical path. Returns the resolved `LeadTimeGraph` without generating options. |
| `enumerate_options` | `(graph: LeadTimeGraph) -> list[DeliveryPathOption]` | Generates all candidate delivery path options from a resolved graph by enumerating participant combinations. Does not prune or rank. |
| `evaluate` | `(order_input: ApparelOrderInput) -> DeliveryFeasibilityPacket` | Full pipeline: validate → build graph → enumerate options → prune → generate variants → compute probabilities → rank → build packet. The primary entry point for all callers. |
| `reforecast` | `(existing_packet: DeliveryFeasibilityPacket, events: list[ProgressEvent]) -> DeliveryFeasibilityPacket` | Applies progress events to the existing packet's options, re-resolves the graph, and returns an updated packet with revised dates and risk flags. |

---

## ApparelOrderInput Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `order_id` | `str` | Yes | Unique order identifier |
| `product_type` | `str` | Yes | Product description (e.g. `"men_shirt_cotton_white"`) |
| `quantity` | `int` | Yes | Total units ordered |
| `requested_delivery_date` | `date \| None` | No | Buyer's requested delivery date |
| `trade_term` | `str \| None` | No | Incoterm (FOB, CIF, DDP, etc.) |
| `destination` | `str \| None` | No | Delivery destination port or city |
| `dynamic_form` | `dict[str, Any]` | No | Pass-through buyer form fields (fabric type, color, QC standard, etc.) |
| `participants` | `list[ParticipantProfile]` | No | Supply-chain participants involved in this order |
| `supplier_memory` | `list[SupplierMemoryRecord]` | No | Historical performance records for participants |
| `supplier_responses` | `list[SupplierResponse]` | No | Formal lead-time confirmations from participants |
| `progress_events` | `list[ProgressEvent]` | No | In-flight progress events already known at evaluation time |
| `calendar` | `CalendarConfig \| None` | No | Working-day calendar configuration |

---

## ParticipantProfile Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `participant_id` | `str` | Yes | Unique participant identifier |
| `name` | `str` | Yes | Display name |
| `participant_type` | `ParticipantType` | Yes | Role in the supply chain |
| `capabilities` | `list[Capability]` | No | Node types this participant can execute |
| `location` | `str \| None` | No | Geographic location |
| `capacity_per_day` | `int \| None` | No | Aggregate throughput in units per working day |
| `moq` | `int \| None` | No | Minimum order quantity |
| `available_from` | `date \| None` | No | Earliest date this participant is available |
| `reliability_score` | `float \| None` | No | Historical reliability 0.0–1.0 |
| `quality_score` | `float \| None` | No | Historical quality pass rate 0.0–1.0 |
| `on_time_delivery_rate` | `float \| None` | No | Historical on-time delivery rate 0.0–1.0 |
| `metadata` | `dict[str, Any]` | No | Custom key-value metadata |

---

## DeliveryFeasibilityPacket Fields

| Field | Type | Description |
|---|---|---|
| `order_id` | `str` | Echoes the input order identifier |
| `status` | `FeasibilityStatus` | Overall feasibility verdict |
| `generated_at` | `datetime` | UTC timestamp of evaluation |
| `earliest_feasible_date` | `date \| None` | Best-case delivery date (p50 path) |
| `most_likely_date` | `date \| None` | Expected delivery date (p80 path) |
| `commitable_date` | `date \| None` | Committed delivery date (p90 path) |
| `risk_adjusted_latest_date` | `date \| None` | Worst-case date including risk buffers |
| `on_time_probability` | `float \| None` | Probability 0.0–1.0 of meeting `requested_delivery_date` |
| `options` | `list[DeliveryPathOption]` | Ranked delivery path options (0–3) |
| `critical_path` | `list[str]` | Ordered node IDs on the critical path |
| `bottleneck_nodes` | `list[str]` | Node IDs identified as bottlenecks |
| `risk_flags` | `list[RiskFlag]` | Structured risk flags with severity |
| `missing_fields` | `list[str]` | Order fields absent that reduce accuracy |
| `evidence_summary` | `list[EvidenceItem]` | Top evidence items (max 30) |
| `recommended_action` | `str \| None` | Human-readable recommended next step |
| `human_review_required` | `bool` | True when automated decision is insufficient |

---

## DeliveryPathOption Fields

| Field | Type | Description |
|---|---|---|
| `option_id` | `str` | Unique option identifier |
| `status` | `OptionStatus` | FEASIBLE / TIGHT / REQUIRES_EXPEDITE / INFEASIBLE |
| `label` | `OptionLabel \| None` | FASTEST / MOST_RELIABLE / BEST_COMMERCIAL_BALANCE |
| `delivery_mode` | `DeliveryMode` | FULL_DELIVERY / SPLIT_SHIPMENT / etc. |
| `participant_combination` | `list[str]` | Participant IDs assigned to this option |
| `nodes` | `list[LeadTimeNode]` | All workflow nodes in this option |
| `edges` | `list[LeadTimeEdge]` | Dependency edges between nodes |
| `earliest_feasible_date` | `date \| None` | Best-case delivery (p50) |
| `most_likely_date` | `date \| None` | Expected delivery (p80) |
| `commitable_date` | `date \| None` | Committed delivery (p90) |
| `risk_adjusted_latest_date` | `date \| None` | Worst-case delivery |
| `on_time_probability` | `float \| None` | Probability of meeting target date |
| `critical_path` | `list[str]` | Critical path node IDs for this option |
| `bottleneck_nodes` | `list[str]` | Bottleneck node IDs for this option |
| `risk_flags` | `list[RiskFlag]` | Option-specific risk flags |
| `missing_fields` | `list[str]` | Missing fields propagated from order |
| `score` | `float \| None` | Composite ranking score 0.0–1.0 |
| `recommendation_reason` | `str \| None` | Human-readable reason for recommendation |
| `evidence_summary` | `list[EvidenceItem]` | Evidence items for this option |
| `infeasibility_reason` | `str \| None` | Explanation when status is INFEASIBLE |

---

## ProgressEvent Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `event_id` | `str` | Yes | Unique event identifier |
| `order_id` | `str` | Yes | Associated order |
| `node_id` | `str \| None` | No | Affected node ID (None = order-level event) |
| `event_type` | `ProgressEventType` | Yes | The type of progress event |
| `event_date` | `date` | Yes | Date the event occurred or was reported |
| `payload` | `dict[str, Any]` | No | Event-specific data fields |
| `evidence` | `list[EvidenceItem]` | No | Supporting evidence for this event |

---

## RiskFlag Fields

| Field | Type | Description |
|---|---|---|
| `code` | `RiskFlagCode` | Machine-readable risk category |
| `description` | `str` | Human-readable description of the risk |
| `severity` | `Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]` | Severity level |
| `affected_nodes` | `list[str]` | Node IDs affected by this risk |
| `mitigation_hint` | `str \| None` | Suggested mitigation action |

---

## Enumerations

### ApparelNodeType (28 values)

`BUYER_REQUIREMENT_CONFIRMATION` · `DESIGN_OR_TECH_PACK_CONFIRMATION` · `FABRIC_SELECTION` · `FABRIC_AVAILABILITY_CONFIRMATION` · `FABRIC_ORDERING` · `FABRIC_DYEING_OR_PRINTING` · `FABRIC_FINISHING` · `FABRIC_TESTING` · `TRIM_SELECTION` · `TRIM_AVAILABILITY_CONFIRMATION` · `TRIM_ORDERING` · `PACKAGING_MATERIAL_CONFIRMATION` · `SAMPLE_MAKING` · `SAMPLE_APPROVAL` · `PP_SAMPLE_APPROVAL` · `PRODUCTION_SLOT_BOOKING` · `CUTTING` · `SEWING` · `WASHING_OR_FINISHING` · `INLINE_QC` · `FINAL_QC` · `REWORK_IF_NEEDED` · `PACKING` · `LOGISTICS_BOOKING` · `CUSTOMS_OR_EXPORT_DOCS` · `SHIPMENT` · `BUYER_RECEIPT` · `BUYER_SIGN_OFF`

### ParticipantType (8 values)

| Value | Role |
|---|---|
| `FABRIC_SUPPLIER` | Fabric mill or fabric trading company |
| `TRIM_SUPPLIER` | Buttons, zippers, labels, accessories supplier |
| `GARMENT_FACTORY` | Cut-make-trim factory |
| `QC_INSPECTOR` | Third-party quality control service |
| `LOGISTICS_PROVIDER` | Freight forwarder or carrier |
| `PACKAGING_SUPPLIER` | Polybag, hanger, carton supplier |
| `BUYING_HOUSE` | Agent or buying house acting on behalf of buyer |
| `BUYER` | End buyer or brand |

### FeasibilityStatus (5 values)

| Value | Meaning |
|---|---|
| `FEASIBLE` | 3+ viable options available |
| `LIMITED_OPTIONS` | 1 or 2 options (limited competition or comparison) |
| `NO_FEASIBLE_OPTION` | No viable delivery path found |
| `REQUIRES_EXPEDITE` | Deadline only achievable with acceleration measures |
| `HUMAN_REVIEW_REQUIRED` | Insufficient data; manual assessment needed |

### OptionStatus (4 values)

`FEASIBLE` · `TIGHT` · `REQUIRES_EXPEDITE` · `INFEASIBLE`

### ProgressEventType (12 values)

`SUPPLIER_CONFIRMED` · `MATERIAL_DELAYED` · `TRIM_DELAYED` · `SAMPLE_APPROVAL_DELAYED` · `PRODUCTION_PROGRESS_UPDATE` · `QC_FAILED` · `REWORK_STARTED` · `REWORK_COMPLETED` · `LOGISTICS_DELAYED` · `BUYER_APPROVAL_DELAYED` · `NODE_COMPLETED` · `NODE_STARTED`

### DependencyType (8 values)

`FINISH_TO_START` · `START_TO_START` · `FINISH_TO_FINISH` · `MATERIAL_READY_BEFORE_START` · `APPROVAL_READY_BEFORE_START` · `CAPACITY_SLOT_REQUIRED` · `OPTIONAL` · `CONDITIONAL`

### EvidenceSourceType (6 values)

`ACTUAL_PROGRESS` · `SUPPLIER_CONFIRMATION` · `HISTORICAL_MEMORY` · `SUPPLIER_QUOTE` · `CATEGORY_BASELINE` · `AI_ESTIMATE`

### RiskFlagCode (15 values)

`LIMITED_COMPETITION` · `LIMITED_COMPARISON` · `NO_FEASIBLE_OPTION` · `MISSING_FABRIC_SUPPLIER` · `MISSING_PRODUCTION_CAPACITY` · `LOW_SUPPLIER_RELIABILITY` · `TIGHT_DEADLINE` · `MISSING_SAMPLE_APPROVAL` · `HIGH_REWORK_RISK` · `LOGISTICS_RISK` · `MISSING_REQUIRED_FIELD` · `CAPACITY_CONSTRAINT` · `SINGLE_SOURCE_RISK` · `QC_RISK` · `CUSTOMS_RISK`

### ConfidenceLevel (4 values)

`HIGH` · `MEDIUM` · `LOW` · `VERY_LOW`

### DeliveryMode (5 values)

`FULL_DELIVERY` · `PARTIAL_DELIVERY` · `SPLIT_SHIPMENT` · `PARALLEL_FACTORY_PRODUCTION` · `SEQUENTIAL_FACTORY_PRODUCTION`

### OptionLabel (3 values)

`FASTEST` · `MOST_RELIABLE` · `BEST_COMMERCIAL_BALANCE`

### NodeStatus (5 values)

`PENDING` · `IN_PROGRESS` · `COMPLETED` · `BLOCKED` · `SKIPPED`

### CostImpactLevel / RiskImpactLevel (4 values each)

`LOW` · `MEDIUM` · `HIGH` · `VERY_HIGH`

---

## CLI Commands

### gltg evaluate

```
usage: gltg evaluate [-h] [-o OUTPUT] [--summary] order

Evaluate an apparel order and produce a feasibility packet.

positional arguments:
  order                 Path to order JSON file (ApparelOrderInput)

optional arguments:
  -o OUTPUT, --output OUTPUT
                        Save the resulting packet to this JSON file
  --summary             Print a human-readable summary instead of full JSON
```

### gltg reforecast

```
usage: gltg reforecast [-h] [-o OUTPUT] [--summary] packet events

Reforecast an existing packet with new progress events.

positional arguments:
  packet                Path to an existing packet JSON file
  events                Path to progress events JSON file (array or {"events": [...]})

optional arguments:
  -o OUTPUT, --output OUTPUT
                        Save the updated packet to this JSON file
  --summary             Print a human-readable summary instead of full JSON
```
