"""execution_graph_replay.py — Reconstruct the B/M-side Industrial Execution Graph.

CLI usage
---------
  python execution_graph_replay.py --project-id <id> --db sqlite:///./test.db --format json
  python execution_graph_replay.py --project-id <id> --db sqlite:///./test.db --format md

Module usage
------------
  from execution_graph_replay import replay_project
  graph = replay_project("sqlite:///./test.db", "<project-id>")

All src.db.* imports are lazy (inside functions only) so this file is safe to
import regardless of whether giraffe_db extras are installed.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so ``import src`` works from any cwd.
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ---------------------------------------------------------------------------
# Internal row-to-dict helpers (no DB imports needed here)
# ---------------------------------------------------------------------------

def _isoformat(val: Any) -> Optional[str]:
    """Safely convert a datetime (or string) to an ISO-8601 string."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def _actor_dict(row: Any) -> dict:
    return {
        "actor_id": row.actor_id,
        "name": row.name,
        "actor_type": row.actor_type,
        "default_language": getattr(row, "default_language", None),
        "is_active": getattr(row, "is_active", None),
    }


def _requirement_dict(row: Any) -> dict:
    return {
        "requirement_id": row.requirement_id,
        "project_id": row.project_id,
        "source_actor_id": row.source_actor_id,
        "category": row.category,
        "quantity": row.quantity,
        "material": row.material,
        "deadline": row.deadline,
        "destination": row.destination,
        "specs_json": row.specs_json,
        "missing_fields_json": row.missing_fields_json,
        "confidence_score": row.confidence_score,
        "created_at": _isoformat(row.created_at),
    }


def _inquiry_dict(row: Any) -> dict:
    return {
        "inquiry_id": row.inquiry_id,
        "project_id": row.project_id,
        "edge_id": row.edge_id,
        "from_actor_id": row.from_actor_id,
        "to_actor_id": row.to_actor_id,
        "status": row.status,
        "created_at": _isoformat(getattr(row, "created_at", None)),
    }


def _response_dict(row: Any) -> dict:
    return {
        "response_id": row.response_id,
        "project_id": row.project_id,
        "edge_id": row.edge_id,
        "inquiry_id": row.inquiry_id,
        "from_actor_id": row.from_actor_id,
        "to_actor_id": row.to_actor_id,
        "can_supply": row.can_supply,
        "price": row.price,
        "currency": row.currency,
        "moq": row.moq,
        "available_quantity": row.available_quantity,
        "lead_time_days": row.lead_time_days,
        "earliest_dispatch_date": row.earliest_dispatch_date,
        "confidence_score": row.confidence_score,
        "completeness_score": row.completeness_score,
        "risk_flags_json": row.risk_flags_json,
        "raw_message": row.raw_message,
        "created_at": _isoformat(row.created_at),
        "updated_at": _isoformat(row.updated_at),
    }


def _rollup_dict(row: Any) -> dict:
    return {
        "rollup_id": row.rollup_id,
        "project_id": row.project_id,
        "main_supplier_actor_id": row.main_supplier_actor_id,
        "can_accept_order": row.can_accept_order,
        "main_capacity_summary": row.main_capacity_summary,
        "completeness_score": row.completeness_score,
        "confidence_score": row.confidence_score,
        "recommended_response_to_buyer_en": row.recommended_response_to_buyer_en,
        "recommended_response_to_buyer_zh": row.recommended_response_to_buyer_zh,
        "risk_flags_json": row.risk_flags_json,
        "unresolved_dependencies_json": row.unresolved_dependencies_json,
        "created_at": _isoformat(row.created_at),
        "updated_at": _isoformat(row.updated_at),
    }


