"""
End-to-end pipeline tests (unit/integration, no live external calls).

These tests verify the data flow:
  CSV row -> made_in_china_scraper.load_csv -> sku_matcher.normalize_sku
    -> weighted_average.calculate_weighted_average -> aggregate_sku

No real database or network connections required.
"""

import csv
import os
import tempfile
from datetime import datetime, timezone

import pytest

from aggregation.weighted_average import aggregate_sku
from matching.sku_matcher import normalize_sku
from scraper.made_in_china_scraper import load_csv


@pytest.fixture()
def sample_csv(tmp_path):
    """Write a well-formed CSV file with 5 price quotes for one SKU."""
    csv_file = tmp_path / "test_import.csv"
    rows = [
        {
            "source_url": f"https://www.made-in-china.com/product/{i}",
            "seller_id": f"seller_{i}",
            "sku_model_raw": "热销 ABC-200 厅家直销",
            "unit_price": str(100 + i * 10),
            "currency": "USD",
            "quote_date": "2026-05-01",
            "moq": "10",
        }
        for i in range(5)
    ]
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return str(csv_file)


def test_csv_load_returns_correct_count(sample_csv, tmp_path):
    records = list(load_csv(sample_csv, snapshot_dir=str(tmp_path)))
    assert len(records) == 5


def test_csv_load_parses_price(sample_csv, tmp_path):
    records = list(load_csv(sample_csv, snapshot_dir=str(tmp_path)))
    prices = [r["unit_price"] for r in records]
    assert prices == [100.0, 110.0, 120.0, 130.0, 140.0]


def test_csv_load_sets_platform_and_method(sample_csv, tmp_path):
    records = list(load_csv(sample_csv, snapshot_dir=str(tmp_path)))
    for rec in records:
        assert rec["source_platform"] == "made_in_china"
        assert rec["extraction_method"] == "manual_import"


def test_csv_load_saves_snapshot(sample_csv, tmp_path):
    list(load_csv(sample_csv, snapshot_dir=str(tmp_path)))
    snapshots = list(tmp_path.glob("mic_manual_*.csv"))
    assert len(snapshots) == 1


def test_sku_normalise_strips_noise_from_csv_row(sample_csv, tmp_path):
    records = list(load_csv(sample_csv, snapshot_dir=str(tmp_path)))
    normalized = normalize_sku(records[0]["sku_model_raw"])
    assert normalized == "ABC-200"


def test_full_pipeline_csv_to_aggregate(sample_csv, tmp_path):
    records = list(load_csv(sample_csv, snapshot_dir=str(tmp_path)))
    ref_time = datetime(2026, 6, 17, tzinfo=timezone.utc)

    # Normalise SKUs
    for rec in records:
        rec["sku_model_normalized"] = normalize_sku(rec["sku_model_raw"])

    # Group by normalised SKU (all 5 rows share the same SKU)
    sku = records[0]["sku_model_normalized"]
    quotes = [{"unit_price": r["unit_price"], "quote_timestamp": r["quote_timestamp"]} for r in records]

    agg = aggregate_sku(sku, quotes, ref_time)

    assert agg is not None
    assert agg["sku_model_normalized"] == "ABC-200"
    assert agg["sample_count"] == 5
    assert agg["low_confidence"] is False
    assert agg["calculation_formula_version"] == "v1.0.0"
    # All quotes same day -> weighted avg = arithmetic mean = (100+110+120+130+140)/5 = 120
    assert agg["weighted_avg_price"] == pytest.approx(120.0, rel=1e-6)


def test_pipeline_rejects_malformed_price_row(tmp_path):
    csv_file = tmp_path / "bad.csv"
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["source_url", "seller_id", "sku_model_raw", "unit_price", "currency", "quote_date"]
        )
        writer.writeheader()
        writer.writerow({
            "source_url": "https://example.com/product/1",
            "seller_id": "seller_1",
            "sku_model_raw": "ABC-100",
            "unit_price": "not_a_number",  # invalid
            "currency": "USD",
            "quote_date": "2026-05-01",
        })
    records = list(load_csv(str(csv_file), snapshot_dir=str(tmp_path)))
    assert records == []  # Malformed row silently skipped


def test_pipeline_rejects_negative_price_row(tmp_path):
    csv_file = tmp_path / "neg.csv"
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["source_url", "seller_id", "sku_model_raw", "unit_price", "currency", "quote_date"]
        )
        writer.writeheader()
        writer.writerow({
            "source_url": "https://example.com/product/2",
            "seller_id": "seller_2",
            "sku_model_raw": "ABC-200",
            "unit_price": "-50.0",  # negative price
            "currency": "USD",
            "quote_date": "2026-05-01",
        })
    records = list(load_csv(str(csv_file), snapshot_dir=str(tmp_path)))
    assert records == []


def test_pipeline_rejects_invalid_url(tmp_path):
    csv_file = tmp_path / "badurl.csv"
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["source_url", "seller_id", "sku_model_raw", "unit_price", "currency", "quote_date"]
        )
        writer.writeheader()
        writer.writerow({
            "source_url": "not_a_url",  # invalid
            "seller_id": "seller_3",
            "sku_model_raw": "ABC-300",
            "unit_price": "100.0",
            "currency": "USD",
            "quote_date": "2026-05-01",
        })
    records = list(load_csv(str(csv_file), snapshot_dir=str(tmp_path)))
    assert records == []
