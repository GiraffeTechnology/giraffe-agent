"""
M-side capacity checker — infers capacity signal from supplier messages and profile.
"""

from __future__ import annotations
import re
from src.core_schema.m_side_types import CapacitySignal, MSideSupplierProfile
from src.m_side.response_normalizer import _parse_can_make


def infer_capacity_signal(
    response_texts: list[str],
    supplier_profile: MSideSupplierProfile | None = None,
) -> CapacitySignal:
    """
    Infer capacity signal from supplier messages and optional supplier profile.
    """
    combined = " ".join(response_texts)

    can_make = _parse_can_make(combined)
    capacity_available = can_make  # default: capacity matches can_make decision

    # Look for capacity notes
    capacity_notes = None
    if re.search(r"产能已满|backlog|over.?capac", combined, re.IGNORECASE):
        capacity_available = False
        capacity_notes = "Supplier reports full capacity"
    elif re.search(r"有空档|有余量|available capacity", combined, re.IGNORECASE):
        capacity_available = True
        capacity_notes = "Capacity available"

    # Earliest start date
    earliest_start = None
    start_match = re.search(
        r"(?:下周[一二三四五六日]|下周|next week|next Monday|next Tuesday|下周开工|最快下周)",
        combined,
        re.IGNORECASE,
    )
    if start_match:
        earliest_start = start_match.group(0)

    # Production days
    production_days = None
    prod_match = re.search(r"大货\s*(\d+)\s*天|production.*?(\d+)\s*days?", combined, re.IGNORECASE)
    if prod_match:
        val = prod_match.group(1) or prod_match.group(2)
        production_days = int(val) if val else None

    # Monthly capacity hint from profile
    monthly_hint = None
    if supplier_profile and supplier_profile.capability.max_quantity_hint:
        monthly_hint = supplier_profile.capability.max_quantity_hint // 12

    # Bottlenecks
    bottlenecks = []
    if re.search(r"外协|outsourc", combined, re.IGNORECASE):
        bottlenecks.append("anodizing/outsourced process")
    if re.search(r"排队|queue|backlog", combined, re.IGNORECASE):
        bottlenecks.append("production queue")

    return CapacitySignal(
        can_make=can_make,
        capacity_available=capacity_available,
        capacity_notes=capacity_notes,
        earliest_start_date=earliest_start,
        production_days=production_days,
        monthly_capacity_hint=monthly_hint,
        bottlenecks=bottlenecks,
    )
