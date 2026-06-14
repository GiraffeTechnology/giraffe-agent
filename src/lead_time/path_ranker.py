"""
Path ranker — assigns ranks and labels to LeadTimePaths.
"""
from src.lead_time.models import LeadTimePath


def _composite_score(path: LeadTimePath) -> float:
    lead_factor = 1 / (1 + path.total_lead_time_days / 30.0)
    risk_factor = 1 / (1 + path.risk_score)
    price_factor = 1.0
    if path.unit_price is not None and path.unit_price > 0:
        price_factor = 1 / (1 + path.unit_price / 100.0)
    feasibility_bonus = 1.2 if path.feasible_before_deadline else 0.5
    return path.confidence_score * lead_factor * risk_factor * (1 + price_factor * 0.1) * feasibility_bonus


def rank_paths(paths: list[LeadTimePath]) -> list[LeadTimePath]:
    """Sort paths by composite score descending, assign rank."""
    scored = sorted(paths, key=_composite_score, reverse=True)
    for i, p in enumerate(scored, start=1):
        p.rank = i
    return scored


def assign_labels(paths: list[LeadTimePath]) -> list[LeadTimePath]:
    """Assign FASTEST / LOWEST_COST / SAFEST / BEST_OVERALL / BACKUP labels."""
    if not paths:
        return paths

    ranked = rank_paths(paths)

    # BEST_OVERALL = rank 1
    ranked[0].label = "BEST_OVERALL"

    used_ids = {ranked[0].path_id}

    # FASTEST = min lead time among remaining
    remaining = [p for p in ranked if p.path_id not in used_ids]
    if remaining:
        fastest = min(remaining, key=lambda p: p.total_lead_time_days)
        if fastest.path_id != ranked[0].path_id:
            fastest.label = "FASTEST"
            used_ids.add(fastest.path_id)

    # LOWEST_COST = min price among remaining
    remaining = [p for p in ranked if p.path_id not in used_ids and p.unit_price is not None]
    if remaining:
        cheapest = min(remaining, key=lambda p: p.unit_price or float("inf"))
        if cheapest:
            cheapest.label = "LOWEST_COST"
            used_ids.add(cheapest.path_id)

    # SAFEST = min risk_flags among remaining
    remaining = [p for p in ranked if p.path_id not in used_ids]
    if remaining:
        safest = min(remaining, key=lambda p: len(p.risk_flags))
        safest.label = "SAFEST"
        used_ids.add(safest.path_id)

    # BACKUP = rest
    for p in ranked:
        if p.path_id not in used_ids:
            p.label = "BACKUP"

    return ranked
