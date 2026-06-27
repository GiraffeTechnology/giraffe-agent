"""
Buyer Option Generation Tests — AIVAN core trade workflow.

Tests:
  - Feasibility report is generated with ranked delivery paths
  - Single supplier produces single option (not error)
  - Multiple suppliers are ranked by score
  - Labels (P50/P80/P90 or Best/Good/Fallback) are assigned
  - Buyer options reflect lead time, price, and risk
  - Option ranking is explainable
  - Options include risk explanation
  - Deadline comparison works
"""

import os
import uuid
import pytest

os.environ.setdefault("GIRAFFE_DB_MODE", "off")


@pytest.fixture()
def workspace_dir(tmp_path, monkeypatch):
    import src.b_side.workspace as ws_mod
    original = ws_mod._DATA_DIR
    ws_mod._DATA_DIR = tmp_path / "b_side_workspaces"
    ws_mod._DATA_DIR.mkdir(parents=True, exist_ok=True)
    yield ws_mod._DATA_DIR
    ws_mod._DATA_DIR = original


def _make_response(
    response_id, supplier_id, supplier_name,
    lead_time=30, unit_price=5.0, currency="USD",
    confidence=0.8, completeness=0.8,
    red_flags=None, can_make=True,
    fabric_days=None, production_days=None,
    rfq_id="RFQ-TEST001", b_workspace_id="bw_test001",
):
    from src.core_schema.b_side_types import SupplierResponseRecord
    breakdown = {}
    if fabric_days is not None:
        breakdown["fabric_days"] = fabric_days
    if production_days is not None:
        breakdown["production_days"] = production_days
    return SupplierResponseRecord(
        response_id=response_id,
        rfq_id=rfq_id,
        b_workspace_id=b_workspace_id,
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        can_make=can_make,
        lead_time_breakdown=breakdown,
        estimated_lead_time_days=lead_time,
        unit_price=unit_price,
        total_price=round(unit_price * 10000, 2),
        currency=currency,
        confidence_score=confidence,
        completeness_score=completeness,
        red_flags=red_flags or [],
    )


def _setup_workspace(workspace_dir, raw_req, responses):
    from src.b_side.workspace import create_b_workspace, save_b_workspace
    from src.b_side.requirement_structurer import structure_requirement

    ws = create_b_workspace(raw_req)
    ws.buyer_requirement = structure_requirement(ws.b_workspace_id, raw_req)
    rfq_id = ws.buyer_requirement.rfq_id
    # Backfill rfq_id and b_workspace_id into responses created without them
    updated_responses = []
    for r in responses:
        if r.rfq_id == "RFQ-TEST001":
            r = r.model_copy(update={"rfq_id": rfq_id, "b_workspace_id": ws.b_workspace_id})
        updated_responses.append(r)
    ws.supplier_responses = updated_responses
    save_b_workspace(ws)
    return ws


def test_zero_supplier_responses_returns_empty_paths(workspace_dir):
    from src.b_side.feasibility_engine import run_feasibility_simulation
    ws = _setup_workspace(workspace_dir, "1000 cotton shirts Munich 45 days", [])
    report = run_feasibility_simulation(ws.b_workspace_id)
    assert report.paths == []


def test_single_supplier_returns_one_path(workspace_dir):
    from src.b_side.feasibility_engine import run_feasibility_simulation
    ws = _setup_workspace(
        workspace_dir,
        "5000 shirts Munich 45 days",
        [_make_response("r1", "sup1", "Supplier A", lead_time=30)],
    )
    report = run_feasibility_simulation(ws.b_workspace_id)
    assert len(report.paths) == 1
    assert report.paths[0].supplier_id == "sup1"


def test_two_suppliers_ranked_by_score(workspace_dir):
    from src.b_side.feasibility_engine import run_feasibility_simulation
    ws = _setup_workspace(
        workspace_dir,
        "10000 shirts Munich 50 days",
        [
            _make_response("r1", "sup1", "Good Supplier", lead_time=30, confidence=0.9, red_flags=[]),
            _make_response("r2", "sup2", "Poor Supplier", lead_time=60, confidence=0.3,
                           red_flags=["missing_cert", "unrealistic_claim"]),
        ],
    )
    report = run_feasibility_simulation(ws.b_workspace_id)
    assert len(report.paths) == 2
    # Good supplier should be ranked first (lower lead time, higher confidence, fewer flags)
    assert report.paths[0].supplier_id == "sup1", (
        f"Good supplier should be ranked first. Got: {[p.supplier_id for p in report.paths]}"
    )


