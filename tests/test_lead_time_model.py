"""
Tests for the canonical Lead Time Path Model — models, calculator, evidence.

Covers:
1. LeadTimeComponent and LeadTimePath model creation
2. ProductionCapacity defaults
3. calculate_lead_time_path — basic calculation
4. Parallel material logic (max, not sum)
5. Sequential post-production logic (sum)
6. Risk buffer from flags
7. Supplier-stated total vs calculated consistency
8. Deadline feasibility check
9. Evidence refs populated
10. Missing fields create risk flags, not 999
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lead_time.models import LeadTimeComponent, LeadTimePath, ProductionCapacity, LeadTimeScenario
from src.lead_time.lead_time_calculator import calculate_lead_time_path
from src.lead_time.evidence import (
    make_evidence_ref,
    validate_component_has_evidence,
    EVIDENCE_TYPE_SUPPLIER_STATED,
    EVIDENCE_TYPE_AI_CALCULATED,
    EVIDENCE_TYPE_DEFAULT_ASSUMPTION,
)


PROJECT_ID = "PROJ-LTTEST"
SUPPLIER_ID = "actor_supplier_1"
SUPPLIER_NAME = "Test Supplier"
RESP_ID = "RESP-001"


class TestLeadTimeModels:
    def test_lead_time_component_creation(self):
        comp = LeadTimeComponent(
            component_id="COMP-001",
            component_type="material",
            duration_days=5.0,
            evidence_type="supplier_stated",
        )
        assert comp.component_id == "COMP-001"
        assert comp.component_type == "material"
        assert comp.duration_days == 5.0
        assert comp.can_parallelize is False

    def test_lead_time_component_parallel_flag(self):
        comp = LeadTimeComponent(
            component_id="COMP-002",
            component_type="trim",
            duration_days=3.0,
            can_parallelize=True,
            evidence_type="supplier_stated",
        )
        assert comp.can_parallelize is True

    def test_production_capacity_defaults(self):
        cap = ProductionCapacity(actor_id="actor_m")
        assert cap.daily_capacity_units == 50.0
        assert cap.setup_days == 1.0
        assert cap.queue_days == 0.0
        assert cap.working_days_per_week == 5
        assert cap.minimum_batch_size == 1
        assert cap.confidence_score == 0.5

    def test_lead_time_path_creation(self):
        path = LeadTimePath(
            path_id="LTP-001",
            project_id=PROJECT_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
        )
        assert path.path_id == "LTP-001"
        assert path.rank == 0
        assert path.label is None
        assert path.feasible_before_deadline is True

    def test_lead_time_scenario_creation(self):
        scenario = LeadTimeScenario(
            scenario_id="SCEN-001",
            project_id=PROJECT_ID,
        )
        assert scenario.scenario_id == "SCEN-001"
        assert scenario.selected_supplier_id is None
        assert scenario.result_path is None


class TestEvidenceUtils:
    def test_make_evidence_ref_basic(self):
        ref = make_evidence_ref(EVIDENCE_TYPE_SUPPLIER_STATED, "src-001", "fabric:5d")
        assert "type:supplier_stated" in ref
        assert "src:src-001" in ref
        assert "note:fabric:5d" in ref

    def test_make_evidence_ref_no_source(self):
        ref = make_evidence_ref(EVIDENCE_TYPE_DEFAULT_ASSUMPTION)
        assert "type:default_assumption" in ref
        assert "src:" not in ref

    def test_validate_component_missing_evidence_type(self):
        warnings = validate_component_has_evidence("COMP-001", None, "some-ref")
        assert any("missing evidence_type" in w for w in warnings)

    def test_validate_component_missing_evidence_ref(self):
        warnings = validate_component_has_evidence("COMP-001", "supplier_stated", None)
        assert any("missing evidence_ref" in w for w in warnings)

    def test_validate_component_no_warnings_when_complete(self):
        warnings = validate_component_has_evidence("COMP-001", "supplier_stated", "type:supplier_stated|src:x")
        assert len(warnings) == 0


class TestLeadTimeCalculatorBasic:
    def test_basic_calculation_returns_path(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            quantity=100,
            fabric_days=5,
            qc_days=2,
            packaging_days=1,
            logistics_days=3,
        )
        assert path.path_id.startswith("LTP-")
        assert path.project_id == PROJECT_ID
        assert path.supplier_id == SUPPLIER_ID

    def test_total_lead_time_is_positive(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            quantity=100,
            fabric_days=5,
            logistics_days=7,
        )
        assert path.total_lead_time_days > 0

    def test_no_sentinel_999_in_output(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
        )
        assert path.total_lead_time_days != 999
        assert path.total_lead_time_days > 0

    def test_components_are_generated(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            fabric_days=5,
            qc_days=2,
            logistics_days=3,
        )
        assert len(path.components) > 0

    def test_evidence_refs_populated(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            fabric_days=5,
        )
        assert len(path.evidence_refs) > 0


class TestParallelMaterialLogic:
    """Material components run in PARALLEL — use max(), not sum()."""

    def test_fabric_and_trim_parallel_uses_max(self):
        """With fabric=5d and trim=3d, material_ready should be max(5, 3) = 5."""
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            quantity=100,
            fabric_days=5,
            trim_days=3,
            qc_days=2,
            packaging_days=1,
            logistics_days=3,
        )
        assert path.material_ready_days == 5.0, (
            f"material_ready should be max(5,3)=5, got {path.material_ready_days}"
        )

    def test_fabric_dominant_over_trim(self):
        """Fabric 10d > trim 3d → material_ready = 10."""
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            quantity=100,
            fabric_days=10,
            trim_days=3,
        )
        assert path.material_ready_days == 10.0

    def test_trim_dominant_over_fabric(self):
        """Trim 8d > fabric 3d → material_ready = 8."""
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            quantity=100,
            fabric_days=3,
            trim_days=8,
        )
        assert path.material_ready_days == 8.0

    def test_packaging_material_included_in_parallel(self):
        """Packaging material (1d) doesn't dominate fabric (5d): material_ready=5."""
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            quantity=100,
            fabric_days=5,
            packaging_material_days=1,
        )
        assert path.material_ready_days == 5.0


