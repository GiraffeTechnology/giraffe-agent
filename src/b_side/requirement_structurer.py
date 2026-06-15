"""
Deterministic buyer requirement parser for B-side AI Buyer.
No LLM required — uses regex and keyword matching.
"""

import re
import uuid
from datetime import datetime, timezone

from src.core_schema.b_side_types import BuyerRequirement


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_quantity(text: str) -> int | None:
    """Extract numeric quantity from text."""
    patterns = [
        r"(\d[\d,]*)\s*pcs",
        r"(\d[\d,]*)\s*pieces",
        r"(\d[\d,]*)\s*units",
        r"(\d[\d,]*)\s*个",
        r"(\d[\d,]*)\s*件",
        r"(\d[\d,]*)\s*套",
        # Apparel and general product counts with possible modifier words between number and product
        r"(\d[\d,]*)\s+(?:[^\d,\n]{1,60}?\s+)?(?:shirts?|t-shirts?|garments?|jackets?|trousers?|pants?|dresses?|hoodies?)\b",
        r"(\d[\d,]*)\s+(?:[^\d,\n]{1,40}?\s+)?(?:items?|products?|goods?)\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1).replace(",", ""))
    return None


def _parse_material(text: str) -> str | None:
    """Detect material keywords."""
    materials = [
        "aluminum 6061", "6061-T6", "6061", "aluminum", "aluminium",
        "steel", "stainless steel", "carbon steel",
        "fabric", "cotton", "polyester", "nylon",
        "plastic", "ABS", "POM", "HDPE",
        "cardboard", "corrugated",
    ]
    tl = text.lower()
    for mat in materials:
        if mat.lower() in tl:
            return mat
    return None


def _parse_tolerance(text: str) -> str | None:
    """Extract tolerance specification."""
    m = re.search(r"[±+\-]?\s*0\.\d+\s*mm", text, re.IGNORECASE)
    if m:
        return m.group(0).strip()
    return None


def _parse_deadline(text: str) -> str | None:
    """Extract deadline expression."""
    patterns = [
        r"before\s+([A-Za-z]+\s+\d{1,2}(?:,?\s*\d{4})?)",
        r"by\s+([A-Za-z]+\s+\d{1,2}(?:,?\s*\d{4})?)",
        r"delivery\s+(?:before|by)?\s*([A-Za-z]+\s+\d{1,2}(?:,?\s*\d{4})?)",
        r"(\d{4}-\d{2}-\d{2})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _parse_destination(text: str) -> str | None:
    """Detect destination city/country."""
    cities = [
        "Munich", "Berlin", "Hamburg", "Frankfurt",
        "Shanghai", "Shenzhen", "Guangzhou", "Beijing",
        "New York", "Los Angeles", "Chicago",
        "London", "Paris", "Amsterdam",
        "Tokyo", "Singapore", "Hong Kong",
        # North America
        "Vancouver", "Toronto", "Montreal", "Calgary",
        "Seattle", "San Francisco", "Boston", "Miami", "Dallas",
        # Europe
        "Madrid", "Barcelona", "Rome", "Milan", "Stockholm",
        "Oslo", "Copenhagen", "Vienna", "Warsaw", "Zurich",
        # Asia-Pacific
        "Sydney", "Melbourne", "Auckland", "Seoul", "Bangkok",
        "Taipei", "Jakarta", "Kuala Lumpur", "Mumbai", "Delhi",
        # Middle East
        "Dubai", "Abu Dhabi", "Riyadh",
        # Country-level destinations
        "Canada", "United States", "USA", "UK", "Germany",
        "France", "Australia", "Japan",
    ]
    tl = text.lower()
    for city in cities:
        if city.lower() in tl:
            return city
    return None


def _parse_category(text: str) -> str:
    """Detect product category from keywords."""
    tl = text.lower()
    cnc_keywords = ["cnc", "machined", "bracket", "motor mount", "tolerance", "anodized",
                    "milled", "turned", "precision", "6061", "aluminum part"]
    apparel_keywords = ["fabric", "cotton", "apparel", "garment", "t-shirt", "shirt",
                        "sewing", "stitching", "clothing"]
    packaging_keywords = ["packaging", "box", "carton", "corrugated", "label",
                          "bag", "pouch", "wrap"]
    for kw in cnc_keywords:
        if kw in tl:
            return "cnc"
    for kw in apparel_keywords:
        if kw in tl:
            return "apparel"
    for kw in packaging_keywords:
        if kw in tl:
            return "packaging"
    return "general"


def structure_requirement(b_workspace_id: str, raw_text: str) -> BuyerRequirement:
    """
    Parse raw buyer requirement text into a structured BuyerRequirement.
    Deterministic — no LLM calls.
    """
    rfq_id = f"RFQ-{uuid.uuid4().hex[:8].upper()}"

    quantity = _parse_quantity(raw_text)
    material = _parse_material(raw_text)
    tolerance = _parse_tolerance(raw_text)
    deadline = _parse_deadline(raw_text)
    destination = _parse_destination(raw_text)
    category = _parse_category(raw_text)

    specs: dict = {}
    if tolerance:
        specs["tolerance"] = tolerance
    if "anodized" in raw_text.lower() or "anodizing" in raw_text.lower():
        specs["surface_finish"] = "black anodized"

    # Determine missing fields
    missing_fields: list[str] = []
    if quantity is None:
        missing_fields.append("quantity")
    if material is None:
        missing_fields.append("material")
    if deadline is None:
        missing_fields.append("deadline")
    if destination is None:
        missing_fields.append("destination")

    # Confidence: percent of key fields present
    key_fields = [quantity, material, deadline, destination]
    filled = sum(1 for f in key_fields if f is not None)
    confidence_score = round(filled / len(key_fields), 2)

    return BuyerRequirement(
        rfq_id=rfq_id,
        b_workspace_id=b_workspace_id,
        raw_text=raw_text,
        category=category,
        quantity=quantity,
        material=material,
        specs_json=specs,
        deadline=deadline,
        destination=destination,
        missing_fields=missing_fields,
        confidence_score=confidence_score,
        created_at=_utcnow(),
    )
