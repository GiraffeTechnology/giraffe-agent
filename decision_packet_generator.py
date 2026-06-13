"""decision_packet_generator.py — Generate a buyer-facing decision packet.

CLI usage
---------
  python decision_packet_generator.py --project-id <id> --db sqlite:///./test.db --output decision_packet.md
  python decision_packet_generator.py --project-id <id> --db sqlite:///./test.db --output decision_packet.json

Module usage
------------
  from decision_packet_generator import generate_packet
  packet = generate_packet("sqlite:///./test.db", "<project-id>")

CRITICAL rules enforced here:
  - NEVER invent missing supplier data. price=None => "Not provided".
  - NEVER present AI output as a final legal or commercial commitment.
  - Clearly distinguish supplier-stated facts from AI-normalised or AI-inferred values.
  - No placeholder values like 999.

All src.db.* imports are lazy (inside functions only).
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

# Confirmation note appended to every packet.
_CONFIRMATION_NOTE = (
    "This packet is AI-generated from structured supplier data recorded in the "
    "Giraffe procurement database. It is NOT a legal or commercial commitment. "
    "All figures (price, lead time, quantity, etc.) are supplier-stated or "
    "AI-normalised — they have NOT been independently verified. "
    "A human buyer MUST review and confirm this packet before placing any order. "
    "Do not treat any recommendation herein as final or binding."
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _display(val: Any, suffix: str = "") -> str:
    """Return a display string; 'Not provided' when val is None."""
    if val is None:
        return "Not provided"
    return f"{val}{suffix}"


def _rfq_summary(req_row: Any) -> dict:
    """Build the RFQ Summary block from a StructuredRequirement ORM row."""
    return {
        "requirement_id": req_row.requirement_id,
        "category": req_row.category,
        "quantity": req_row.quantity,
        "material": req_row.material,
        "deadline": req_row.deadline,
        "destination": req_row.destination,
        "specs_json": req_row.specs_json,
        "missing_fields_json": req_row.missing_fields_json,
        "confidence_score": req_row.confidence_score,
    }


def _supplier_row_dict(resp: Any) -> dict:
    """Convert a SupplierResponse ORM row into a comparison-table row dict."""
    return {
        "response_id": resp.response_id,
        "inquiry_id": resp.inquiry_id,
        "edge_id": resp.edge_id,
        "supplier_id": resp.from_actor_id,
        "can_supply": resp.can_supply,
        "price": resp.price,
        "currency": resp.currency,
        "lead_time_days": resp.lead_time_days,
        "moq": resp.moq,
        "available_quantity": resp.available_quantity,
        "confidence_score": resp.confidence_score,
        "completeness_score": resp.completeness_score,
        "risk_flags_json": resp.risk_flags_json,
        "raw_message": resp.raw_message,
    }


def _missing_fields_for(resp_dict: dict) -> List[str]:
    """Return a list of field names that are None in this response dict."""
    check_fields = [
        "price", "currency", "lead_time_days", "moq",
        "available_quantity", "can_supply",
    ]
    return [f for f in check_fields if resp_dict.get(f) is None]


def _collect_risk_flags(responses: List[dict]) -> List[dict]:
    """Aggregate all risk_flags_json entries across responses into a flat list."""
    flags: List[dict] = []
    for resp in responses:
        rf = resp.get("risk_flags_json") or {}
        if isinstance(rf, dict):
            for key, val in rf.items():
                flags.append({
                    "response_id": resp["response_id"],
                    "supplier_id": resp["supplier_id"],
                    "flag_key": key,
                    "flag_value": val,
                    "source": "supplier-stated",
                })
        elif isinstance(rf, list):
            for item in rf:
                flags.append({
                    "response_id": resp["response_id"],
                    "supplier_id": resp["supplier_id"],
                    "flag": item,
                    "source": "supplier-stated",
                })
    return flags


def _rank_options(responses: List[dict]) -> List[dict]:
    """Return responses sorted by price ASC (None prices go last)."""
    with_price = [r for r in responses if r.get("price") is not None]
    without_price = [r for r in responses if r.get("price") is None]
    sorted_with = sorted(with_price, key=lambda r: r["price"])
    return sorted_with + without_price


def _recommended_option(responses: List[dict]) -> dict:
    """Pick the cheapest response that has BOTH price AND lead_time_days set."""
    complete = [
        r for r in responses
        if r.get("price") is not None and r.get("lead_time_days") is not None
    ]
    if not complete:
        return {
            "status": "insufficient_data",
            "reason": (
                "No supplier response contains both a price and a lead time. "
                "Human review is required before any option can be recommended."
            ),
        }
    best = min(complete, key=lambda r: r["price"])
    return {
        "status": "recommended",
        "response_id": best["response_id"],
        "supplier_id": best["supplier_id"],
        "inquiry_id": best["inquiry_id"],
        "edge_id": best["edge_id"],
        "price": best["price"],
        "currency": best["currency"],
        "lead_time_days": best["lead_time_days"],
        "confidence_score": best["confidence_score"],
        "completeness_score": best["completeness_score"],
        "evidence_note": (
            f"Cheapest complete option. "
            f"Source: response_id={best['response_id']}, "
            f"inquiry_id={best['inquiry_id']}, "
            f"edge_id={best['edge_id']}. "
            "Data labelled 'supplier-stated'. NOT verified by Giraffe."
        ),
    }


# ---------------------------------------------------------------------------
# Core packet function
# ---------------------------------------------------------------------------

def generate_packet(db_url: str, project_id: str) -> dict:
    """Generate the buyer-facing decision packet for *project_id*.

    Returns a dict matching the documented JSON output shape.  Returns a dict
    with an "error" key when *project_id* is not found or has no data.
    All src.db.* imports are lazy (inside this function only).
    """
    # Lazy imports — only triggered at call time, never at module import.
    import bm_db_adapter as _bma
    from src.db.models.project import Project
    from src.db.models.requirement import StructuredRequirement
    from src.db.models.response import SupplierResponse
    from src.db.models.procurement_edge import ProcurementEdge

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

    # --------------------------------------------------- structured requirement
    req_row = (
        session.query(StructuredRequirement)
        .filter(StructuredRequirement.project_id == project_id)
        .order_by(StructuredRequirement.created_at)
        .first()
    )
    rfq_summary: dict = _rfq_summary(req_row) if req_row else {}

    # ---------------------------------------------------------------- responses
    # Use BMDbAdapter helper which serialises all columns we need.
    resp_rows = (
        session.query(SupplierResponse)
        .filter(SupplierResponse.project_id == project_id)
        .order_by(SupplierResponse.created_at)
        .all()
    )
    supplier_comparison: List[dict] = [_supplier_row_dict(r) for r in resp_rows]

    # ------------------------------------------------------ evidence edge data
    # Collect edge_id -> edge status for evidence links.
    edge_rows = (
        session.query(ProcurementEdge)
        .filter(ProcurementEdge.project_id == project_id)
        .all()
    )
    edge_by_id: Dict[str, str] = {e.edge_id: e.status for e in edge_rows}

    adapter.close()

    # ----------------------------------------------------------------- ranking
    ranked = _rank_options(supplier_comparison)
    top_3_raw = ranked[:3]

    top_3_options: List[dict] = []
    for rank, resp in enumerate(top_3_raw, 1):
        top_3_options.append({
            "rank": rank,
            "response_id": resp["response_id"],
            "supplier_id": resp["supplier_id"],
            "inquiry_id": resp["inquiry_id"],
            "edge_id": resp["edge_id"],
            "edge_status": edge_by_id.get(resp["edge_id"] or "", "unknown"),
            "can_supply": resp["can_supply"],
            "price": resp["price"],
            "currency": resp["currency"],
            "lead_time_days": resp["lead_time_days"],
            "confidence_score": resp["confidence_score"],
            "completeness_score": resp["completeness_score"],
            "data_label": "supplier-stated",
            "evidence_links": {
                "supplier_response_id": resp["response_id"],
                "inquiry_id": resp["inquiry_id"],
                "edge_id": resp["edge_id"],
            },
        })

    # -------------------------------------------------------- recommended option
    recommended_option = _recommended_option(supplier_comparison)

    # ---------------------------------------------------------------- risk flags
    risk_flags = _collect_risk_flags(supplier_comparison)

    # -------------------------------------------------------------- missing fields
    missing_fields: List[dict] = []
    for resp in supplier_comparison:
        mf = _missing_fields_for(resp)
        if mf:
            missing_fields.append({
                "response_id": resp["response_id"],
                "supplier_id": resp["supplier_id"],
                "missing": mf,
            })

    return {
        "project_id": project_id,
        "rfq_summary": rfq_summary,
        "supplier_comparison": supplier_comparison,
        "top_3_options": top_3_options,
        "recommended_option": recommended_option,
        "risk_flags": risk_flags,
        "missing_fields": missing_fields,
        "human_confirmation_required": True,
        "confirmation_note": _CONFIRMATION_NOTE,
        "generated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def _render_packet_markdown(packet: dict) -> str:
    lines: List[str] = []

    def h(level: int, text: str) -> None:
        lines.append(f"{'#' * level} {text}")
        lines.append("")

    def kv(label: str, value: Any, data_label: str = "") -> None:
        display = _display(value)
        tag = f" _(source: {data_label})_" if data_label else ""
        lines.append(f"- **{label}:** {display}{tag}")

    project_id = packet.get("project_id", "unknown")
    h(1, f"Decision Packet — Project `{project_id}`")

    if "error" in packet:
        lines.append(f"> ERROR: {packet['error']}")
        return "\n".join(lines)

    # Human confirmation banner
    lines.append(
        "> **HUMAN CONFIRMATION REQUIRED** — "
        + packet.get("confirmation_note", "")
    )
    lines.append("")
    lines.append(f"_Generated at: {packet.get('generated_at', 'unknown')}_")
    lines.append("")

    # RFQ Summary
    h(2, "1. RFQ Summary")
    rfq = packet.get("rfq_summary") or {}
    if rfq:
        kv("requirement_id", rfq.get("requirement_id"))
        kv("category", rfq.get("category"), "supplier-stated")
        kv("quantity", rfq.get("quantity"), "supplier-stated")
        kv("material", rfq.get("material"), "supplier-stated")
        kv("deadline", rfq.get("deadline"), "supplier-stated")
        kv("destination", rfq.get("destination"), "supplier-stated")
        kv("confidence_score", rfq.get("confidence_score"), "AI-normalised")
    else:
        lines.append("_No structured requirement found for this project._")
    lines.append("")

    # Supplier Comparison Table
    h(2, "2. Supplier Comparison Table")
    comparisons = packet.get("supplier_comparison", [])
    if comparisons:
        header = (
            "| supplier_id | can_supply | price | currency | lead_time_days "
            "| confidence | completeness | risk_flags | response_id | inquiry_id | edge_id |"
        )
        sep = (
            "|---|---|---|---|---|---|---|---|---|---|---|"
        )
        lines.append(header)
        lines.append(sep)
        for row in comparisons:
            rf = row.get("risk_flags_json") or {}
            rf_str = json.dumps(rf) if rf else "none"
            lines.append(
                f"| `{row.get('supplier_id', '')}` "
                f"| {_display(row.get('can_supply'))} "
                f"| {_display(row.get('price'))} "
                f"| {_display(row.get('currency'))} "
                f"| {_display(row.get('lead_time_days'))} "
                f"| {_display(row.get('confidence_score'))} "
                f"| {_display(row.get('completeness_score'))} "
                f"| {rf_str} "
                f"| `{row.get('response_id', '')}` "
                f"| `{row.get('inquiry_id', '')}` "
                f"| `{row.get('edge_id', '')}` |"
            )
    else:
        lines.append("_No supplier responses recorded for this project._")
    lines.append("")

    # Top 3 Options
    h(2, "3. Top 3 Options (ranked by price ASC)")
    top3 = packet.get("top_3_options", [])
    if top3:
        for opt in top3:
            h(3, f"Option #{opt['rank']}")
            kv("supplier_id", opt.get("supplier_id"))
            kv("price", opt.get("price"), "supplier-stated")
            kv("currency", opt.get("currency"), "supplier-stated")
            kv("lead_time_days", opt.get("lead_time_days"), "supplier-stated")
            kv("can_supply", opt.get("can_supply"), "supplier-stated")
            kv("confidence_score", opt.get("confidence_score"), "AI-normalised")
            kv("completeness_score", opt.get("completeness_score"), "AI-normalised")
            lines.append(
                f"- **Evidence links:** "
                f"response_id=`{opt.get('response_id')}` "
                f"inquiry_id=`{opt.get('inquiry_id')}` "
                f"edge_id=`{opt.get('edge_id')}` "
                f"edge_status=`{opt.get('edge_status')}`"
            )
            lines.append("")
    else:
        lines.append("_No options available (no supplier responses)._")
    lines.append("")

    # Recommended Option
    h(2, "4. Recommended Option")
    rec = packet.get("recommended_option") or {}
    if rec.get("status") == "insufficient_data":
        lines.append(f"> **Insufficient data:** {rec.get('reason')}")
    else:
        kv("supplier_id", rec.get("supplier_id"))
        kv("price", rec.get("price"), "supplier-stated")
        kv("currency", rec.get("currency"), "supplier-stated")
        kv("lead_time_days", rec.get("lead_time_days"), "supplier-stated")
        kv("confidence_score", rec.get("confidence_score"), "AI-normalised")
        lines.append(f"- **Note:** {rec.get('evidence_note', '')}")
        lines.append(
            f"- **Evidence links:** "
            f"response_id=`{rec.get('response_id')}` "
            f"inquiry_id=`{rec.get('inquiry_id')}` "
            f"edge_id=`{rec.get('edge_id')}`"
        )
    lines.append("")

    # Risk Flags
    h(2, "5. Risk Flags")
    risk_flags = packet.get("risk_flags", [])
    if risk_flags:
        for rf in risk_flags:
            resp_id = rf.get("response_id", "")
            supplier_id = rf.get("supplier_id", "")
            if "flag_key" in rf:
                lines.append(
                    f"- [{rf.get('source', 'supplier-stated')}] "
                    f"supplier=`{supplier_id}` response=`{resp_id}` "
                    f"flag=`{rf['flag_key']}`: {rf.get('flag_value')}"
                )
            else:
                lines.append(
                    f"- [{rf.get('source', 'supplier-stated')}] "
                    f"supplier=`{supplier_id}` response=`{resp_id}` "
                    f"flag={rf.get('flag')}"
                )
    else:
        lines.append("_No risk flags reported._")
    lines.append("")

    # Missing Fields
    h(2, "6. Missing Fields by Supplier")
    missing = packet.get("missing_fields", [])
    if missing:
        for mf in missing:
            fields_str = ", ".join(mf.get("missing", []))
            lines.append(
                f"- supplier=`{mf.get('supplier_id')}` "
                f"response=`{mf.get('response_id')}` "
                f"missing: **{fields_str}**"
            )
    else:
        lines.append("_All responses are complete._")
    lines.append("")

    # Human Confirmation
    h(2, "7. Human Confirmation Required")
    lines.append(f"> {packet.get('confirmation_note', '')}")
    lines.append("")
    lines.append("**Checklist before placing order:**")
    lines.append("- [ ] Buyer has reviewed price and lead time with supplier directly.")
    lines.append("- [ ] Legal terms and payment conditions agreed separately.")
    lines.append("- [ ] Quality and compliance requirements confirmed.")
    lines.append("- [ ] Authorised signatory has approved this procurement.")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a buyer-facing decision packet from DB procurement data."
    )
    parser.add_argument("--project-id", required=True, help="Project UUID.")
    parser.add_argument(
        "--db",
        default=os.environ.get("GIRAFFE_DB_URL", "sqlite:///./bm_integration.db"),
        help=(
            "SQLAlchemy DB URL "
            "(default: GIRAFFE_DB_URL env var or sqlite:///./bm_integration.db)."
        ),
    )
    parser.add_argument(
        "--output",
        required=True,
        help=(
            "Output file path. Extension determines format: "
            ".json => JSON, anything else => Markdown."
        ),
    )
    args = parser.parse_args()

    packet = generate_packet(db_url=args.db, project_id=args.project_id)

    output_path: str = args.output
    if output_path.endswith(".json"):
        content = json.dumps(packet, indent=2, default=str)
    else:
        content = _render_packet_markdown(packet)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(content)

    print(f"Decision packet written to: {output_path}")


if __name__ == "__main__":
    _main()
