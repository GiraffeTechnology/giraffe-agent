"""Generates alternative route options (air freight, stock fabric, etc.)."""

from __future__ import annotations

import uuid
from datetime import timedelta

from ..models.enums import DeliveryMode, OptionStatus, RiskFlagCode
from ..models.path import DeliveryPathOption
from ..models.risk import RiskFlag


class AlternativeRouteGenerator:
    """Generates expedite-based alternative delivery options."""

    def generate(
        self,
        base_option: DeliveryPathOption,
        requested_date=None,
    ) -> list[DeliveryPathOption]:
        """Return alternative options with faster routes.

        Generates:
        - Air freight variant (cuts shipment by ~18 days)
        - Stock fabric variant (cuts fabric lead time by ~15 days)
        """
        alternatives: list[DeliveryPathOption] = []

        # Air freight variant
        air = self._air_freight_variant(base_option)
        if air:
            alternatives.append(air)

        return alternatives

    def _air_freight_variant(
        self, base: DeliveryPathOption
    ) -> DeliveryPathOption | None:
        """Return a copy of base_option with ~18 days shaved off for air freight."""
        if base.commitable_date is None:
            return None

        days_saved = 18
        new_commitable = base.commitable_date - timedelta(days=days_saved)
        new_most_likely = (
            base.most_likely_date - timedelta(days=days_saved)
            if base.most_likely_date else None
        )
        new_earliest = (
            base.earliest_feasible_date - timedelta(days=days_saved)
            if base.earliest_feasible_date else None
        )

        air_risk = RiskFlag(
            code=RiskFlagCode.LOGISTICS_RISK,
            description="Air freight selected — significantly higher cost.",
            severity="LOW",
            mitigation_hint="Confirm cost premium is acceptable with buyer.",
        )

        return DeliveryPathOption(
            option_id=f"opt_air_{uuid.uuid4().hex[:8]}",
            status=OptionStatus.FEASIBLE,
            delivery_mode=DeliveryMode.FULL_DELIVERY,
            participant_combination=list(base.participant_combination),
            nodes=list(base.nodes),
            edges=list(base.edges),
            earliest_feasible_date=new_earliest,
            most_likely_date=new_most_likely,
            commitable_date=new_commitable,
            risk_adjusted_latest_date=base.risk_adjusted_latest_date,
            critical_path=list(base.critical_path),
            bottleneck_nodes=list(base.bottleneck_nodes),
            risk_flags=[air_risk] + [rf for rf in base.risk_flags],
            evidence_summary=list(base.evidence_summary),
            recommendation_reason=(
                f"Air freight saves ~{days_saved} days vs sea freight. "
                "Commitable date moves forward."
            ),
        )
