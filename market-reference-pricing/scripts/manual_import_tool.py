"""
Manual import tool for compliant data collection from platforms
that prohibit automated scraping (e.g. Made-in-China.com).

Usage:
  python -m scripts.manual_import_tool --file data.csv --platform made_in_china

CSV template columns:
  source_url, seller_id, sku_model_raw, unit_price, currency, quote_date, moq

All records are validated before insertion and a snapshot of the source
CSV is archived for audit traceability.
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as "python -m scripts.manual_import_tool" from module root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, insert, text
from sqlalchemy.orm import sessionmaker

from matching.sku_matcher import normalize_sku
from scraper.made_in_china_scraper import load_csv
from storage.models import RawMarketQuote

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("manual_import")

SUPPORTED_PLATFORMS = {"made_in_china", "global_sources", "other"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import manually collected B2B price data")
    parser.add_argument("--file", required=True, help="Path to the CSV file")
    parser.add_argument(
        "--platform",
        required=True,
        choices=sorted(SUPPORTED_PLATFORMS),
        help="Source platform identifier",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only, do not write to database",
    )
    args = parser.parse_args()

    load_dotenv(".env.market-reference")

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL is not set. Cannot connect to database.")
        sys.exit(1)

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)

    snapshot_dir = os.getenv("HTML_SNAPSHOT_DIR", "/data/snapshots")
    records = list(load_csv(args.file, snapshot_dir=snapshot_dir))

    if not records:
        logger.warning("No valid records found in %s", args.file)
        return

    # Normalise SKU for each record
    for rec in records:
        rec["sku_model_normalized"] = normalize_sku(rec["sku_model_raw"])
        rec["source_platform"] = args.platform

    logger.info(
        "Loaded %d valid records from %s (platform=%s)",
        len(records),
        args.file,
        args.platform,
    )

    if args.dry_run:
        logger.info("Dry-run mode: skipping database write.")
        for rec in records[:5]:
            logger.info("  Sample record: sku=%s price=%s url=%s",
                        rec["sku_model_normalized"], rec["unit_price"], rec["source_url"])
        return

    with Session() as session:
        # Ensure schema exists
        session.execute(text("CREATE SCHEMA IF NOT EXISTS market_reference"))
        session.commit()

        inserted = 0
        for rec in records:
            try:
                session.execute(insert(RawMarketQuote).values(**rec))
                inserted += 1
            except Exception as exc:
                logger.warning("Failed to insert record (url=%s): %s", rec.get("source_url"), exc)
                session.rollback()
        session.commit()

    logger.info("Inserted %d / %d records into market_reference.raw_market_quotes", inserted, len(records))


if __name__ == "__main__":
    main()
