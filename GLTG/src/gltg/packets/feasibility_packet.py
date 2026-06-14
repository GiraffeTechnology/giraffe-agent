"""Assembles the final DeliveryFeasibilityPacket from ranked options."""

from __future__ import annotations

from datetime import date, datetime

from ..models.enums import FeasibilityStatus, OptionStatus, RiskFlagCode
from ..models.packet import DeliveryFeasibilityPacket
from ..models.path import DeliveryPathOption
from ..models.risk import RiskFlag


class FeasibilityPacketBuilder:
    """Builds a DeliveryFeasibilityPacket from a set of scored options."""

    def build(
        self,
        order_id: str,
        options: list[DeliveryPathOption],
        missing_fields: list[str],
        risk_flags: list[RiskFlag],
        requested_date: date | None = None,
    ) -> DeliveryFeasibilityPacket:
        """Assemble the packet.

        Feasibility rules:
          - 0 options: NO_FEASIBLE_OPTION
          - 1 option: LIMITED_OPTIONS + LIMITED_COMPETITION flag
          - 2 options: LIMITED_OPTIONS + LIMITED_COMPARISON flag
          - 3+ options: FEASIBLE (return top 3)
        """
        feasible_options = [o for o in options if o.status != OptionStatus.INFEASIBLE]
        n = len(feasible_options)

        extra_flags: list[RiskFlag] = []

        if n == 0:
            status = FeasibilityStatus.NO_FEASIBLE_OPTION
            extra_flags.append(RiskFlag(
                code=RiskFlagCode.NO_FEASIBLE_OPTION,
                description="No feasible delivery path found for this order.",
                severity="CRITICAL",
                mitigation_hint="Revise requirements, extend deadline, or find additional suppliers.",
            ))
            top_options: list[DeliveryPathOption] = []
            recommended_action = "No feasible delivery path. Human review required."
            human_review = True

        elif n == 1:
            status = FeasibilityStatus.LIMITED_OPTIONS
            extra_flags.append(RiskFlag(
                code=RiskFlagCode.LIMITED_COMPETITION,
                description="Only one feasible delivery option found — limited competition.",
                severity="MEDIUM",
                mitigation_hint="Source additional participants to increase competition.",
            ))
            top_options = feasible_options[:1]
            recommended_action = "Proceed with caution — only one option available."
            human_review = True

        elif n == 2:
            status = FeasibilityStatus.LIMITED_OPTIONS
            extra_flags.append(RiskFlag(
                code=RiskFlagCode.LIMITED_COMPARISON,
                description="Only two feasible delivery options — limited comparison.",
                severity="LOW",
                mitigation_hint="Consider sourcing a third option for better comparison.",
            ))
            top_options = feasible_options[:2]
            recommended_action = "Two options available — review both before deciding."
            human_review = False

        else:
            status = FeasibilityStatus.FEASIBLE
            top_options = feasible_options[:3]
            recommended_action = "Review top 3 options and select the best fit."
            human_review = False

        # If any option requires expedite, escalate status
        if status == FeasibilityStatus.FEASIBLE and any(
            o.status == OptionStatus.REQUIRES_EXPEDITE for o in top_options
        ):
            status = FeasibilityStatus.REQUIRES_EXPEDITE

        # Derive packet-level dates from the best (first) option
        best = top_options[0] if top_options else None
        earliest = best.earliest_feasible_date if best else None
        most_likely = best.most_likely_date if best else None
        commitable = best.commitable_date if best else None
        risk_adj = best.risk_adjusted_latest_date if best else None
        critical_path = best.critical_path if best else []
        bottlenecks = best.bottleneck_nodes if best else []
        otp = best.on_time_probability if best else None

        # Collect all evidence from options
        all_evidence = []
        for opt in top_options:
            all_evidence.extend(opt.evidence_summary)
        # Deduplicate by evidence_id
        seen = set()
        unique_evidence = []
        for ev in all_evidence:
            if ev.evidence_id not in seen:
                seen.add(ev.evidence_id)
                unique_evidence.append(ev)

        all_flags = list(risk_flags) + extra_flags
        # Deduplicate flags by code
        seen_codes = set()
        unique_flags = []
        for rf in all_flags:
            if rf.code not in seen_codes:
                seen_codes.add(rf.code)
                unique_flags.append(rf)

        return DeliveryFeasibilityPacket(
            order_id=order_id,
            status=status,
            generated_at=datetime.utcnow(),
            earliest_feasible_date=earliest,
            most_likely_date=most_likely,
            commitable_date=commitable,
            risk_adjusted_latest_date=risk_adj,
            on_time_probability=otp,
            options=top_options,
            critical_path=critical_path,
            bottleneck_nodes=bottlenecks,
            risk_flags=unique_flags,
            missing_fields=missing_fields,
            evidence_summary=unique_evidence[:30],
            recommended_action=recommended_action,
            human_review_required=human_review,
        )
