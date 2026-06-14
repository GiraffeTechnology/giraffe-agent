"""Generates split/partial delivery options."""

from __future__ import annotations

import uuid
from datetime import timedelta

from ..models.enums import DeliveryMode, OptionStatus
from ..models.path import DeliveryPathOption
from ..models.risk import RiskFlag
from ..models.enums import RiskFlagCode


class BatchSplitAnalyzer:
    """Creates split-delivery options from a base full-delivery option."""

    DEFAULT_SPLIT_FRACTIONS = [0.4, 0.6]  # first batch / remainder

    def generate_splits(
        self,
        base_option: DeliveryPathOption,
        quantity: int,
        split_fractions: list[float] | None = None,
    ) -> list[DeliveryPathOption]:
        """Return split-delivery variants of base_option.

        The first batch delivers the fast fraction early,
        the remainder follows later.
        """
        fractions = split_fractions or self.DEFAULT_SPLIT_FRACTIONS
        if len(fractions) < 2:
            return []

        options: list[DeliveryPathOption] = []

        first_frac, second_frac = fractions[0], fractions[1]
        first_qty = int(quantity * first_frac)
        second_qty = quantity - first_qty

        # First batch: same commitable date but partial quantity
        first_commitable = base_option.commitable_date
        # Second batch: add an offset proportional to remaining quantity
        if base_option.commitable_date and base_option.risk_adjusted_latest_date:
            extra_days = int(
                (base_option.risk_adjusted_latest_date - base_option.commitable_date).days
                * second_frac
            )
            second_commitable = base_option.commitable_date + timedelta(days=max(extra_days, 7))
        else:
            second_commitable = base_option.commitable_date

        split_risk = RiskFlag(
            code=RiskFlagCode.LOGISTICS_RISK,
            description=(
                f"Split shipment: {first_qty} pcs by {first_commitable}, "
                f"{second_qty} pcs by {second_commitable}."
            ),
            severity="LOW",
            mitigation_hint="Confirm buyer accepts partial delivery.",
        )

        split_option = DeliveryPathOption(
            option_id=f"opt_split_{uuid.uuid4().hex[:8]}",
            status=OptionStatus.FEASIBLE,
            delivery_mode=DeliveryMode.SPLIT_SHIPMENT,
            participant_combination=list(base_option.participant_combination),
            nodes=list(base_option.nodes),
            edges=list(base_option.edges),
            earliest_feasible_date=base_option.earliest_feasible_date,
            most_likely_date=base_option.most_likely_date,
            commitable_date=first_commitable,
            risk_adjusted_latest_date=second_commitable,
            on_time_probability=base_option.on_time_probability,
            critical_path=list(base_option.critical_path),
            bottleneck_nodes=list(base_option.bottleneck_nodes),
            risk_flags=[split_risk] + list(base_option.risk_flags),
            evidence_summary=list(base_option.evidence_summary),
            recommendation_reason=(
                f"Split delivery: {int(first_frac * 100)}% first, "
                f"{int(second_frac * 100)}% remainder."
            ),
        )
        options.append(split_option)
        return options
