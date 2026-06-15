"""
GLTG No Silent Fallback Tests.

Verifies that:
1. Embedded GLTG always sets fallback_model_used = False.
2. model_name is always "GLTG" — never the legacy default.
3. AIVAN path enumerator never produces legacy-only paths.
4. Existing lead-time model tests still pass (regression guard).
5. Human approval gate is unaffected by GLTG changes.
"""

import pytest

from src.gltg.engine import GLTG_MODEL_NAME, GLTG_MODEL_VERSION, calculate_gltg_lead_time_path
from src.lead_time.path_enumerator import enumerate_delivery_paths
from src.lead_time.models import ProductionCapacity


def _cap(**kwargs):
    defaults = dict(actor_id="sup", daily_capacity_units=500, setup_days=1, queue_days=0, confidence_score=0.8)
    defaults.update(kwargs)
    return ProductionCapacity(**defaults)


# ─── Fallback must always be explicit ─────────────────────────────────────────

def test_embedded_gltg_fallback_model_used_is_false():
    """Embedded GLTG must never set fallback_model_used = True."""
    path = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-FB1",
        supplier_id="sup1",
        supplier_name="Supplier 1",
        project_id="PROJ-FB",
        quantity=1000,
        fabric_days=7,
        qc_days=2,
        packaging_days=1,
        logistics_days=5,
        production_capacity=_cap(),
        confidence_score=0.8,
        completeness_score=0.8,
    )
    assert path.fallback_model_used is False, (
        "Embedded GLTG must not mark itself as a fallback. "
        f"Got fallback_model_used={path.fallback_model_used!r}"
    )


def test_embedded_gltg_model_name_is_gltg():
    """model_name must always be 'GLTG' for GLTG paths — never the legacy default."""
    path = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-MN",
        supplier_id="sup_mn",
        supplier_name="Supplier MN",
        project_id="PROJ-MN",
        quantity=500,
        fabric_days=5,
        qc_days=1,
        packaging_days=1,
        logistics_days=3,
        production_capacity=_cap(),
        confidence_score=0.7,
        completeness_score=0.7,
    )
    assert path.model_name == GLTG_MODEL_NAME, (
        f"model_name must be '{GLTG_MODEL_NAME}'. Got {path.model_name!r}"
    )
    assert path.model_name != "lead_time_calculator", (
        "model_name must not be the legacy default 'lead_time_calculator'"
    )


def test_embedded_gltg_model_version_is_set():
    """model_version must be set and match the embedded GLTG version."""
    path = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-VER",
        supplier_id="sup_ver",
        supplier_name="Supplier VER",
        project_id="PROJ-VER",
        quantity=500,
        fabric_days=5,
        qc_days=1,
        packaging_days=1,
        logistics_days=3,
        production_capacity=_cap(),
        confidence_score=0.8,
        completeness_score=0.8,
    )
    assert path.model_version == GLTG_MODEL_VERSION
    assert path.model_version != "legacy", "model_version must not be the legacy default"


def test_path_enumerator_no_legacy_only_paths():
    """enumerate_delivery_paths must never return a path with the legacy model_name."""
    paths = enumerate_delivery_paths(
        project_id="PROJ-ENUM-FB",
        buyer_deadline_days=45,
        quantity=5000,
        supplier_responses=[
            {
                "response_id": "RESP-E1",
                "supplier_id": "sup_e1",
                "supplier_name": "Supplier E1",
                "fabric_days": 8,
                "qc_days": 2,
                "packaging_days": 1,
                "logistics_days": 5,
                "confidence_score": 0.8,
                "completeness_score": 0.8,
            },
            {
                "response_id": "RESP-E2",
                "supplier_id": "sup_e2",
                "supplier_name": "Supplier E2",
                "fabric_days": 14,
                "qc_days": 2,
                "packaging_days": 1,
                "logistics_days": 7,
                "confidence_score": 0.6,
                "completeness_score": 0.6,
            },
        ],
        production_capacity=_cap(),
    )
    assert len(paths) == 2
    for path in paths:
        assert path.model_name == GLTG_MODEL_NAME, (
            f"supplier={path.supplier_id}: model_name must be 'GLTG', got {path.model_name!r}"
        )
        assert path.fallback_model_used is False, (
            f"supplier={path.supplier_id}: fallback_model_used must be False"
        )
        assert path.model_version is not None, "model_version must not be None"
        assert path.model_version != "legacy", "model_version must not be the legacy default"


# ─── GLTG path always exposes all required fields ─────────────────────────────

def test_gltg_path_all_required_fields_present():
    """A GLTG path must expose every required field with non-None values."""
    path = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-ALL",
        supplier_id="sup_all",
        supplier_name="Supplier All",
        project_id="PROJ-ALL",
        quantity=1000,
        fabric_days=7,
        qc_days=2,
        packaging_days=1,
        logistics_days=5,
        production_capacity=_cap(),
        buyer_deadline_days=45,
        confidence_score=0.8,
        completeness_score=0.8,
    )
    assert path.model_name == "GLTG"
    assert path.model_version is not None
    assert path.p50_lead_time_days is not None
    assert path.p80_lead_time_days is not None
    assert path.p90_lead_time_days is not None
    assert path.p50_lead_time_days <= path.p80_lead_time_days <= path.p90_lead_time_days
    assert path.feasibility_basis == "p80"
    assert path.fallback_model_used is False
    gltg_refs = [ref for ref in path.evidence_refs if "GLTG" in ref or "gltg" in ref.lower()]
    assert gltg_refs, "GLTG evidence reference must be present"


# ─── Human approval gate regression guard ─────────────────────────────────────

def test_human_approval_gate_unaffected_by_gltg():
    """The human approval gate must still require approval status on drafts."""
    from src.openclaw_skill.message_draft_store import create_draft, find_pending_drafts
    import os
    os.environ.setdefault("GIRAFFE_DB_MODE", "off")

    d = create_draft("proj_gltg_gate", "openclaw-mock", "supplier", "Test draft for approval gate")
    assert d.approval_status == "pending_approval", (
        "Draft must start in 'pending_approval' — approval gate is untouched by GLTG changes"
    )
    pending = find_pending_drafts("proj_gltg_gate")
    assert any(x.id == d.id for x in pending), "New draft must appear in pending_drafts list"


# ─── Regression: legacy calculator tests not broken ───────────────────────────

def test_legacy_calculate_lead_time_path_still_works():
    """The legacy deterministic calculator must still be callable and correct."""
    from src.lead_time.lead_time_calculator import calculate_lead_time_path
    path = calculate_lead_time_path(
        supplier_response_id="RESP-LEG",
        supplier_id="sup_leg",
        supplier_name="Supplier Legacy",
        project_id="PROJ-LEG",
        quantity=1000,
        fabric_days=7,
        qc_days=2,
        packaging_days=1,
        logistics_days=5,
        confidence_score=0.8,
        completeness_score=0.8,
    )
    assert path.total_lead_time_days > 0
    assert path.model_name == "lead_time_calculator", (
        "Legacy calculator must still default to 'lead_time_calculator' — only GLTG wrapper promotes to 'GLTG'"
    )
