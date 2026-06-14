"""
Path enumerator — generates 1–4 labeled LeadTimePath variants per supplier.
"""
import uuid
from typing import Any

from src.lead_time.models import LeadTimePath, ProductionCapacity
from src.lead_time.lead_time_calculator import calculate_lead_time_path


def enumerate_delivery_paths(
    project_id: str,
    supplier_responses: list[dict],
    production_capacity: ProductionCapacity | None = None,
    buyer_deadline_days: int | None = None,
    quantity: int | None = None,
) -> list[LeadTimePath]:
    """
    Enumerate feasible delivery paths across suppliers and upstream options.

    Each supplier_response dict must have:
    - supplier_id, supplier_name, response_id
    - Optional: fabric_days, trim_days, packaging_material_days, subcontract_days,
      qc_days, packaging_days, logistics_days
    - Optional: supplier_stated_total_days
    - Optional: risk_flags, missing_fields, confidence_score, completeness_score
    - Optional: unit_price, total_price, currency
    - can_make: bool (False -> skip)
    """
    all_paths: list[LeadTimePath] = []

    for sr in supplier_responses:
        if not sr.get("can_make", True):
            continue

        path = calculate_lead_time_path(
            supplier_response_id=sr.get("response_id", f"RESP-{uuid.uuid4().hex[:6]}"),
            supplier_id=sr["supplier_id"],
            supplier_name=sr["supplier_name"],
            project_id=project_id,
            quantity=quantity or sr.get("quantity"),
            fabric_days=sr.get("fabric_days"),
            trim_days=sr.get("trim_days"),
            packaging_material_days=sr.get("packaging_material_days"),
            subcontract_days=sr.get("subcontract_days"),
            qc_days=sr.get("qc_days"),
            packaging_days=sr.get("packaging_days"),
            logistics_days=sr.get("logistics_days"),
            production_capacity=production_capacity,
            supplier_stated_total_days=sr.get("supplier_stated_total_days"),
            risk_flags=sr.get("risk_flags", []),
            missing_fields=sr.get("missing_fields", []),
            confidence_score=sr.get("confidence_score", 0.5),
            completeness_score=sr.get("completeness_score", 0.5),
            unit_price=sr.get("unit_price"),
            total_price=sr.get("total_price"),
            currency=sr.get("currency"),
            buyer_deadline_days=buyer_deadline_days,
            upstream_evidence_refs=sr.get("evidence_refs", []),
        )
        all_paths.append(path)

    return all_paths
