"""On-time delivery probability calculator."""

from __future__ import annotations

import math
from datetime import date

from ..models.duration import DurationEstimate


class OnTimeProbabilityCalculator:
    """Computes probability of delivering by a target date.

    Uses a log-normal distribution approximation parameterised from
    p50 and p90 percentiles.
    """

    def compute(
        self,
        start_date: date,
        duration_estimate: DurationEstimate | None,
        target_date: date | None,
    ) -> float | None:
        """Return probability (0–1) of finishing by target_date, or None."""
        if target_date is None or duration_estimate is None:
            return None

        available_days = (target_date - start_date).days
        if available_days <= 0:
            return 0.0

        p50 = duration_estimate.p50_days
        p90 = duration_estimate.p90_days

        if p50 <= 0:
            return 1.0

        # Approximate log-normal parameters from p50 and p90
        # p50 = exp(mu)  =>  mu = ln(p50)
        # p90 = exp(mu + 1.2816 * sigma)  =>  sigma = (ln(p90) - ln(p50)) / 1.2816
        mu = math.log(max(p50, 0.1))
        if p90 > p50:
            sigma = (math.log(max(p90, p50 + 0.1)) - mu) / 1.2816
        else:
            sigma = 0.1  # small default variance

        # CDF of log-normal at available_days
        # P(X <= x) = Phi((ln(x) - mu) / sigma)
        if available_days <= 0:
            return 0.0

        z = (math.log(max(available_days, 0.1)) - mu) / max(sigma, 0.01)
        prob = self._normal_cdf(z)
        return round(min(1.0, max(0.0, prob)), 4)

    def _normal_cdf(self, z: float) -> float:
        """Standard normal CDF using math.erf."""
        return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

    def from_option_dates(
        self,
        commitable_date: date | None,
        risk_adjusted_date: date | None,
        target_date: date | None,
    ) -> float | None:
        """Estimate probability from high-level date fields.

        Simpler heuristic when full distribution is unavailable.
        """
        if target_date is None or commitable_date is None:
            return None

        delta_commitable = (target_date - commitable_date).days
        if delta_commitable >= 14:
            return 0.95
        elif delta_commitable >= 7:
            return 0.85
        elif delta_commitable >= 0:
            return 0.70
        elif delta_commitable >= -7:
            return 0.45
        elif delta_commitable >= -14:
            return 0.25
        else:
            return 0.10
