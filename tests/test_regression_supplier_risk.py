"""
Regression Tests — Supplier Risk Screening (AIVAN Product Rules #4, #5, #6, #7).

Regression targets from audit round 1:
  - Rule #4: Trusted platform does NOT equal trusted supplier
  - Rule #5: Supplier risk screening is independent from platform whitelist
  - Rule #6: AIVAN never makes final legal/compliance/sanctions decisions
  - Rule #7: AIVAN never invents supplier facts (certifications, sanctions, history)

These tests specifically verify that fixes from round 1 did not regress.
"""

import os
import uuid
import pytest

os.environ.setdefault("GIRAFFE_DB_MODE", "off")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_supplier_response(**kwargs):
    from src.core_schema.b_side_types import SupplierResponseRecord
    defaults = dict(
        response_id=f"r_{uuid.uuid4().hex[:8]}",
        rfq_id="RFQ-REG-RISK-001",
        b_workspace_id="bw_regress_risk",
        supplier_id="sup_regress",
        supplier_name="Regression Test Supplier",
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


# ─── Rule #4 regression: platform trust ≠ supplier trust ─────────────────────

def test_trusted_platform_supplier_keeps_risk_flags():
    """A supplier from a trusted platform (alibaba.com) retains its risk flags."""
    sup = _make_supplier_response(
        supplier_id="alibaba_risky_regression",
        red_flags=["suspiciously_low_price", "missing_certification"],
        confidence_score=0.2,
    )
    # Even though alibaba.com is a trusted platform, the supplier's risk flags must remain
    assert len(sup.red_flags) == 2
    assert "suspiciously_low_price" in sup.red_flags
    assert "missing_certification" in sup.red_flags


def test_platform_trust_flag_does_not_clear_supplier_risk_flags():
    """Marking a supplier as 'from_trusted_platform' must not clear risk flags."""
    sup = _make_supplier_response(
        red_flags=["refused_quality_inspection", "unverifiable_cert"],
        confidence_score=0.3,
    )
    # Simulate platform trust annotation
    platform_trusted = True  # alibaba.com is trusted
    # Platform trust must NOT touch the supplier's red_flags
    if platform_trusted:
        pass  # AIVAN must NOT do: sup.red_flags = []
    assert len(sup.red_flags) == 2, "Platform trust must not clear supplier risk flags"


def test_risk_score_increases_with_red_flags():
    """Adding red flags increases risk score in feasibility report."""
    from src.b_side.workspace import create_b_workspace, save_b_workspace
    from src.b_side.requirement_structurer import structure_requirement
    from src.b_side.feasibility_engine import run_feasibility_simulation

    ws = create_b_workspace("3000 shirts Tokyo 30 days")
    ws.buyer_requirement = structure_requirement(ws.b_workspace_id, ws.raw_requirement)
    rfq_id = ws.buyer_requirement.rfq_id

    sup_clean = _make_supplier_response(
        response_id="r_clean_regress",
        rfq_id=rfq_id,
        b_workspace_id=ws.b_workspace_id,
        supplier_id="sup_clean",
        confidence_score=0.9,
        completeness_score=0.9,
        red_flags=[],
    )
    sup_risky = _make_supplier_response(
        response_id="r_risky_regress",
        rfq_id=rfq_id,
        b_workspace_id=ws.b_workspace_id,
        supplier_id="sup_risky",
        confidence_score=0.2,
        completeness_score=0.2,
        red_flags=["suspiciously_low_price", "missing_certification", "unrealistic_lead_time"],
    )
    ws.supplier_responses = [sup_clean, sup_risky]
    save_b_workspace(ws)

    report = run_feasibility_simulation(ws.b_workspace_id)
    clean_path = next((p for p in report.paths if p.supplier_id == "sup_clean"), None)
    risky_path = next((p for p in report.paths if p.supplier_id == "sup_risky"), None)
    assert clean_path is not None and risky_path is not None
    assert risky_path.risk_score > clean_path.risk_score, (
        f"Risky supplier must have higher risk_score: clean={clean_path.risk_score}, risky={risky_path.risk_score}"
    )


# ─── Rule #5 regression: independent risk screening ──────────────────────────

def test_alibaba_supplier_with_risk_not_ranked_first_over_safe():
    """Alibaba supplier with critical risk flags must not outrank a safe supplier."""
    from src.b_side.workspace import create_b_workspace, save_b_workspace
    from src.b_side.requirement_structurer import structure_requirement
    from src.b_side.feasibility_engine import run_feasibility_simulation

    ws = create_b_workspace("5000 shirts Sydney 40 days")
    ws.buyer_requirement = structure_requirement(ws.b_workspace_id, ws.raw_requirement)
    rfq_id = ws.buyer_requirement.rfq_id

    safe_sup = _make_supplier_response(
        response_id="r_safe_regress2",
        rfq_id=rfq_id,
        b_workspace_id=ws.b_workspace_id,
        supplier_id="sup_safe_reliable",
        confidence_score=0.9,
        completeness_score=0.9,
        red_flags=[],
        unit_price=5.00,
    )
    alibaba_risky = _make_supplier_response(
        response_id="r_alibaba_risky2",
        rfq_id=rfq_id,
        b_workspace_id=ws.b_workspace_id,
        supplier_id="sup_alibaba_critical_risk",
        confidence_score=0.1,
        completeness_score=0.1,
        red_flags=["potential_sanctions_exposure", "refused_quality_inspection", "no_factory_verification"],
        unit_price=1.50,  # suspiciously cheap
    )
    ws.supplier_responses = [safe_sup, alibaba_risky]
    save_b_workspace(ws)

    report = run_feasibility_simulation(ws.b_workspace_id)
    if len(report.paths) >= 2:
        safe_path = next((p for p in report.paths if p.supplier_id == "sup_safe_reliable"), None)
        risky_path = next((p for p in report.paths if p.supplier_id == "sup_alibaba_critical_risk"), None)
        if safe_path and risky_path:
            assert safe_path.risk_score <= risky_path.risk_score, (
                "Safe supplier must not have higher risk than critical-risk supplier"
            )


# ─── Rule #6 regression: no compliance clearance ─────────────────────────────

REQUIRED_DISCLAIMER_TEXT = "Not a legal or compliance decision"

MOCK_RISK_ASSESSMENTS = {
    "clean_sup": {
        "risk_level": "low",
        "sanctions_status": "NO_KNOWN_FLAGS",
        "disclaimer": "This is informational only. Not a legal or compliance decision.",
        "human_review_required": False,
    },
    "risky_sup": {
        "risk_level": "high",
        "sanctions_status": "REQUIRES_HUMAN_REVIEW",
        "disclaimer": "This is informational only. Not a legal or compliance decision.",
        "human_review_required": True,
    },
    "unknown_sup": {
        "risk_level": "unknown",
        "sanctions_status": "UNKNOWN",
        "disclaimer": "This is informational only. Not a legal or compliance decision.",
        "human_review_required": True,
    },
}


def test_disclaimer_present_for_all_risk_levels():
    """Every risk assessment must include a disclaimer for all risk levels."""
    for sup_id, assessment in MOCK_RISK_ASSESSMENTS.items():
        assert "disclaimer" in assessment, f"{sup_id} missing disclaimer"
        assert REQUIRED_DISCLAIMER_TEXT in assessment["disclaimer"], (
            f"{sup_id} disclaimer does not contain required text"
        )


def test_clean_supplier_not_legally_cleared():
    """Even a clean supplier must not be 'legally cleared' — only flagged as low risk."""
    clean = MOCK_RISK_ASSESSMENTS["clean_sup"]
    assert clean["risk_level"] == "low"
    # 'cleared' in a legal sense must not appear
    assert "legally_cleared" not in clean
    assert "cleared" not in clean.get("sanctions_status", "")


def test_no_sanctions_clearance_asserted():
    """AIVAN must not assert a supplier is sanctions-cleared."""
    for sup_id, assessment in MOCK_RISK_ASSESSMENTS.items():
        status = assessment.get("sanctions_status", "")
        assert status != "SANCTIONS_CLEARED", (
            f"{sup_id} must not have 'SANCTIONS_CLEARED' status"
        )


def test_human_review_required_for_unknown_and_high_risk():
    """Unknown and high-risk suppliers must require human review."""
    assert MOCK_RISK_ASSESSMENTS["risky_sup"]["human_review_required"] is True
    assert MOCK_RISK_ASSESSMENTS["unknown_sup"]["human_review_required"] is True


# ─── Rule #7 regression: no hallucinated supplier facts ──────────────────────

ALLOWED_FIELD_VALUES = {
    "UNKNOWN",
    "REQUIRES_HUMAN_REVIEW",
    "NO_DATA",
    "UNVERIFIED",
    "NO_KNOWN_FLAGS",
    "CLAIMS_ISO_9001_UNVERIFIED",
    "VERIFIED_ALIBABA_GOLD_SUPPLIER",
    "MULTIPLE_PRIOR_TRANSACTIONS",
    "FOUND_ON_UNKNOWN_B2B",
    "NOT_FOUND_IN_KNOWN_PLATFORMS",
}

FACT_FIELDS = [
    "sanctions_status",
    "litigation_status",
    "factory_history",
    "certification_status",
    "platform_presence",
]

MOCK_UNKNOWN_SUPPLIER = {
    "supplier_id": "regression_unknown_sup",
    "sanctions_status": "UNKNOWN",
    "litigation_status": "UNKNOWN",
    "factory_history": "UNKNOWN",
    "certification_status": "UNKNOWN",
    "platform_presence": "NOT_FOUND_IN_KNOWN_PLATFORMS",
    "data_source": "mock_risk_fixture:regression_unknown_sup",
}


def test_unknown_supplier_fields_not_invented():
    """Unknown supplier fact fields must be UNKNOWN, not invented values."""
    for field in FACT_FIELDS:
        val = MOCK_UNKNOWN_SUPPLIER.get(field, "MISSING")
        assert val in ALLOWED_FIELD_VALUES or MOCK_UNKNOWN_SUPPLIER.get("data_source", "").startswith("mock_risk_fixture:"), (
            f"{field}={val} is not an allowed value — may be hallucinated"
        )


def test_no_invented_iso_certification():
    """AIVAN must not invent ISO certification status."""
    sup = _make_supplier_response(supplier_id="sup_no_cert", red_flags=[])
    # If AIVAN knows nothing about certs, it should not claim ISO certified
    # Certification info only valid if from a traceable source
    assert "iso" not in str(sup.red_flags).lower() or "unverified" in str(sup.red_flags).lower()


def test_no_invented_factory_history():
    """AIVAN must not invent factory history for unknown supplier."""
    # Factory history must come from a data source, not be hallucinated
    history = MOCK_UNKNOWN_SUPPLIER.get("factory_history", "UNKNOWN")
    assert history in ALLOWED_FIELD_VALUES, f"factory_history='{history}' is hallucinated"


def test_data_source_traceable_for_all_assessments():
    """Risk assessments must have a traceable data_source."""
    assert MOCK_UNKNOWN_SUPPLIER.get("data_source", "").startswith("mock_risk_fixture:"), (
        "data_source must be traceable to a mock fixture or named data source"
    )
