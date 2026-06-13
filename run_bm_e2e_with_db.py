#!/usr/bin/env python3
"""B/M-side End-to-End runner with optional database persistence.

Runs the complete procurement lifecycle — requirement structuring, inquiry
dispatch, supplier response, rollup, order confirmation, production/QC/logistics
events — using the ``BMDbAdapter`` from ``bm_db_adapter``.

Environment variables:
    GIRAFFE_DB_MODE   'on' or 'off'  (default: 'off')
    GIRAFFE_DB_URL    SQLAlchemy URL (required when mode is 'on')
                      e.g.  sqlite:///./test.db

DB-off mode:
    python run_bm_e2e_with_db.py
    Nothing from src.db is imported; the adapter runs entirely in memory.

DB-on mode:
    GIRAFFE_DB_MODE=on GIRAFFE_DB_URL=sqlite:///./test.db python run_bm_e2e_with_db.py
    The script creates the schema if needed, then runs and persists the
    lifecycle. Uses real SQLAlchemy repositories from src.db.
"""

from __future__ import annotations

import os
import sys

# Ensure project root is on sys.path so both ``import src`` and
# ``import bm_db_adapter`` resolve from any working directory.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import bm_db_adapter  # noqa: E402 — must come after sys.path fixup


# ---------------------------------------------------------------------------
# Schema bootstrap (DB-on only)
# ---------------------------------------------------------------------------


def _ensure_schema(db_url: str) -> None:
    """Create all tables idempotently via SQLAlchemy create_all."""
    from sqlalchemy import create_engine

    kwargs: dict = {}
    if db_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(db_url, echo=False, **kwargs)

    # These imports only execute when this function is called (on-mode only).
    from src.db.base import Base
    import src.db.models  # noqa: F401 — registers all ORM models

    Base.metadata.create_all(bind=engine)
    print(f"[run_bm_e2e] Schema ready at: {db_url}")


# ---------------------------------------------------------------------------
# Full procurement lifecycle
# ---------------------------------------------------------------------------


