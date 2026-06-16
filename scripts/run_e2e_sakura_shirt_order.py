#!/usr/bin/env python3
"""
E2E Integration Test — Sakura Fashion Shirt Order
===================================================
Proves the complete pipeline: Inquiry → GLTG → Qwen → DB

Business scenario (from giraffe-mcp-server-demo):
  Buyer:    Sakura Fashion Japan (sourcing@sakura-fashion.jp)
  Product:  10,000 pcs women's spring shirts, 5 colors
  Deadline: April 10, 2026 (spring shelf launch)
  Inquiry:  January 5, 2026  →  deadline_days ≈ 95

Suppliers tested (from demo fixtures):
  1. Suzhou Alpha    — USD 8.40, split delivery, fabric mostly in-stock
  2. Guangzhou Beta  — USD 7.20, single batch, 3 colors uncertain
  3. Nantong Delta   — USD 7.80, all fabric in-stock, optimized ratio

Pipeline:
  1. Parse demo fixture data → structured requirement
  2. Run GLTG on each supplier response → DeliveryFeasibilityPacket (P50/P80/P90)
  3. Call Qwen → AI procurement recommendation JSON
  4. Persist everything to SQLite via BMDbAdapter (on-mode)
  5. Verify DB records match expected state

Usage:
  # Mock Qwen (GLTG + DB always real):
  E2E_QWEN_MODE=mock uv run python scripts/run_e2e_sakura_shirt_order.py

  # Real Qwen (requires QWEN_API_KEY or DASHSCOPE_API_KEY):
  QWEN_API_KEY=<YOUR_KEY> E2E_QWEN_MODE=real uv run python scripts/run_e2e_sakura_shirt_order.py

Environment:
  QWEN_API_KEY or DASHSCOPE_API_KEY  — real Qwen key (NEVER printed in output)
  E2E_QWEN_MODE                      — 'real' or 'mock' (default: 'mock')
  GIRAFFE_DB_URL                     — SQLite path (default: sqlite:///./e2e_sakura_shirt.db)
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

_HERE = Path(__file__).parent.parent
sys.path.insert(0, str(_HERE))

import bm_db_adapter

# ---------------------------------------------------------------------------
# Constants — Sakura Fashion business scenario
# ---------------------------------------------------------------------------

BUYER_NAME = "Sakura Fashion Japan"
BUYER_EMAIL = "sourcing@sakura-fashion.jp"
PRODUCT = "Women's Spring Shirts"
QUANTITY = 10_000
COLORS = ["white", "sky blue", "black", "pink", "olive green"]
SIZES = ["S", "M", "L", "XL"]
INQUIRY_DATE = date(2026, 1, 5)
SHELF_DATE = date(2026, 4, 10)
DEADLINE_DAYS = (SHELF_DATE - INQUIRY_DATE).days  # 95 days

# Supplier data extracted from giraffe-mcp-server-demo fixture emails
SUPPLIER_RESPONSES = [
    {
        "supplier_id": "suzhou_alpha",
        "supplier_name": "Suzhou Alpha Apparel Co.",
        "response_id": "RESP-SAKURA-M01",
        "email": "sales@suzhou-alpha.example",
        "can_make": True,
        # Parsed from m01_suzhou_alpha_reply.eml
        "unit_price": 8.40,
        "currency": "USD",
        "moq": 1000,
        "fabric_days": 5,          # olive green dyeing required
        "qc_days": 3,              # inline QC at 4 points
        "packaging_days": 2,
        "logistics_days": 14,      # sea freight Shanghai → Tokyo
        "confidence_score": 0.90,
        "completeness_score": 0.95,
        "risk_flags": ["olive_green_dyeing_5d", "split_delivery_batch1_3000_batch2_7000"],
        "missing_fields": [],
        "can_split": True,
        "batch1_qty": 3000,
        "batch2_qty": 7000,
        "batch1_exfactory": "2026-02-20",
        "batch2_exfactory": "2026-03-05",
        "notes": "Split delivery confirmed. Olive green dyeing approval needed immediately.",
    },
    {
        "supplier_id": "guangzhou_beta",
        "supplier_name": "Guangzhou Beta Garment Factory",
        "response_id": "RESP-SAKURA-M02",
        "email": "rfq@guangzhou-beta.example",
        "can_make": True,
        # Parsed from m02_guangzhou_beta_reply.eml
        "unit_price": 7.20,
        "currency": "USD",
        "moq": 5000,
        "fabric_days": 10,         # 3 of 5 colors NOT confirmed (8-10 days to source)
        "qc_days": 1,              # final inspection only
        "packaging_days": 2,
        "logistics_days": 16,      # sea freight 14-18 days
        "confidence_score": 0.65,
        "completeness_score": 0.70,
        "risk_flags": [
            "sky_blue_fabric_uncertain_8_10d",
            "pink_fabric_uncertain_8_10d",
            "olive_green_fabric_uncertain",
            "no_split_delivery",
            "final_inspection_only",
        ],
        "missing_fields": ["split_delivery_option", "inline_qc"],
        "can_split": False,
        "exfactory": "2026-03-15",
        "notes": "3 of 5 fabric colors not confirmed. Single batch only. Final QC only.",
    },
    {
        "supplier_id": "nantong_delta",
        "supplier_name": "Nantong Delta Shirts Ltd.",
        "response_id": "RESP-SAKURA-M03",
        "email": "inquiry@nantong-delta.example",
        "can_make": True,
        # Parsed from m03_nantong_delta_reply.eml
        "unit_price": 7.80,
        "currency": "USD",
        "moq": 500,
        "fabric_days": 0,          # all 5 colors in-stock at Nantong warehouse
        "qc_days": 2,              # inline QC available
        "packaging_days": 2,
        "logistics_days": 14,      # Tokyo arrival March 11 from Feb 25 exfactory
        "confidence_score": 0.85,
        "completeness_score": 0.90,
        "risk_flags": ["size_ratio_pending_buyer_approval"],
        "missing_fields": ["buyer_size_ratio_confirmation"],
        "can_split": False,
        "exfactory_optimized": "2026-02-25",
        "exfactory_standard": "2026-03-02",
        "notes": "All fabric in-stock. Optimized size ratio saves 3 production days. Buyer approval required.",
    },
]


# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------


def _ensure_schema(db_url: str) -> None:
    from sqlalchemy import create_engine
    from src.db.base import Base
    import src.db.models  # noqa: F401

    kwargs = {"connect_args": {"check_same_thread": False}} if "sqlite" in db_url else {}
    engine = create_engine(db_url, echo=False, **kwargs)
    Base.metadata.create_all(bind=engine)
    print(f"  [DB] Schema ready: {db_url}")


# ---------------------------------------------------------------------------
# GLTG Phase
# ---------------------------------------------------------------------------


def run_gltg_for_supplier(sr: dict) -> dict:
    """Run GLTG on one supplier response. Returns enriched result dict."""
    from src.gltg.engine import calculate_gltg_lead_time_path
    from src.lead_time.models import ProductionCapacity

    t0 = time.time()
    path = calculate_gltg_lead_time_path(
        supplier_response_id=sr["response_id"],
        supplier_id=sr["supplier_id"],
        supplier_name=sr["supplier_name"],
        project_id="PROJ-SAKURA-SHIRT-E2E",
        quantity=QUANTITY,
        fabric_days=sr.get("fabric_days"),
        qc_days=sr.get("qc_days"),
        packaging_days=sr.get("packaging_days"),
        logistics_days=sr.get("logistics_days"),
        production_capacity=ProductionCapacity(
            actor_id=sr["supplier_id"],
            daily_capacity_units=500,
            setup_days=1,
            queue_days=0,
            confidence_score=sr["confidence_score"],
        ),
        buyer_deadline_days=DEADLINE_DAYS,
        confidence_score=sr["confidence_score"],
        completeness_score=sr["completeness_score"],
        unit_price=sr.get("unit_price"),
        currency=sr.get("currency"),
        risk_flags=sr.get("risk_flags", []),
        missing_fields=sr.get("missing_fields", []),
    )
    elapsed_ms = (time.time() - t0) * 1000

    return {
        "supplier_id": sr["supplier_id"],
        "supplier_name": sr["supplier_name"],
        "response_id": sr["response_id"],
        "p50_days": path.p50_lead_time_days,
        "p80_days": path.p80_lead_time_days,
        "p90_days": path.p90_lead_time_days,
        "total_lead_time_days": path.total_lead_time_days,
        "feasible": path.feasible_before_deadline,
        "slack_days": path.slack_days,
        "risk_score": path.risk_score,
        "model_name": path.model_name,
        "model_version": path.model_version,
        "feasibility_basis": path.feasibility_basis,
        "evidence_refs": path.evidence_refs,
        "unit_price": sr.get("unit_price"),
        "currency": sr.get("currency"),
        "notes": sr.get("notes", ""),
        "elapsed_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# Qwen Phase
# ---------------------------------------------------------------------------


def _build_qwen_prompt(gltg_results: list[dict]) -> str:
    summary_lines = []
    for r in gltg_results:
        feasible_str = "FEASIBLE" if r["feasible"] else "NOT FEASIBLE"
        summary_lines.append(
            f"- {r['supplier_name']}: P80={r['p80_days']}d, slack={r['slack_days']}d, "
            f"risk_score={r['risk_score']}, unit_price=USD {r['unit_price']}, "
            f"status={feasible_str}, notes: {r['notes']}"
        )
    supplier_summary = "\n".join(summary_lines)

    return f"""You are a B2M procurement advisor for fashion brands.
