"""
GLTG Functional Rules Tests.

Covers:
1. P80 is the default deadline feasibility basis (not P50, not deterministic).
2. Supplier-stated lead time is evidence, not truth.
3. GLTG evidence trail is present.
4. Risk flags increase P90 (uncertainty widens under risk).
5. Larger order does not produce shorter lead time under equal capacity.
"""

import pytest

from src.gltg.engine import GLTG_MODEL_NAME, calculate_gltg_lead_time_path
from src.lead_time.models import ProductionCapacity


def _capacity(actor_id="sup", daily=500, setup=1, queue=0, confidence=0.85):
    return ProductionCapacity(
        actor_id=actor_id,
        daily_capacity_units=daily,
        setup_days=setup,
        queue_days=queue,
        confidence_score=confidence,
    )


# ─── Rule 1: P80 is the default feasibility basis ─────────────────────────────

def test_p80_used_for_feasibility_not_p50():
    """When deadline is tight, feasibility must be checked against P80, not P50."""
    path = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-P80",
        supplier_id="sup_p80",
        supplier_name="Supplier P80",
        project_id="PROJ-P80",
        quantity=10000,
        fabric_days=10,
        qc_days=2,
        packaging_days=1,
        logistics_days=7,
        production_capacity=_capacity(),
        buyer_deadline_days=1,
        confidence_score=0.8,
        completeness_score=0.8,
    )
    assert path.feasibility_basis == "p80"
    assert path.feasible_before_deadline is False
    expected_slack = 1 - path.p80_lead_time_days
    assert path.slack_days == expected_slack, (
        f"slack_days should be deadline - P80. Got {path.slack_days}, expected {expected_slack}"
    )


def test_feasible_path_uses_p80_not_p50():
    """A path that is feasible under P80 must be marked feasible."""
    path = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-FEAS",
        supplier_id="sup_feas",
        supplier_name="Supplier Feasible",
        project_id="PROJ-FEAS",
        quantity=100,
        fabric_days=3,
        qc_days=1,
        packaging_days=1,
        logistics_days=3,
        production_capacity=_capacity(daily=500),
        buyer_deadline_days=60,
        confidence_score=0.9,
        completeness_score=0.9,
    )
    assert path.feasibility_basis == "p80"
    assert path.p80_lead_time_days <= 60
    assert path.feasible_before_deadline is True
    assert path.slack_days == 60 - path.p80_lead_time_days


def test_deadline_flag_uses_p80_not_p50():
    """The infeasibility risk flag must reference p80, not p50."""
    path = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-FLAG",
        supplier_id="sup_flag",
        supplier_name="Supplier Flag",
        project_id="PROJ-FLAG",
        quantity=10000,
        fabric_days=10,
        qc_days=2,
        packaging_days=1,
        logistics_days=7,
        production_capacity=_capacity(),
        buyer_deadline_days=1,
        confidence_score=0.8,
        completeness_score=0.8,
    )
    infeasible_flags = [f for f in path.risk_flags if "gltg_p80_deadline_infeasible" in f]
    assert infeasible_flags, (
        f"Expected a gltg_p80_deadline_infeasible flag. Got flags: {path.risk_flags}"
    )


# ─── Rule 2: Supplier-stated lead time is evidence, not truth ─────────────────

def test_unrealistic_supplier_stated_does_not_override_calculated():
    """A supplier claiming 1-day delivery for 10k units must not produce a 1-day path."""
    path = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-UNREAL",
        supplier_id="sup_unreal",
        supplier_name="Unrealistic Supplier",
        project_id="PROJ-UNREAL",
        quantity=10000,
        fabric_days=10,
        qc_days=2,
        packaging_days=1,
        logistics_days=7,
        production_capacity=_capacity(),
        supplier_stated_total_days=1,
        confidence_score=0.5,
        completeness_score=0.3,
    )
    assert path.total_lead_time_days > 1, (
        f"Calculated lead time must exceed unrealistic supplier claim of 1d. Got {path.total_lead_time_days}"
    )
    assert path.p80_lead_time_days > 1, (
        f"p80 must exceed unrealistic supplier claim. Got {path.p80_lead_time_days}"
    )
    has_consistency_note = path.lead_time_consistency_note is not None
    has_risk_flag = any("inconsist" in f or "diff" in f.lower() or "stated" in f.lower()
                        for f in path.risk_flags)
    assert has_consistency_note or has_risk_flag, (
        "Unrealistic supplier claim must produce a consistency note or risk flag"
    )