def _edge_dict(row: Any) -> dict:
    return {
        "edge_id": row.edge_id,
        "project_id": row.project_id,
        "from_actor_id": row.from_actor_id,
        "to_actor_id": row.to_actor_id,
        "edge_type": row.edge_type,
        "parent_edge_id": row.parent_edge_id,
        "inquiry_id": row.inquiry_id,
        "response_id": row.response_id,
        "status": row.status,
        "metadata_json": row.metadata_json,
        "created_at": _isoformat(row.created_at),
        "updated_at": _isoformat(row.updated_at),
    }


def _event_dict(row: Any) -> dict:
    return {
        "event_id": row.event_id,
        "project_id": row.project_id,
        "event_type": row.event_type,
        "actor_id": row.actor_id,
        "edge_id": row.edge_id,
        "payload_json": row.payload_json,
        "source_channel": getattr(row, "source_channel", None),
        "confidence_score": getattr(row, "confidence_score", None),
        "created_at": _isoformat(row.created_at),
    }


# ---------------------------------------------------------------------------
# Core replay function
# ---------------------------------------------------------------------------

def replay_project(db_url: str, project_id: str) -> dict:
    """Reconstruct the full execution graph for *project_id* from the DB.

    Returns a dict matching the documented JSON output shape.  Returns a dict
    with an "error" key when *project_id* is not found or DB has no rows.
    All src.db.* imports are lazy (inside this function only).
    """
    # Lazy imports — only reached when called.
    import bm_db_adapter as _bma
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.db.models.actor import Actor
    from src.db.models.project import Project
    from src.db.models.requirement import StructuredRequirement
    from src.db.models.inquiry import SupplierInquiry
    from src.db.models.response import SupplierResponse
    from src.db.models.rollup import SupplierResponseRollup
    from src.db.models.procurement_edge import ProcurementEdge
    from src.db.models.execution_event import ExecutionEvent

    # Build a dedicated adapter in "on" mode for this DB URL.
    _bma.DB_MODE = "on"
    adapter = _bma.BMDbAdapter(db_url=db_url)
    session = adapter._session  # noqa: SLF001

    # ------------------------------------------------------------------ project
    project = session.query(Project).filter(Project.project_id == project_id).first()
    if project is None:
        adapter.close()
        return {
            "error": f"Project '{project_id}' not found in database.",
            "project_id": project_id,
        }

    # ------------------------------------------------------------------ actors
    buyer_actor: Optional[dict] = None
    supplier_actor: Optional[dict] = None

    buyer_row = (
        session.query(Actor)
        .filter(Actor.actor_id == project.original_buyer_actor_id)
        .first()
    )
    if buyer_row:
        buyer_actor = _actor_dict(buyer_row)

    if project.main_supplier_actor_id:
        supplier_row = (
            session.query(Actor)
            .filter(Actor.actor_id == project.main_supplier_actor_id)
            .first()
        )
        if supplier_row:
            supplier_actor = _actor_dict(supplier_row)

    # --------------------------------------------------- structured requirement
    req_row = (
        session.query(StructuredRequirement)
        .filter(StructuredRequirement.project_id == project_id)
        .order_by(StructuredRequirement.created_at)
        .first()
    )
    structured_requirement: Optional[dict] = (
        _requirement_dict(req_row) if req_row else None
    )

    # ---------------------------------------------------------------- inquiries
    inq_rows = (
        session.query(SupplierInquiry)
        .filter(SupplierInquiry.project_id == project_id)
        .order_by(SupplierInquiry.created_at)
        .all()
    )
    inquiries: List[dict] = [_inquiry_dict(r) for r in inq_rows]

    # --------------------------------------------------------------- responses
    # ALL versions are included for conflict tracking.
    resp_rows = (
        session.query(SupplierResponse)
        .filter(SupplierResponse.project_id == project_id)
        .order_by(SupplierResponse.created_at)
        .all()
    )
    responses: List[dict] = [_response_dict(r) for r in resp_rows]

    # ------------------------------------------------------------------ rollup
    rollup_row = (
        session.query(SupplierResponseRollup)
        .filter(SupplierResponseRollup.project_id == project_id)
        .order_by(SupplierResponseRollup.created_at.desc())
        .first()
    )
    rollup: Optional[dict] = _rollup_dict(rollup_row) if rollup_row else None

    # ------------------------------------------------------- selected edge
    # Prefer APPROVED edge; fall back to the most-recently-created edge.
    edge_rows = (
        session.query(ProcurementEdge)
        .filter(ProcurementEdge.project_id == project_id)
        .order_by(ProcurementEdge.created_at.desc())
        .all()
    )

    selected_edge: Optional[dict] = None
    for edge in edge_rows:
        if edge.status == "APPROVED":
            selected_edge = _edge_dict(edge)
            break
    if selected_edge is None and edge_rows:
        selected_edge = _edge_dict(edge_rows[0])

    # -------------------------------------------------------- execution events
    event_rows = (
        session.query(ExecutionEvent)
        .filter(ExecutionEvent.project_id == project_id)
        .order_by(ExecutionEvent.created_at)
        .all()
    )
    execution_events: List[dict] = [_event_dict(r) for r in event_rows]

    # ---------------------------------------------------------------- timeline
    event_timeline: List[str] = []
    for ev in execution_events:
        ts = ev.get("created_at") or "unknown-time"
        eid = (ev.get("event_id") or "")[:8]
        event_timeline.append(
            f"{ev['event_type']} @ {ts} [event_id={eid}]"
        )

    adapter.close()

    return {
        "project_id": project_id,
        "buyer": buyer_actor,
        "supplier": supplier_actor,
        "structured_requirement": structured_requirement,
        "inquiries": inquiries,
        "responses": responses,
        "rollup": rollup,
        "selected_edge": selected_edge,
        "execution_events": execution_events,
        "event_timeline": event_timeline,
    }


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def _render_markdown(graph: dict) -> str:
    lines: List[str] = []

    def h(level: int, text: str) -> None:
        lines.append(f"{'#' * level} {text}")
        lines.append("")

    def kv(label: str, value: Any) -> None:
        display = value if value is not None else "_Not provided_"
        lines.append(f"- **{label}:** {display}")

    project_id = graph.get("project_id", "unknown")
    h(1, f"Execution Graph — Project `{project_id}`")

    if "error" in graph:
        lines.append(f"> ERROR: {graph['error']}")
        return "\n".join(lines)

    # Buyer
    h(2, "Buyer")
    buyer = graph.get("buyer") or {}
    kv("actor_id", buyer.get("actor_id"))
    kv("name", buyer.get("name"))
    kv("actor_type", buyer.get("actor_type"))
    lines.append("")

    # Supplier
    h(2, "Supplier")
    supplier = graph.get("supplier") or {}
    if supplier:
        kv("actor_id", supplier.get("actor_id"))
        kv("name", supplier.get("name"))
        kv("actor_type", supplier.get("actor_type"))
    else:
        lines.append("_No supplier linked to this project._")
    lines.append("")

    # Structured Requirement
    h(2, "Structured Requirement")
    req = graph.get("structured_requirement")
    if req:
        kv("requirement_id", req.get("requirement_id"))
        kv("category", req.get("category"))
        kv("quantity", req.get("quantity"))
        kv("material", req.get("material"))
        kv("deadline", req.get("deadline"))
        kv("destination", req.get("destination"))
        kv("confidence_score", req.get("confidence_score"))
    else:
        lines.append("_No structured requirement found._")
    lines.append("")

    # Inquiries
    h(2, "Supplier Inquiries")
    inquiries = graph.get("inquiries", [])
    if inquiries:
        for inq in inquiries:
            lines.append(
                f"- inquiry_id=`{inq.get('inquiry_id')}` "
                f"edge_id=`{inq.get('edge_id')}` "
                f"status=`{inq.get('status')}` "
                f"to=`{inq.get('to_actor_id')}`"
            )
    else:
        lines.append("_No inquiries found._")
    lines.append("")

    # Responses — all versions
    h(2, "Supplier Responses (all versions)")
    responses = graph.get("responses", [])
    if responses:
        for resp in responses:
            price_str = (
                f"{resp.get('price')} {resp.get('currency') or ''}".strip()
                if resp.get("price") is not None
                else "Not provided"
            )
            lead_str = (
                str(resp.get("lead_time_days"))
                if resp.get("lead_time_days") is not None
                else "Not provided"
            )
            lines.append(
                f"- response_id=`{resp.get('response_id')}` "
                f"inquiry_id=`{resp.get('inquiry_id')}` "
                f"edge_id=`{resp.get('edge_id')}` "
                f"can_supply=`{resp.get('can_supply')}` "
                f"price=`{price_str}` "
                f"lead_time_days=`{lead_str}`"
            )
    else:
        lines.append("_No responses found._")
    lines.append("")

    # Rollup
    h(2, "Supplier Response Rollup")
    rollup = graph.get("rollup")
    if rollup:
        kv("rollup_id", rollup.get("rollup_id"))
        kv("can_accept_order", rollup.get("can_accept_order"))
        kv("main_capacity_summary", rollup.get("main_capacity_summary"))
        kv("completeness_score", rollup.get("completeness_score"))
        kv("confidence_score", rollup.get("confidence_score"))
        rec_en = rollup.get("recommended_response_to_buyer_en")
        if rec_en:
            lines.append(f"\n**Recommended response (EN):** {rec_en}\n")
    else:
        lines.append("_No rollup found._")
    lines.append("")

    # Selected Edge
    h(2, "Selected Edge")
    edge = graph.get("selected_edge")
    if edge:
        kv("edge_id", edge.get("edge_id"))
        kv("status", edge.get("status"))
        kv("edge_type", edge.get("edge_type"))
        kv("inquiry_id", edge.get("inquiry_id"))
        kv("response_id", edge.get("response_id"))
        kv("from_actor_id", edge.get("from_actor_id"))
        kv("to_actor_id", edge.get("to_actor_id"))
    else:
        lines.append("_No edge found._")
    lines.append("")

    # Event Timeline
    h(2, "Execution Event Timeline")
    timeline = graph.get("event_timeline", [])
    if timeline:
        for i, entry in enumerate(timeline, 1):
            lines.append(f"{i}. {entry}")
    else:
        lines.append("_No execution events found._")
    lines.append("")

    # Execution Events detail
    h(2, "Execution Events (detail)")
    events = graph.get("execution_events", [])
    if events:
        for ev in events:
            lines.append(
                f"- event_id=`{ev.get('event_id')}` "
                f"type=`{ev.get('event_type')}` "
                f"actor_id=`{ev.get('actor_id')}` "
                f"edge_id=`{ev.get('edge_id')}` "
                f"at=`{ev.get('created_at')}`"
            )
    else:
        lines.append("_No execution events found._")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Reconstruct the B/M-side Industrial Execution Graph from the database."
        )
    )
    parser.add_argument("--project-id", required=True, help="Project UUID to replay.")
    parser.add_argument(
        "--db",
        default=os.environ.get("GIRAFFE_DB_URL", "sqlite:///./bm_integration.db"),
        help=(
            "SQLAlchemy DB URL "
            "(default: GIRAFFE_DB_URL env var or sqlite:///./bm_integration.db)."
        ),
    )
    parser.add_argument(
        "--format",
        choices=["json", "md"],
        default="json",
        help="Output format: json (default) or md (Markdown).",
    )
    args = parser.parse_args()

    graph = replay_project(db_url=args.db, project_id=args.project_id)

    if args.format == "json":
        print(json.dumps(graph, indent=2, default=str))
    else:
        print(_render_markdown(graph))


if __name__ == "__main__":
    _main()
