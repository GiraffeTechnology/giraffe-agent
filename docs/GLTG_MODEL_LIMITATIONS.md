# GLTG Lead Time Model: Limitations and Assumptions

## What the GLTG model is

The **Industrial Execution Graph (GLTG)** is an append-only execution record that tracks what actually happened across an order lifecycle. The **lead time model** (`src/lead_time/`) is a separate, deterministic calculation layer that estimates total delivery time from a path of stages (material → subcontractors → packaging → logistics → buyer).

Both are local, deterministic, and do not call any external services.

## Deterministic local model

The lead time calculator operates as a pure function over structured inputs. Given the same path configuration and supplier data, it always produces the same output. There is no probabilistic sampling, no external data fetch, and no machine learning model involved.

## P50 / P80 / P90 meaning

The model outputs **percentile estimates** for total path duration:

- **P50**: Median expected lead time — half of historical deliveries on this path type complete by this date.
- **P80**: 80th-percentile lead time — a more conservative estimate used when the buyer has some schedule buffer.
- **P90**: 90th-percentile lead time — a conservative estimate used for hard deadlines or high-risk paths.

These percentiles are computed from configurable distribution assumptions (currently triangular distributions over min/mode/max day ranges per stage). They are **not** derived from real historical delivery data unless the operator has loaded such data into the system.

## Supplier-stated lead time is evidence, not truth

When a supplier states a lead time (e.g., "38 days FOB Shenzhen"), the model treats this as a **stated commitment**, not a verified fact. The model:

- Records the stated lead time as a data point
- Compares it to the system's internal stage estimates
- Flags discrepancies as risk signals

A supplier-stated lead time that is significantly shorter than the internal estimate triggers a `RISK: stated_vs_estimated_gap` flag. This flag requires human review before the path is presented to the buyer for selection.

## Default assumptions

The following defaults are used when supplier data is incomplete. All values are in calendar days.

| Stage | Default (days) | Notes |
|---|---|---|
| QC days | 2 | In-line inspection only; third-party audit adds 3–5 days |
| Packaging days | 1 | Standard carton; custom packaging adds 2–4 days |
| Logistics days | 12 | Sea freight, standard port-to-door; air freight reduces to 3–5 |
| Default capacity | 10,000 units/month | Used when supplier has not stated MOQ or production rate |
| Setup / changeover days | 1 | Line setup; complex colour/construction changeovers add 1–3 days |

These defaults are conservative estimates for apparel and light manufacturing. They are **not validated against** a specific supplier's actual production record unless the supplier has provided verified data via the M-side structured response flow.

## How risk flags are created

Risk flags are attached to a path when:

1. **Stated vs estimated gap**: Supplier's stated lead time is more than 20% shorter than the model's P50 estimate.
2. **Missing critical stage**: A required stage (e.g., QC) has no supplier assigned.
3. **Capacity shortfall**: Required quantity divided by daily capacity exceeds available calendar days before the buyer's deadline.
4. **Single-source dependency**: A critical material or subcontracting stage has only one supplier assigned with no backup.
5. **Unknown logistics provider**: The logistics leg uses a provider not in the registered provider registry.

Risk flags are informational. They are surfaced in the feasibility report for human review. They do not automatically block path selection.

## Why missing values do not use sentinel 999

Earlier versions of this model used `999` as a sentinel value for "unknown lead time." This was removed because:

- Sentinel values propagate silently through arithmetic (a path with one unknown stage would show a wildly inflated total).
- Tests that assert on sentinel values become false negatives when sentinel-carrying paths accidentally pass threshold checks.

Missing values are now represented as `None` and propagate as `None` through the calculation. A path with any `None` stage lead time is flagged with `RISK: incomplete_stage_data` and must receive human review before being presented to the buyer.

## What needs human confirmation before buyer-facing quotation

The following conditions require human review and confirmation before a lead time estimate or delivery path can be presented to a buyer in a formal quotation:

1. **Any `RISK:` flag** on the path — all risk flags must be reviewed and either resolved or explicitly accepted.
2. **Supplier-stated data not yet verified** — if the supplier's lead time and capacity data come from a first-inquiry response (not a follow-up verification), the estimate is provisional.
3. **Logistics provider not confirmed** — if a logistics provider is selected from defaults rather than from a confirmed booking or rate card.
4. **Deadline is within 10% of P90** — if the buyer's target date falls within the P90 window, the path is considered high-risk and requires explicit sign-off.
5. **No QC supplier assigned** — a path with no QC stage cannot be quoted without explicit buyer acknowledgement of the QC gap.

The Giraffe Agent enforces a mandatory **human approval gate** before any outbound message to a supplier or buyer is sent. This gate covers the trade messages, not the lead time estimates directly. Operators are responsible for ensuring their human approval workflow covers feasibility reports and quotation documents before they reach the buyer.
