"""
Made-in-China.com adapter — manual import mode only.

COMPLIANCE: Made-in-China.com prohibits automated scraping (robots.txt +
ToS Section 10) and provides no public API. Data must be collected manually
by a human operator and imported via this module.

Workflow:
  1. Human operator browses Made-in-China.com and records product data
     in CSV format following the template at scripts/mic_import_template.csv
  2. Run: python -m scripts.manual_import_tool --file data.csv --platform made_in_china
  3. This module validates, normalises, and writes records to the database
"""

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "source_url",
    "seller_id",
    "sku_model_raw",
    "unit_price",
    "currency",
    "quote_date",  # YYYY-MM-DD format
}


def load_csv(
    csv_path: str,
    snapshot_dir: Optional[str] = None,
) -> Iterator[dict]:
    """
    Validate and yield rows from a manually prepared CSV file.
    Saves a copy of the input CSV as a snapshot for audit traceability.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    scraped_at = datetime.now(timezone.utc)
    snapshot_path = _archive_csv(path, scraped_at, snapshot_dir)

    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("Empty CSV file")

        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV is missing required columns: {missing}")

        for i, row in enumerate(reader, start=2):  # line 1 is header
            try:
                yield _parse_row(row, scraped_at, snapshot_path)
            except (ValueError, KeyError) as exc:
                logger.warning("Skipping CSV row %d: %s", i, exc)


def _parse_row(row: dict, scraped_at: datetime, snapshot_path: Optional[str]) -> dict:
    unit_price = float(row["unit_price"].strip().replace(",", ""))
    if unit_price <= 0:
        raise ValueError(f"Invalid unit_price: {row['unit_price']}")

    source_url = row["source_url"].strip()
    if not source_url.startswith("http"):
        raise ValueError(f"source_url must be a full URL, got: {source_url}")

    quote_date_str = row["quote_date"].strip()
    quote_timestamp = datetime.strptime(quote_date_str, "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    )

    moq = None
    if row.get("moq", "").strip():
        try:
            moq = int(row["moq"].strip())
        except ValueError:
            pass

    return {
        "source_platform": "made_in_china",
        "source_url": source_url,
        "seller_id": row["seller_id"].strip(),
        "sku_model_raw": row["sku_model_raw"].strip(),
        "unit_price": unit_price,
        "currency": row.get("currency", "USD").strip().upper(),
        "moq": moq,
        "quote_timestamp": quote_timestamp,
        "scraped_at": scraped_at,
        "raw_html_snapshot_path": snapshot_path,
        "extraction_method": "manual_import",
        "extraction_confidence": 1.0,  # Human-entered data — confidence is operator responsibility
    }


def _archive_csv(
    csv_path: Path,
    scraped_at: datetime,
    snapshot_dir: Optional[str],
) -> Optional[str]:
    if not snapshot_dir:
        import os
        snapshot_dir = os.getenv("HTML_SNAPSHOT_DIR", "/data/snapshots")
    Path(snapshot_dir).mkdir(parents=True, exist_ok=True)

    ts = scraped_at.strftime("%Y%m%dT%H%M%SZ")
    dest = Path(snapshot_dir) / f"mic_manual_{ts}_{csv_path.name}"
    dest.write_bytes(csv_path.read_bytes())
    return str(dest)
