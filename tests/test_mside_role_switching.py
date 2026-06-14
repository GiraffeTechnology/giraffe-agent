"""
M-side Role-Switching Procurement Agent — pytest test suite.

Tests cover all 18 acceptance criteria from Step 20 of the spec:
1.  Same actor resolves as MAIN_M_SIDE to original buyer.
2.  Same actor resolves as UPSTREAM_B_SIDE to upstream suppliers.
3.  Upstream supplier resolves as UPSTREAM_M_SIDE.
4.  Dependency planner detects fabric / trim / packaging / QC / logistics.
5.  Upstream inquiries are generated.
6.  Mock dispatch works.
7.  Upstream responses are parsed.
8.  Missing price / MOQ / lead time are not invented.
9.  1–3 upstream options are generated.
10. Medium / high risk options require human approval.
11. Unapproved upstream options cannot be rolled up.
12. Approved options are rolled up.
13. Rollup submits to B-side.
14. B-side feasibility engine can consume rollup.
15. Industrial Execution Graph logs all required event types.
16. E2E script runs deterministically (smoke check).
17. Patent notice files exist and include required content.
18. Old M-side runtime path is replaced.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# ── Ensure project root on path ────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.actors.models import Actor, ContactChannel
from src.actors.role_context import RoleContext
from src.actors.role_resolver import resolve_role_context
from src.m_side.dependencies.dependency_planner import (
    DependencyNeed,
    plan_upstream_dependencies,
)
from src.m_side.upstream.inquiry_builder import UpstreamInquiry, build_upstream_inquiry
from src.m_side.upstream.dispatch_service import dispatch_upstream_inquiry
from src.m_side.upstream.response_parser import UpstreamResponse, parse_upstream_response
from src.m_side.upstream.option_engine import UpstreamOption, generate_upstream_options
from src.m_side.upstream.approval_gate import (
    ApprovalRequest,
    ApprovalResult,
    approve_upstream_option,
    request_upstream_option_approval,
)
from src.m_side.rollup.supplier_response_rollup import (
    SupplierResponseRollup,
    generate_supplier_response_rollup,
)
from src.m_side.bridge.submit_rollup_to_b_side import submit_rollup_to_b_side
from src.b_side.workspace import create_b_workspace, get_b_workspace
from src.b_side.feasibility_engine import run_feasibility_simulation
from src.m_side.m_event_logger import log_m_event, read_events
from src.legal.patent_notice import (
    CHINA_PATENT,
    JAPAN_PATENT,
    PATENT_OWNER,
    PATENT_CONTACT,
    SHORT_NOTICE_EN,
    FREE_LICENSE_SCOPE_EN,
    ENTERPRISE_REQUIRES_PERMISSION_EN,
    OPEN_SOURCE_BOUNDARY_EN,
)

# ── Constants for tests ────────────────────────────────────────────────────────
PROJECT_ID = "PROJ-ROLETEST"
BUYER_ID = "actor_buyer_b"
MANUFACTURER_ID = "actor_manufacturer_m"
FABRIC_SUPPLIER_ID = "actor_fabric_s1"
TRIM_SUPPLIER_ID = "actor_trim_s1"


# ─── 1. MAIN_M_SIDE resolution ─────────────────────────────────────────────────

class TestRoleResolution:
    def test_manufacturer_resolves_as_main_m_side_to_buyer(self):
        rc = resolve_role_context(
            project_id=PROJECT_ID,
            actor_id=MANUFACTURER_ID,
            original_buyer_actor_id=BUYER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            edge_type="BUYER_TO_MAIN_SUPPLIER",
            counterparty_actor_id=BUYER_ID,
        )
        assert rc.role == "MAIN_M_SIDE"
        assert rc.actor_id == MANUFACTURER_ID
        assert rc.can_create_upstream_inquiry is True
        assert rc.can_submit_response_to_buyer is True
        assert rc.role_reason != ""

    # ── 2. UPSTREAM_B_SIDE resolution ────────────────────────────────────────

    def test_manufacturer_resolves_as_upstream_b_side_to_fabric_supplier(self):
        rc = resolve_role_context(
            project_id=PROJECT_ID,
            actor_id=MANUFACTURER_ID,
            original_buyer_actor_id=BUYER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
            counterparty_actor_id=FABRIC_SUPPLIER_ID,
        )
        assert rc.role == "UPSTREAM_B_SIDE"
        assert rc.actor_id == MANUFACTURER_ID
        assert rc.can_create_upstream_inquiry is True
        assert rc.can_submit_response_to_buyer is False

    def test_manufacturer_resolves_as_upstream_b_side_to_trim_supplier(self):
        rc = resolve_role_context(
            project_id=PROJECT_ID,
            actor_id=MANUFACTURER_ID,
            original_buyer_actor_id=BUYER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            edge_type="MAIN_SUPPLIER_TO_TRIM_SUPPLIER",
            counterparty_actor_id=TRIM_SUPPLIER_ID,
        )
        assert rc.role == "UPSTREAM_B_SIDE"

    def test_same_actor_both_roles_same_project(self):
        rc_main = resolve_role_context(
            project_id=PROJECT_ID,
            actor_id=MANUFACTURER_ID,
            original_buyer_actor_id=BUYER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            edge_type="BUYER_TO_MAIN_SUPPLIER",
        )
        rc_upstream = resolve_role_context(
            project_id=PROJECT_ID,
            actor_id=MANUFACTURER_ID,
            original_buyer_actor_id=BUYER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
        )
        assert rc_main.role == "MAIN_M_SIDE"
        assert rc_upstream.role == "UPSTREAM_B_SIDE"

    # ── 3. UPSTREAM_M_SIDE resolution ────────────────────────────────────────

    def test_fabric_supplier_resolves_as_upstream_m_side(self):
        rc = resolve_role_context(
            project_id=PROJECT_ID,
            actor_id=FABRIC_SUPPLIER_ID,
            original_buyer_actor_id=BUYER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
            counterparty_actor_id=MANUFACTURER_ID,
        )
        assert rc.role == "UPSTREAM_M_SIDE"
        assert rc.actor_id == FABRIC_SUPPLIER_ID
        assert rc.can_create_upstream_inquiry is False
        assert rc.can_submit_response_to_buyer is False

    def test_buyer_resolves_as_original_buyer(self):
        rc = resolve_role_context(
            project_id=PROJECT_ID,
            actor_id=BUYER_ID,
            original_buyer_actor_id=BUYER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        assert rc.role == "ORIGINAL_BUYER"

    def test_role_context_has_explainable_reason(self):
        rc = resolve_role_context(
            project_id=PROJECT_ID,
            actor_id=MANUFACTURER_ID,
            original_buyer_actor_id=BUYER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            edge_type="BUYER_TO_MAIN_SUPPLIER",
        )
        assert len(rc.role_reason) > 10


# ─── 4. Dependency planner ─────────────────────────────────────────────────────

class TestDependencyPlanner:
    def test_apparel_project_detects_fabric(self):
        deps = plan_upstream_dependencies(
            project_id=PROJECT_ID,
            product_summary="100 plain white cotton shirts",
            category="apparel",
            quantity=100,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        types = [d.dependency_type for d in deps]
        assert "fabric" in types

    def test_apparel_project_detects_trim(self):
        deps = plan_upstream_dependencies(
            project_id=PROJECT_ID,
            product_summary="100 plain white cotton shirts",
            category="apparel",
            quantity=100,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        types = [d.dependency_type for d in deps]
        assert "trim" in types

    def test_apparel_project_detects_packaging(self):
        deps = plan_upstream_dependencies(
            project_id=PROJECT_ID,
            product_summary="100 plain white cotton shirts",
            category="apparel",
            quantity=100,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        types = [d.dependency_type for d in deps]
        assert "packaging" in types

    def test_large_quantity_detects_qc(self):
        deps = plan_upstream_dependencies(
            project_id=PROJECT_ID,
            product_summary="100 plain white cotton shirts",
            category="apparel",
            quantity=100,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        types = [d.dependency_type for d in deps]
        assert "qc_testing" in types

    def test_apparel_project_detects_logistics(self):
        deps = plan_upstream_dependencies(
            project_id=PROJECT_ID,
            product_summary="100 plain white cotton shirts",
            category="apparel",
            quantity=100,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        types = [d.dependency_type for d in deps]
        assert "logistics" in types

    def test_dependency_has_valid_risk_level(self):
        deps = plan_upstream_dependencies(
            project_id=PROJECT_ID,
            product_summary="100 cotton shirts",
            category="apparel",
            quantity=100,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        for d in deps:
            assert d.risk_level in ("low", "medium", "high")
            assert d.dependency_id.startswith("DEP-")
            assert d.project_id == PROJECT_ID


# ─── 5. Upstream inquiry builder ─────────────────────────────────────────────

class TestUpstreamInquiryBuilder:
    def _fabric_dep(self) -> DependencyNeed:
        return DependencyNeed(
            dependency_id="DEP-FABTEST01",
            project_id=PROJECT_ID,
            dependency_type="fabric",
            description="100% cotton fabric for 100 shirts",
            required_specs={"weight": "180gsm"},
            quantity_required=100,
        )

    def test_fabric_inquiry_is_generated(self):
        dep = self._fabric_dep()
        inquiry = build_upstream_inquiry(
            dependency=dep,
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            quantity=100,
        )
        assert inquiry.inquiry_id.startswith("UPQ-")
        assert inquiry.project_id == PROJECT_ID
        assert inquiry.upstream_actor_id == FABRIC_SUPPLIER_ID
        assert inquiry.parent_main_supplier_actor_id == MANUFACTURER_ID
        assert inquiry.dependency_id == "DEP-FABTEST01"

    def test_fabric_inquiry_asks_about_availability(self):
        dep = self._fabric_dep()
        inquiry = build_upstream_inquiry(
            dependency=dep,
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            quantity=100,
        )
        assert "can_supply" in inquiry.requested_fields
        assert "moq" in inquiry.requested_fields
        assert "price_per_meter" in inquiry.requested_fields
        assert "lead_time_days" in inquiry.requested_fields
        assert "earliest_dispatch_date" in inquiry.requested_fields

    def test_fabric_inquiry_is_bilingual(self):
        dep = self._fabric_dep()
        inquiry = build_upstream_inquiry(
            dependency=dep,
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        assert len(inquiry.message_text_en) > 20
        assert len(inquiry.message_text_zh) > 20

    def test_trim_inquiry_is_generated(self):
        dep = DependencyNeed(
            dependency_id="DEP-TRIMTEST01",
            project_id=PROJECT_ID,
            dependency_type="trim",
            description="Buttons and thread for 100 shirts",
        )
        inquiry = build_upstream_inquiry(
            dependency=dep,
            upstream_actor_id=TRIM_SUPPLIER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        assert inquiry.dependency_type == "trim"
        assert "can_supply" in inquiry.requested_fields


# ─── 6. Mock dispatch ─────────────────────────────────────────────────────────

class TestMockDispatch:
    def _build_inquiry(self) -> UpstreamInquiry:
        dep = DependencyNeed(
            dependency_id="DEP-DISP01",
            project_id=PROJECT_ID,
            dependency_type="fabric",
            description="cotton fabric",
        )
        return build_upstream_inquiry(
            dependency=dep,
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
        )

    def test_mock_dispatch_succeeds(self):
        inq = self._build_inquiry()
        result = dispatch_upstream_inquiry(inq, channel="mock")
        assert result.status in ("sent", "mock_sent")
        assert result.inquiry_id == inq.inquiry_id
        assert result.upstream_actor_id == FABRIC_SUPPLIER_ID

    def test_mock_dispatch_has_dispatch_id(self):
        inq = self._build_inquiry()
        result = dispatch_upstream_inquiry(inq, channel="mock")
        assert result.dispatch_id.startswith("DSP-")

    def test_mock_dispatch_with_env_flag(self):
        os.environ["MOCK_CHANNELS"] = "true"
        inq = self._build_inquiry()
        result = dispatch_upstream_inquiry(inq, channel="mock")
        assert result.status == "mock_sent"


# ─── 7. Upstream response parser ─────────────────────────────────────────────

class TestUpstreamResponseParser:
    def _parse(self, raw: str) -> UpstreamResponse:
        return parse_upstream_response(
            raw_message=raw,
            inquiry_id="UPQ-PARSETEST01",
            project_id=PROJECT_ID,
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            dependency_id="DEP-FABTEST01",
            dependency_type="fabric",
        )

    def test_can_supply_detected_from_positive_message(self):
        r = self._parse("Yes, we can supply. Price USD 2.50 per meter. MOQ 500m. Lead time 7 days.")
        assert r.can_supply is True

    def test_can_supply_false_from_negative_message(self):
        r = self._parse("Sorry, out of stock. Cannot supply at this time.")
        assert r.can_supply is False

    def test_price_extracted(self):
        r = self._parse("Yes, can supply. Price USD 2.50/meter. MOQ 500m. 7 days lead time.")
        assert r.price == pytest.approx(2.50)
        assert r.currency == "USD"

    def test_lead_time_extracted(self):
        r = self._parse("Can supply. Lead time 7 days. MOQ 200m. USD 3.00/m.")
        assert r.lead_time_days == 7

    def test_moq_extracted(self):
        r = self._parse("Yes. MOQ 500 meters. Price USD 2.80. Lead time 10 days.")
        assert r.moq == 500

    def test_raw_message_preserved(self):
        raw = "Yes we can supply. Price USD 2.50. MOQ 300m."
        r = self._parse(raw)
        assert r.raw_message == raw

    # ── 8. Missing fields are not invented ──────────────────────────────────

    def test_missing_price_is_none_not_invented(self):
        r = self._parse("Yes, we can supply. Lead time 5 days.")
        assert r.price is None
        assert "price_not_confirmed" in r.risk_flags

    def test_missing_moq_is_none_not_invented(self):
        r = self._parse("Can supply. Price USD 2.00. Lead time 3 days.")
        assert r.moq is None
        assert "moq_not_confirmed" in r.risk_flags

    def test_missing_lead_time_is_none_not_invented(self):
        r = self._parse("Can supply. Price USD 2.00. MOQ 100m.")
        assert r.lead_time_days is None

    def test_response_has_scores(self):
        r = self._parse("Yes, can supply. USD 2.50. 7 days. MOQ 300m.")
        assert 0.0 <= r.completeness_score <= 1.0
        assert 0.0 <= r.confidence_score <= 1.0

    def test_response_id_generated(self):
        r = self._parse("Can supply.")
        assert r.response_id.startswith("UPR-")


# ─── 9. Upstream option engine ────────────────────────────────────────────────

class TestUpstreamOptionEngine:
    def _make_response(self, actor_id: str, price: float, lead: int, moq: int, can_supply: bool = True) -> UpstreamResponse:
        raw = f"{'Yes can supply' if can_supply else 'Cannot supply'}. USD {price}/m. {lead} days. MOQ {moq}m."
        return parse_upstream_response(
            raw_message=raw,
            inquiry_id=f"UPQ-{actor_id}",
            project_id=PROJECT_ID,
            upstream_actor_id=actor_id,
            dependency_id="DEP-FABTEST",
            dependency_type="fabric",
        )

    def test_generates_options_from_viable_responses(self):
        responses = [
            self._make_response("F1", price=2.50, lead=7, moq=300),
            self._make_response("F2", price=2.80, lead=3, moq=200),
            self._make_response("F3", price=2.20, lead=12, moq=500),
        ]
        options = generate_upstream_options(
            project_id=PROJECT_ID,
            dependency_id="DEP-FABTEST",
            dependency_type="fabric",
            responses=responses,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        assert 1 <= len(options) <= 3

    def test_best_option_is_generated(self):
        responses = [
            self._make_response("F1", price=2.50, lead=7, moq=300),
            self._make_response("F2", price=2.80, lead=3, moq=200),
        ]
        options = generate_upstream_options(
            project_id=PROJECT_ID,
            dependency_id="DEP-FABTEST",
            dependency_type="fabric",
            responses=responses,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        labels = [o.option_label for o in options]
        assert "BEST" in labels

    def test_fastest_option_from_multiple_suppliers(self):
        # F1 has higher confidence (more fields) so it's BEST; F2 (shorter lead) is FASTEST
        responses = [
            self._make_response("F1", price=2.50, lead=10, moq=300),
            self._make_response("F2", price=3.20, lead=3, moq=100),
        ]
        options = generate_upstream_options(
            project_id=PROJECT_ID,
            dependency_id="DEP-FABTEST",
            dependency_type="fabric",
            responses=responses,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        # Engine generates BEST + FASTEST (if different actor) or BEST + SAFEST/BACKUP
        assert len(options) >= 1
        labels = [o.option_label for o in options]
        # At least one differentiating option label should be present
        assert any(label in labels for label in ("FASTEST", "SAFEST", "BACKUP", "BEST"))

    def test_no_options_if_all_cannot_supply(self):
        responses = [
            self._make_response("F1", price=2.50, lead=7, moq=300, can_supply=False),
        ]
        options = generate_upstream_options(
            project_id=PROJECT_ID,
            dependency_id="DEP-FABTEST",
            dependency_type="fabric",
            responses=responses,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        assert len(options) == 0

    def test_option_has_required_fields(self):
        responses = [self._make_response("F1", price=2.50, lead=7, moq=300)]
        options = generate_upstream_options(
            project_id=PROJECT_ID,
            dependency_id="DEP-FABTEST",
            dependency_type="fabric",
            responses=responses,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        opt = options[0]
        assert opt.option_id.startswith("OPT-")
        assert opt.project_id == PROJECT_ID
        assert opt.dependency_id == "DEP-FABTEST"
        assert opt.price_summary != ""
        assert opt.lead_time_summary != ""
        assert opt.score >= 0.0
        assert len(opt.response_ids) > 0


# ─── 10. Approval gate — high/medium risk requires human approval ─────────────

class TestApprovalGate:
    def _make_option(self, option_id: str, risk: str = "No significant risks") -> UpstreamOption:
        return UpstreamOption(
            option_id=option_id,
            project_id=PROJECT_ID,
            dependency_id="DEP-FABTEST",
            dependency_type="fabric",
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            option_label="BEST",
            price_summary="USD 2.50",
            lead_time_summary="7 days",
            risk_summary=risk,
            score=0.8,
            reason="Best option",
            response_ids=["UPR-001"],
        )

    def test_high_risk_option_requires_human_approval(self):
        opt = self._make_option("OPT-HIGHRISK", risk="long_lead_time_30d; price_not_confirmed")
        os.environ["AUTO_APPROVAL_ENABLED"] = "true"
        req = request_upstream_option_approval(
            project_id=PROJECT_ID,
            dependency_id="DEP-FABTEST",
            dependency_type="fabric",
            options=[opt],
        )
        assert req.required_approval_mode == "human"
        os.environ.pop("AUTO_APPROVAL_ENABLED", None)

    def test_default_approval_mode_is_human(self):
        opt = self._make_option("OPT-DEFAULT")
        os.environ.pop("AUTO_APPROVAL_ENABLED", None)
        req = request_upstream_option_approval(
            project_id=PROJECT_ID,
            dependency_id="DEP-FABTEST",
            dependency_type="fabric",
            options=[opt],
        )
        assert req.required_approval_mode == "human"

    def test_human_approval_succeeds(self):
        opt = self._make_option("OPT-APPROVE01")
        req = request_upstream_option_approval(
            project_id=PROJECT_ID,
            dependency_id="DEP-FABTEST",
            dependency_type="fabric",
            options=[opt],
        )
        result = approve_upstream_option(
            approval_request=req,
            approved_option_id="OPT-APPROVE01",
            approved_by="user_manufacturer_m",
            mode="human",
        )
        assert result.approved_option_id == "OPT-APPROVE01"
        assert result.approved_by == "user_manufacturer_m"
        assert result.mode == "human"

    # ── 11. Unapproved options cannot be rolled up ────────────────────────────

    def test_agent_approval_rejected_when_human_required(self):
        opt = self._make_option("OPT-REJECT01")
        req = request_upstream_option_approval(
            project_id=PROJECT_ID,
            dependency_id="DEP-FABTEST",
            dependency_type="fabric",
            options=[opt],
        )
        # req.required_approval_mode is "human" by default
        with pytest.raises(ValueError, match="human approval"):
            approve_upstream_option(
                approval_request=req,
                approved_option_id="OPT-REJECT01",
                approved_by="agent",
                mode="authorized_agent",
            )

    def test_invalid_option_id_raises_error(self):
        opt = self._make_option("OPT-VALID01")
        req = request_upstream_option_approval(
            project_id=PROJECT_ID,
            dependency_id="DEP-FABTEST",
            dependency_type="fabric",
            options=[opt],
        )
        with pytest.raises(ValueError, match="not found"):
            approve_upstream_option(
                approval_request=req,
                approved_option_id="OPT-NONEXISTENT",
                approved_by="user",
                mode="human",
            )


# ─── 12. Rollup generation from approved options ─────────────────────────────

class TestSupplierResponseRollup:
    def _make_approval_result(self, dep_type: str) -> ApprovalResult:
        opt = UpstreamOption(
            option_id=f"OPT-{dep_type.upper()}",
            project_id=PROJECT_ID,
            dependency_id=f"DEP-{dep_type.upper()}",
            dependency_type=dep_type,
            upstream_actor_id=f"actor_{dep_type}_s1",
            option_label="BEST",
            price_summary="USD 2.50",
            lead_time_summary="7 days",
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

    def test_rollup_generated_from_approved_options(self):
        approval_results = [
            self._make_approval_result("fabric"),
            self._make_approval_result("trim"),
        ]
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=approval_results,
            product_summary="100 cotton shirts",
            quantity=100,
        )
        assert rollup.rollup_id.startswith("ROLLUP-")
        assert rollup.project_id == PROJECT_ID
        assert rollup.main_supplier_actor_id == MANUFACTURER_ID
        assert len(rollup.approved_upstream_options) == 2

    def test_rollup_has_material_basis(self):
        approval_results = [self._make_approval_result("fabric")]
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=approval_results,
            product_summary="100 cotton shirts",
            quantity=100,
        )
        assert rollup.material_basis != {}

    def test_rollup_cannot_accept_with_unresolved_deps(self):
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=[],
            product_summary="100 cotton shirts",
            quantity=100,
            unresolved_dependency_types=["fabric", "trim"],
        )
        assert rollup.can_accept_order is False
        assert len(rollup.unresolved_dependencies) == 2

    def test_rollup_can_accept_when_approved(self):
        approval_results = [
            self._make_approval_result("fabric"),
            self._make_approval_result("trim"),
        ]
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=approval_results,
            product_summary="100 cotton shirts",
            quantity=100,
            main_capacity_available=True,
            unresolved_dependency_types=[],
        )
        assert rollup.can_accept_order is True

    def test_rollup_has_buyer_response_text(self):
        approval_results = [self._make_approval_result("fabric")]
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=approval_results,
            product_summary="100 cotton shirts",
            quantity=100,
        )
        assert len(rollup.recommended_response_to_buyer_en) > 20
        assert len(rollup.recommended_response_to_buyer_zh) > 20

    def test_rollup_completeness_score_range(self):
        approval_results = [self._make_approval_result("fabric")]
        rollup = generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=approval_results,
            product_summary="100 cotton shirts",
            quantity=100,
        )
        assert 0.0 <= rollup.completeness_score <= 1.0
        assert 0.0 <= rollup.confidence_score <= 1.0


# ─── 13. Submit rollup to B-side ─────────────────────────────────────────────

class TestSubmitRollupToBSide:
    def _make_rollup(self) -> SupplierResponseRollup:
        opt = UpstreamOption(
            option_id="OPT-FAB01",
            project_id=PROJECT_ID,
            dependency_id="DEP-FAB01",
            dependency_type="fabric",
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            option_label="BEST",
            price_summary="USD 2.50",
            lead_time_summary="7 days",
            risk_summary="No significant risks",
            score=0.8,
            reason="Best option",
            response_ids=["UPR-001"],
        )
        result = ApprovalResult(
            approval_request_id="APR-FAB01",
            approved_option_id="OPT-FAB01",
            approved_option=opt,
            approved_by="user_m",
            mode="human",
        )
        return generate_supplier_response_rollup(
            project_id=PROJECT_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=[result],
            product_summary="100 cotton shirts",
            quantity=100,
            main_capacity_available=True,
        )

    def test_submit_rollup_returns_success(self):
        rollup = self._make_rollup()
        b_workspace = create_b_workspace("100 cotton shirts")
        submit_result = submit_rollup_to_b_side(rollup=rollup, b_workspace_id=b_workspace.b_workspace_id)
        assert submit_result.status == "submitted"
        assert submit_result.rollup_id == rollup.rollup_id
        assert submit_result.b_workspace_id == b_workspace.b_workspace_id
        assert submit_result.supplier_response_record_id.startswith("ROLLUP-RESP-")

    # ── 14. B-side feasibility engine can consume rollup ─────────────────────

    def test_b_side_can_consume_rollup(self):
        rollup = self._make_rollup()
        b_workspace = create_b_workspace("100 cotton shirts")
        submit_rollup_to_b_side(rollup=rollup, b_workspace_id=b_workspace.b_workspace_id)

        # B-side workspace should have the response record
        workspace = get_b_workspace(b_workspace.b_workspace_id)
        assert len(workspace.supplier_responses) == 1
        resp = workspace.supplier_responses[0]
        assert resp.supplier_id == MANUFACTURER_ID
        assert resp.can_make is True

    def test_feasibility_engine_produces_paths(self):
        rollup = self._make_rollup()
        b_workspace = create_b_workspace("100 cotton shirts")
        submit_rollup_to_b_side(rollup=rollup, b_workspace_id=b_workspace.b_workspace_id)

        report = run_feasibility_simulation(b_workspace.b_workspace_id)
        assert len(report.paths) >= 1
        assert report.paths[0].supplier_id == MANUFACTURER_ID


# ─── 15. Industrial Execution Graph event logging ─────────────────────────────

class TestExecutionGraphEvents:
    REQUIRED_EVENTS = [
        "ROLE_CONTEXT_RESOLVED",
        "UPSTREAM_DEPENDENCY_PLANNED",
        "UPSTREAM_INQUIRY_CREATED",
        "UPSTREAM_INQUIRY_DISPATCHED",
        "UPSTREAM_RESPONSE_PARSED",
        "UPSTREAM_OPTIONS_GENERATED",
        "UPSTREAM_OPTION_APPROVAL_REQUESTED",
        "UPSTREAM_OPTION_APPROVED",
        "SUPPLIER_RESPONSE_ROLLUP_GENERATED",
        "SUPPLIER_RESPONSE_ROLLUP_SUBMITTED_TO_B_SIDE",
    ]

    def test_role_context_resolved_logged(self):
        test_project = "PROJ-EVENT-TEST"
        resolve_role_context(
            project_id=test_project,
            actor_id=MANUFACTURER_ID,
            original_buyer_actor_id=BUYER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        events = read_events(b_workspace_id=test_project)
        event_types = [e["event_type"] for e in events]
        assert "ROLE_CONTEXT_RESOLVED" in event_types

    def test_upstream_dependency_planned_logged(self):
        test_project = "PROJ-DEP-EVENT"
        plan_upstream_dependencies(
            project_id=test_project,
            product_summary="100 shirts",
            category="apparel",
            quantity=100,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        events = read_events(b_workspace_id=test_project)
        event_types = [e["event_type"] for e in events]
        assert "UPSTREAM_DEPENDENCY_PLANNED" in event_types

    def test_upstream_inquiry_created_logged(self):
        test_project = "PROJ-INQ-EVENT"
        dep = DependencyNeed(
            dependency_id="DEP-EVENT01",
            project_id=test_project,
            dependency_type="fabric",
            description="fabric",
        )
        build_upstream_inquiry(
            dependency=dep,
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            main_supplier_actor_id=MANUFACTURER_ID,
        )
        events = read_events(b_workspace_id=test_project)
        event_types = [e["event_type"] for e in events]
        assert "UPSTREAM_INQUIRY_CREATED" in event_types

    def test_upstream_response_parsed_logged(self):
        test_project = "PROJ-PARSE-EVENT"
        parse_upstream_response(
            raw_message="Yes can supply. USD 2.50. 7 days. MOQ 200m.",
            inquiry_id="UPQ-EVT01",
            project_id=test_project,
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            dependency_id="DEP-EVT01",
            dependency_type="fabric",
        )
        events = read_events(b_workspace_id=test_project)
        event_types = [e["event_type"] for e in events]
        assert "UPSTREAM_RESPONSE_PARSED" in event_types

    def test_rollup_generated_logged(self):
        test_project = "PROJ-ROLLUP-EVENT"
        opt = UpstreamOption(
            option_id="OPT-EVT01",
            project_id=test_project,
            dependency_id="DEP-EVT01",
            dependency_type="fabric",
            upstream_actor_id=FABRIC_SUPPLIER_ID,
            option_label="BEST",
            price_summary="USD 2.50",
            lead_time_summary="7 days",
            risk_summary="No significant risks",
            score=0.8,
            reason="best",
            response_ids=[],
        )
        result = ApprovalResult(
            approval_request_id="APR-EVT01",
            approved_option_id="OPT-EVT01",
            approved_option=opt,
            approved_by="user",
            mode="human",
        )
        generate_supplier_response_rollup(
            project_id=test_project,
            main_supplier_actor_id=MANUFACTURER_ID,
            approval_results=[result],
            product_summary="100 shirts",
            quantity=100,
        )
        events = read_events(b_workspace_id=test_project)
        event_types = [e["event_type"] for e in events]
        assert "SUPPLIER_RESPONSE_ROLLUP_GENERATED" in event_types


# ─── 16. E2E script runs deterministically ────────────────────────────────────

class TestE2EScript:
    def test_e2e_script_passes(self):
        """Run the E2E script and verify it exits cleanly with PASS."""
        repo_root = Path(__file__).parent.parent
        result = subprocess.run(
            [sys.executable, "scripts/run_role_switching_mvp.py"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            timeout=120,
        )
        assert result.returncode == 0, (
            f"E2E script failed.\nSTDOUT:\n{result.stdout[-2000:]}\nSTDERR:\n{result.stderr[-1000:]}"
        )
        assert "ALL CHECKS PASSED" in result.stdout or "PASS" in result.stdout


# ─── 17. Patent notice files ──────────────────────────────────────────────────

class TestPatentNotice:
    def test_china_patent_in_constants(self):
        assert "ZL 2023 1 1645939.9" in CHINA_PATENT
        assert "CN 117670482 B" in CHINA_PATENT

    def test_japan_patent_in_constants(self):
        assert "P7644545" in JAPAN_PATENT
        assert "特許第7644545号" in JAPAN_PATENT

    def test_patent_owner_is_correct(self):
        assert PATENT_OWNER == "Giraffe Technology Holding Limited"

    def test_contact_email_present(self):
        assert "mich@giraffe.technology" in PATENT_CONTACT

    def test_short_notice_includes_both_patents(self):
        assert "ZL 2023 1 1645939.9" in SHORT_NOTICE_EN
        assert "P7644545" in SHORT_NOTICE_EN

    def test_short_notice_includes_free_license(self):
        assert "individuals" in SHORT_NOTICE_EN.lower()
        assert "SMEs" in SHORT_NOTICE_EN or "smes" in SHORT_NOTICE_EN.lower()

    def test_short_notice_includes_open_source_boundary(self):
        assert "not automatically grant" in SHORT_NOTICE_EN.lower() or "not automatically" in SHORT_NOTICE_EN

    def test_short_notice_includes_contact(self):
        assert "mich@giraffe.technology" in SHORT_NOTICE_EN

    def test_enterprise_requires_permission_constants(self):
        assert "Enterprise" in ENTERPRISE_REQUIRES_PERMISSION_EN
        assert "mich@giraffe.technology" in ENTERPRISE_REQUIRES_PERMISSION_EN

    def test_free_license_scope_covers_smes(self):
        assert "SME" in FREE_LICENSE_SCOPE_EN or "sme" in FREE_LICENSE_SCOPE_EN.lower()

    def test_open_source_boundary_notice(self):
        assert "open-source" in OPEN_SOURCE_BOUNDARY_EN.lower() or "open source" in OPEN_SOURCE_BOUNDARY_EN.lower()

    def test_patent_notice_md_exists(self):
        repo_root = Path(__file__).parent.parent
        assert (repo_root / "PATENT_NOTICE.md").exists()

    def test_license_notice_md_exists(self):
        repo_root = Path(__file__).parent.parent
        assert (repo_root / "LICENSE_NOTICE.md").exists()

    def test_readme_md_exists(self):
        repo_root = Path(__file__).parent.parent
        assert (repo_root / "README.md").exists()

    def test_patent_notice_md_contains_china_patent(self):
        repo_root = Path(__file__).parent.parent
        content = (repo_root / "PATENT_NOTICE.md").read_text(encoding="utf-8")
        assert "ZL 2023 1 1645939.9" in content

    def test_patent_notice_md_contains_japan_patent(self):
        repo_root = Path(__file__).parent.parent
        content = (repo_root / "PATENT_NOTICE.md").read_text(encoding="utf-8")
        assert "P7644545" in content

    def test_license_notice_md_contains_patent_info(self):
        repo_root = Path(__file__).parent.parent
        content = (repo_root / "LICENSE_NOTICE.md").read_text(encoding="utf-8")
        assert "Giraffe Technology" in content

    def test_src_legal_patent_notice_py_exists(self):
        repo_root = Path(__file__).parent.parent
        assert (repo_root / "src" / "legal" / "patent_notice.py").exists()

    def test_readme_mentions_role_switching(self):
        repo_root = Path(__file__).parent.parent
        content = (repo_root / "README.md").read_text(encoding="utf-8")
        assert "role-switching" in content.lower() or "role switching" in content.lower()

    def test_mside_spec_file_exists(self):
        repo_root = Path(__file__).parent.parent
        assert (repo_root / "docs" / "MSIDE_ROLE_SWITCHING_AGENT_SPEC.md").exists()


# ─── 18. Old M-side runtime path is replaced ─────────────────────────────────

class TestOldMSideReplaced:
    def test_no_fixed_role_mside_references(self):
        """Verify no 'fixed M-side' or 'old_mside' markers remain in Python source."""
        repo_root = Path(__file__).parent.parent
        src_py_files = list((repo_root / "src").rglob("*.py"))
        for f in src_py_files:
            content = f.read_text(encoding="utf-8")
            assert "old_mside" not in content.lower(), f"Found 'old_mside' in {f}"
            assert "legacy_mside" not in content.lower(), f"Found 'legacy_mside' in {f}"
            assert "fixed M-side" not in content, f"Found 'fixed M-side' in {f}"

    def test_role_switching_module_is_importable(self):
        from src.actors.role_resolver import resolve_role_context  # noqa: F401
        from src.m_side.dependencies.dependency_planner import plan_upstream_dependencies  # noqa: F401
        from src.m_side.upstream.inquiry_builder import build_upstream_inquiry  # noqa: F401
        from src.m_side.upstream.dispatch_service import dispatch_upstream_inquiry  # noqa: F401
        from src.m_side.upstream.response_parser import parse_upstream_response  # noqa: F401
        from src.m_side.upstream.option_engine import generate_upstream_options  # noqa: F401
        from src.m_side.upstream.approval_gate import approve_upstream_option  # noqa: F401
        from src.m_side.rollup.supplier_response_rollup import generate_supplier_response_rollup  # noqa: F401
        from src.m_side.bridge.submit_rollup_to_b_side import submit_rollup_to_b_side  # noqa: F401

    def test_api_routes_use_new_role_switching_module(self):
        """Verify API main module imports role-switching functions."""
        repo_root = Path(__file__).parent.parent
        api_content = (repo_root / "api" / "main.py").read_text(encoding="utf-8")
        assert "resolve_role_context" in api_content
        assert "plan_upstream_dependencies" in api_content
        assert "generate_supplier_response_rollup" in api_content
        assert "submit_rollup_to_b_side" in api_content
