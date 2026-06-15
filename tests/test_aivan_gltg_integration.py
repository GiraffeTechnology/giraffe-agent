"""AIVAN × GLTG integration tests.

These tests enforce the product rule that AIVAN must use GLTG as its lead-time
and feasibility engine. The legacy deterministic calculator can remain as an
internal core, but AIVAN-facing delivery paths must expose GLTG provenance,
P50/P80/P90 estimates, and explicit fallback status.
"""

from src.gltg.engine import GLTG_MODEL_NAME, calculate_gltg_lead_time_path
from src.lead_time.path_enumerator import enumerate_delivery_paths
from src.lead_time.models import ProductionCapacity


def test_gltg_direct_result_exposes_percentiles_and_model_provenance():
    path = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-GLTG-001",
        supplier_id="supplier_a",
        supplier_name="Supplier A",
        project_id="PROJ-GLTG",
        quantity=10000,
        fabric_days=10,
        qc_days=2,
        packaging_days=1,
        logistics_days=7,
        production_capacity=ProductionCapacity(
            actor_id="supplier_a",
            daily_capacity_units=500,
            setup_days=1,
            queue_days=0,
            confidence_score=0.85,
        ),
        buyer_deadline_days=45,
        confidence_score=0.8,
        completeness_score=0.8,
    )

    assert path.model_name == GLTG_MODEL_NAME
    assert path.model_version.startswith("0.1")
    assert path.fallback_model_used is False
    assert path.feasibility_basis == "p80"
    assert path.p50_lead_time_days is not None
    assert path.p80_lead_time_days is not None
    assert path.p90_lead_time_days is not None
    assert path.p50_lead_time_days <= path.p80_lead_time_days <= path.p90_lead_time_days
    assert path.p80_lead_time_days == path.total_lead_time_days
    assert any("GLTG" in ref or "gltg" in ref.lower() for ref in path.evidence_refs)


def test_aivan_path_enumerator_uses_gltg_not_legacy_only():
    paths = enumerate_delivery_paths(
        project_id="PROJ-AIVAN-GLTG",
        buyer_deadline_days=45,
        quantity=10000,
        supplier_responses=[
            {
                "response_id": "RESP-A",
                "supplier_id": "supplier_a",
                "supplier_name": "Supplier A",
                "fabric_days": 10,
                "qc_days": 2,
                "packaging_days": 1,
                "logistics_days": 7,
                "confidence_score": 0.8,
                "completeness_score": 0.8,
                "unit_price": 4.8,
                "currency": "USD",
            }
        ],
        production_capacity=ProductionCapacity(
            actor_id="supplier_a",
            daily_capacity_units=500,
            setup_days=1,
            queue_days=0,
            confidence_score=0.85,
        ),
    )

    assert len(paths) == 1
    path = paths[0]
    assert path.model_name == "GLTG"
    assert path.fallback_model_used is False
    assert path.feasibility_basis == "p80"
    assert path.p80_lead_time_days == path.total_lead_time_days
    assert path.deadline_days == 45


def test_gltg_uses_p80_for_deadline_feasibility():
    path = calculate_gltg_lead_time_path(
        supplier_response_id="RESP-TIGHT",
        supplier_id="supplier_tight",
        supplier_name="Supplier Tight",
        project_id="PROJ-GLTG-TIGHT",
        quantity=10000,
        fabric_days=10,
        qc_days=2,
        packaging_days=1,
        logistics_days=7,
        production_capacity=ProductionCapacity(
            actor_id="supplier_tight",
            daily_capacity_units=500,
            setup_days=1,
        ),
        buyer_deadline_days=1,
        confidence_score=0.8,
        completeness_score=0.8,
    )

    assert path.p80_lead_time_days == path.total_lead_time_days
    assert path.feasible_before_deadline is False
    assert path.slack_days == 1 - path.p80_lead_time_days
    assert any("gltg_p80_deadline_infeasible" in flag for flag in path.risk_flags)
