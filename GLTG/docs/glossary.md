# GLTG Glossary

A reference for GLTG-specific terminology used throughout the codebase and documentation.

---

## Lead-Time Graph (LTG)

A directed acyclic graph (DAG) in which each **node** represents a discrete step in the apparel production and logistics workflow, and each **edge** represents a dependency between steps. The LTG models the entire journey of an order from buyer requirement confirmation through to buyer sign-off. Duration estimates on each node are probabilistic (p50/p80/p90), making the LTG a stochastic scheduling model rather than a simple Gantt chart.

---

## Commitable Date

The delivery date the GLTG engine will formally commit to for a given delivery path option. It is derived from the **p90 duration band** -- the 90th-percentile estimate -- of the terminal node in the lead-time graph. This means there is approximately a 90% probability that the order will be delivered by this date given the current evidence. The `commitable_date` is the primary decision date surfaced to buyers and agents.

---

## Critical Path

The sequence of workflow nodes in the lead-time graph that determines the minimum total duration of the order. Any delay on a critical path node directly delays the overall commitable date. Nodes on the critical path have zero or near-zero float (slack). The GLTG engine identifies the critical path using a backward-pass computation over the resolved graph and returns the ordered list of `node_id` values as `packet.critical_path`.

---

## Bottleneck Node

A node on the critical path that has the smallest float among all critical nodes -- i.e., a node where even a small delay will most severely impact the overall timeline. GLTG identifies bottleneck nodes using the `CriticalPathFinder.find_bottlenecks()` method. Common bottlenecks in apparel orders are SEWING (high duration, quantity-dependent) and FABRIC_ORDERING (long lead time with mill dependency).

---

## Evidence Weight

A numerical multiplier (0.0-1.0) assigned to each evidence source type that reflects how authoritative and verifiable that source is. Evidence weights are used by `EvidenceWeighter.blend()` to compute a weighted-average duration estimate. The six tiers are: `ACTUAL_PROGRESS` (1.00), `SUPPLIER_CONFIRMATION` (0.85), `HISTORICAL_MEMORY` (0.70), `SUPPLIER_QUOTE` (0.55), `CATEGORY_BASELINE` (0.40), and `AI_ESTIMATE` (0.25). Higher-tier evidence dominates the blended result.

---

## Delivery Feasibility Packet

The primary output of the GLTG engine (`DeliveryFeasibilityPacket`). It contains all information needed for an agent or buyer to make an informed delivery decision: the overall feasibility status, up to three ranked delivery path options, the commitable date, on-time probability, critical path, bottleneck nodes, risk flags, missing data fields, and a recommended action. The packet is a Pydantic v2 model and is fully serializable to JSON.

---

## Path Option

A `DeliveryPathOption` representing one specific combination of participants executing the workflow. Each option has its own set of nodes, edges, dates, risks, and a ranking score. The engine returns up to three options (capped by the number of distinct participants), labelled FASTEST, MOST_RELIABLE, and BEST_COMMERCIAL_BALANCE. Options with status INFEASIBLE are excluded from the final output.

---

## Reforecast

The process of updating an existing `DeliveryFeasibilityPacket` with new in-flight information captured as `ProgressEvent` objects. Rather than re-evaluating the order from scratch, the `ReforecastEngine` applies each event to the relevant graph nodes, re-resolves dependency dates, re-identifies the critical path, and returns an updated packet with revised commitable dates and any new risk flags. The delta between the original and new commitable date is reported as `delta_days`.

---

## Expedite Lever

An actionable intervention that can recover schedule slippage identified during reforecasting. GLTG models six expedite levers: air freight (saves 18 days), stock fabric (saves 14 days), expedited trim ordering (saves 7 days), overtime production (saves 5 days), sample approval fast-track (saves 4 days), and parallel cutting and sewing (saves 3 days). Each lever has a cost impact, risk impact, and optional precondition. Levers are returned in `acceleration_options` when slippage is detected.

---

## Supplier Memory

A collection of historical performance records (`SupplierMemoryRecord`) capturing what a specific participant actually delivered on prior orders, versus what they stated. Each record covers a specific `participant_id`, `node_type`, order quantity, stated days, and actual days. The `DurationEstimator` uses supplier memory to compute `memory_adjusted_days` -- a more realistic duration estimate that accounts for observed delays or accelerations.

---

## Apparel Node Type

One of the 28 discrete workflow steps in the standard apparel production and logistics sequence, represented by the `ApparelNodeType` enum. Examples include `FABRIC_ORDERING`, `SEWING`, `FINAL_QC`, and `SHIPMENT`. Each node type has a participant type affinity, baseline lead-time statistics, required inputs, and outputs. Optional nodes (e.g. `FABRIC_DYEING_OR_PRINTING`, `WASHING_OR_FINISHING`) are only included in the graph when the order configuration requires them.

---

## Dependency Type

One of the 8 values in the `DependencyType` enum that describes how two workflow nodes are related. The most common is `FINISH_TO_START` (successor cannot start until predecessor completes). Other types include `MATERIAL_READY_BEFORE_START` (physical material must be present), `APPROVAL_READY_BEFORE_START` (documented approval required), and `CAPACITY_SLOT_REQUIRED` (production slot must be booked before work begins).

---

## On-Time Probability

A probability value between 0.0 and 1.0 representing the likelihood that the order will be delivered by the `requested_delivery_date`. Computed by `OnTimeProbabilityCalculator` from the relationship between `commitable_date`, `risk_adjusted_latest_date`, and the requested date. A probability of 1.0 means the commitable date is well ahead of the deadline; 0.0 means even the best-case date misses the deadline.

---

## Working Days

Calendar days excluding weekends and configured holidays. All duration estimates and date arithmetic in GLTG operate in working days by default when `CalendarConfig.use_working_days = True`. The number of working days per week is configurable (default 5, some factories operate 6-day weeks). Holiday dates are specified as a list of ISO date strings in `CalendarConfig.holiday_dates`.

---

## Risk Flag

A structured `RiskFlag` object surfaced by the engine to alert decision-makers to potential supply-chain risks. Each flag has a `code` (from `RiskFlagCode` enum), a `description`, a `severity` (LOW / MEDIUM / HIGH / CRITICAL), a list of affected node IDs, and an optional `mitigation_hint`. Risk flags are deduplicated by code within a packet. Common flags include `LIMITED_COMPETITION`, `TIGHT_DEADLINE`, `LOGISTICS_RISK`, and `QC_RISK`.

---

## Confidence Level

A qualitative label (`ConfidenceLevel` enum: HIGH / MEDIUM / LOW / VERY_LOW) assigned to each `LeadTimeNode` based on the composite confidence score of its duration estimate. High confidence requires strong evidence (actual progress or confirmed supplier responses). Low or VERY_LOW confidence triggers wider p80/p90 percentile bands, resulting in more conservative commitable dates. The confidence level is visible on each node in the delivered `DeliveryPathOption`.
