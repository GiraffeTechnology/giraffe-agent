"""Apparel category baseline lead times in working days."""

from __future__ import annotations

from ..models.enums import ApparelNodeType

# Default baselines for each node type.
# Keys: p50, p80, p90, min, max
_STATIC_BASELINES: dict[ApparelNodeType, dict[str, float]] = {
    ApparelNodeType.BUYER_REQUIREMENT_CONFIRMATION: dict(p50=2, p80=3, p90=5, min=1, max=7),
    ApparelNodeType.DESIGN_OR_TECH_PACK_CONFIRMATION: dict(p50=3, p80=5, p90=7, min=2, max=10),
    ApparelNodeType.FABRIC_SELECTION: dict(p50=3, p80=5, p90=7, min=1, max=10),
    ApparelNodeType.FABRIC_AVAILABILITY_CONFIRMATION: dict(p50=2, p80=3, p90=5, min=1, max=7),
    ApparelNodeType.FABRIC_ORDERING: dict(p50=21, p80=28, p90=35, min=14, max=45),
    ApparelNodeType.FABRIC_DYEING_OR_PRINTING: dict(p50=10, p80=14, p90=21, min=7, max=30),
    ApparelNodeType.FABRIC_FINISHING: dict(p50=5, p80=7, p90=10, min=3, max=14),
    ApparelNodeType.FABRIC_TESTING: dict(p50=7, p80=10, p90=14, min=5, max=21),
    ApparelNodeType.TRIM_SELECTION: dict(p50=2, p80=3, p90=5, min=1, max=7),
    ApparelNodeType.TRIM_AVAILABILITY_CONFIRMATION: dict(p50=2, p80=3, p90=5, min=1, max=7),
    ApparelNodeType.TRIM_ORDERING: dict(p50=14, p80=21, p90=28, min=7, max=35),
    ApparelNodeType.PACKAGING_MATERIAL_CONFIRMATION: dict(p50=2, p80=3, p90=5, min=1, max=7),
    ApparelNodeType.SAMPLE_MAKING: dict(p50=7, p80=10, p90=14, min=5, max=21),
    ApparelNodeType.SAMPLE_APPROVAL: dict(p50=5, p80=7, p90=10, min=3, max=14),
    ApparelNodeType.PP_SAMPLE_APPROVAL: dict(p50=3, p80=5, p90=7, min=2, max=10),
    ApparelNodeType.PRODUCTION_SLOT_BOOKING: dict(p50=2, p80=3, p90=5, min=1, max=7),
    ApparelNodeType.CUTTING: dict(p50=2, p80=3, p90=4, min=1, max=7),
    # SEWING is quantity-based -- handled separately
    ApparelNodeType.SEWING: dict(p50=7, p80=10, p90=14, min=5, max=21),
    ApparelNodeType.WASHING_OR_FINISHING: dict(p50=3, p80=5, p90=7, min=2, max=10),
    ApparelNodeType.INLINE_QC: dict(p50=1, p80=2, p90=3, min=1, max=5),
    ApparelNodeType.FINAL_QC: dict(p50=2, p80=3, p90=4, min=1, max=7),
    ApparelNodeType.REWORK_IF_NEEDED: dict(p50=3, p80=5, p90=7, min=1, max=14),
    ApparelNodeType.PACKING: dict(p50=2, p80=3, p90=4, min=1, max=7),
    ApparelNodeType.LOGISTICS_BOOKING: dict(p50=3, p80=5, p90=7, min=2, max=10),
    ApparelNodeType.CUSTOMS_OR_EXPORT_DOCS: dict(p50=2, p80=3, p90=5, min=1, max=7),
    ApparelNodeType.SHIPMENT: dict(p50=21, p80=28, p90=35, min=14, max=45),
    ApparelNodeType.BUYER_RECEIPT: dict(p50=1, p80=2, p90=3, min=1, max=5),
    ApparelNodeType.BUYER_SIGN_OFF: dict(p50=2, p80=3, p90=5, min=1, max=7),
}

_DEFAULT_BASELINE: dict[str, float] = dict(p50=2, p80=3, p90=5, min=1, max=7)

# Sewing: 7 days per 1,000 pcs at p50 baseline; scale linearly
_SEWING_DAYS_PER_1000 = 7.0


def _sewing_baseline(quantity: int) -> dict[str, float]:
    """Scale sewing baseline proportionally to order quantity."""
    ratio = max(quantity, 1) / 1000.0
    p50 = max(1.0, round(_SEWING_DAYS_PER_1000 * ratio, 1))
    p80 = max(1.0, round(p50 * 1.4, 1))
    p90 = max(1.0, round(p50 * 2.0, 1))
    min_d = max(1.0, round(p50 * 0.7, 1))
    max_d = max(1.0, round(p50 * 3.0, 1))
    return dict(p50=p50, p80=p80, p90=p90, min=min_d, max=max_d)


def get_baseline(node_type: ApparelNodeType, quantity: int = 1000) -> dict[str, float]:
    """Return baseline lead-time stats (days) for a node type.

    For SEWING, duration scales with quantity.
    """
    if node_type == ApparelNodeType.SEWING:
        return _sewing_baseline(quantity)
    return dict(_STATIC_BASELINES.get(node_type, _DEFAULT_BASELINE))
