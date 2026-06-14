"""
Tests verifying that M-side rollup and bridge populate lead time components.

Covers:
1. SupplierResponseRollup has new lead time fields
2. generate_supplier_response_rollup populates calculated_total_lead_time_days
3. lead_time_components is populated
4. lead_time_evidence_refs is populated
5. submit_rollup_to_b_side populates lead_time_breakdown on SupplierResponseRecord
6. lead_time_breakdown contains expected keys
7. UpstreamOption has evidence fields
8. option_engine populates dispatch_lead_time_days
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.m_side.upstream.approval_gate import ApprovalRequest, ApprovalResult
from src.m_side.upstream.option_engine import UpstreamOption, generate_upstream_options
from src.m_side.upstream.response_parser import parse_upstream_response
from src.m_side.rollup.supplier_response_rollup import (
    SupplierResponseRollup,
    generate_supplier_response_rollup,
)
from src.m_side.bridge.submit_rollup_to_b_side import submit_rollup_to_b_side
from src.b_side.workspace import create_b_workspace, get_b_workspace

PROJECT_ID = "PROJ-ROLLUPTEST"
MANUFACTURER_ID = "actor_manufacturer_m"
FABRIC_SUPPLIER_ID = "actor_fabric_s1"


def _make_approval_result(dep_type: str, lead_time_summary: str = "7 days") -> ApprovalResult:
    opt = UpstreamOption(
        option_id=f"OPT-{dep_type.upper()}",
        project_id=PROJECT_ID,
        dependency_id=f"DEP-{dep_type.upper()}",
        dependency_type=dep_type,
        upstream_actor_id=f"actor_{dep_type}_s1",
        option_label="BEST",
        price_summary="USD 2.50",
        lead_time_summary=lead_time_summary,
        risk_summary="No significant risks",
        score=0.8,
        reason="Best option",
        response_ids=["UPR-001"],
    )
    req = ApprovalRequest(
        approval_request_id=f"APR-{dep_type.upper()}",
        project_id=PROJECT_ID,
        dependency_id=f"DEP-{dep_type.upper()}",
        dependency_type=dep_type,
        options=[opt],
        required_approval_mode="human",
    )
    return ApprovalResult(
        approval_request_id=req.approval_request_id,
        approved_option_id=opt.option_id,
        approved_option=opt,
        approved_by="user_manufacturer_m",
        mode="human",
    )


class TestSupplierResponseRollupLeadTimeFields:
    def test_rollup_has_calculated_total_lead_time_days(self):
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=[_make_approval_result("fabric")],
            product_summary="100 cotton shirts",
            quantity=100,
        )
        assert hasattr(rollup, "calculated_total_lead_time_days")

    def test_rollup_calculated_lead_time_is_positive_integer(self):
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=[_make_approval_result("fabric")],
            product_summary="100 cotton shirts",
            quantity=100,
        )
        assert rollup.calculated_total_lead_time_days is not None
        assert rollup.calculated_total_lead_time_days > 0

    def test_rollup_has_lead_time_components(self):
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=[_make_approval_result("fabric")],
            product_summary="100 cotton shirts",
            quantity=100,
        )
        assert hasattr(rollup, "lead_time_components")
        assert isinstance(rollup.lead_time_components, list)
        assert len(rollup.lead_time_components) > 0

    def test_rollup_has_lead_time_evidence_refs(self):
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=[_make_approval_result("fabric")],
            product_summary="100 cotton shirts",
            quantity=100,
        )
        assert hasattr(rollup, "lead_time_evidence_refs")
        assert isinstance(rollup.lead_time_evidence_refs, list)
        assert len(rollup.lead_time_evidence_refs) > 0

    def test_rollup_has_material_ready_days(self):
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=[_make_approval_result("fabric", lead_time_summary="5 days")],
            product_summary="100 cotton shirts",
            quantity=100,
        )
        assert rollup.material_ready_days is not None
        assert rollup.material_ready_days >= 0

    def test_rollup_has_production_days(self):
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=[_make_approval_result("fabric")],
            product_summary="100 cotton shirts",
            quantity=100,
        )
        assert rollup.production_days is not None
        assert rollup.production_days > 0

    def test_rollup_has_risk_buffer_days(self):
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=[_make_approval_result("fabric")],
            product_summary="100 cotton shirts",
            quantity=100,
        )
        assert hasattr(rollup, "risk_buffer_days")
        assert rollup.risk_buffer_days is not None

    def test_rollup_has_lead_time_risk_flags(self):
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=[_make_approval_result("fabric")],
            product_summary="100 cotton shirts",
            quantity=100,
        )
        assert hasattr(rollup, "lead_time_risk_flags")
        assert isinstance(rollup.lead_time_risk_flags, list)

    def test_rollup_components_have_required_keys(self):
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=[_make_approval_result("fabric")],
            product_summary="100 cotton shirts",
            quantity=100,
        )
        for comp in rollup.lead_time_components:
            assert "component_id" in comp
            assert "component_type" in comp
            assert "duration_days" in comp
            assert "evidence_type" in comp


class TestSubmitRollupLeadTimeBreakdown:
    def _make_rollup(self) -> SupplierResponseRollup:
        return generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=[
                _make_approval_result("fabric", lead_time_summary="5 days"),
                _make_approval_result("logistics", lead_time_summary="3 days"),
            ],
            product_summary="100 cotton shirts",
            quantity=100,
            main_capacity_available=True,
        )

    def test_submit_creates_record_with_lead_time_breakdown(self):
        rollup = self._make_rollup()
        b_workspace = create_b_workspace("100 cotton shirts")
        submit_rollup_to_b_side(rollup=rollup, b_workspace_id=b_workspace.b_workspace_id)

        workspace = get_b_workspace(b_workspace.b_workspace_id)
        assert len(workspace.supplier_responses) == 1
        resp = workspace.supplier_responses[0]
        assert hasattr(resp, "lead_time_breakdown")
        assert isinstance(resp.lead_time_breakdown, dict)

    def test_lead_time_breakdown_has_expected_keys(self):
        rollup = self._make_rollup()
        b_workspace = create_b_workspace("100 cotton shirts")
        submit_rollup_to_b_side(rollup=rollup, b_workspace_id=b_workspace.b_workspace_id)

        workspace = get_b_workspace(b_workspace.b_workspace_id)
        resp = workspace.supplier_responses[0]
        breakdown = resp.lead_time_breakdown
        assert "fabric_days" in breakdown or "material_days" in breakdown
        assert "production_days" in breakdown
        assert "evidence_refs" in breakdown
        assert "components" in breakdown

    def test_lead_time_breakdown_calculated_total_days(self):
        rollup = self._make_rollup()
        b_workspace = create_b_workspace("100 cotton shirts")
        submit_rollup_to_b_side(rollup=rollup, b_workspace_id=b_workspace.b_workspace_id)

        workspace = get_b_workspace(b_workspace.b_workspace_id)
        resp = workspace.supplier_responses[0]
        # calculated_total_days should be set
        assert resp.lead_time_breakdown.get("calculated_total_days") is not None
        assert resp.lead_time_breakdown["calculated_total_days"] > 0

    def test_estimated_lead_time_days_uses_calculated(self):
        """estimated_lead_time_days should now come from the path model, not sum of basis days."""
        rollup = self._make_rollup()
        b_workspace = create_b_workspace("100 cotton shirts")
        submit_rollup_to_b_side(rollup=rollup, b_workspace_id=b_workspace.b_workspace_id)

        workspace = get_b_workspace(b_workspace.b_workspace_id)
        resp = workspace.supplier_responses[0]
        # Should be the calculated value, not 999 or None for valid rollup
        if resp.estimated_lead_time_days is not None:
            assert resp.estimated_lead_time_days != 999
            assert resp.estimated_lead_time_days > 0


class TestUpstreamOptionLeadTimeFields:
    def test_upstream_option_has_dispatch_lead_time_days(self):
        opt = UpstreamOption(
            option_id="OPT-001",
            project_id=PROJECT_ID,
            dependency_id="DEP-FAB",
            dependency_type="fabric",
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            option_label="BEST",
            price_summary="USD 2.50",
            lead_time_summary="7 days",
            risk_summary="No significant risks",
            score=0.8,
            reason="Best option",
        )
        assert hasattr(opt, "dispatch_lead_time_days")
        assert hasattr(opt, "evidence_refs")
        assert hasattr(opt, "lead_time_risk_flags")
        assert hasattr(opt, "lead_time_components")
        assert hasattr(opt, "material_availability_days")
        assert hasattr(opt, "shipping_to_manufacturer_days")

    def test_upstream_option_evidence_refs_default_empty(self):
        opt = UpstreamOption(
            option_id="OPT-001",
            project_id=PROJECT_ID,
            dependency_id="DEP-FAB",
            dependency_type="fabric",
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            option_label="BEST",
            price_summary="USD 2.50",
            lead_time_summary="7 days",
            risk_summary="No significant risks",
            score=0.8,
            reason="Best option",
        )
        assert opt.evidence_refs == []
        assert opt.lead_time_risk_flags == []
        assert opt.lead_time_components == []

    def test_generate_options_populates_dispatch_lead_time_days(self):
        raw = "Yes can supply. USD 2.50/m. 7 days lead time. MOQ 200m."
        resp = parse_upstream_response(
            raw_message=raw,
            inquiry_id="UPQ-EVTEST01",
            project_id=PROJECT_ID,
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            dependency_id="DEP-FABEV01",
            dependency_type="fabric",
        )
        options = generate_upstream_options(
            project_id=PROJECT_ID,
            dependency_id="DEP-FABEV01",
            dependency_type="fabric",
            responses=[resp],
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        assert len(options) >= 1
        opt = options[0]
        assert opt.dispatch_lead_time_days == 7

    def test_generate_options_populates_evidence_refs(self):
        raw = "Yes can supply. USD 2.50/m. 7 days lead time. MOQ 200m."
        resp = parse_upstream_response(
            raw_message=raw,
            inquiry_id="UPQ-EVTEST02",
            project_id=PROJECT_ID,
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            dependency_id="DEP-FABEV02",
            dependency_type="fabric",
        )
        options = generate_upstream_options(
            project_id=PROJECT_ID,
            dependency_id="DEP-FABEV02",
            dependency_type="fabric",
            responses=[resp],
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        assert len(options) >= 1
        opt = options[0]
        assert isinstance(opt.evidence_refs, list)
        assert len(opt.evidence_refs) > 0

    def test_unknown_lead_time_creates_risk_flag(self):
        raw = "Yes can supply. USD 2.50/m. MOQ 200m."  # no lead time stated
        resp = parse_upstream_response(
            raw_message=raw,
            inquiry_id="UPQ-EVTEST03",
            project_id=PROJECT_ID,
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            dependency_id="DEP-FABEV03",
            dependency_type="fabric",
        )
        options = generate_upstream_options(
            project_id=PROJECT_ID,
            dependency_id="DEP-FABEV03",
            dependency_type="fabric",
            responses=[resp],
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        assert len(options) >= 1
        opt = options[0]
        assert "lead_time_not_confirmed" in opt.lead_time_risk_flags
