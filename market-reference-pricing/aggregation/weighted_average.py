"""
Time-decay weighted average calculation.

This module is 100% deterministic: no ML model, no randomness, no external calls.
All inputs are concrete numbers; the output is a closed-form mathematical result.

Formula version: v1.0.0
  weight(quote) = exp(-DECAY_LAMBDA * max(days_since_quote, 0))
  weighted_avg  = sum(price * weight) / sum(weight)

DECAY_LAMBDA must be confirmed by Michael/Steve before production deployment.
Any change to DECAY_LAMBDA requires bumping FORMULA_VERSION and re-running
aggregation (do not overwrite historical sku_reference_price rows).
"""

import math
from datetime import datetime
from typing import Optional

# ~70-day half-life: exp(-LAMBDA * 70) ≈ 0.5
# To be calibrated against actual quote update frequency in acceptance testing.
DECAY_LAMBDA: float = 0.0099

FORMULA_VERSION: str = "v1.0.0"


def calculate_weighted_average(
    quotes: list[dict],
    reference_time: datetime,
) -> Optional[dict]:
    """
    Compute time-decay weighted statistics for a list of price quotes.

    Args:
        quotes: list of dicts, each with keys:
                  unit_price (float)  — the quoted price
                  quote_timestamp (datetime, timezone-aware)
        reference_time: the datetime to measure age against (typically now)

    Returns None for an empty list.

    Return dict keys:
        weighted_avg_price, sample_count,
        p25_price, median_price, p75_price,
        min_price, max_price,
        low_confidence (True when sample_count < 5)

    Constraints:
        - All computation is arithmetic; no ML inference step.
        - Future quotes (negative days_since) are clamped to 0 days
          (i.e. treated as if quoted right now).
        - sample_count < 5 → low_confidence=True; frontend MUST show
          "样本不足，仅供参考" warning.
    """
    if not quotes:
        return None

    weights: list[float] = []
    prices: list[float] = []

    for q in quotes:
        days_since = (reference_time - q["quote_timestamp"]).days
        w = math.exp(-DECAY_LAMBDA * max(days_since, 0))
        weights.append(w)
        prices.append(float(q["unit_price"]))

    weight_total = sum(weights)
    weighted_avg = (
        sum(p * w for p, w in zip(prices, weights)) / weight_total
        if weight_total > 0
        else None
    )

    sorted_prices = sorted(prices)
    n = len(sorted_prices)

    return {
        "weighted_avg_price": weighted_avg,
        "sample_count": n,
        "p25_price": sorted_prices[int(n * 0.25)],
        "median_price": sorted_prices[int(n * 0.50)],
        "p75_price": sorted_prices[int(n * 0.75)],
        "min_price": sorted_prices[0],
        "max_price": sorted_prices[-1],
        "low_confidence": n < 5,
    }


def aggregate_sku(
    sku_model_normalized: str,
    quotes: list[dict],
    reference_time: datetime,
) -> Optional[dict]:
    """
    Full aggregation row ready to upsert into sku_reference_price.
    Returns None if there are no quotes.
    """
    stats = calculate_weighted_average(quotes, reference_time)
    if stats is None:
        return None

    return {
        **stats,
        "sku_model_normalized": sku_model_normalized,
        "calculation_timestamp": reference_time,
        "calculation_formula_version": FORMULA_VERSION,
    }
