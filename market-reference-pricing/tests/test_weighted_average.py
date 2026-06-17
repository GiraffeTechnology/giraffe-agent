"""
Unit tests for aggregation/weighted_average.py.

Contains >= 20 boundary cases covering:
- Empty/None input
- Single quote (today, 70 days ago)
- low_confidence threshold at 4 vs 5 samples
- Weighted average formula correctness (manual verification)
- Future timestamps (clamped to 0)
- Percentile calculations (4, 8, 10 items)
- min/max extraction
- Very small / very large prices
- All same price, all same timestamp
"""

import math
from datetime import datetime, timedelta, timezone

import pytest

from aggregation.weighted_average import DECAY_LAMBDA, calculate_weighted_average

REF = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)


def q(price: float, days_ago: int) -> dict:
    return {"unit_price": price, "quote_timestamp": REF - timedelta(days=days_ago)}


# ── Case 1 ──────────────────────────────────────────────────────────────────
def test_empty_list_returns_none():
    assert calculate_weighted_average([], REF) is None


# ── Case 2 ──────────────────────────────────────────────────────────────────
def test_single_quote_today_weighted_avg_equals_price():
    result = calculate_weighted_average([q(100.0, 0)], REF)
    assert result is not None
    assert result["sample_count"] == 1
    assert result["weighted_avg_price"] == pytest.approx(100.0)


# ── Case 3 ──────────────────────────────────────────────────────────────────
def test_single_quote_today_low_confidence():
    result = calculate_weighted_average([q(100.0, 0)], REF)
    assert result["low_confidence"] is True


# ── Case 4 ──────────────────────────────────────────────────────────────────
def test_single_quote_70_days_ago_weighted_avg_still_equals_price():
    """With only one quote, weighted avg == that price regardless of weight magnitude."""
    result = calculate_weighted_average([q(200.0, 70)], REF)
    assert result["weighted_avg_price"] == pytest.approx(200.0)


# ── Case 5 ──────────────────────────────────────────────────────────────────
def test_4_quotes_is_low_confidence():
    result = calculate_weighted_average([q(100.0, i) for i in range(4)], REF)
    assert result["low_confidence"] is True
    assert result["sample_count"] == 4


# ── Case 6 ──────────────────────────────────────────────────────────────────
def test_5_quotes_is_not_low_confidence():
    result = calculate_weighted_average([q(100.0, i) for i in range(5)], REF)
    assert result["low_confidence"] is False
    assert result["sample_count"] == 5


# ── Case 7 ──────────────────────────────────────────────────────────────────
def test_all_same_price_weighted_avg_equals_that_price():
    quotes = [q(500.0, d) for d in [0, 10, 30, 60, 90]]
    result = calculate_weighted_average(quotes, REF)
    assert result["weighted_avg_price"] == pytest.approx(500.0, rel=1e-9)


# ── Case 8 ──────────────────────────────────────────────────────────────────
def test_all_same_timestamp_gives_arithmetic_mean():
    """Same day ⇒ all weights = exp(0) = 1.0 ⇒ weighted avg = arithmetic mean."""
    quotes = [q(p, 0) for p in [100.0, 200.0, 300.0, 400.0, 500.0]]
    result = calculate_weighted_average(quotes, REF)
    assert result["weighted_avg_price"] == pytest.approx(300.0, rel=1e-9)


# ── Case 9 ──────────────────────────────────────────────────────────────────
def test_newer_quote_has_more_weight_than_older():
    """Today’s price=200, 70-days-ago price=100. Weighted avg must be > 150 (arith. mean)."""
    quotes = [q(200.0, 0), q(100.0, 70)]
    result = calculate_weighted_average(quotes, REF)
    assert result["weighted_avg_price"] > 150.0


# ── Case 10 — manual formula verification ───────────────────────────────────
def test_decay_formula_manual_verification():
    """
    Quote A: price=100, days=0  ⇒ w_A = exp(0)            = 1.0
    Quote B: price=200, days=70 ⇒ w_B = exp(-0.0099*70)  ~ 0.4994
    Expected weighted_avg = (100*1.0 + 200*w_B) / (1.0 + w_B)
    """
    quotes = [q(100.0, 0), q(200.0, 70)]
    result = calculate_weighted_average(quotes, REF)

    w_b = math.exp(-DECAY_LAMBDA * 70)
    expected = (100.0 * 1.0 + 200.0 * w_b) / (1.0 + w_b)

    assert result["weighted_avg_price"] == pytest.approx(expected, rel=1e-9)


# ── Case 11 ──────────────────────────────────────────────────────────────────
def test_very_old_quote_has_minimal_impact():
    """365-day quote should have tiny weight; avg should stay near the fresh price."""
    quotes = [q(100.0, 0), q(9999.0, 365)]
    result = calculate_weighted_average(quotes, REF)
    w_old = math.exp(-DECAY_LAMBDA * 365)
    expected = (100.0 + 9999.0 * w_old) / (1.0 + w_old)
    assert result["weighted_avg_price"] == pytest.approx(expected, rel=1e-9)
    # Numerically verify: avg should be much closer to 100 than to 9999
    assert result["weighted_avg_price"] < 500.0