def test_cannot_make_supplier_excluded(workspace_dir):
    from src.b_side.feasibility_engine import run_feasibility_simulation
    ws = _setup_workspace(
        workspace_dir,
        "5000 shirts Munich 40 days",
        [
            _make_response("r1", "sup1", "Can Make", lead_time=30, can_make=True),
            _make_response("r2", "sup2", "Cannot Make", lead_time=20, can_make=False),
        ],
    )
    report = run_feasibility_simulation(ws.b_workspace_id)
    supplier_ids = [p.supplier_id for p in report.paths]
    assert "sup1" in supplier_ids
    assert "sup2" not in supplier_ids, "Supplier who cannot make should be excluded from paths"


def test_path_has_label(workspace_dir):
    from src.b_side.feasibility_engine import run_feasibility_simulation
    ws = _setup_workspace(
        workspace_dir,
        "5000 shirts Munich 60 days",
        [
            _make_response("r1", "sup1", "Supplier A", lead_time=25),
            _make_response("r2", "sup2", "Supplier B", lead_time=35, confidence=0.7),
            _make_response("r3", "sup3", "Supplier C", lead_time=50, confidence=0.5),
        ],
    )
    report = run_feasibility_simulation(ws.b_workspace_id)
    assert len(report.paths) == 3
    for path in report.paths:
        assert path.label is not None and len(path.label) > 0, (
            f"DeliveryPath must have a label. supplier={path.supplier_id}"
        )


def test_lead_time_model_supplier_a_capacity(workspace_dir):
    """Supplier A: 500 pcs/day, 10,000 pcs order → ~35 days ex-factory."""
    from src.integrations.gltg_leadtime import estimate_lead_time_path as calculate_lead_time_path

    path = calculate_lead_time_path(
        supplier_response_id="r_sup_a",
        supplier_id="sup_a",
        supplier_name="Supplier A",
        project_id="test_proj_a",
        quantity=10000,
        fabric_days=10,
        trim_days=3,
        packaging_material_days=2,
        subcontract_days=0,
        qc_days=2,
        packaging_days=2,
        logistics_days=5,
        supplier_stated_total_days=35,
        risk_flags=[],
        missing_fields=[],
        confidence_score=0.9,
        completeness_score=0.9,
        unit_price=5.0,
        total_price=50000.0,
        currency="USD",
        buyer_deadline_days=45,
    )
    assert path.total_lead_time_days is not None
    assert path.total_lead_time_days > 0
    assert path.feasible_before_deadline is not None


def test_lead_time_model_supplier_d_unrealistic(workspace_dir):
    """Supplier D: 1-day delivery claim must be flagged."""
    from src.integrations.gltg_leadtime import estimate_lead_time_path as calculate_lead_time_path

    path = calculate_lead_time_path(
        supplier_response_id="r_sup_d",
        supplier_id="sup_d",
        supplier_name="Supplier D",
        project_id="test_proj_d",
        quantity=10000,
        fabric_days=None,
        trim_days=None,
        packaging_material_days=None,
        subcontract_days=None,
        qc_days=None,
        packaging_days=None,
        logistics_days=None,
        supplier_stated_total_days=1,
        risk_flags=[],
        missing_fields=[],
        confidence_score=0.5,
        completeness_score=0.3,
        unit_price=1.0,
        total_price=10000.0,
        currency="USD",
        buyer_deadline_days=45,
    )
    # Unrealistic claim should be flagged
    assert len(path.risk_flags) > 0 or path.lead_time_consistency_note is not None, (
        "1-day delivery for 10,000 pcs must generate a risk flag or consistency note"
    )


def test_options_include_risk_explanation(workspace_dir):
    """Buyer options must include risk explanation when supplier has red flags."""
    from src.b_side.feasibility_engine import run_feasibility_simulation
    ws = _setup_workspace(
        workspace_dir,
        "10000 shirts Munich 45 days",
        [_make_response(
            "r_risk", "sup_risk", "Risky Supplier",
            lead_time=25, red_flags=["missing_cert", "unverified_capacity"]
        )],
    )
    report = run_feasibility_simulation(ws.b_workspace_id)
    assert report.paths
    path = report.paths[0]
    assert path.risk_score is not None and path.risk_score > 0
    assert path.notes is not None and len(path.notes) > 0, (
        "Risk notes must be included in buyer option when supplier has red flags"
    )


def test_ranking_explainable_with_multiple_suppliers(workspace_dir):
    """Each path should have rank, label, and notes for explainability."""
    from src.b_side.feasibility_engine import run_feasibility_simulation
    ws = _setup_workspace(
        workspace_dir,
        "5000 shirts Munich 50 days",
        [
            _make_response("r1", "sup1", "Best Supplier", lead_time=25, confidence=0.95),
            _make_response("r2", "sup2", "Mid Supplier", lead_time=40, confidence=0.7),
        ],
    )
    report = run_feasibility_simulation(ws.b_workspace_id)
    for i, path in enumerate(report.paths):
        assert path.rank is not None, f"Path {i} has no rank"
        assert path.label is not None, f"Path {i} has no label"
