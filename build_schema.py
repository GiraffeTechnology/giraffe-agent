#!/usr/bin/env python3
"""Create or update the giraffe-agent database schema.

Resolves the database URL in this order:
  1. --url CLI argument
  2. GIRAFFE_DB_URL environment variable
  3. Fallback: sqlite:///./giraffe_mvp.db

When GIRAFFE_DB_MODE=off the script exits early with a noop so it is safe
to call unconditionally from CI scripts.

Usage:
    python build_schema.py [--url <sqlalchemy-url>]

    GIRAFFE_DB_URL=sqlite:///./test.db python build_schema.py
"""

from __future__ import annotations

import argparse
import os
import sys

# Project root → sys.path so ``import src`` resolves from any working dir.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def build(db_url: str) -> None:
    """Apply schema to *db_url* using SQLAlchemy ``create_all`` (idempotent)."""
    from sqlalchemy import create_engine

    kwargs: dict = {}
    if db_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(db_url, echo=False, **kwargs)

    # Import Base and register every ORM model.
    from src.db.base import Base
    import src.db.models  # noqa: F401 — side-effect: populates Base.metadata

    Base.metadata.create_all(bind=engine)
    print(f"[build_schema] Schema applied to: {db_url}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build giraffe-agent DB schema.")
    parser.add_argument("--url", default=None, help="SQLAlchemy database URL")
    args = parser.parse_args()

    db_mode = os.environ.get("GIRAFFE_DB_MODE", "on").lower()
    if db_mode == "off":
        print("[build_schema] GIRAFFE_DB_MODE=off — schema creation skipped.")
        return

    db_url: str = (
        args.url
        or os.environ.get("GIRAFFE_DB_URL")
        or "sqlite:///./giraffe_mvp.db"
    )
    build(db_url)


if __name__ == "__main__":
    main()
