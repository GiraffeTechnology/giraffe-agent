"""
Tests verifying that B-side feasibility engine uses the canonical Lead Time Path Model.

Covers:
1. run_feasibility_simulation returns a FeasibilityReport
2. DeliveryPath has lead time model fields populated
3. calculated_lead_time_days is set (not None)
4. evidence_refs are populated
5. lead_time_components are populated
6. critical_path_summary is set
7. label is assigned
8. supplier_stated_lead_time_days is preserved (not used for ranking)
9. estimated_lead_time_days from SupplierResponseRecord treated as supplier_stated only
10. SupplierResponseRecord has lead_time_breakdown field
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core_schema.b_side_types import (
    BWWorkspace,
    DeliveryPath,
    FeasibilityReport,
    SupplierResponseRecord,
)
from src.b_side.workspace import create_b_workspace, get_b_workspace
from src.b_side.feasibility_engine import run_feasibility_simulation


def _make_workspace_with_response(
    estimated_lead_time_days: int = 20,
    can_make: bool = True,
    red_flags: list | None = None,
    confidence_score: float = 0.8,
    lead_time_breakdown: dict | None = None,
    unit_price: float | None = None,
) -> BWWorkspace:
    """Create a B-side workspace with one supplier response."""
    workspace = create_b_workspace("100 cotton shirts")

    record = SupplierResponseRecord(
        response_id="RESP-TEST-001",
        rfq_id=workspace.rfq_id,
        b_workspace_id=workspace.b_workspace_id,
        supplier_id="actor_supplier_test",
        supplier_name="Test Supplier",
        can_make=can_make,
        estimated_lead_time_days=estimated_lead_time_days,
        red_flags=red_flags or [],
        confidence_score=confidence_score,
        completeness_score=confidence_score,
        unit_price=unit_price,
        lead_time_breakdown=lead_time_breakdown or {},
    )
    workspace.supplier_responses.append(record)

    from src.b_side.workspace import save_b_workspace
    save_b_workspace(workspace)

    return workspace


class TestFeasibilityEngineUsesLeadTimeModel:
    def test_feasibility_returns_report(self):
        ws = _make_workspace_with_response()
        report = run_feasibility_simulation(ws.b_workspace_id)
        assert isinstance(report, FeasibilityReport)

    def test_feasibility_report_has_paths(self):
        ws = _make_workspace_with_response()
        report = run_feasibility_simulation(ws.b_workspace_id)
        assert len(report.paths) >= 1

    def test_delivery_path_has_calculated_lead_time_days(self):
        ws = _make_workspace_with_response()
        report = run_feasibility_simulation(ws.b_workspace_id)
        path = report.paths[0]
        assert path.calculated_lead_time_days is not None
        assert path.calculated_lead_time_days > 0

    def test_delivery_path_has_evidence_refs(self):
        ws = _make_workspace_with_response()
        report = run_feasibility_simulation(ws.b_workspace_id)
        path = report.paths[0]
        assert isinstance(path.evidence_refs, list)
        assert len(path.evidence_refs) > 0

    def test_delivery_path_has_lead_time_components(self):
        ws = _make_workspace_with_response()
        report = run_feasibility_simulation(ws.b_workspace_id)
        path = report.paths[0]
        assert isinstance(path.lead_time_components, list)
        assert len(path.lead_time_components) > 0

    def test_delivery_path_has_critical_path_summary(self):
        ws = _make_workspace_with_response()
        report = run_feasibility_simulation(ws.b_workspace_id)
        path = report.paths[0]
        assert path.critical_path_summary is not None
        assert "=" in path.critical_path_summary

    def test_delivery_path_has_label(self):
        ws = _make_workspace_with_response()
        report = run_feasibility_simulation(ws.b_workspace_id)
        path = report.paths[0]
        assert path.label is not None
        assert path.label in ("BEST_OVERALL", "FASTEST", "LOWEST_COST", "SAFEST", "BACKUP")

    def test_lead_time_days_matches_calculated(self):
        ws = _make_workspace_with_response()
        report = run_feasibility_simulation(ws.b_workspace_id)
        path = report.paths[0]
        # lead_time_days (backward compat) should equal calculated_lead_time_days
        assert path.lead_time_days == path.calculated_lead_time_days

    def test_supplier_stated_lead_time_preserved(self):
        """estimated_lead_time_days is preserved as supplier_stated, not used for ranking."""
        ws = _make_workspace_with_response(estimated_lead_time_days=20)
        report = run_feasibility_simulation(ws.b_workspace_id)
        path = report.paths[0]
        # supplier_stated should be preserved
        assert path.supplier_stated_lead_time_days == 20

    def test_calculated_lead_time_may_differ_from_stated(self):
        """The engine calculates lead time from components, not from stated."""
        ws = _make_workspace_with_response(
            estimated_lead_time_days=999,  # absurdly large stated
            lead_time_breakdown={
                "fabric_days": 5,
                "qc_days": 2,
                "packaging_days": 1,
                "logistics_days": 3,
            },
            confidence_score=0.85,
        )
        report = run_feasibility_simulation(ws.b_workspace_id)
        path = report.paths[0]
        # Calculated should be reasonable, not 999
        assert path.calculated_lead_time_days != 999
        assert path.calculated_lead_time_days < 100

    def test_no_sentinel_999_in_lead_time_days(self):
        """lead_time_days should never be 999 (old sentinel value)."""
        ws = _make_workspace_with_response(estimated_lead_time_days=None)
        report = run_feasibility_simulation(ws.b_workspace_id)
        for path in report.paths:
            assert path.lead_time_days != 999
            assert path.calculated_lead_time_days != 999

    def test_can_make_false_excluded(self):
        ws = _make_workspace_with_response(can_make=False)
        report = run_feasibility_simulation(ws.b_workspace_id)
        assert len(report.paths) == 0

    def test_lead_time_risk_flags_populated(self):
        ws = _make_workspace_with_response(red_flags=["substitute_material"])
        report = run_feasibility_simulation(ws.b_workspace_id)
        path = report.paths[0]
        assert isinstance(path.lead_time_risk_flags, list)

    def test_multiple_suppliers_ranked_correctly(self):
        """With two suppliers, both get paths and the best gets rank=1."""
        workspace = create_b_workspace("200 shirts")

        records = [
            SupplierResponseRecord(
                response_id="RESP-A",
                rfq_id=workspace.rfq_id,
                b_workspace_id=workspace.b_workspace_id,
                supplier_id="supplier_a",
                supplier_name="Supplier A",
                can_make=True,
                lead_time_breakdown={"fabric_days": 5, "logistics_days": 3, "qc_days": 2, "packaging_days": 1},
                confidence_score=0.9,
            ),
            SupplierResponseRecord(
                response_id="RESP-B",
                rfq_id=workspace.rfq_id,
                b_workspace_id=workspace.b_workspace_id,
                supplier_id="supplier_b",
                supplier_name="Supplier B",
                can_make=True,
                lead_time_breakdown={"fabric_days": 20, "logistics_days": 10, "qc_days": 2, "packaging_days": 1},
                confidence_score=0.5,
            ),
        ]
        workspace.supplier_responses = records

        from src.b_side.workspace import save_b_workspace
        save_b_workspace(workspace)

        report = run_feasibility_simulation(workspace.b_workspace_id)
        assert len(report.paths) == 2

        ranks = {p.supplier_id: p.rank for p in report.paths}
        # supplier_a (better) should have rank=1
        assert ranks["supplier_a"] == 1

    def test_workspace_status_updated_to_feasibility_complete(self):
        ws = _make_workspace_with_response()
        run_feasibility_simulation(ws.b_workspace_id)
        updated_ws = get_b_workspace(ws.b_workspace_id)
        assert updated_ws.status == "feasibility_complete"


class TestSupplierResponseRecordLeadTimeBreakdown:
    def test_supplier_response_record_has_lead_time_breakdown_field(self):
        record = SupplierResponseRecord(
            response_id="RESP-001",
            rfq_id="RFQ-001",
            b_workspace_id="WS-001",
            supplier_id="actor_s1",
            supplier_name="Supplier 1",
        )
        assert hasattr(record, "lead_time_breakdown")
        assert isinstance(record.lead_time_breakdown, dict)

    def test_lead_time_breakdown_defaults_to_empty_dict(self):
        record = SupplierResponseRecord(
            response_id="RESP-001",
            rfq_id="RFQ-001",
            b_workspace_id="WS-001",
            supplier_id="actor_s1",
            supplier_name="Supplier 1",
        )
        assert record.lead_time_breakdown == {}

    def test_lead_time_breakdown_can_be_set(self):
        breakdown = {
            "fabric_days": 5,
            "logistics_days": 3,
            "qc_days": 2,
        }
        record = SupplierResponseRecord(
            response_id="RESP-001",
            rfq_id="RFQ-001",
            b_workspace_id="WS-001",
            supplier_id="actor_s1",
            supplier_name="Supplier 1",
            lead_time_breakdown=breakdown,
        )
        assert record.lead_time_breakdown["fabric_days"] == 5
        assert record.lead_time_breakdown["logistics_days"] == 3


class TestDeliveryPathNewFields:
    def test_delivery_path_has_all_new_fields(self):
        path = DeliveryPath(
            path_id="PATH-001",
            rfq_id="RFQ-001",
            supplier_id="s1",
            supplier_name="Supplier 1",
        )
        assert hasattr(path, "calculated_lead_time_days")
        assert hasattr(path, "supplier_stated_lead_time_days")
        assert hasattr(path, "lead_time_components")
        assert hasattr(path, "critical_path_summary")
        assert hasattr(path, "slack_days")
        assert hasattr(path, "deadline_feasible")
        assert hasattr(path, "evidence_refs")
        assert hasattr(path, "lead_time_risk_flags")
        assert hasattr(path, "label")

    def test_delivery_path_new_fields_default_to_none_or_empty(self):
        path = DeliveryPath(
            path_id="PATH-001",
            rfq_id="RFQ-001",
            supplier_id="s1",
            supplier_name="Supplier 1",
        )
        assert path.calculated_lead_time_days is None
        assert path.supplier_stated_lead_time_days is None
        assert path.lead_time_components == []
        assert path.critical_path_summary is None
        assert path.slack_days is None
        assert path.deadline_feasible is None
        assert path.evidence_refs == []
        assert path.lead_time_risk_flags == []
        assert path.label is None
