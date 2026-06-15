# Path Enumeration in GLTG

## Overview

The path enumerator generates delivery path options by assigning participant combinations to the workflow nodes in the lead-time graph. Each unique assignment of garment factories (and other key participants) to production nodes produces a distinct `DeliveryPathOption`. Options are then pruned, enriched with batch-split and alternative-route variants, scored, and returned as the top ranked results.

---

## How the Path Enumerator Generates Options from Participant Combinations

The `PathEnumerator` works as follows:

1. **Identify assignable node types**: Not all nodes require participant assignment. The enumerator focuses on nodes with types that a participant's `capabilities` list covers.

2. **Build assignment combinations**: For each garment factory in the participant list, a candidate graph is constructed where that factory is assigned to its covered nodes (CUTTING, SEWING, PACKING, etc.). Non-factory participants (fabric suppliers, QC inspectors, logistics providers) are assigned based on capability coverage.

3. **Resolve each candidate graph**: The `DependencyResolver` runs a forward-pass scheduling algorithm, computing `earliest_start` and finish dates for every node based on the dependency edges and duration estimates.

4. **Extract terminal dates**: The terminal node in each candidate graph (typically BUYER_RECEIPT or BUYER_SIGN_OFF) determines the option's delivery dates:
   - `earliest_feasible_date` from the `earliest_finish` of the terminal node
   - `most_likely_date` from `most_likely_finish`
   - `commitable_date` from `commitable_finish`

5. **Respect the participant cap**: The engine caps the number of options at `min(3, unique_participant_count)`. If only one garment factory is provided, only one option is generated.

---

## The Pruning Rules

After enumeration, the `PathPruner` classifies each option against the `requested_delivery_date`:

| Classification | Condition | `OptionStatus` |
|---|---|---|
| **FEASIBLE** | `commitable_date <= requested_date` with buffer >= 7 days | `FEASIBLE` |
| **TIGHT** | `commitable_date <= requested_date` with buffer < 7 days | `TIGHT` |
| **REQUIRES_EXPEDITE** | `commitable_date > requested_date` but `most_likely_date <= requested_date` | `REQUIRES_EXPEDITE` |
| **REQUIRES_EXPEDITE** | `commitable_date > requested_date` but `earliest_date <= requested_date` | `REQUIRES_EXPEDITE` |
| **INFEASIBLE** | Even `earliest_feasible_date > requested_date` | `INFEASIBLE` |

When no `requested_delivery_date` is provided, all options default to `FEASIBLE`.

Infeasible options are retained in the intermediate list for reporting purposes but are excluded from the final ranked output returned to callers.

---

## Batch and Split Delivery Modes

The `BatchSplitAnalyzer` generates variants of the best feasible option by modelling alternative delivery structures:

| Mode | `DeliveryMode` | Description |
|---|---|---|
| Full delivery | `FULL_DELIVERY` | All units shipped together (default) |
| Partial delivery | `PARTIAL_DELIVERY` | A subset of units shipped early while remainder continues |
| Split shipment | `SPLIT_SHIPMENT` | Two or more discrete shipments on different vessels/dates |
| Parallel factory | `PARALLEL_FACTORY_PRODUCTION` | Two factories produce concurrently; combined output shipped together |
| Sequential factory | `SEQUENTIAL_FACTORY_PRODUCTION` | First factory produces a batch, second factory picks up remainder |

Split variants are only generated when there is more than one garment factory participant with capacity, or when the single factory has sufficient total capacity to justify batching.

---

## Alternative Route Generation

The `AlternativeRouteGenerator` creates synthetic variants of the best option to model non-standard supply scenarios:

1. **Air freight variant**: Replaces the SHIPMENT node duration (typically 21-28 days by sea) with an air freight duration (typically 3-5 days). This reduces the commitable date at significantly higher cost.

2. **Stock fabric variant**: Replaces FABRIC_ORDERING duration with a near-zero lead time representing use of fabric already in mill inventory. This can save 7-14 days on the critical path.

Both variants are classified and pruned the same way as primary options. Their scores are penalized by cost and risk multipliers during ranking.

---

## The Ranking Formula -- 8-Factor Scoring

The `OptionRanker` assigns a composite score to each option using eight weighted factors:

| Factor | Weight | Description |
|---|---|---|
| On-time probability | **0.30** | `option.on_time_probability` -- probability of meeting `requested_delivery_date` |
| Evidence completeness | **0.15** | Average confidence across the option's evidence items |
| Supplier reliability | **0.20** | Penalises options with HIGH or CRITICAL risk flags |
| Margin safety | **0.15** | Buffer days between `commitable_date` and `requested_date` (capped at 21 days full credit) |
| Delay risk | **?0.10** | Penalty per TIGHT_DEADLINE or LOGISTICS_RISK flag |
| QC risk | **?0.05** | Penalty per QC_RISK or HIGH_REWORK_RISK flag |
| Missing field penalty | **?0.03** | Penalty per missing order field |
| Operational complexity | **?0.02** | Applied to SPLIT_SHIPMENT and PARALLEL_FACTORY_PRODUCTION modes |

The total score is clamped to [0.0, 1.0]. Options are sorted descending by score. The top three are returned.

Semantic labels are then assigned to the top-ranked options:

- **FASTEST**: The option with the earliest `commitable_date`.
- **MOST_RELIABLE**: The option with the highest `on_time_probability` (among those not already labelled FASTEST).
- **BEST_COMMERCIAL_BALANCE**: The remaining ranked option.

---

## The 0/1/2/3 Participant Cap Rule

The maximum number of delivery options returned is capped by:

```
max_options = min(3, unique_participant_count)
```

If `unique_participant_count` is 0, `max_options` is 0 and the status is `NO_FEASIBLE_OPTION`.

This rule prevents the engine from returning more options than there are distinct participant combinations, which would be misleading. The cap applies after ranking: if the top-3 ranking produces 5 feasible options but only 2 participants were supplied, only 2 options are returned.

The feasibility rules then apply on top of the cap:

| Returned options | `FeasibilityStatus` |
|---|---|
| 0 | `NO_FEASIBLE_OPTION` |
| 1 | `LIMITED_OPTIONS` + `LIMITED_COMPETITION` flag |
| 2 | `LIMITED_OPTIONS` + `LIMITED_COMPARISON` flag |
| 3 | `FEASIBLE` |