class TestSequentialPostProductionLogic:
    """QC, packaging, logistics run SEQUENTIALLY — use sum()."""

    def test_post_production_is_sum_of_qc_packaging_logistics(self):
        """QC=2, packaging=1, logistics=3 → post_production = 6."""
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            qc_days=2,
            packaging_days=1,
            logistics_days=3,
        )
        assert path.post_production_days == 6.0, (
            f"post_production should be 2+1+3=6, got {path.post_production_days}"
        )

    def test_total_is_material_plus_production_plus_post(self):
        """Sanity: total = material_ready + production + post_production + buffer."""
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            quantity=100,
            fabric_days=5,
            trim_days=3,
            qc_days=2,
            packaging_days=1,
            logistics_days=3,
            confidence_score=0.9,  # high confidence → minimal buffer
        )
        # material_ready = max(5, 3) = 5
        # production = ceil(100/50) + 1 setup = 2 + 1 = 3
        # post = 2 + 1 + 3 = 6
        # buffer = 0 (high confidence, no risk flags)
        # total = 5 + 3 + 6 = 14
        assert path.material_ready_days == 5.0
        assert path.production_days == 3.0
        assert path.post_production_days == 6.0
        assert path.total_lead_time_days == 14


class TestRiskBuffer:
    def test_substitute_material_adds_buffer(self):
        path_no_sub = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            fabric_days=5,
            confidence_score=0.85,
        )
        path_with_sub = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            fabric_days=5,
            confidence_score=0.85,
            risk_flags=["substitute_material"],
        )
        assert path_with_sub.risk_buffer_days >= 2.0
        assert path_with_sub.total_lead_time_days > path_no_sub.total_lead_time_days

    def test_low_confidence_adds_buffer(self):
        path_low_conf = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            fabric_days=5,
            confidence_score=0.3,  # very low
        )
        assert path_low_conf.risk_buffer_days >= 3.0

    def test_high_confidence_no_buffer(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            fabric_days=5,
            confidence_score=0.9,
            risk_flags=[],
        )
        assert path.risk_buffer_days == 0.0

    def test_missing_lead_time_field_adds_buffer(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            missing_fields=["lead_time_days"],
            confidence_score=0.8,
        )
        assert path.risk_buffer_days >= 3.0


class TestMissingFieldsBehavior:
    """Missing fields must create risk_flags, never sentinel 999 values."""

    def test_no_fabric_days_adds_risk_flag(self):
        # No fabric_days, no trim_days → material unknown
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
        )
        assert "material_lead_time_unknown" in path.risk_flags

    def test_no_logistics_adds_default_not_999(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            # no logistics_days specified
        )
        assert path.total_lead_time_days != 999
        assert path.post_production_days > 0  # uses default

    def test_risk_flags_list_populated_from_missing(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            missing_fields=["lead_time_days", "price"],
            confidence_score=0.5,
        )
        # Should have risk_flags, not crash
        assert isinstance(path.risk_flags, list)


