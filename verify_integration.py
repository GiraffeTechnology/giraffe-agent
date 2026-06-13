#!/usr/bin/env python3
"""Reproducibility verifier for the B/M-side DB integration.

Runs the full procurement lifecycle ``--runs`` times against a single SQLite
database, asserts row counts and payload integrity after every run, then checks
SQLite PRAGMA integrity_check and PRAGMA foreign_key_check.

Usage:
    python verify_integration.py --db sqlite:///./test.db --runs 5

Verifier design:
  - Buyer and supplier actors are created once and reused across runs
    (get-or-create idempotency).
  - Each run creates a *new* project (keyed by run number) so row counts
    grow monotonically: N runs → N projects, N requirements, N inquiries, etc.
  - After run N the verifier asserts: actors >= 2, projects >= N,
    structured_requirements >= N, supplier_inquiries >= N,
    supplier_responses >= N, supplier_response_rollups >= N,
    procurement_edges >= N, execution_events >= N * 4.
  - Each run's edge is checked for inquiry_id linkage, response_id linkage,
    and status == APPROVED.
  - Final PRAGMA checks confirm DB-level integrity and no FK violations.

Return code 0 = all runs passed; 1 = one or more failures.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

# Project root on sys.path so ``import src`` and ``import bm_db_adapter`` work.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# pydantic_stub exposes BaseModel / Field with or without a full pydantic
# installation. Import it before bm_db_adapter so the stub is available for
# the RunResult model below.
from pydantic_stub import BaseModel, Field  # noqa: E402

import bm_db_adapter  # noqa: E402


# ---------------------------------------------------------------------------
# Typed run result (uses pydantic_stub so it works with or without pydantic)
# ---------------------------------------------------------------------------


class RunResult(BaseModel):
    run: int
    project_id: str
    inquiry_id: str
    response_id: str
    edge_id: str
    counts: dict
    passed: bool


# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------


def _ensure_schema(db_url: str) -> None:
    """Create all tables idempotently via SQLAlchemy create_all."""
    from sqlalchemy import create_engine

    kwargs: dict = {}
    if db_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(db_url, echo=False, **kwargs)

    from src.db.base import Base
    import src.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Single lifecycle run
# ---------------------------------------------------------------------------


def _run_lifecycle(
    adapter: bm_db_adapter.BMDbAdapter,
    run_num: int,
) -> RunResult:
    """Execute one full procurement lifecycle and return a RunResult.

    Lifecycle:
        1.  Actors (buyer + main supplier) — idempotent across runs.
        2.  Project — unique per run_num so rows accumulate.
        3.  Structured requirement.
        4.  Procurement edge (DRAFT → SENT → RESPONDED → APPROVED).
        5.  Supplier inquiry linked to edge.
        6.  Supplier response linked to inquiry and edge.
        7.  Supplier response rollup.
        8.  Order confirmation (edge → APPROVED, project → ORDER_CONFIRMED).
        9.  Execution events: ORDER_CONFIRMED, PRODUCTION_UPDATE_RECEIVED,
            QC_UPDATE_RECEIVED, LOGISTICS_HANDOVER_RECEIVED.
    """

    # 1. Actors — idempotent
    buyer = adapter.get_or_create_actor("VerifyBuyer Corp", "buyer")
    supplier = adapter.get_or_create_actor("VerifySupplier GmbH", "manufacturer")

    # 2. Project — unique per run (product_summary acts as idempotency key)
    project = adapter.get_or_create_project(
        original_buyer_actor_id=buyer["actor_id"],
        project_key=f"verify-polo-shirts-run-{run_num}",
        main_supplier_actor_id=supplier["actor_id"],
        category="textiles",
        quantity=1000,
    )

    # 3. Structured requirement
    req = adapter.create_requirement(
        project_id=project["project_id"],
        source_actor_id=buyer["actor_id"],
        category="textiles",
        quantity=1000,
        material="100% cotton",
        specs_json={"gsm": 180, "color": "white"},
        deadline="2026-09-01",
        confidence_score=0.95,
    )

    # 4. Procurement edge (starts DRAFT, inquiry_id unknown yet)
    edge = adapter.create_edge(
        project_id=project["project_id"],
        from_actor_id=buyer["actor_id"],
        to_actor_id=supplier["actor_id"],
        edge_type="BUYER_TO_MAIN_SUPPLIER",
        status="DRAFT",
    )

    # 5. Supplier inquiry (must reference existing edge)
    inquiry = adapter.create_inquiry(
        project_id=project["project_id"],
        edge_id=edge["edge_id"],
        from_actor_id=buyer["actor_id"],
        to_actor_id=supplier["actor_id"],
        requirement_id=req["requirement_id"],
        message_text_en=(
            f"RFQ run-{run_num}: 1 000 polo shirts, 100% cotton, "
            "180 gsm, white."
        ),
        status="SENT",
    )

    # 6a. Link inquiry_id → edge; advance to SENT
    adapter.update_edge(
        edge["edge_id"],
        inquiry_id=inquiry["inquiry_id"],
        status="SENT",
    )

    # 6b. Supplier response
    response = adapter.create_response(
        project_id=project["project_id"],
        edge_id=edge["edge_id"],
        from_actor_id=supplier["actor_id"],
        to_actor_id=buyer["actor_id"],
        inquiry_id=inquiry["inquiry_id"],
        can_supply=True,
        price=7.80,
        currency="USD",
        moq=200.0,
        available_quantity=5000.0,
        lead_time_days=30,
        confidence_score=0.91,
        completeness_score=0.89,
    )

    # 6c. Link response_id → edge; advance to RESPONDED
    adapter.update_edge(
        edge["edge_id"],
        response_id=response["response_id"],
        status="RESPONDED",
    )

    # 7. Rollup
    adapter.create_rollup(
        project_id=project["project_id"],
        main_supplier_actor_id=supplier["actor_id"],
        can_accept_order=True,
        main_capacity_summary="5 000 units available; 30-day lead time.",
        completeness_score=0.89,
        confidence_score=0.91,
    )

    # 8. Order confirmation — edge status: APPROVED (confirmed)
    adapter.update_edge(edge["edge_id"], status="APPROVED")
    adapter.update_project_status(project["project_id"], "ORDER_CONFIRMED")

    # 9. Execution events
    for event_type in (
        "ORDER_CONFIRMED",
        "PRODUCTION_UPDATE_RECEIVED",
        "QC_UPDATE_RECEIVED",
        "LOGISTICS_HANDOVER_RECEIVED",
    ):
        adapter.log_event(event_type, project_id=project["project_id"])

    adapter.commit()

    counts = adapter.get_counts()
    return RunResult(
        run=run_num,
        project_id=project["project_id"],
        inquiry_id=inquiry["inquiry_id"],
        response_id=response["response_id"],
        edge_id=edge["edge_id"],
        counts=counts,
        passed=True,
    )


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------


def _assert_counts(result: RunResult, run_num: int) -> None:
    """Assert cumulative row counts are consistent after run_num iterations."""
    c = result.counts
    n = run_num
    errors: list[str] = []

    checks = [
        ("actors", c["actors"], 2, ">="),
        ("projects", c["projects"], n, ">="),
        ("structured_requirements", c["structured_requirements"], n, ">="),
        ("supplier_inquiries", c["supplier_inquiries"], n, ">="),
        ("supplier_responses", c["supplier_responses"], n, ">="),
        ("supplier_response_rollups", c["supplier_response_rollups"], n, ">="),
        ("procurement_edges", c["procurement_edges"], n, ">="),
        ("execution_events", c["execution_events"], n * 4, ">="),
    ]
    for name, actual, minimum, op in checks:
        if not (actual >= minimum):
            errors.append(f"{name}: expected >={minimum}, got {actual}")

    if errors:
        raise AssertionError(
            f"Run {run_num} count assertions failed:\n  "
            + "\n  ".join(errors)
        )


def _assert_edge_links(
    adapter: bm_db_adapter.BMDbAdapter,
    result: RunResult,
) -> None:
    """Assert edge.inquiry_id, edge.response_id, and edge.status are correct."""
    edge = adapter.get_edge(result.edge_id)

    if edge["inquiry_id"] != result.inquiry_id:
        raise AssertionError(
            f"Run {result.run}: edge.inquiry_id mismatch — "
            f"expected {result.inquiry_id!r}, got {edge['inquiry_id']!r}"
        )
    if edge["response_id"] != result.response_id:
        raise AssertionError(
            f"Run {result.run}: edge.response_id mismatch — "
            f"expected {result.response_id!r}, got {edge['response_id']!r}"
        )
    if edge["status"] != "APPROVED":
        raise AssertionError(
            f"Run {result.run}: edge.status expected 'APPROVED' "
            f"(order confirmed), got {edge['status']!r}"
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify B/M-side DB integration reproducibility."
    )
    parser.add_argument(
        "--db",
        default="sqlite:///./verify_test.db",
        help="SQLAlchemy database URL (default: sqlite:///./verify_test.db)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Lifecycle iterations to execute (default: 5)",
    )
    args = parser.parse_args()

    db_url: str = args.db
    total_runs: int = args.runs

    # The verifier always uses on-mode — set DB_MODE before instantiating
    # so BMDbAdapter.__init__ reads the overridden value.
    bm_db_adapter.DB_MODE = "on"
    os.environ["GIRAFFE_DB_MODE"] = "on"
    os.environ["GIRAFFE_DB_URL"] = db_url

    print(f"[verify_integration] DB:   {db_url}")
    print(f"[verify_integration] Runs: {total_runs}")

    _ensure_schema(db_url)

    adapter = bm_db_adapter.BMDbAdapter(db_url=db_url)
    passed = 0

    try:
        for i in range(1, total_runs + 1):
            try:
                result = _run_lifecycle(adapter, i)
                _assert_counts(result, i)
                _assert_edge_links(adapter, result)
                print(
                    f"  run {i}/{total_runs}: PASS  "
                    f"(project={result.project_id[:8]}…)"
                )
                passed += 1
            except AssertionError as exc:
                print(f"  run {i}/{total_runs}: FAIL  {exc}")

        # DB-level health checks
        integrity = adapter.check_integrity()
        fk_violations = adapter.check_foreign_keys()

    finally:
        adapter.close()

    print(
        f"[verify_integration] PRAGMA integrity_check: {integrity}"
    )
    if fk_violations:
        print(
            f"[verify_integration] PRAGMA foreign_key_check: "
            f"{len(fk_violations)} violation(s)"
        )
        for v in fk_violations:
            print(f"    {v}")
    else:
        print("[verify_integration] PRAGMA foreign_key_check: ok")

    print(f"[verify_integration] Result: {passed}/{total_runs} passed")

    if passed < total_runs or integrity != "ok" or fk_violations:
        sys.exit(1)


if __name__ == "__main__":
    main()
