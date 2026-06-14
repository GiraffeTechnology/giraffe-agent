"""Confidence level conversion and aggregation."""

from __future__ import annotations

from ..models.enums import ConfidenceLevel
from ..models.evidence import EvidenceItem


class ConfidenceCalculator:
    """Converts numeric confidence scores to ConfidenceLevel enum values."""

    # Thresholds for ConfidenceLevel bands
    THRESHOLDS = [
        (0.75, ConfidenceLevel.HIGH),
        (0.55, ConfidenceLevel.MEDIUM),
        (0.35, ConfidenceLevel.LOW),
        (0.0, ConfidenceLevel.VERY_LOW),
    ]

    def to_level(self, confidence: float) -> ConfidenceLevel:
        """Convert a 0–1 float to a ConfidenceLevel."""
        for threshold, level in self.THRESHOLDS:
            if confidence >= threshold:
                return level
        return ConfidenceLevel.VERY_LOW

    def from_evidence(self, evidence_items: list[EvidenceItem]) -> float:
        """Compute overall confidence from a list of evidence items.

        Returns 0–1 float. Accounts for evidence diversity and magnitude.
        """
        if not evidence_items:
            return 0.2

        # Weighted average of individual confidence scores
        total_weight = 0.0
        weighted_sum = 0.0
        for item in evidence_items:
            # Higher-confidence items contribute more
            weight = item.confidence
            weighted_sum += item.confidence * weight
            total_weight += weight

        if total_weight == 0:
            return 0.2

        base = weighted_sum / total_weight
        # Bonus for having multiple independent sources
        unique_sources = len({item.source_type for item in evidence_items})
        diversity_bonus = min(0.15, (unique_sources - 1) * 0.05)
        return min(1.0, base + diversity_bonus)

    def aggregate(self, confidences: list[float]) -> float:
        """Return the harmonic-mean-like aggregate of multiple confidence scores.

        Penalises having any very low confidence component.
        """
        if not confidences:
            return 0.2
        # Use geometric mean to penalise weak links
        import math
        product = 1.0
        for c in confidences:
            product *= max(c, 0.01)
        return min(1.0, product ** (1.0 / len(confidences)))