A Japanese fashion buyer (Sakura Fashion) needs {QUANTITY:,} pcs women's spring shirts
in {len(COLORS)} colors ({', '.join(COLORS)}) delivered to Tokyo by {SHELF_DATE} (deadline: {DEADLINE_DAYS} days).

GLTG delivery feasibility results for {len(gltg_results)} suppliers:
{supplier_summary}

Please provide a structured procurement recommendation in JSON format with these fields:
{{
  "recommended_supplier": "<supplier_id>",
  "recommended_supplier_name": "<name>",
  "confidence": "high|medium|low",
  "ranking": [
    {{"rank": 1, "supplier_id": "...", "reason": "..."}},
    {{"rank": 2, "supplier_id": "...", "reason": "..."}},
    {{"rank": 3, "supplier_id": "...", "reason": "..."}}
  ],
  "risk_summary": "<2-3 sentences>",
  "recommended_action": "<immediate next step for the buyer>",
  "split_delivery_feasible": true|false,
  "price_tradeoff": "<cost vs risk analysis>"
}}"""


def run_qwen(gltg_results: list[dict], mode: str) -> dict:
    """Call Qwen (real) or return a structured mock response."""
    if mode == "mock":
        print("  [Qwen] Mode=mock — returning deterministic mock recommendation")
        return {
            "recommended_supplier": "suzhou_alpha",
            "recommended_supplier_name": "Suzhou Alpha Apparel Co.",
            "confidence": "high",
            "ranking": [
                {"rank": 1, "supplier_id": "suzhou_alpha", "reason": "Best risk-adjusted delivery: P80=45d, split delivery confirmed, inline QC at 4 points."},
                {"rank": 2, "supplier_id": "nantong_delta", "reason": "All fabric in-stock, competitive price, but requires size ratio approval."},
                {"rank": 3, "supplier_id": "guangzhou_beta", "reason": "Lowest price but 3 fabric colors uncertain and no split delivery option."},
            ],
            "risk_summary": (
                "Suzhou Alpha offers the strongest combination of delivery certainty and split delivery capability. "
                "The main risk is olive green dyeing (5 days) which must be approved immediately. "
                "Guangzhou Beta's uncertain fabric sourcing for 3 of 5 colors introduces schedule risk."
            ),
            "recommended_action": "Issue PO to Suzhou Alpha with immediate approval for olive green dyeing start.",
            "split_delivery_feasible": True,
            "price_tradeoff": "Suzhou Alpha costs USD 1.20/pc more than Guangzhou Beta but eliminates fabric sourcing risk and provides split delivery capability for the spring launch.",
            "_mode": "mock",
        }

    # Real Qwen call
    from src.llm.qwen_provider import QwenProvider
    from src.llm.provider_config import get_qwen_api_key

    api_key = get_qwen_api_key()
    if not api_key:
        raise RuntimeError(
            "Qwen API key not set. Set QWEN_API_KEY=<YOUR_KEY> or DASHSCOPE_API_KEY=<YOUR_KEY> "
            "in your environment before running in real mode."
        )

    provider = QwenProvider(api_key=api_key)
    prompt = _build_qwen_prompt(gltg_results)

    print(f"  [Qwen] Calling real API — model={provider.text_model} ...")
    t0 = time.time()
    result = provider.extract_json(prompt=prompt)
    elapsed_ms = (time.time() - t0) * 1000
    print(f"  [Qwen] Response received in {elapsed_ms:.0f}ms")

    data = result.data
    data["_mode"] = "real"
    data["_elapsed_ms"] = elapsed_ms
    data["_model"] = provider.text_model
    return data


# ---------------------------------------------------------------------------
# DB Phase — persist full procurement lifecycle
# ---------------------------------------------------------------------------


def persist_to_db(adapter: bm_db_adapter.BMDbAdapter, gltg_results: list[dict], qwen_result: dict) -> dict:
    """Persist the complete Sakura Fashion shirt order lifecycle to DB."""

    # 1. Actors
    buyer = adapter.get_or_create_actor(BUYER_NAME, "buyer")
    actors = {"buyer": buyer}
    for sr in SUPPLIER_RESPONSES:
        actor = adapter.get_or_create_actor(sr["supplier_name"], "manufacturer")
        actors[sr["supplier_id"]] = actor

    print(f"  [DB] Actors created/retrieved: {len(actors)}")

    # 2. Project
    main_supplier = actors["suzhou_alpha"]  # recommended supplier
    project = adapter.get_or_create_project(
        original_buyer_actor_id=buyer["actor_id"],
        project_key="sakura-shirt-10k-spring-2026",
        main_supplier_actor_id=main_supplier["actor_id"],
        category="apparel",
        quantity=QUANTITY,
        status="CREATED",
    )
    print(f"  [DB] Project: {project['project_id'][:12]}...")

    # 3. Structured requirement
    req = adapter.create_requirement(
        project_id=project["project_id"],
        source_actor_id=buyer["actor_id"],
        category="apparel",
        quantity=QUANTITY,
        material="woven fabric",
        specs_json={
            "product": PRODUCT,
            "colors": COLORS,
            "sizes": SIZES,
            "buyer": BUYER_EMAIL,
            "shelf_date": str(SHELF_DATE),
            "deadline_days": DEADLINE_DAYS,
        },
        confidence_score=0.95,
    )

    # 4–9. For each supplier: edge → inquiry → response → rollup
    db_records: dict[str, dict] = {}
    for sr in SUPPLIER_RESPONSES:
        supplier_actor = actors[sr["supplier_id"]]
        gltg = next(r for r in gltg_results if r["supplier_id"] == sr["supplier_id"])

        # Edge (DRAFT)
        edge = adapter.create_edge(
            project_id=project["project_id"],
            from_actor_id=buyer["actor_id"],
            to_actor_id=supplier_actor["actor_id"],
            edge_type="BUYER_TO_SUPPLIER",
            status="DRAFT",
        )

        # Inquiry
        inquiry = adapter.create_inquiry(
            project_id=project["project_id"],
            edge_id=edge["edge_id"],
            from_actor_id=buyer["actor_id"],
            to_actor_id=supplier_actor["actor_id"],
            requirement_id=req["requirement_id"],
            message_text_en=(
                f"RFQ: {QUANTITY:,} pcs women's spring shirts, 5 colors. "
                f"Deadline: {SHELF_DATE}. Please quote price, lead time, split delivery."
            ),
            status="SENT",
        )

        # Link inquiry → edge, advance to SENT
        adapter.update_edge(edge["edge_id"], inquiry_id=inquiry["inquiry_id"], status="SENT")

        # Supplier response
        response = adapter.create_response(
            project_id=project["project_id"],
            edge_id=edge["edge_id"],
            from_actor_id=supplier_actor["actor_id"],
            to_actor_id=buyer["actor_id"],
            inquiry_id=inquiry["inquiry_id"],
            can_supply=True,
            price=sr.get("unit_price"),
            currency=sr.get("currency", "USD"),
            moq=float(sr.get("moq", 0)),
            available_quantity=float(QUANTITY),
            lead_time_days=gltg["total_lead_time_days"],
            confidence_score=sr["confidence_score"],
            completeness_score=sr["completeness_score"],
        )

        # Link response → edge, advance to RESPONDED
        adapter.update_edge(edge["edge_id"], response_id=response["response_id"], status="RESPONDED")

        # Rollup — includes GLTG summary
        rollup_summary = (
            f"GLTG P80={gltg['p80_days']}d | slack={gltg['slack_days']}d | "
            f"feasible={gltg['feasible']} | risk_score={gltg['risk_score']} | "
            f"model={gltg['model_name']}/{gltg['model_version']}"
        )
        adapter.create_rollup(
            project_id=project["project_id"],
            main_supplier_actor_id=supplier_actor["actor_id"],
            can_accept_order=gltg["feasible"],
            main_capacity_summary=rollup_summary,
            completeness_score=sr["completeness_score"],
            confidence_score=sr["confidence_score"],
        )

        db_records[sr["supplier_id"]] = {
            "edge_id": edge["edge_id"],
            "inquiry_id": inquiry["inquiry_id"],
            "response_id": response["response_id"],
        }

    # 10. Order confirmation (on recommended supplier edge)
    recommended_sid = qwen_result.get("recommended_supplier", "suzhou_alpha")
    if recommended_sid in db_records:
        adapter.update_edge(db_records[recommended_sid]["edge_id"], status="APPROVED")
    adapter.update_project_status(project["project_id"], "ORDER_CONFIRMED")

    # 11. Execution events — full chain record
    for event_type in (
        "BUYER_INQUIRY_RECEIVED",
        "SUPPLIER_RFQS_DISPATCHED",
        "GLTG_FEASIBILITY_EVALUATED",
        "QWEN_RECOMMENDATION_GENERATED",
        "ORDER_CONFIRMED",
        "PRODUCTION_MONITORING_STARTED",
    ):
        adapter.log_event(event_type, project_id=project["project_id"])

    adapter.commit()

    counts = adapter.get_counts()
    print(f"  [DB] Counts after persist: {counts}")

    return {
        "project_id": project["project_id"],
        "requirement_id": req["requirement_id"],
        "db_records": db_records,
        "counts": counts,
    }


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------


def _assert_gltg(results: list[dict]) -> None:
    for r in results:
        assert r["model_name"] == "GLTG", f"Expected GLTG model, got {r['model_name']}"
        assert r["feasibility_basis"] == "p80", f"Expected p80 basis for {r['supplier_id']}"
        assert r["p50_days"] <= r["p80_days"] <= r["p90_days"], \
            f"Percentile ordering violated for {r['supplier_id']}: P50={r['p50_days']} P80={r['p80_days']} P90={r['p90_days']}"

    # Suzhou Alpha must be feasible (confirmed fabric, good lead time)
    alpha = next(r for r in results if r["supplier_id"] == "suzhou_alpha")
    assert alpha["feasible"], f"Suzhou Alpha should be feasible, got P80={alpha['p80_days']}d deadline={DEADLINE_DAYS}d"
    assert alpha["slack_days"] > 0, f"Suzhou Alpha must have positive slack"

    # All three must have GLTG evidence refs
    for r in results:
        has_gltg_ref = any("GLTG" in ref or "gltg" in ref.lower() for ref in r["evidence_refs"])
        assert has_gltg_ref, f"Missing GLTG evidence ref for {r['supplier_id']}: {r['evidence_refs']}"


def _assert_qwen(result: dict) -> None:
    assert "recommended_supplier" in result, "Qwen result missing recommended_supplier"
    assert "risk_summary" in result, "Qwen result missing risk_summary"
    assert isinstance(result.get("ranking"), list), "Qwen result ranking must be a list"
    assert len(result["ranking"]) > 0, "Qwen ranking must not be empty"


def _assert_db(db_result: dict, adapter: bm_db_adapter.BMDbAdapter) -> None:
    counts = db_result["counts"]
    assert counts["actors"] >= 4, f"Expected ≥4 actors (1 buyer + 3 suppliers), got {counts['actors']}"
    assert counts["projects"] >= 1, f"Expected ≥1 project, got {counts['projects']}"
    assert counts["structured_requirements"] >= 1, f"Missing requirement records"
    assert counts["supplier_inquiries"] >= 3, f"Expected ≥3 inquiries, got {counts['supplier_inquiries']}"
    assert counts["supplier_responses"] >= 3, f"Expected ≥3 responses, got {counts['supplier_responses']}"
    assert counts["supplier_response_rollups"] >= 3, f"Expected ≥3 rollups, got {counts['supplier_response_rollups']}"
    assert counts["procurement_edges"] >= 3, f"Expected ≥3 edges, got {counts['procurement_edges']}"
    assert counts["execution_events"] >= 6, f"Expected ≥6 events, got {counts['execution_events']}"

    # Verify each edge was correctly linked
    for sid, rec in db_result["db_records"].items():
        edge_state = adapter.get_edge(rec["edge_id"])
        assert edge_state["inquiry_id"] == rec["inquiry_id"], \
            f"Edge inquiry_id not linked for {sid}: {edge_state['inquiry_id']} != {rec['inquiry_id']}"
        assert edge_state["response_id"] == rec["response_id"], \
            f"Edge response_id not linked for {sid}: {edge_state['response_id']} != {rec['response_id']}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    db_url = os.environ.get("GIRAFFE_DB_URL", "sqlite:///./e2e_sakura_shirt.db")
    qwen_mode = os.environ.get("E2E_QWEN_MODE", "mock").lower()

    print()
    print("=" * 70)
    print("  Giraffe Agent — E2E Integration Test: Sakura Fashion Shirt Order")
    print("=" * 70)
    print(f"  Buyer:       {BUYER_NAME}")
    print(f"  Product:     {QUANTITY:,} pcs {PRODUCT}")
    print(f"  Colors:      {', '.join(COLORS)}")
    print(f"  Deadline:    {SHELF_DATE}  ({DEADLINE_DAYS} days from inquiry)")
    print(f"  Suppliers:   {len(SUPPLIER_RESPONSES)}")
    print(f"  DB:          {db_url}")
    print(f"  Qwen mode:   {qwen_mode}")
    print()

    total_start = time.time()

    # ─── Phase 1: DB Schema ────────────────────────────────────────────────
    print("[Phase 1] Initializing database schema...")
    _ensure_schema(db_url)

    # ─── Phase 2: GLTG ────────────────────────────────────────────────────
    print()
    print("[Phase 2] Running GLTG delivery feasibility per supplier...")
    gltg_results = []
    for sr in SUPPLIER_RESPONSES:
        r = run_gltg_for_supplier(sr)
        feasible_str = "✓ FEASIBLE" if r["feasible"] else "✗ INFEASIBLE"
        print(f"  {r['supplier_name']:<35}  P80={r['p80_days']:>3}d  slack={r['slack_days']:>3}d  "
              f"risk={r['risk_score']:.2f}  {feasible_str}  ({r['elapsed_ms']:.1f}ms)")
        gltg_results.append(r)

    _assert_gltg(gltg_results)
    print("  [GLTG] All assertions passed ✓")

    # ─── Phase 3: Qwen ────────────────────────────────────────────────────
    print()
    print(f"[Phase 3] Calling Qwen for procurement recommendation (mode={qwen_mode})...")
    t0 = time.time()
    qwen_result = run_qwen(gltg_results, mode=qwen_mode)
    qwen_elapsed = (time.time() - t0) * 1000

    _assert_qwen(qwen_result)
    print(f"  [Qwen] Recommended: {qwen_result.get('recommended_supplier_name', qwen_result.get('recommended_supplier'))}")
    print(f"  [Qwen] Confidence:  {qwen_result.get('confidence', 'N/A')}")
    print(f"  [Qwen] Action:      {qwen_result.get('recommended_action', 'N/A')}")
    print(f"  [Qwen] Elapsed:     {qwen_elapsed:.0f}ms")
    print("  [Qwen] Assertions passed ✓")

    # ─── Phase 4: DB Persist ──────────────────────────────────────────────
    print()
    print("[Phase 4] Persisting full lifecycle to database...")
    bm_db_adapter.DB_MODE = "on"
    adapter = bm_db_adapter.BMDbAdapter(db_url=db_url)
    try:
        db_result = persist_to_db(adapter, gltg_results, qwen_result)
        _assert_db(db_result, adapter)
        print("  [DB] All assertions passed ✓")
    finally:
        adapter.close()

    # ─── Summary ──────────────────────────────────────────────────────────
    total_elapsed = (time.time() - total_start) * 1000
    print()
    print("=" * 70)
    print("  RESULT: PASS")
    print("=" * 70)
    print(f"  Total elapsed:   {total_elapsed:.0f}ms")
    print()
    print("  GLTG Results:")
    for r in gltg_results:
        print(f"    {r['supplier_name']:<35}  P80={r['p80_days']}d  feasible={r['feasible']}  risk={r['risk_score']}")
    print()
    print("  Qwen Recommendation:")
    print(f"    Recommended:  {qwen_result.get('recommended_supplier_name', qwen_result.get('recommended_supplier'))}")
    print(f"    Confidence:   {qwen_result.get('confidence', 'N/A')}")
    print(f"    Risk summary: {qwen_result.get('risk_summary', 'N/A')[:100]}...")
    print()
    print("  DB State:")
    counts = db_result["counts"]
    print(f"    actors={counts['actors']}  projects={counts['projects']}  "
          f"inquiries={counts['supplier_inquiries']}  responses={counts['supplier_responses']}  "
          f"rollups={counts['supplier_response_rollups']}  events={counts['execution_events']}")
    print()
    print(f"  Project ID: {db_result['project_id']}")
    print(f"  DB file:    {db_url}")
    print()


if __name__ == "__main__":
    main()
