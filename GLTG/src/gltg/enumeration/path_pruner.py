"""Prunes infeasible delivery path options."""

from __future__ import annotations

from datetime import date

from ..models.enums import OptionStatus
from ..models.path import DeliveryPathOption


class PathPruner:
    """Filters and classifies options as feasible, tight, or infeasible."""

    def prune(
        self,
        options: list[DeliveryPathOption],
        requested_date: date | None,
    ) -> list[DeliveryPathOption]:
        """Mark options that cannot meet the requested delivery date.

        Infeasible options are kept (for reporting) with status=INFEASIBLE.
        Feasible options are classified as FEASIBLE, TIGHT, or REQUIRES_EXPEDITE.
        """
        if not options:
            return options

        result: list[DeliveryPathOption] = []
        for option in options:
            option = self._classify(option, requested_date)
            result.append(option)

        return result

    def _classify(
        self,
        option: DeliveryPathOption,
        requested_date: date | None,
    ) -> DeliveryPathOption:
        """Set option status based on its dates vs requested_date."""
        if requested_date is None:
            # No target — all options are feasible by default
            option.status = OptionStatus.FEASIBLE
            return option

        commitable = option.commitable_date
        most_likely = option.most_likely_date
        earliest = option.earliest_feasible_date

        if commitable is None:
            option.status = OptionStatus.INFEASIBLE
            option.infeasibility_reason = "No commitable date could be resolved."
            return option

        if commitable <= requested_date:
            # On track — check how tight
            days_buffer = (requested_date - commitable).days
            if days_buffer >= 7:
                option.status = OptionStatus.FEASIBLE
            else:
                option.status = OptionStatus.TIGHT
        elif most_likely and most_likely <= requested_date:
            option.status = OptionStatus.REQUIRES_EXPEDITE
            option.infeasibility_reason = (
                f"Most likely date {most_likely} meets deadline but commitable date "
                f"{commitable} does not — requires some acceleration."
            )
        elif earliest and earliest <= requested_date:
            option.status = OptionStatus.REQUIRES_EXPEDITE
            option.infeasibility_reason = (
                f"Only earliest feasible date {earliest} meets deadline — "
                "requires significant expediting."
            )
        else:
            option.status = OptionStatus.INFEASIBLE
            option.infeasibility_reason = (
                f"Even the earliest feasible date ({earliest}) is after "
                f"the requested delivery date ({requested_date})."
            )

        return option

    def filter_feasible(
        self, options: list[DeliveryPathOption]
    ) -> list[DeliveryPathOption]:
        """Return only options that are not INFEASIBLE."""
        return [
            o for o in options
            if o.status != OptionStatus.INFEASIBLE
        ]
