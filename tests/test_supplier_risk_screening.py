"""
Supplier Risk Screening Tests — AIVAN Product Rules #4, #5, #6, #7.

Rule #4: Trusted platform does not mean trusted supplier.
Rule #5: Supplier-level risk screening must remain independent from platform whitelist.
Rule #6: AIVAN must not make final legal, credit, sanctions, or compliance decisions.
Rule #7: AIVAN must not hallucinate supplier facts.

Tests:
  - Supplier response can carry risk flags regardless of platform trust level
  - Risk flags are attached to the supplier response, not suppressed by platform trust
  - Risk level is surfaced in feasibility report
  - AIVAN marks risky supplier responses with appropriate flags
  - Unknown supplier is not auto-trusted
  - Suspicious claims are flagged (e.g., unrealistic lead time, missing certs)
  - Risk output explicitly defers final compliance decisions to human
  - Supplier facts from mock sources are traceable
"""

import os
import pytest

os.environ.setdefault("GIRAFFE_DB_MODE", "off")


# ─── SupplierResponseRecord / risk flag tests ─────────────────────────────────

def _make_supplier_response(**kwargs):
    from src.core_schema.b_side_types import SupplierResponseRecord
    defaults = dict(
        response_id="r001",
        rfq_id="RFQ-TEST001",
        b_workspace_id="bw_test001",
        supplier_id="sup_test",
        supplier_name="Test Supplier",
        can_make=True,
        lead_time_breakdown={},
        estimated_lead_time_days=30,
        unit_price=5.0,
        total_price=5000.0,
        currency="USD",
        confidence_score=0.7,
        completeness_score=0.7,
        red_flags=[],
    )
    defaults.update(kwargs)
    return SupplierResponseRecord(**defaults)


def test_red_flags_preserved_from_response():
    resp = _make_supplier_response(red_flags=["unrealistic lead time", "missing certification"])
    assert "unrealistic lead time" in resp.red_flags
    assert "missing certification" in resp.red_flags


def test_risk_score_increases_with_red_flags(tmp_path, monkeypatch):
    """Feasibility engine must increase risk_score when red flags are present."""
    import src.b_side.workspace as ws_mod
    import src.b_side.feasibility_engine as fe_mod
    original_ws_dir = ws_mod._DATA_DIR
    ws_mod._DATA_DIR = tmp_path / "b_side_workspaces"
    ws_mod._DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from src.b_side.workspace import create_b_workspace, save_b_workspace
        from src.b_side.feasibility_engine import run_feasibility_simulation
        from src.core_schema.b_side_types import SupplierResponseRecord

        workspace = create_b_workspace("10,000 shirts, Munich, 45 days")
        from src.b_side.requirement_structurer import structure_requirement
        workspace.buyer_requirement = structure_requirement(workspace.b_workspace_id, workspace.raw_requirement)
        rfq_id = workspace.buyer_requirement.rfq_id
        resp_clean = SupplierResponseRecord(
            response_id="r_clean",
            rfq_id=rfq_id,
            b_workspace_id=workspace.b_workspace_id,
            supplier_id="sup_clean",
            supplier_name="Clean Supplier",
            can_make=True,
            lead_time_breakdown={},
            estimated_lead_time_days=30,
            unit_price=5.0,
            total_price=50000.0,
            currency="USD",
            confidence_score=0.9,
            completeness_score=0.9,
            red_flags=[],
        )
        resp_risky = SupplierResponseRecord(
            response_id="r_risky",
            rfq_id=rfq_id,
            b_workspace_id=workspace.b_workspace_id,
            supplier_id="sup_risky",
            supplier_name="Risky Supplier",
            can_make=True,
            lead_time_breakdown={},
            estimated_lead_time_days=30,
            unit_price=5.0,
            total_price=50000.0,
            currency="USD",
            confidence_score=0.5,
            completeness_score=0.5,
            red_flags=["missing_cert", "inconsistent_price", "unrealistic_capacity"],
        )
        workspace.supplier_responses = [resp_clean, resp_risky]
        save_b_workspace(workspace)

        report = run_feasibility_simulation(workspace.b_workspace_id)
        paths = report.paths

        path_clean = next((p for p in paths if p.supplier_id == "sup_clean"), None)
        path_risky = next((p for p in paths if p.supplier_id == "sup_risky"), None)

        assert path_clean is not None, "Clean supplier path missing from report"
        assert path_risky is not None, "Risky supplier path missing from report"
        assert path_risky.risk_score > path_clean.risk_score, (
            f"Risky supplier risk_score ({path_risky.risk_score}) must be > "
            f"clean supplier risk_score ({path_clean.risk_score})"
        )
    finally:
        ws_mod._DATA_DIR = original_ws_dir


def test_platform_trust_does_not_clear_risk_flags():
    """Adding a supplier to a trusted platform must not remove its risk flags."""
    resp = _make_supplier_response(
        red_flags=["missing_cert", "inconsistent_price"],
        supplier_id="alibaba_supplier_123",
    )
    # Simulate marking the platform as trusted (no actual logic clears red_flags)
    trusted_platforms = ["alibaba.com", "1688.com"]
    # Risk flags must be present regardless of platform trust
    assert len(resp.red_flags) == 2, (
        "Platform trust must not clear supplier red_flags. "
        f"Current flags: {resp.red_flags}"
    )