class TestDeadlineFeasibility:
    def test_feasible_when_within_deadline(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            quantity=100,
            fabric_days=5,
            qc_days=2,
            packaging_days=1,
            logistics_days=3,
            buyer_deadline_days=60,
            confidence_score=0.9,
        )
        assert path.feasible_before_deadline is True
        assert path.slack_days is not None
        assert path.slack_days >= 0

    def test_infeasible_when_exceeds_deadline(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            quantity=100,
            fabric_days=20,
            qc_days=5,
            packaging_days=3,
            logistics_days=15,
            buyer_deadline_days=5,  # impossible
            confidence_score=0.9,
        )
        assert path.feasible_before_deadline is False
        assert path.slack_days is not None
        assert path.slack_days < 0
        assert any("deadline_infeasible" in f for f in path.risk_flags)

    def test_no_deadline_no_feasibility_check(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            buyer_deadline_days=None,
        )
        assert path.deadline_days is None
        assert path.slack_days is None
        assert path.feasible_before_deadline is True  # default


class TestSupplierStatedConsistency:
    def test_consistent_supplier_stated_boosts_confidence(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            quantity=100,
            fabric_days=5,
            qc_days=2,
            packaging_days=1,
            logistics_days=3,
            confidence_score=0.7,
            supplier_stated_total_days=14,  # close to calculated 14
        )
        assert path.lead_time_consistency_note is not None
        assert "consistent" in path.lead_time_consistency_note.lower()

    def test_inconsistent_supplier_stated_adds_risk_flag(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            quantity=100,
            fabric_days=5,
            qc_days=2,
            packaging_days=1,
            logistics_days=3,
            supplier_stated_total_days=5,  # way off from calculated ~14
        )
        assert "supplier_stated_lead_time_inconsistent" in path.risk_flags

    def test_supplier_stated_preserved_in_path(self):
        path = calculate_lead_time_path(
            supplier_response_id=RESP_ID,
            supplier_id=SUPPLIER_ID,
            supplier_name=SUPPLIER_NAME,
            project_id=PROJECT_ID,
            supplier_stated_total_days=20,
        )
        assert path.supplier_stated_lead_time_days == 20


class TestDemoFixtureExpectedValues:
    """Verify the demo fixture expected values match the calculator."""

    def _make_capacity(self) -> ProductionCapacity:
        return ProductionCapacity(
            actor_id="actor_manufacturer_m",
            daily_capacity_units=50.0,
            setup_days=1.0,
            queue_days=0.0,
            confidence_score=0.85,
        )

    def test_fastest_path_12_days(self):
        """FASTEST path (Fabric B, 2d): material=max(2,3,1)=3, prod=3, post=6, buffer=0 → 12."""
        cap = self._make_capacity()
        path = calculate_lead_time_path(
            supplier_response_id="RESP-FAST",
            supplier_id="actor_fabric_supplier_2",
            supplier_name="Fabric Supplier B (Fast)",
            project_id=PROJECT_ID,
            quantity=100,
            fabric_days=2,
            trim_days=3,
            packaging_material_days=1,
            qc_days=2,
            packaging_days=1,
            logistics_days=3,
            production_capacity=cap,
            confidence_score=0.85,
            risk_flags=[],
        )
        assert path.material_ready_days == 3.0
        assert path.production_days == 3.0
        assert path.post_production_days == 6.0
        assert path.risk_buffer_days == 0.0
        assert path.total_lead_time_days == 12

    def test_best_overall_path_14_days(self):
        """BEST_OVERALL (Fabric A, 5d): material=max(5,3,1)=5, prod=3, post=6, buffer=0 → 14."""
        cap = self._make_capacity()
        path = calculate_lead_time_path(
            supplier_response_id="RESP-BEST",
            supplier_id="actor_fabric_supplier_1",
            supplier_name="Fabric Supplier A (Premium)",
            project_id=PROJECT_ID,
            quantity=100,
            fabric_days=5,
            trim_days=3,
            packaging_material_days=1,
            qc_days=2,
            packaging_days=1,
            logistics_days=3,
            production_capacity=cap,
            confidence_score=0.9,
            risk_flags=[],
        )
        assert path.material_ready_days == 5.0
        assert path.total_lead_time_days == 14

    def test_lowest_cost_path_15_days_with_buffer(self):
        """LOWEST_COST (Fabric C, substitute): material=max(3,3,1)=3, prod=3, post=6,
        buffer=2.5 (substitute_material=2.0 + confidence<0.75=0.5) → ceil(14.5)=15."""
        cap = self._make_capacity()
        path = calculate_lead_time_path(
            supplier_response_id="RESP-LOWEST",
            supplier_id="actor_fabric_supplier_3",
            supplier_name="Fabric Supplier C (Substitute)",
            project_id=PROJECT_ID,
            quantity=100,
            fabric_days=3,
            trim_days=3,
            packaging_material_days=1,
            qc_days=2,
            packaging_days=1,
            logistics_days=3,
            production_capacity=cap,
            confidence_score=0.7,
            risk_flags=["substitute_material"],
        )
        assert path.material_ready_days == 3.0
        assert path.risk_buffer_days == 2.5  # substitute(2.0) + confidence<0.75(0.5)
        assert path.total_lead_time_days == 15  # ceil(3+3+6+2.5) = ceil(14.5) = 15
