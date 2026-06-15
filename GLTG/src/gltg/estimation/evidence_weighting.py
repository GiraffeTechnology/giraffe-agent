"""Evidence hierarchy weighting for duration estimates."""

from __future__ import annotations

from ..models.enums import EvidenceSourceType

# Evidence hierarchy weights -- higher = more authoritative
EVIDENCE_WEIGHTS: dict[EvidenceSourceType, float] = {
    EvidenceSourceType.ACTUAL_PROGRESS: 1.0,
    EvidenceSourceType.SUPPLIER_CONFIRMATION: 0.85,
    EvidenceSourceType.HISTORICAL_MEMORY: 0.70,
    EvidenceSourceType.SUPPLIER_QUOTE: 0.55,
    EvidenceSourceType.CATEGORY_BASELINE: 0.40,
    EvidenceSourceType.AI_ESTIMATE: 0.25,
}


class EvidenceWeighter:
    """Computes blended duration values from multiple evidence sources."""

    def get_weight(self, source_type: EvidenceSourceType) -> float:
        """Return the authority weight for an evidence source type."""
        return EVIDENCE_WEIGHTS.get(source_type, 0.3)

    def blend(
        self,
        items: list[tuple[float, EvidenceSourceType, float]],
        # (days_value, source_type, item_confidence)
    ) -> float | None:
        """Return a weighted-average days value from evidence items.

        Args:
            items: List of (days_value, source_type, item_confidence) tuples.

        Returns:
            Weighted blended days, or None if no items.
        """
        if not items:
            return None

        total_weight = 0.0
        weighted_sum = 0.0
        for days, source_type, item_conf in items:
            w = self.get_weight(source_type) * item_conf
            weighted_sum += days * w
            total_weight += w

        if total_weight == 0:
            return None

        return weighted_sum / total_weight

    def overall_confidence(
        self,
        items: list[tuple[EvidenceSourceType, float]],
        # (source_type, item_confidence)
    ) -> float:
        """Compute overall confidence from multiple evidence items.

        Confidence increases with more authoritative and consistent sources.
        Returns a value in [0, 1].
        """
        if not items:
            return 0.2

        weights = [self.get_weight(s) * c for s, c in items]
        total = sum(weights)
        count = len(items)
        base = total / count if count else 0.0
        # Bonus for multiple sources (diminishing returns)
        multi_bonus = min(0.15, (count - 1) * 0.05)
        return min(1.0, base + multi_bonus)
