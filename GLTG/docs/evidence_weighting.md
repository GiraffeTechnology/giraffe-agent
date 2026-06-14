# Evidence Weighting in GLTG

## Overview

Every duration estimate in the GLTG engine is backed by one or more evidence items. Each item carries a source type, a raw days value, and a confidence score. The engine blends these into a single probabilistic estimate using a hierarchical weighting scheme.

---

## The 6 Evidence Tiers and Their Weights

Evidence sources are ranked by how authoritative and verifiable they are. A higher weight means the engine trusts that source more when blending estimates.

| Tier | `EvidenceSourceType` | Base Weight | Rationale |
|---|---|---|---|
| 1 | `ACTUAL_PROGRESS` | **1.00** | Ground truth — an event that has already happened or is verified in-flight |
| 2 | `SUPPLIER_CONFIRMATION` | **0.85** | A formal, dated supplier response with committed lead days |
| 3 | `HISTORICAL_MEMORY` | **0.70** | Observed actuals from a prior order with the same participant on the same node type |
| 4 | `SUPPLIER_QUOTE` | **0.55** | An informal estimate or verbal/email quote without formal commitment |
| 5 | `CATEGORY_BASELINE` | **0.40** | Industry baseline for this node type and approximate order volume |
| 6 | `AI_ESTIMATE` | **0.25** | Synthetic estimate generated when no other evidence is available |

The base weights reflect the decreasing reliability of evidence further down the hierarchy. `ACTUAL_PROGRESS` is fully trusted because it is observed fact. `AI_ESTIMATE` is the weakest signal and is only used as a last resort.

---

## How Weights Adjust Based on Evidence Availability

The `EvidenceWeighter.blend()` method does not modify the base weights themselves, but the effective contribution of each source is modulated by its `item_confidence` (a 0.0–1.0 value assigned at evidence creation time):

```
effective_weight_i = base_weight(source_type_i) * item_confidence_i
```

This means:

- A supplier confirmation with `confidence=0.9` contributes `0.85 * 0.9 = 0.765` to the weighted average.
- A historical memory record with `confidence=0.6` (e.g., only one prior order on record) contributes `0.70 * 0.6 = 0.42`.
- A category baseline with `confidence=1.0` contributes `0.40 * 1.0 = 0.40`.

When multiple evidence items are available, higher-tier sources dominate the blend because their effective weights are larger.

---

## How Confidence Is Computed from Multiple Evidence Items

The `EvidenceWeighter.overall_confidence()` method computes a composite confidence score for a node's duration estimate from all contributing evidence items:

```python
weights = [base_weight(source_i) * item_confidence_i  for each item]
base_confidence = sum(weights) / count(items)
multi_source_bonus = min(0.15, (count - 1) * 0.05)
overall_confidence = min(1.0, base_confidence + multi_source_bonus)
```

The multi-source bonus rewards having diverse evidence. Adding a second source (regardless of type) adds up to 0.05 to the confidence. Each additional source adds another 0.05, capped at 0.15 total bonus. This reflects the statistical principle that multiple independent evidence sources reduce uncertainty.

---

## Worked Examples

### Example 1: Supplier Claim Only — Low Confidence

A garment factory provides a verbal lead time of 14 days for SEWING, but there is no historical memory and no supplier confirmation (just an informal quote).

```
Evidence items:
  - source: SUPPLIER_QUOTE, days=14, item_confidence=0.70

effective_weight = 0.55 * 0.70 = 0.385
blended_days     = 14.0
overall_confidence = (0.55 * 0.70) / 1 + 0 bonus = 0.385
→ ConfidenceLevel: VERY_LOW
```

The engine will still generate an estimate but will tag the node as VERY_LOW confidence and surface a risk flag recommending a formal supplier response.

---

### Example 2: Actual Progress + Historical Memory — High Confidence

The factory has completed cutting (ACTUAL_PROGRESS confirms 2 days elapsed) and has two historical memory records for the same participant on SEWING (14 days stated, 16 days actual on a prior 8,000-piece order) plus a confirmed supplier response for the current order (15 days for SEWING).

```
Evidence items:
  - source: ACTUAL_PROGRESS,      days=2,   item_confidence=0.95  (cutting done on time)
  - source: HISTORICAL_MEMORY,    days=16,  item_confidence=0.80  (8k pcs actual)
  - source: SUPPLIER_CONFIRMATION, days=15, item_confidence=0.90  (formal response)

effective_weights:
  1.00 * 0.95 = 0.950
  0.70 * 0.80 = 0.560
  0.85 * 0.90 = 0.765
  total_weight = 2.275

blended_days = (2*0.950 + 16*0.560 + 15*0.765) / 2.275
             = (1.9 + 8.96 + 11.475) / 2.275
             = 22.335 / 2.275
             ≈ 9.82 days  (sewing-only portion after cutting completes)

multi_source_bonus = min(0.15, (3-1) * 0.05) = 0.10
base_confidence    = 2.275 / 3 = 0.758
overall_confidence = min(1.0, 0.758 + 0.10) = 0.858
→ ConfidenceLevel: HIGH
```

The presence of actual progress from the current order and confirmed supplier data drives the confidence to HIGH.

---

## The Weighted Formula for Duration Estimation

For each node, the `DurationEstimator` gathers all available evidence items and produces a `DurationEstimate` with three percentile bands:

- **p50 (median)**: Blended estimate using all evidence items.
- **p80 (comfortable buffer)**: p50 multiplied by a percentile factor (typically 1.3–1.5 depending on confidence level).
- **p90 (committable)**: p50 multiplied by a larger factor (typically 1.7–2.0), used as the basis for `commitable_date`.

The p80 and p90 multipliers shrink as `overall_confidence` increases:

| Confidence Range | p80 Multiplier | p90 Multiplier |
|---|---|---|
| 0.80–1.00 (HIGH) | 1.25 | 1.50 |
| 0.60–0.79 (MEDIUM) | 1.35 | 1.75 |
| 0.40–0.59 (LOW) | 1.50 | 2.00 |
| 0.00–0.39 (VERY_LOW) | 1.70 | 2.50 |

This means that when evidence is weak, the engine adds conservative buffers to protect the commitment date. High-quality evidence allows tighter bands and earlier commitable dates.