def _full_lifecycle(
    adapter: bm_db_adapter.BMDbAdapter,
    run_label: str = "e2e-run-1",
) -> None:
    """Execute one complete B/M procurement lifecycle end-to-end.

    Lifecycle steps:
        1.  Buyer and supplier actors (idempotent get-or-create)
        2.  Project (idempotent by run_label)
        3.  Structured requirement
        4.  Procurement edge (DRAFT)
        5.  Supplier inquiry (references edge)
        6.  Link inquiry_id → edge, advance to SENT
        7.  Supplier response (references inquiry)
        8.  Link response_id → edge, advance to RESPONDED
        9.  Supplier response rollup
        10. Order confirmation (edge → APPROVED, project → ORDER_CONFIRMED)
        11. Execution events: ORDER_CONFIRMED, PRODUCTION_UPDATE_RECEIVED,
            QC_UPDATE_RECEIVED, LOGISTICS_HANDOVER_RECEIVED
    """

    # 1. Actors
    buyer = adapter.get_or_create_actor("E2E Buyer Corp", "buyer")
    supplier = adapter.get_or_create_actor("E2E Supplier Ltd", "manufacturer")
    print(
        f"  actors: buyer={buyer['actor_id'][:8]}  "
        f"supplier={supplier['actor_id'][:8]}"
    )

    # 2. Project (product_summary doubles as stable idempotency key)
    project = adapter.get_or_create_project(
        original_buyer_actor_id=buyer["actor_id"],
        project_key=f"polo-shirts-{run_label}",
        main_supplier_actor_id=supplier["actor_id"],
        category="textiles",
        quantity=500,
        status="CREATED",
    )
    print(f"  project: {project['project_id'][:8]}")

    # 3. Structured requirement
    req = adapter.create_requirement(
        project_id=project["project_id"],
        source_actor_id=buyer["actor_id"],
        category="textiles",
        quantity=500,
        material="cotton-polyester blend",
        specs_json={"color": "navy", "size_range": "S-XL"},
        confidence_score=0.92,
    )

    # 4. Edge (starts DRAFT, inquiry_id not yet known)
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
            "Please quote for 500 polo shirts in navy, sizes S-XL, "
            "cotton-polyester blend."
        ),
        status="SENT",
    )

    # 6. Back-fill inquiry_id on edge; advance to SENT
    adapter.update_edge(
        edge["edge_id"],
        inquiry_id=inquiry["inquiry_id"],
        status="SENT",
    )

    # 7. Supplier response
    response = adapter.create_response(
        project_id=project["project_id"],
        edge_id=edge["edge_id"],
        from_actor_id=supplier["actor_id"],
        to_actor_id=buyer["actor_id"],
        inquiry_id=inquiry["inquiry_id"],
        can_supply=True,
        price=8.50,
        currency="USD",
        moq=100.0,
        available_quantity=2000.0,
        lead_time_days=45,
        confidence_score=0.88,
        completeness_score=0.90,
    )

    # 8. Back-fill response_id on edge; advance to RESPONDED
    adapter.update_edge(
        edge["edge_id"],
        response_id=response["response_id"],
        status="RESPONDED",
    )

    # 9. Supplier response rollup
    adapter.create_rollup(
        project_id=project["project_id"],
        main_supplier_actor_id=supplier["actor_id"],
        can_accept_order=True,
        main_capacity_summary="2 000 units in stock; 45-day lead time confirmed.",
        completeness_score=0.90,
        confidence_score=0.88,
    )

    # 10. Order confirmation — edge becomes APPROVED
    adapter.update_edge(edge["edge_id"], status="APPROVED")
    adapter.update_project_status(project["project_id"], "ORDER_CONFIRMED")

    # 11. Lifecycle events
    for event_type in (
        "ORDER_CONFIRMED",
        "PRODUCTION_UPDATE_RECEIVED",
        "QC_UPDATE_RECEIVED",
        "LOGISTICS_HANDOVER_RECEIVED",
    ):
        adapter.log_event(event_type, project_id=project["project_id"])

    adapter.commit()

    # ---- Inline assertions ----
    edge_state = adapter.get_edge(edge["edge_id"])
    assert edge_state["inquiry_id"] == inquiry["inquiry_id"], (
        f"Edge inquiry_id not linked: {edge_state['inquiry_id']} != {inquiry['inquiry_id']}"
    )
    assert edge_state["response_id"] == response["response_id"], (
        f"Edge response_id not linked: {edge_state['response_id']} != {response['response_id']}"
    )
    assert edge_state["status"] == "APPROVED", (
        f"Expected edge status APPROVED, got: {edge_state['status']}"
    )

    counts = adapter.get_counts()
    assert counts["actors"] >= 2, f"actors: {counts['actors']}"
    assert counts["projects"] >= 1, f"projects: {counts['projects']}"
    assert counts["structured_requirements"] >= 1
    assert counts["supplier_inquiries"] >= 1
    assert counts["supplier_responses"] >= 1
    assert counts["supplier_response_rollups"] >= 1
    assert counts["procurement_edges"] >= 1
    assert counts["execution_events"] >= 4

    print(f"  counts: {counts}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    mode = bm_db_adapter.DB_MODE
    db_url = os.environ.get("GIRAFFE_DB_URL", "sqlite:///./bm_e2e_test.db")

    print(f"[run_bm_e2e_with_db] mode={mode}")

    if mode == "on":
        _ensure_schema(db_url)

    adapter = bm_db_adapter.BMDbAdapter(
        db_url=db_url if mode == "on" else None
    )
    try:
        _full_lifecycle(adapter, run_label="e2e-run-1")
    finally:
        adapter.close()

    print("[run_bm_e2e_with_db] PASS")


if __name__ == "__main__":
    main()
