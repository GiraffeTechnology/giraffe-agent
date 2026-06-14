"""
Upstream Option Engine — generates 1–3 recommended options from upstream supplier responses.
"""

import uuid
from typing import Literal
from pydantic import BaseModel, Field

from src.m_side.upstream.response_parser import UpstreamResponse
from src.m_side.m_event_logger import log_m_event
from src.lead_time.evidence import make_evidence_ref, EVIDENCE_TYPE_SUPPLIER_STATED, EVIDENCE_TYPE_DEFAULT_ASSUMPTION


class UpstreamOption(BaseModel):
    option_id: str
    project_id: str
    dependency_id: str
    dependency_type: str
    upstream_actor_id: str
    option_label: Literal["BEST", "FASTEST", "SAFEST", "LOWEST_COST", "BACKUP"]
    price_summary: str
    lead_time_summary: str
    risk_summary: str
    score: float
    reason: str
    response_ids: list[str] = Field(default_factory=list)
    # Lead time evidence fields (new)
    lead_time_components: list[dict] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    dispatch_lead_time_days: int | None = None  # supplier-stated dispatch
    material_availability_days: int | None = None
    shipping_to_manufacturer_days: int | None = None
    lead_time_risk_flags: list[str] = Field(default_factory=list)


def _score_response(r: UpstreamResponse) -> float:
    if not r.can_supply:
        return 0.0
    lead = r.lead_time_days or 999
    price = r.price or 9999.0
    confidence = r.confidence_score or 0.1
    red_flags = len(r.risk_flags)
    score = confidence / (1 + lead / 30.0) / (1 + red_flags * 0.1)
    price_factor = 1 / (1 + price / 100.0)
    return round(score * (1 + price_factor * 0.1), 4)


def _fmt_price(r: UpstreamResponse) -> str:
    if r.price is not None and r.currency:
        return f"{r.currency} {r.price:.2f}"
    if r.price is not None:
        return f"{r.price:.2f}"
    return "price TBC"


def _fmt_lead(r: UpstreamResponse) -> str:
    if r.lead_time_days:
        return f"{r.lead_time_days} days"
    return "lead time TBC"


def _fmt_risk(r: UpstreamResponse) -> str:
    if not r.risk_flags:
        return "No significant risks"
    return "; ".join(r.risk_flags)


def _build_upstream_lt_evidence(r: UpstreamResponse) -> list[str]:
    """Build evidence refs for upstream lead time."""
    refs = []
    if r.lead_time_days is not None:
        refs.append(make_evidence_ref(EVIDENCE_TYPE_SUPPLIER_STATED, r.response_id, f"dispatch:{r.lead_time_days}d"))
    else:
        refs.append(make_evidence_ref(EVIDENCE_TYPE_DEFAULT_ASSUMPTION, r.response_id, "dispatch:unknown"))
    return refs


