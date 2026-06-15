from datetime import date, datetime

SCORE_WEIGHTS = {
    "category_fit": 0.15,
    "fabric_capability_fit": 0.12,
    "quantity_fit": 0.10,
    "moq_fit": 0.08,
    "capacity_fit": 0.08,
    "lead_time_fit": 0.10,
    "location_fit": 0.07,
    "trade_term_fit": 0.07,
    "quality_history_fit": 0.10,
    "on_time_delivery_fit": 0.08,
    "response_quality_fit": 0.03,
    "risk_penalty": 0.02,  # weight for penalty dimension (applied as subtraction)
}

# Risk penalty weight is separate: subtract from score rather than weight into average
_RISK_PENALTY_WEIGHT = 0.10


def _parse_date(val) -> date | None:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    try:
        return datetime.fromisoformat(str(val)).date()
    except (ValueError, TypeError):
        return None


def score_participant_for_section(
    participant_profile: dict,
    form_fields: dict,
    supplier_memory: dict | None,
    section: dict,
) -> dict:
    """
    Returns score_breakdown dict with all 12 dimensions and final match_score.
    Missing data is set to 0.5 (neutral) and tracked in missing_participant_data.
    """
    breakdown: dict[str, float] = {}
    missing: list[str] = []

    # 1. category_fit
    product_type = form_fields.get("product_type")
    categories = participant_profile.get("product_categories")
    if categories is None:
        breakdown["category_fit"] = 0.5
        missing.append("product_categories")
    elif product_type and isinstance(categories, list):
        breakdown["category_fit"] = 1.0 if product_type in categories else 0.0
    else:
        breakdown["category_fit"] = 0.5

    # 2. fabric_capability_fit
    fabric_type = form_fields.get("fabric_type")
    fabric_caps = participant_profile.get("fabric_capabilities")
    if fabric_caps is None:
        breakdown["fabric_capability_fit"] = 0.5
        missing.append("fabric_capabilities")
    elif fabric_type and isinstance(fabric_caps, list):
        breakdown["fabric_capability_fit"] = 1.0 if fabric_type in fabric_caps else 0.0
    else:
        breakdown["fabric_capability_fit"] = 0.5

    # 3. quantity_fit: 1.0 if quantity between moq and capacity
    quantity = form_fields.get("quantity")
    moq = participant_profile.get("moq")
    cap_max = participant_profile.get("quantity_range_max")
    if quantity is None:
        breakdown["quantity_fit"] = 0.5
    elif moq is None and cap_max is None:
        breakdown["quantity_fit"] = 0.5
        missing.append("moq")
    else:
        above_moq = (moq is None) or (quantity >= moq)
        below_cap = (cap_max is None) or (quantity <= cap_max)
        breakdown["quantity_fit"] = 1.0 if (above_moq and below_cap) else 0.0

    # 4. moq_fit
    if moq is None:
        breakdown["moq_fit"] = 0.5
    elif quantity is None:
        breakdown["moq_fit"] = 0.5
    else:
        breakdown["moq_fit"] = 1.0 if quantity >= moq else 0.0

    # 5. capacity_fit
    if cap_max is None:
        breakdown["capacity_fit"] = 0.5
    elif quantity is None:
        breakdown["capacity_fit"] = 0.5
    else:
        breakdown["capacity_fit"] = 1.0 if cap_max >= quantity else 0.0

    # 6. lead_time_fit
    deadline_raw = form_fields.get("delivery_deadline")
    lt_max = participant_profile.get("lead_time_days_max")
    deadline = _parse_date(deadline_raw)
    if deadline is None or lt_max is None:
        breakdown["lead_time_fit"] = 0.5
        if lt_max is None:
            missing.append("lead_time_days_max")
    else:
        days_available = (deadline - date.today()).days
        breakdown["lead_time_fit"] = 1.0 if lt_max <= days_available else 0.0

    # 7. location_fit: 1.0 if participant country appears in destination
    destination = form_fields.get("destination", "")
    country = participant_profile.get("country")
    if country is None:
        breakdown["location_fit"] = 0.5
        missing.append("country")
    else:
        breakdown["location_fit"] = 1.0 if country.upper() in destination.upper() else 0.5

    # 8. trade_term_fit
    trade_term = form_fields.get("trade_term")
    supported_terms = participant_profile.get("supported_trade_terms")
    if supported_terms is None:
        breakdown["trade_term_fit"] = 0.5
        missing.append("supported_trade_terms")
    elif trade_term and isinstance(supported_terms, list):
        breakdown["trade_term_fit"] = 1.0 if trade_term in supported_terms else 0.0
    else:
        breakdown["trade_term_fit"] = 0.5

    # 9. quality_history_fit: from supplier_memory qc_pass_rate
    qc_pass_rate = (supplier_memory or {}).get("qc_pass_rate")
    if qc_pass_rate is None:
        breakdown["quality_history_fit"] = 0.5
    else:
        breakdown["quality_history_fit"] = float(qc_pass_rate)

    # 10. on_time_delivery_fit: from supplier_memory on_time_delivery (0.0/1.0 or rate)
    otd = (supplier_memory or {}).get("on_time_delivery_rate", (supplier_memory or {}).get("on_time_delivery"))
    if otd is None:
        breakdown["on_time_delivery_fit"] = 0.5
    else:
        breakdown["on_time_delivery_fit"] = float(otd)

    # 11. response_quality_fit: from profile_completeness_score
    completeness = participant_profile.get("profile_completeness_score", 0.5)
    breakdown["response_quality_fit"] = float(completeness)

    # 12. risk_penalty dimension (-1.0 if quality_issue_count >= 2, else 0)
    quality_issue_count = (supplier_memory or {}).get("quality_issue_count", 0)
    breakdown["risk_penalty"] = -1.0 if quality_issue_count >= 2 else 0.0

    # Compute weighted score (exclude risk_penalty from normal sum)
    positive_dims = [k for k in SCORE_WEIGHTS if k != "risk_penalty"]
    total_weight = sum(SCORE_WEIGHTS[k] for k in positive_dims)
    weighted_sum = sum(breakdown[k] * SCORE_WEIGHTS[k] for k in positive_dims)
    base_score = weighted_sum / total_weight if total_weight > 0 else 0.5

    # Apply risk penalty
    penalty = abs(breakdown["risk_penalty"]) * _RISK_PENALTY_WEIGHT
    match_score = max(0.0, min(1.0, base_score - penalty))

    return {
        "match_score": round(match_score, 4),
        "score_breakdown": breakdown,
        "missing_participant_data": missing,
    }


def compute_risk_flags(participant_profile: dict, supplier_memory: dict | None) -> list[str]:
    flags: list[str] = []
    if not supplier_memory:
        flags.append("No quality history")
    else:
        qc_rate = supplier_memory.get("qc_pass_rate")
        if qc_rate is not None and qc_rate < 0.8:
            flags.append("Low QC pass rate")
        otd = supplier_memory.get("on_time_delivery_rate", supplier_memory.get("on_time_delivery"))
        if otd is not None and float(otd) < 0.9:
            flags.append("Late delivery history")
        if supplier_memory.get("quality_issue_count", 0) >= 2:
            flags.append("Approaching replacement threshold")
    if participant_profile.get("profile_completeness_score", 1.0) < 0.5:
        flags.append("Incomplete profile")
    return flags
