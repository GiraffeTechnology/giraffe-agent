# Reforecasting in GLTG

## Overview

Reforecasting is the process of updating an existing `DeliveryFeasibilityPacket` with new in-flight information captured as `ProgressEvent` objects. Rather than re-running the full evaluation from scratch, the `ReforecastEngine` applies each event to the relevant nodes in the existing options, re-resolves the dependency graph, and returns an updated packet with revised dates and risk flags.

The primary API entry point is:

```python
updated_packet = engine.reforecast(existing_packet, events)
```

---

## The 9 Supported Progress Event Types

All event types are values of the `ProgressEventType` enum. The `payload` field carries event-specific data.

| # | `ProgressEventType` | Meaning | Key Payload Fields |
|---|---|---|---|
| 1 | `SUPPLIER_CONFIRMED` | A participant has formally confirmed their lead time or start date | `participant_id`, `confirmed_start` |
| 2 | `MATERIAL_DELAYED` | Fabric or other raw material has been delayed | `delay_days`, `reason` |
| 3 | `TRIM_DELAYED` | Trim or accessory delivery has been delayed | `delay_days`, `reason` |
| 4 | `SAMPLE_APPROVAL_DELAYED` | Buyer sample approval has been delayed | `delay_days`, `expected_date` |
| 5 | `PRODUCTION_PROGRESS_UPDATE` | Factory provides a units-completed update | `units_completed`, `units_total`, `percent_done` |
| 6 | `QC_FAILED` | Final or inline QC inspection has failed | `failure_rate`, `failed_units`, `reason` |
| 7 | `REWORK_STARTED` | Rework has been initiated following QC failure | `rework_units`, `expected_days` |
| 8 | `REWORK_COMPLETED` | Rework has been completed | `rework_units`, `actual_days` |
| 9 | `LOGISTICS_DELAYED` | Shipment or freight booking has been delayed | `delay_days`, `new_etd` |
| 10 | `BUYER_APPROVAL_DELAYED` | Buyer has not yet confirmed approval for a milestone | `delay_days`, `milestone` |
| 11 | `NODE_COMPLETED` | A specific workflow node has been confirmed complete | `completed_date` |
| 12 | `NODE_STARTED` | A specific workflow node has started | `started_date` |

> Note: `BUYER_APPROVAL_DELAYED`, `NODE_COMPLETED`, and `NODE_STARTED` are also available in the `ProgressEventType` enum, bringing the total supported types to 12.

---

## How Each Event Type Modifies the Graph

The `EventApplier` processes each event against the temporary graph built from the option's nodes and edges:

| Event Type | Graph Modification |
|---|---|
| `SUPPLIER_CONFIRMED` | Sets `earliest_start` on the relevant participant's node(s) to `confirmed_start` |
| `MATERIAL_DELAYED` | Adds `delay_days` to the `lag_days` of edges feeding into CUTTING or FABRIC_ORDERING nodes |
| `TRIM_DELAYED` | Adds `delay_days` to edges feeding into SEWING (trim dependency) |
| `SAMPLE_APPROVAL_DELAYED` | Extends `duration_estimate.p90_days` on the SAMPLE_APPROVAL node |
| `PRODUCTION_PROGRESS_UPDATE` | Recalculates remaining SEWING duration based on units not yet completed |
| `QC_FAILED` | Activates the REWORK_IF_NEEDED node; adds rework duration estimate |
| `REWORK_STARTED` | Sets REWORK_IF_NEEDED node to `IN_PROGRESS`; adjusts its duration from payload |
| `REWORK_COMPLETED` | Sets REWORK_IF_NEEDED node to `COMPLETED`; uses `actual_days` from payload |
| `LOGISTICS_DELAYED` | Extends LOGISTICS_BOOKING or SHIPMENT node duration by `delay_days` |
| `BUYER_APPROVAL_DELAYED` | Extends the relevant approval node duration by `delay_days` |
| `NODE_COMPLETED` | Sets node `status = COMPLETED`; fixes `commitable_finish` to `completed_date` |
| `NODE_STARTED` | Sets node `status = IN_PROGRESS`; fixes `earliest_start` to `started_date` |

After all events are applied, the `DependencyResolver` re-runs a forward-pass scheduling computation and the `CriticalPathFinder` re-identifies the critical path.

---

## The Reforecast Output

The reforecast returns an updated `DeliveryFeasibilityPacket`. Key changes from the original:

| Field | Description of Change |
|---|---|
| `commitable_date` | Updated to reflect new terminal node dates after event application |
| `most_likely_date` | Updated from p80 path of revised graph |
| `earliest_feasible_date` | Updated from p50 path of revised graph |
| `critical_path` | Re-identified critical path node IDs (may differ from original) |
| `bottleneck_nodes` | Re-identified bottleneck nodes |
| `risk_flags` | New risk flags appended (e.g. `TIGHT_DEADLINE` if slip > 7 days) |
| `generated_at` | Reset to current UTC timestamp |

**Delta computation**: The number of days slipped (or recovered) is computed as:

```python
delta_days = (new_commitable_date - previous_commitable_date).days
# positive = later (slippage), negative = earlier (acceleration)
```

If `delta_days > 7`, a new `TIGHT_DEADLINE` risk flag is appended to `packet.risk_flags` with `severity="HIGH"`.

---

## Expedite Levers

When the reforecast reveals schedule slippage (`delta_days > 0`), the `ExpediteOptionGenerator` produces a ranked list of actionable recovery options. Six lever types are available:

| # | Lever Name | Days Saved | Cost Impact | Risk Impact | Precondition |
|---|---|---|---|---|---|
| 1 | Air freight (sea → air) | **18** | VERY_HIGH | LOW | Buyer approves air freight |
| 2 | Stock fabric (pre-book from mill inventory) | **14** | MEDIUM | MEDIUM | Stock fabric available at mill |
| 3 | Expedited trim ordering | **7** | MEDIUM | LOW | Local trim supplier available |
| 4 | Overtime production | **5** | MEDIUM | LOW | Factory agrees to overtime/weekend shifts |
| 5 | Sample approval fast-track | **4** | LOW | MEDIUM | Buyer accepts digital/video approval |
| 6 | Parallel cutting and sewing | **3** | LOW | LOW | No precondition required |

Levers are sorted by `days_saved` descending. The `ReforecastEngine` includes these in `acceleration_options` when building a `ReforecastResult`. Callers can filter by `cost_impact` budget constraint using the `available_budget` parameter of `ExpediteOptionGenerator.generate()`.

Combining multiple levers is possible. For example, air freight (18 days) combined with overtime production (5 days) can recover up to 23 days of slippage, subject to preconditions being met.