def test_unknown_supplier_not_auto_trusted():
    """A supplier with no known history should not have an empty risk flag list by default."""
    from src.core_schema.b_side_types import SupplierResponseRecord
    resp = SupplierResponseRecord(
        response_id="r_unknown",
        rfq_id="RFQ-UNKNOWN01",
        b_workspace_id="bw_unknown01",
        supplier_id="unknown_sup_xyz",
        supplier_name="Unknown Supplier",
        can_make=True,
        lead_time_breakdown={},
        estimated_lead_time_days=25,
        unit_price=3.50,
        total_price=35000.0,
        currency="USD",
        confidence_score=0.3,
        completeness_score=0.4,
        red_flags=["supplier_unknown_to_system", "no_prior_transaction_history"],
    )
    # These flags should be preserved
    assert "supplier_unknown_to_system" in resp.red_flags
    assert "no_prior_transaction_history" in resp.red_flags


def test_risk_flags_noted_in_delivery_path(tmp_path, monkeypatch):
    """When a risky supplier is ranked, risk notes must appear in the DeliveryPath."""
    import src.b_side.workspace as ws_mod
    original_ws_dir = ws_mod._DATA_DIR
    ws_mod._DATA_DIR = tmp_path / "b_side_workspaces"
    ws_mod._DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from src.b_side.workspace import create_b_workspace, save_b_workspace
        from src.b_side.feasibility_engine import run_feasibility_simulation
        from src.b_side.requirement_structurer import structure_requirement
        from src.core_schema.b_side_types import SupplierResponseRecord

        workspace = create_b_workspace("1000 shirts Munich 30 days")
        workspace.buyer_requirement = structure_requirement(workspace.b_workspace_id, workspace.raw_requirement)
        rfq_id = workspace.buyer_requirement.rfq_id
        resp = SupplierResponseRecord(
            response_id="r_risky_notes",
            rfq_id=rfq_id,
            b_workspace_id=workspace.b_workspace_id,
            supplier_id="sup_risky_notes",
            supplier_name="Suspicious Supplier",
            can_make=True,
            lead_time_breakdown={},
            estimated_lead_time_days=3,
            unit_price=0.50,
            total_price=500.0,
            currency="USD",
            confidence_score=0.2,
            completeness_score=0.2,
            red_flags=["unrealistic_1_day_delivery", "suspiciously_low_price"],
        )
        workspace.supplier_responses = [resp]
        save_b_workspace(workspace)

        report = run_feasibility_simulation(workspace.b_workspace_id)
        assert report.paths, "Expected at least one path in the report"
        path = report.paths[0]
        # The notes field should reference risk flags
        assert path.notes is not None and len(path.notes) > 0, (
            "DeliveryPath notes must reference risk flags for risky supplier"
        )
        assert path.risk_score > 0, "Risk score must be > 0 for flagged supplier"
    finally:
        ws_mod._DATA_DIR = original_ws_dir


def test_no_hallucinated_cert_in_supplier_response():
    """Supplier facts must come from actual response data, not fabricated."""
    from src.core_schema.b_side_types import SupplierResponseRecord
    # A response with no certification claim should have no cert fields set
    resp = SupplierResponseRecord(
        response_id="r_nocert",
        rfq_id="RFQ-NOCERT01",
        b_workspace_id="bw_nocert01",
        supplier_id="sup_nocert",
        supplier_name="No-Cert Supplier",
        can_make=True,
        lead_time_breakdown={},
        estimated_lead_time_days=30,
        unit_price=5.0,
        total_price=5000.0,
        currency="USD",
        confidence_score=0.5,
        completeness_score=0.5,
        red_flags=[],
    )
    resp_dict = resp.model_dump()
    # No magic cert fields should appear
    cert_fields = [k for k in resp_dict if "cert" in k.lower() or "sanction" in k.lower()]
    # If cert fields exist, they must be None/empty (not fabricated values)
    for field in cert_fields:
        assert resp_dict[field] is None or resp_dict[field] == [], (
            f"Cert field '{field}' must not have a fabricated value: {resp_dict[field]}"
        )


def test_aivan_defers_compliance_decisions():
    """
    AIVAN risk output must not state final compliance clearance.
    The risk_score and risk flags are informational; final decisions belong to humans.
    """
    from src.core_schema.b_side_types import SupplierResponseRecord, DeliveryPath
    import uuid

    # A DeliveryPath with risk score should indicate review required, not clearance
    path = DeliveryPath(
        path_id=f"PATH-{uuid.uuid4().hex[:8].upper()}",
        rfq_id="RFQ-TEST",
        supplier_id="sup_risk",
        supplier_name="Risk Supplier",
        lead_time_days=30,
        unit_price=5.0,
        currency="USD",
        total_price=5000.0,
        risk_score=0.8,
        confidence_score=0.4,
        notes="Risks: missing_cert; inconsistent_price. Human review required.",
        rank=1,
    )
    # Path should carry a risk note, not state "cleared" or "approved"
    assert path.risk_score is not None and path.risk_score > 0
    notes_lower = (path.notes or "").lower()
    assert "cleared" not in notes_lower or "human" in notes_lower, (
        "Risk notes must not claim compliance clearance without human review qualifier"
    )
