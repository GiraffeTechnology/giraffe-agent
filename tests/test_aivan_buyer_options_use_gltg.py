"""
Buyer Options GLTG Tests — AIVAN product rule.

Every AIVAN-facing buyer option (DeliveryPath) must carry GLTG provenance:
model name, P50/P80/P90 percentile estimates, feasibility basis, and explicit
fallback status.  Tests here verify the full B-side path from supplier
responses to DeliveryPath objects.
"""

import os
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
    response_id,
    supplier_id,
    supplier_name,
    fabric_days=10,
    qc_days=2,
    packaging_days=1,
    logistics_days=7,
    unit_price=5.0,
    confidence=0.8,
    completeness=0.8,
    red_flags=None,
    rfq_id="RFQ-GLTG-TEST",
    b_workspace_id="bw_gltg_test",
):
    from src.core_schema.b_side_types import SupplierResponseRecord
    return SupplierResponseRecord(
        response_id=response_id,
        rfq_id=rfq_id,
        b_workspace_id=b_workspace_id,
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        can_make=True,
        lead_time_breakdown={
            "fabric_days": fabric_days,
            "qc_days": qc_days,
            "packaging_days": packaging_days,
            "logistics_days": logistics_days,
        },
        unit_price=unit_price,
        total_price=round(unit_price * 1000, 2),
        currency="USD",
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
    updated = []
    for r in responses:
        if r.rfq_id == "RFQ-GLTG-TEST":
            r = r.model_copy(update={"rfq_id": rfq_id, "b_workspace_id": ws.b_workspace_id})
        updated.append(r)
    ws.supplier_responses = updated
    save_b_workspace(ws)
    return ws


def test_buyer_option_has_gltg_model_name(workspace_dir):
    """DeliveryPath.lead_time_model must equal 'GLTG'."""
    from src.b_side.feasibility_engine import run_feasibility_simulation
    ws = _setup_workspace(workspace_dir, "1000 shirts 45 days",
                          [_make_response("r1", "sup1", "Supplier A")])
    report = run_feasibility_simulation(ws.b_workspace_id)
    assert report.paths, "Expected at least one delivery path"
    path = report.paths[0]
    assert path.lead_time_model == "GLTG", (
        f"lead_time_model must be 'GLTG', got: {path.lead_time_model!r}"
    )


def test_buyer_option_has_p50_p80_p90(workspace_dir):
    """DeliveryPath must expose P50, P80, P90 lead-time percentiles from GLTG."""
    from src.b_side.feasibility_engine import run_feasibility_simulation
    ws = _setup_workspace(workspace_dir, "1000 shirts 45 days",
                          [_make_response("r1", "sup1", "Supplier A")])
    report = run_feasibility_simulation(ws.b_workspace_id)
    path = report.paths[0]
    assert path.p50_lead_time_days is not None, "p50_lead_time_days must be set"
    assert path.p80_lead_time_days is not None, "p80_lead_time_days must be set"
    assert path.p90_lead_time_days is not None, "p90_lead_time_days must be set"


def test_buyer_option_percentile_ordering(workspace_dir):
    """P50 <= P80 <= P90 must hold on every buyer option."""
    from src.b_side.feasibility_engine import run_feasibility_simulation
    ws = _setup_workspace(workspace_dir, "1000 shirts 45 days",
                          [_make_response("r1", "sup1", "Supplier A")])
    report = run_feasibility_simulation(ws.b_workspace_id)
    path = report.paths[0]
    assert path.p50_lead_time_days <= path.p80_lead_time_days <= path.p90_lead_time_days, (
        f"P50={path.p50_lead_time_days} P80={path.p80_lead_time_days} P90={path.p90_lead_time_days}: "
        "percentile ordering violated"
    )


def test_buyer_option_feasibility_basis_is_p80(workspace_dir):
    """DeliveryPath.feasibility_basis must be 'p80', not p50 or deterministic."""
    from src.b_side.feasibility_engine import run_feasibility_simulation
    ws = _setup_workspace(workspace_dir, "1000 shirts 45 days",
                          [_make_response("r1", "sup1", "Supplier A")])
    report = run_feasibility_simulation(ws.b_workspace_id)
    path = report.paths[0]
    assert path.feasibility_basis == "p80", (
        f"feasibility_basis must be 'p80', got: {path.feasibility_basis!r}"
    )


def test_buyer_option_fallback_is_false(workspace_dir):
    """fallback_model_used must be False for embedded GLTG (never silent fallback)."""
    from src.b_side.feasibility_engine import run_feasibility_simulation
    ws = _setup_workspace(workspace_dir, "1000 shirts 45 days",
                          [_make_response("r1", "sup1", "Supplier A")])
    report = run_feasibility_simulation(ws.b_workspace_id)
    path = report.paths[0]
    assert path.fallback_model_used is False, (
        f"fallback_model_used must be False for embedded GLTG, got: {path.fallback_model_used!r}"
    )


def test_multiple_buyer_options_all_have_gltg_fields(workspace_dir):
    """All buyer options in a multi-supplier scenario must carry GLTG metadata."""
    from src.b_side.feasibility_engine import run_feasibility_simulation
    ws = _setup_workspace(
        workspace_dir,
        "5000 shirts Munich 60 days",
        [
            _make_response("r1", "sup1", "Fast Supplier", fabric_days=5, logistics_days=5),
            _make_response("r2", "sup2", "Slow Supplier", fabric_days=20, logistics_days=14),
        ],
    )
    report = run_feasibility_simulation(ws.b_workspace_id)
    assert len(report.paths) == 2
    for path in report.paths:
        assert path.lead_time_model == "GLTG", (
            f"supplier={path.supplier_id}: lead_time_model must be 'GLTG'"
        )
        assert path.p50_lead_time_days is not None
        assert path.p80_lead_time_days is not None
        assert path.p90_lead_time_days is not None
        assert path.feasibility_basis == "p80"
        assert path.fallback_model_used is False


def test_buyer_option_p80_matches_calculated_lead_time(workspace_dir):
    """p80_lead_time_days must equal calculated_lead_time_days (P80 is the base estimate)."""
    from src.b_side.feasibility_engine import run_feasibility_simulation
    ws = _setup_workspace(workspace_dir, "1000 shirts 45 days",
                          [_make_response("r1", "sup1", "Supplier A")])
    report = run_feasibility_simulation(ws.b_workspace_id)
    path = report.paths[0]
    assert path.p80_lead_time_days == path.calculated_lead_time_days, (
        f"p80_lead_time_days ({path.p80_lead_time_days}) must equal "
        f"calculated_lead_time_days ({path.calculated_lead_time_days})"
    )