# ─── Rule 3: GLTG evidence trail ──────────────────────────────────────────────

def test_gltg_evidence_ref_present():
    """Every GLTG path must carry an evidence reference proving GLTG provenance."""
    path = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-EV",
        supplier_id="sup_ev",
        supplier_name="Supplier Evidence",
        project_id="PROJ-EV",
        quantity=1000,
        fabric_days=7,
        qc_days=2,
        packaging_days=1,
        logistics_days=5,
        production_capacity=_capacity(),
        confidence_score=0.8,
        completeness_score=0.8,
    )
    gltg_refs = [ref for ref in path.evidence_refs if "GLTG" in ref or "gltg" in ref.lower()]
    assert gltg_refs, (
        f"GLTG evidence reference must be present. evidence_refs: {path.evidence_refs}"
    )


def test_gltg_model_name_and_version():
    """model_name must be 'GLTG' and model_version must be set."""
    path = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-MV",
        supplier_id="sup_mv",
        supplier_name="Supplier MV",
        project_id="PROJ-MV",
        quantity=500,
        fabric_days=5,
        qc_days=1,
        packaging_days=1,
        logistics_days=3,
        production_capacity=_capacity(),
        confidence_score=0.8,
        completeness_score=0.8,
    )
    assert path.model_name == GLTG_MODEL_NAME
    assert path.model_version is not None
    assert len(path.model_version) > 0


# ─── Rule 4: Risk increases P90 ───────────────────────────────────────────────

def test_risk_flags_increase_p90():
    """A risky path must have a higher P90 than an identical clean path."""
    kwargs = dict(
        supplier_id="sup",
        supplier_name="Supplier",
        project_id="PROJ-RISK",
        quantity=1000,
        fabric_days=7,
        qc_days=2,
        packaging_days=1,
        logistics_days=5,
        production_capacity=_capacity(),
        confidence_score=0.8,
        completeness_score=0.8,
    )
    clean = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-CLEAN",
        risk_flags=[],
        **kwargs,
    )
    risky = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-RISKY",
        risk_flags=["substitute_material", "unconfirmed_logistics", "compressed"],
        **kwargs,
    )
    assert risky.p90_lead_time_days >= clean.p90_lead_time_days, (
        f"Risky path P90 ({risky.p90_lead_time_days}) must be >= clean path P90 ({clean.p90_lead_time_days})"
    )


def test_low_confidence_increases_uncertainty():
    """Low confidence must produce higher P90 relative to P80 than high confidence."""
    base_kwargs = dict(
        supplier_id="sup",
        supplier_name="Supplier",
        project_id="PROJ-CONF",
        quantity=1000,
        fabric_days=7,
        qc_days=2,
        packaging_days=1,
        logistics_days=5,
        production_capacity=_capacity(),
    )
    high_conf = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-HI",
        confidence_score=0.95,
        completeness_score=0.95,
        **base_kwargs,
    )
    low_conf = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-LO",
        confidence_score=0.2,
        completeness_score=0.2,
        **base_kwargs,
    )
    hi_spread = high_conf.p90_lead_time_days - high_conf.p80_lead_time_days
    lo_spread = low_conf.p90_lead_time_days - low_conf.p80_lead_time_days
    assert lo_spread >= hi_spread, (
        f"Low confidence must produce wider P80–P90 spread. "
        f"High conf spread={hi_spread}, Low conf spread={lo_spread}"
    )


# ─── Rule 5: Larger order must not produce shorter lead time ──────────────────

def test_larger_order_does_not_produce_shorter_lead_time():
    """With identical supplier capacity, a larger order must take at least as long as a smaller one."""
    cap = _capacity(daily=500)
    base_kwargs = dict(
        supplier_id="sup",
        supplier_name="Supplier",
        project_id="PROJ-SIZE",
        fabric_days=7,
        qc_days=2,
        packaging_days=1,
        logistics_days=5,
        production_capacity=cap,
        confidence_score=0.8,
        completeness_score=0.8,
    )
    small = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-SMALL",
        quantity=100,
        **base_kwargs,
    )
    large = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-LARGE",
        quantity=10000,
        **base_kwargs,
    )
    assert large.p80_lead_time_days >= small.p80_lead_time_days, (
        f"Large order P80 ({large.p80_lead_time_days}) must be >= small order P80 ({small.p80_lead_time_days})"
    )
    assert large.total_lead_time_days >= small.total_lead_time_days, (
        f"Large order total ({large.total_lead_time_days}) must be >= small order total ({small.total_lead_time_days})"
    )
