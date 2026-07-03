"""
Dependency Planner — identifies upstream dependencies for a procurement project.
"""

from __future__ import annotations
import uuid
from typing import TYPE_CHECKING, Literal
from pydantic import BaseModel, Field

from src.m_side.m_event_logger import log_m_event

if TYPE_CHECKING:
    from src.m_side.professional_free.cad_cnc_matcher import CADCNCMachiningMatchResult


class DependencyNeed(BaseModel):
    dependency_id: str
    project_id: str
    dependency_type: Literal[
        "fabric",
        "trim",
        "raw_material",
        "component",
        "subcontract_process",
        "surface_treatment",
        "heat_treatment",
        "qc_testing",
        "packaging",
        "logistics",
    ]
    description: str
    required_specs: dict = Field(default_factory=dict)
    quantity_required: float | int | None = None
    required_by_date: str | None = None
    risk_level: Literal["low", "medium", "high"] = "medium"
    why_needed: str = ""
    candidate_actor_ids: list[str] = Field(default_factory=list)


_APPAREL_FABRIC_KEYWORDS = {"shirt", "blouse", "dress", "jacket", "coat", "fabric", "cloth", "textile", "garment", "apparel"}
_APPAREL_TRIM_KEYWORDS = {"button", "zipper", "label", "patch", "trim", "thread", "lining", "interlining", "elastic"}
_PACKAGING_KEYWORDS = {"packaging", "polybag", "carton", "hangtag", "box", "bag"}
_QC_KEYWORDS = {"quality", "inspection", "test", "qc", "audit"}
_LOGISTICS_KEYWORDS = {"ship", "deliver", "export", "import", "freight", "logistics", "transport"}


def _matches_keywords(text: str, keywords: set[str]) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def plan_upstream_dependencies(
    project_id: str,
    product_summary: str,
    category: str,
    quantity: int | None,
    main_supplier_actor_id: str,
    candidate_fabric_ids: list[str] | None = None,
    candidate_trim_ids: list[str] | None = None,
    candidate_packaging_ids: list[str] | None = None,
    candidate_qc_ids: list[str] | None = None,
    candidate_logistics_ids: list[str] | None = None,
    destination: str | None = None,
) -> list[DependencyNeed]:
    """
    Determine upstream dependencies for this procurement project.

    For apparel/garment categories, always identifies: fabric, trim, packaging, QC, logistics.
    For other categories, derives dependencies from product_summary keywords.
    """
    deps: list[DependencyNeed] = []
    is_apparel = (
        category.lower() in {"apparel", "garment", "clothing", "textile", "shirt", "fashion"}
        or _matches_keywords(product_summary, _APPAREL_FABRIC_KEYWORDS)
    )

    if is_apparel:
        deps.append(DependencyNeed(
            dependency_id=f"DEP-{uuid.uuid4().hex[:8].upper()}",
            project_id=project_id,
            dependency_type="fabric",
            description=f"Fabric for {product_summary}",
            required_specs={
                "product": product_summary,
                "quantity": quantity,
                "notes": "Confirm fabric type, color, weight, shrinkage, MOQ, lead time",
            },
            quantity_required=quantity,
            risk_level="high",
            why_needed="Fabric is the primary material. Availability and lead time determine feasibility.",
            candidate_actor_ids=candidate_fabric_ids or [],
        ))
        deps.append(DependencyNeed(
            dependency_id=f"DEP-{uuid.uuid4().hex[:8].upper()}",
            project_id=project_id,
            dependency_type="trim",
            description=f"Trims and buttons for {product_summary}",
            required_specs={
                "product": product_summary,
                "quantity": quantity,
                "notes": "Buttons, zippers, labels, threads — confirm availability and MOQ",
            },
            quantity_required=quantity,
            risk_level="medium",
            why_needed="Trims are required for finishing. Late delivery or unavailability blocks production.",
            candidate_actor_ids=candidate_trim_ids or [],
        ))
        deps.append(DependencyNeed(
            dependency_id=f"DEP-{uuid.uuid4().hex[:8].upper()}",
            project_id=project_id,
            dependency_type="packaging",
            description=f"Packaging for {product_summary} — polybags, cartons, hangtags",
            required_specs={"quantity": quantity, "notes": "Polybags + outer cartons"},
            quantity_required=quantity,
            risk_level="low",
            why_needed="Packaging is needed for final shipment preparation.",
            candidate_actor_ids=candidate_packaging_ids or [],
        ))

    # QC — always include if destination is mentioned or quantity > 50
    if destination or (quantity and quantity >= 50) or _matches_keywords(product_summary, _QC_KEYWORDS):
        deps.append(DependencyNeed(
            dependency_id=f"DEP-{uuid.uuid4().hex[:8].upper()}",
            project_id=project_id,
            dependency_type="qc_testing",
            description="QC inspection before shipment",
            required_specs={"quantity": quantity, "destination": destination or "TBD"},
            quantity_required=quantity,
            risk_level="medium",
            why_needed="Pre-shipment inspection ensures quality before delivery to buyer.",
            candidate_actor_ids=candidate_qc_ids or [],
        ))

    # Logistics — always include
    deps.append(DependencyNeed(
        dependency_id=f"DEP-{uuid.uuid4().hex[:8].upper()}",
        project_id=project_id,
        dependency_type="logistics",
        description=f"Logistics to destination{': ' + destination if destination else ''}",
        required_specs={"destination": destination or "TBD", "quantity": quantity},
        quantity_required=quantity,
        risk_level="low",
        why_needed="Delivery lead time and cost affect the final feasibility response to buyer.",
        candidate_actor_ids=candidate_logistics_ids or [],
    ))

    log_m_event(
        event_type="UPSTREAM_DEPENDENCY_PLANNED",
        b_workspace_id=project_id,
        supplier_id=main_supplier_actor_id,
        payload={
            "dependency_count": len(deps),
            "dependency_types": [d.dependency_type for d in deps],
            "project_id": project_id,
        },
    )

    return deps


