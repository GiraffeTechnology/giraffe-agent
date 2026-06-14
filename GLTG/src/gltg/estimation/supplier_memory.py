"""Analyses historical supplier records to produce memory-adjusted estimates."""

from __future__ import annotations

import statistics

from ..models.enums import ApparelNodeType
from ..models.participant import SupplierMemoryRecord


class SupplierMemoryAnalyzer:
    """Derives adjusted duration estimates from past performance records."""

    def analyze(
        self,
        participant_id: str,
        node_type: ApparelNodeType | None,
        records: list[SupplierMemoryRecord],
        quantity: int = 1000,
    ) -> dict | None:
        """Return a dict with memory_adjusted_days and confidence, or None.

        Uses actual_days from past records when available,
        falls back to stated_days, scaled by quantity ratio.
        """
        relevant = [
            r for r in records
            if r.participant_id == participant_id
            and (node_type is None or r.node_type == node_type)
        ]

        if not relevant:
            return None

        # Prefer actual_days; fall back to stated_days
        days_values: list[float] = []
        for r in relevant:
            if r.actual_days is not None:
                days_values.append(r.actual_days)
            elif r.stated_days is not None:
                days_values.append(r.stated_days)

        if not days_values:
            return None

        # Scale by quantity ratio if records have quantities
        scaled_values: list[float] = []
        for r, d in zip(relevant, days_values):
            if r.order_quantity and r.order_quantity > 0 and quantity > 0:
                scale = quantity / r.order_quantity
                # Assume sub-linear scaling: sqrt relationship beyond 2x
                if scale > 2:
                    scale = 2 + (scale - 2) ** 0.6
                scaled_values.append(d * scale)
            else:
                scaled_values.append(d)

        if not scaled_values:
            return None

        mean_days = statistics.mean(scaled_values)

        # Compute on-time rate for confidence bonus
        on_time_records = [r for r in relevant if r.on_time is not None]
        on_time_rate = (
            sum(1 for r in on_time_records if r.on_time) / len(on_time_records)
            if on_time_records else 0.5
        )

        # Confidence grows with number of records and on-time rate
        record_conf = min(0.9, 0.4 + 0.1 * len(scaled_values))
        confidence = record_conf * (0.5 + 0.5 * on_time_rate)

        # p80 and p90 from distribution if enough data
        if len(scaled_values) >= 3:
            sorted_vals = sorted(scaled_values)
            p80 = sorted_vals[int(0.8 * len(sorted_vals))]
            p90 = sorted_vals[min(int(0.9 * len(sorted_vals)), len(sorted_vals) - 1)]
        else:
            p80 = mean_days * 1.3
            p90 = mean_days * 1.6

        return {
            "memory_adjusted_days": mean_days,
            "p80_days": p80,
            "p90_days": p90,
            "confidence": confidence,
            "record_count": len(scaled_values),
            "on_time_rate": on_time_rate,
        }