# ── Case 12 — future timestamp clamped to 0 days ────────────────────────────
def test_future_quote_timestamp_treated_as_zero_days():
    """
    A quote with a timestamp in the future has days_since = negative ⇒ clamped to 0.
    Two such quotes (both clamped to 0) ⇒ same weight ⇒ arithmetic mean.
    """
    future_ts = REF + timedelta(days=30)
    quotes = [
        {"unit_price": 100.0, "quote_timestamp": future_ts},
        {"unit_price": 200.0, "quote_timestamp": future_ts},
    ]
    result = calculate_weighted_average(quotes, REF)
    assert result["weighted_avg_price"] == pytest.approx(150.0, rel=1e-9)


# ── Case 13 ──────────────────────────────────────────────────────────────────
def test_100_quotes_not_low_confidence():
    result = calculate_weighted_average([q(100.0, 0)] * 100, REF)
    assert result["low_confidence"] is False
    assert result["sample_count"] == 100


# ── Case 14 — percentiles with 4 items ─────────────────────────────────────
def test_percentiles_4_items():
    # sorted: [100, 200, 300, 400]
    # p25 = sorted[int(4*0.25)] = sorted[1] = 200
    # median = sorted[int(4*0.50)] = sorted[2] = 300
    # p75 = sorted[int(4*0.75)] = sorted[3] = 400
    result = calculate_weighted_average([q(p, 0) for p in [100.0, 400.0, 200.0, 300.0]], REF)
    assert result["p25_price"] == 200.0
    assert result["median_price"] == 300.0
    assert result["p75_price"] == 400.0


# ── Case 15 — percentiles with 8 items ─────────────────────────────────────
def test_percentiles_8_items():
    # sorted: [1..8]
    # p25 = sorted[2] = 3, median = sorted[4] = 5, p75 = sorted[6] = 7
    result = calculate_weighted_average([q(float(i), 0) for i in range(1, 9)], REF)
    assert result["p25_price"] == 3.0
    assert result["median_price"] == 5.0
    assert result["p75_price"] == 7.0


# ── Case 16 — percentiles with 10 items ─────────────────────────────────────
def test_percentiles_10_items():
    # sorted: [1..10]
    # p25 = sorted[2] = 3, median = sorted[5] = 6, p75 = sorted[7] = 8
    result = calculate_weighted_average([q(float(i), 0) for i in range(1, 11)], REF)
    assert result["p25_price"] == 3.0
    assert result["median_price"] == 6.0
    assert result["p75_price"] == 8.0


# ── Case 17 — min / max ───────────────────────────────────────────────────
def test_min_max_single_item():
    result = calculate_weighted_average([q(42.5, 0)], REF)
    assert result["min_price"] == 42.5
    assert result["max_price"] == 42.5


# ── Case 18 ──────────────────────────────────────────────────────────────────
def test_min_max_multiple_items():
    result = calculate_weighted_average(
        [q(p, 0) for p in [300.0, 100.0, 500.0, 200.0, 400.0]], REF
    )
    assert result["min_price"] == 100.0
    assert result["max_price"] == 500.0


# ── Case 19 ──────────────────────────────────────────────────────────────────
def test_all_same_price_percentiles_equal():
    result = calculate_weighted_average([q(250.0, 0)] * 10, REF)
    assert result["p25_price"] == 250.0
    assert result["median_price"] == 250.0
    assert result["p75_price"] == 250.0
    assert result["min_price"] == 250.0
    assert result["max_price"] == 250.0


# ── Case 20 — very small price ───────────────────────────────────────────────
def test_very_small_price():
    result = calculate_weighted_average([q(0.0001, 0)] * 5, REF)
    assert result["weighted_avg_price"] == pytest.approx(0.0001, rel=1e-4)


# ── Case 21 — very large price ───────────────────────────────────────────────
def test_very_large_price():
    result = calculate_weighted_average([q(999999.9999, 0)] * 5, REF)
    assert result["weighted_avg_price"] == pytest.approx(999999.9999, rel=1e-6)


# ── Case 22 — all required keys present ─────────────────────────────────────
def test_all_required_keys_returned():
    result = calculate_weighted_average([q(100.0, 0)] * 5, REF)
    required = {
        "weighted_avg_price",
        "sample_count",
        "p25_price",
        "median_price",
        "p75_price",
        "min_price",
        "max_price",
        "low_confidence",
    }
    assert required.issubset(set(result.keys()))


# ── Case 23 — three-quote manual verification ────────────────────────────────
def test_three_quote_manual_verification():
    """
    Quote A: price=120, days=0   ⇒ w = exp(0) = 1.0
    Quote B: price=180, days=35  ⇒ w = exp(-0.0099*35) = exp(-0.3465)
    Quote C: price=90,  days=70  ⇒ w = exp(-0.0099*70) = exp(-0.693)
    """
    quotes = [q(120.0, 0), q(180.0, 35), q(90.0, 70)]
    result = calculate_weighted_average(quotes, REF)

    w_a = math.exp(-DECAY_LAMBDA * 0)
    w_b = math.exp(-DECAY_LAMBDA * 35)
    w_c = math.exp(-DECAY_LAMBDA * 70)
    expected = (120.0 * w_a + 180.0 * w_b + 90.0 * w_c) / (w_a + w_b + w_c)

    assert result["weighted_avg_price"] == pytest.approx(expected, rel=1e-9)


# ── Case 24 — exact 5-quote boundary not low_confidence ─────────────────────
def test_exactly_5_quotes_boundary():
    assert calculate_weighted_average([q(100.0, 0)] * 5, REF)["low_confidence"] is False


# ── Case 25 — exact 4-quote boundary IS low_confidence ───────────────────────
def test_exactly_4_quotes_boundary():
    assert calculate_weighted_average([q(100.0, 0)] * 4, REF)["low_confidence"] is True