def generate_upstream_options(
    project_id: str,
    dependency_id: str,
    dependency_type: str,
    responses: list[UpstreamResponse],
    main_supplier_actor_id: str,
) -> list[UpstreamOption]:
    """
    Generate up to 3 upstream options (BEST, FASTEST, SAFEST) from parsed responses.
    Filters out responses where can_supply=False.
    """
    viable = [r for r in responses if r.can_supply]
    if not viable:
        log_m_event(
            event_type="UPSTREAM_OPTIONS_GENERATED",
            b_workspace_id=project_id,
            supplier_id=main_supplier_actor_id,
            payload={
                "dependency_id": dependency_id,
                "dependency_type": dependency_type,
                "option_count": 0,
                "note": "No viable suppliers found",
            },
        )
        return []

    scored = sorted(viable, key=_score_response, reverse=True)
    options: list[UpstreamOption] = []

    # BEST — highest composite score
    best = scored[0]
    options.append(UpstreamOption(
        option_id=f"OPT-{uuid.uuid4().hex[:8].upper()}",
        project_id=project_id,
        dependency_id=dependency_id,
        dependency_type=dependency_type,
        upstream_actor_id=best.upstream_actor_id,
        option_label="BEST",
        price_summary=_fmt_price(best),
        lead_time_summary=_fmt_lead(best),
        risk_summary=_fmt_risk(best),
        score=_score_response(best),
        reason=(
            f"Best overall score (confidence={best.confidence_score:.2f}, "
            f"completeness={best.completeness_score:.2f}). "
            f"Price {_fmt_price(best)}, lead time {_fmt_lead(best)}."
        ),
        response_ids=[best.response_id],
        dispatch_lead_time_days=best.lead_time_days,
        material_availability_days=None,
        shipping_to_manufacturer_days=None,
        lead_time_risk_flags=["lead_time_not_confirmed"] if best.lead_time_days is None else [],
        evidence_refs=_build_upstream_lt_evidence(best),
    ))

    # FASTEST — shortest lead time
    fastest = min(viable, key=lambda r: r.lead_time_days or 9999)
    if fastest.upstream_actor_id != best.upstream_actor_id:
        options.append(UpstreamOption(
            option_id=f"OPT-{uuid.uuid4().hex[:8].upper()}",
            project_id=project_id,
            dependency_id=dependency_id,
            dependency_type=dependency_type,
            upstream_actor_id=fastest.upstream_actor_id,
            option_label="FASTEST",
            price_summary=_fmt_price(fastest),
            lead_time_summary=_fmt_lead(fastest),
            risk_summary=_fmt_risk(fastest),
            score=_score_response(fastest),
            reason=(
                f"Fastest delivery: {_fmt_lead(fastest)}. "
                f"Price {_fmt_price(fastest)}. "
                f"Trade-off: may have higher price or lower confidence."
            ),
            response_ids=[fastest.response_id],
            dispatch_lead_time_days=fastest.lead_time_days,
            material_availability_days=None,
            shipping_to_manufacturer_days=None,
            lead_time_risk_flags=["lead_time_not_confirmed"] if fastest.lead_time_days is None else [],
            evidence_refs=_build_upstream_lt_evidence(fastest),
        ))

    # SAFEST / BACKUP — fewest risk flags among remaining
    remaining = [r for r in viable if r.upstream_actor_id not in {best.upstream_actor_id, fastest.upstream_actor_id}]
    if remaining:
        safest = min(remaining, key=lambda r: len(r.risk_flags))
        options.append(UpstreamOption(
            option_id=f"OPT-{uuid.uuid4().hex[:8].upper()}",
            project_id=project_id,
            dependency_id=dependency_id,
            dependency_type=dependency_type,
            upstream_actor_id=safest.upstream_actor_id,
            option_label="SAFEST" if len(safest.risk_flags) == 0 else "BACKUP",
            price_summary=_fmt_price(safest),
            lead_time_summary=_fmt_lead(safest),
            risk_summary=_fmt_risk(safest),
            score=_score_response(safest),
            reason=(
                f"{'Fewest risk flags' if not safest.risk_flags else 'Backup option'}. "
                f"Price {_fmt_price(safest)}, lead time {_fmt_lead(safest)}. "
                f"Risks: {_fmt_risk(safest)}."
            ),
            response_ids=[safest.response_id],
            dispatch_lead_time_days=safest.lead_time_days,
            material_availability_days=None,
            shipping_to_manufacturer_days=None,
            lead_time_risk_flags=["lead_time_not_confirmed"] if safest.lead_time_days is None else [],
            evidence_refs=_build_upstream_lt_evidence(safest),
        ))
    elif len(options) == 1 and len(viable) >= 2:
        # if FASTEST was same as BEST, use 2nd scored as BACKUP
        backup = scored[1] if len(scored) > 1 else None
        if backup:
            options.append(UpstreamOption(
                option_id=f"OPT-{uuid.uuid4().hex[:8].upper()}",
                project_id=project_id,
                dependency_id=dependency_id,
                dependency_type=dependency_type,
                upstream_actor_id=backup.upstream_actor_id,
                option_label="BACKUP",
                price_summary=_fmt_price(backup),
                lead_time_summary=_fmt_lead(backup),
                risk_summary=_fmt_risk(backup),
                score=_score_response(backup),
                reason=f"Backup option. Score={_score_response(backup):.4f}.",
                response_ids=[backup.response_id],
                dispatch_lead_time_days=backup.lead_time_days,
                material_availability_days=None,
                shipping_to_manufacturer_days=None,
                lead_time_risk_flags=["lead_time_not_confirmed"] if backup.lead_time_days is None else [],
                evidence_refs=_build_upstream_lt_evidence(backup),
            ))

    log_m_event(
        event_type="UPSTREAM_OPTIONS_GENERATED",
        b_workspace_id=project_id,
        supplier_id=main_supplier_actor_id,
        payload={
            "dependency_id": dependency_id,
            "dependency_type": dependency_type,
            "option_count": len(options),
            "option_labels": [o.option_label for o in options],
            "viable_supplier_count": len(viable),
        },
    )

    return options
