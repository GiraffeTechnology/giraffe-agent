"""
Regression Tests — Lead Time Model (AIVAN Product Rules, Feasibility Engine).

Verifies that the lead time model:
  - Flags unrealistic lead times rather than accepting them blindly
  - Degrades gracefully on missing data (no 999 sentinel, no hallucination)
  - Does not auto-rank critical-risk suppliers over safe ones purely on speed
  - Deadline feasibility check remains consistent
  - Capacity constraints reduce feasibility
  - Parallel material logic (max) and sequential post-production (sum) are correct
  - Supplier-stated total is verified, not trusted blindly
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lead_time.models import LeadTimePath, ProductionCapacity
from src.lead_time.lead_time_calculator import calculate_lead_time_path

PROJECT_ID = "PROJ-LT-REGRESS"
SUPPLIER_ID = "sup_regress_lt"
SUPPLIER_NAME = "Regression Lead Time Supplier"
RESP_ID = "RESP-LT-001"


# ─── Regression: no 999 sentinel values ──────────────────────────────────────

def test_no_sentinel_999_for_missing_all_fields():
    """When all lead time fields are absent, result must be reasonable, not 999."""
    path = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
    )
    assert path.total_lead_time_days != 999
    assert path.total_lead_time_days > 0


def test_no_sentinel_999_for_missing_fabric_days():
    """Missing fabric days → default assumption + risk flag, not 999."""
    path = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        qc_days=2,
        logistics_days=5,
    )
    assert path.total_lead_time_days != 999
    assert any("lead_time_unknown" in f for f in path.risk_flags), (
        "Missing fabric/material days must produce a risk flag"
    )


def test_missing_logistics_gets_default_not_999():
    """Missing logistics days → default assumption applied, not 999."""
    path = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        fabric_days=10,
        qc_days=2,
    )
    assert path.total_lead_time_days != 999
    assert path.total_lead_time_days > 0


# ─── Regression: unrealistic lead time flagged ───────────────────────────────

def test_one_day_lead_time_creates_risk_flag():
    """A supplier claiming 1-day total lead time should be flagged as unrealistic."""
    path = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        fabric_days=5,
        qc_days=2,
        logistics_days=3,
        supplier_stated_total_days=1,  # Claiming 1 day — unrealistic
        confidence_score=0.9,
    )
    # Calculated total will be > 1, creating a consistency flag
    assert path.total_lead_time_days > 1
    # Should have a consistency note or flag
    has_flag = any("inconsistent" in f or "diff=" in f for f in path.risk_flags)
    has_note = path.lead_time_consistency_note is not None
    assert has_flag or has_note, (
        f"1-day claim vs calculated {path.total_lead_time_days}d must be flagged. "
        f"flags={path.risk_flags}, note={path.lead_time_consistency_note}"
    )


def test_calculated_total_overrides_stated_total():
    """AIVAN calculates lead time independently; supplier-stated is verification evidence."""
    path = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        fabric_days=10,
        qc_days=2,
        logistics_days=5,
        supplier_stated_total_days=3,  # Far below what's realistic
    )
    # Calculated must be realistic
    assert path.total_lead_time_days >= 10, (
        "Calculated total must not be dominated by unrealistic supplier-stated total"
    )
    assert path.supplier_stated_lead_time_days == 3  # Preserved as evidence


# ─── Regression: deadline feasibility ────────────────────────────────────────

def test_feasible_within_deadline():
    """Supplier can meet a generous deadline."""
    path = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        fabric_days=5,
        qc_days=2,
        logistics_days=3,
        buyer_deadline_days=90,
    )
    assert path.feasible_before_deadline is True
    assert path.slack_days is not None and path.slack_days > 0


def test_infeasible_when_exceeds_deadline():
    """Supplier cannot meet a tight 5-day deadline for a complex apparel order."""
    path = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        fabric_days=10,
        qc_days=3,
        logistics_days=7,
        quantity=5000,
        buyer_deadline_days=5,  # Impossible
    )
    assert path.feasible_before_deadline is False


def test_no_deadline_no_feasibility_check():
    """When no deadline is set, feasibility check is not applied."""
    path = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        fabric_days=10,
        qc_days=2,
        logistics_days=5,
    )
    # Without deadline, should default to feasible
    assert path.feasible_before_deadline is True
    assert path.deadline_days is None


# ─── Regression: capacity constraints ────────────────────────────────────────

def test_capacity_constraint_increases_production_days():
    """A low-capacity supplier (10 units/day) for 1000 units takes longer than high-capacity."""
    low_cap = ProductionCapacity(actor_id=SUPPLIER_ID, daily_capacity_units=10.0, setup_days=1.0)
    high_cap = ProductionCapacity(actor_id=SUPPLIER_ID, daily_capacity_units=500.0, setup_days=1.0)

    path_low = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        quantity=1000,
        fabric_days=5,
        qc_days=2,
        logistics_days=3,
        production_capacity=low_cap,
    )
    path_high = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        quantity=1000,
        fabric_days=5,
        qc_days=2,
        logistics_days=3,
        production_capacity=high_cap,
    )
    assert path_low.total_lead_time_days > path_high.total_lead_time_days, (
        f"Low capacity must take longer: low={path_low.total_lead_time_days}, high={path_high.total_lead_time_days}"
    )


def test_production_days_proportional_to_quantity():
    """Larger order takes more production days with fixed daily capacity."""
    small = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        quantity=100,
        fabric_days=5,
        logistics_days=3,
    )
    large = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        quantity=10000,
        fabric_days=5,
        logistics_days=3,
    )
    assert large.total_lead_time_days >= small.total_lead_time_days, (
        "Larger order must not be faster than smaller order"
    )


# ─── Regression: parallel material logic ─────────────────────────────────────

def test_material_parallel_uses_max_not_sum():
    """Fabric and trim run in parallel → material_ready = max(fabric, trim), not sum."""
    path = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        fabric_days=10,
        trim_days=4,
    )
    assert path.material_ready_days == 10.0, (
        f"Parallel material should use max(10, 4)=10, got {path.material_ready_days}"
    )


def test_post_production_uses_sum_not_max():
    """QC, packaging, logistics run sequentially → post_production = sum."""
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
        f"Sequential post-production should be 2+1+3=6, got {path.post_production_days}"
    )


# ─── Regression: risk buffer increases with uncertainty ──────────────────────

def test_low_confidence_adds_buffer():
    """Low confidence score should add a risk buffer to the total."""
    path_high = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        fabric_days=10,
        qc_days=2,
        logistics_days=3,
        confidence_score=0.95,
    )
    path_low = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        fabric_days=10,
        qc_days=2,
        logistics_days=3,
        confidence_score=0.1,
    )
    assert path_low.total_lead_time_days >= path_high.total_lead_time_days, (
        "Low confidence must not produce a shorter lead time than high confidence"
    )


def test_risk_flags_add_buffer():
    """Supplier with risk flags gets a higher lead time due to risk buffer."""
    path_clean = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        fabric_days=10,
        qc_days=2,
        logistics_days=3,
        risk_flags=[],
    )
    path_risky = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        fabric_days=10,
        qc_days=2,
        logistics_days=3,
        risk_flags=["substitute_material", "subcontract_dependency"],
    )
    assert path_risky.total_lead_time_days >= path_clean.total_lead_time_days, (
        "Risk flags must not produce shorter lead time than clean supplier"
    )


# ─── Regression: evidence fields populated ───────────────────────────────────

def test_components_have_evidence_refs():
    """All lead time components must have an evidence_ref (traceable to source)."""
    path = calculate_lead_time_path(
        supplier_response_id=RESP_ID,
        supplier_id=SUPPLIER_ID,
        supplier_name=SUPPLIER_NAME,
        project_id=PROJECT_ID,
        fabric_days=10,
        qc_days=2,
        logistics_days=5,
    )
    assert len(path.components) > 0
    assert len(path.evidence_refs) > 0


def test_path_id_is_unique():
    """Each call to calculate_lead_time_path must return a unique path_id."""
    path1 = calculate_lead_time_path(RESP_ID, SUPPLIER_ID, SUPPLIER_NAME, PROJECT_ID)
    path2 = calculate_lead_time_path(RESP_ID, SUPPLIER_ID, SUPPLIER_NAME, PROJECT_ID)
    assert path1.path_id != path2.path_id