def plan_dependencies_from_cad_cnc_match(
    project_id: str,
    match_result: "CADCNCMachiningMatchResult",
    main_supplier_actor_id: str,
) -> list[DependencyNeed]:
    """
    Derive upstream/subcontractor dependency needs from a CAD-CNC match result.

    Rules (from spec section 11):
    - material_fit == purchasable → raw_material supplier inquiry
    - surface_finish_fit == requires_external_process → surface_treatment subcontractor
    - qc_fit == external_qc_required → qc_testing provider
    - schedule_fit == limited → subcontract_process (backup capacity)
    - work_envelope_fit == not_fit → subcontract_process (full machining)
    - tolerance_fit == marginal → qc_testing (process review)
    - tooling_fit == setup_required → subcontract_process (tooling confirmation)
    """
    deps: list[DependencyNeed] = []

    if match_result.material_fit == "purchasable":
        deps.append(DependencyNeed(
            dependency_id=f"DEP-{uuid.uuid4().hex[:8].upper()}",
            project_id=project_id,
            dependency_type="raw_material",
            description=f"Raw material procurement required — not in stock",
            required_specs={"material": match_result.actor_id, "fit": match_result.material_fit},
            risk_level="high",
            why_needed="Material not in stock; purchase required before production can start.",
            candidate_actor_ids=[],
        ))

    if match_result.surface_finish_fit == "requires_external_process":
        deps.append(DependencyNeed(
            dependency_id=f"DEP-{uuid.uuid4().hex[:8].upper()}",
            project_id=project_id,
            dependency_type="surface_treatment",
            description="External surface treatment / polishing required",
            required_specs={"surface_finish_fit": match_result.surface_finish_fit},
            risk_level="medium",
            why_needed="Required surface finish cannot be achieved in-house.",
            candidate_actor_ids=[],
        ))

    if match_result.qc_fit in ("external_qc_required", "missing"):
        deps.append(DependencyNeed(
            dependency_id=f"DEP-{uuid.uuid4().hex[:8].upper()}",
            project_id=project_id,
            dependency_type="qc_testing",
            description="External QC provider required for inspection",
            required_specs={"qc_fit": match_result.qc_fit},
            risk_level="medium",
            why_needed="In-house QC cannot satisfy the required inspection standard.",
            candidate_actor_ids=[],
        ))

    if match_result.schedule_fit == "limited":
        deps.append(DependencyNeed(
            dependency_id=f"DEP-{uuid.uuid4().hex[:8].upper()}",
            project_id=project_id,
            dependency_type="subcontract_process",
            description="Backup subcontractor capacity required — shop schedule limited",
            required_specs={"schedule_fit": match_result.schedule_fit},
            risk_level="medium",
            why_needed="Limited internal capacity; backup subcontractor ensures on-time delivery.",
            candidate_actor_ids=[],
        ))

    if match_result.work_envelope_fit == "not_fit":
        deps.append(DependencyNeed(
            dependency_id=f"DEP-{uuid.uuid4().hex[:8].upper()}",
            project_id=project_id,
            dependency_type="subcontract_process",
            description="Full subcontract machining required — part exceeds work envelope",
            required_specs={"work_envelope_fit": "not_fit"},
            risk_level="high",
            why_needed="Part dimensions exceed all in-house machine envelopes.",
            candidate_actor_ids=[],
        ))

    if match_result.tolerance_fit == "marginal":
        deps.append(DependencyNeed(
            dependency_id=f"DEP-{uuid.uuid4().hex[:8].upper()}",
            project_id=project_id,
            dependency_type="qc_testing",
            description="QC process review required — tolerance is marginal",
            required_specs={"tolerance_fit": "marginal"},
            risk_level="medium",
            why_needed="Tolerance is close to machine limit; QC validation required.",
            candidate_actor_ids=[],
        ))

    if match_result.tooling_fit == "setup_required":
        deps.append(DependencyNeed(
            dependency_id=f"DEP-{uuid.uuid4().hex[:8].upper()}",
            project_id=project_id,
            dependency_type="component",
            description="Tooling setup confirmation required",
            required_specs={"tooling_fit": "setup_required"},
            risk_level="low",
            why_needed="Some tooling setup required before production can start.",
            candidate_actor_ids=[],
        ))

    # Log each dependency created
    for dep in deps:
        log_m_event(
            event_type="DEPENDENCY_CREATED_FROM_CAD_CNC_MATCH",
            b_workspace_id=project_id,
            supplier_id=main_supplier_actor_id,
            payload={
                "dependency_id": dep.dependency_id,
                "dependency_type": dep.dependency_type,
                "risk_level": dep.risk_level,
                "match_id": getattr(match_result, "match_id", None),
            },
        )

    return deps
