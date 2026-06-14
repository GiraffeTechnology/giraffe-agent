"""Ranks delivery path options using a multi-factor scoring model."""

from __future__ import annotations

from ..models.enums import OptionLabel, RiskFlagCode
from ..models.path import DeliveryPathOption


# Scoring weights
W1_ON_TIME_PROB = 0.30
W2_EVIDENCE_COMPLETENESS = 0.15
W3_SUPPLIER_RELIABILITY = 0.20
W4_MARGIN_SAFETY = 0.15
W5_DELAY_RISK = 0.10
W6_QC_RISK = 0.05
W7_MISSING_FIELD_PENALTY = 0.03
W8_OPERATIONAL_COMPLEXITY = 0.02


class OptionRanker:
    """Scores and ranks options, assigns labels to top 3."""

    def rank(
        self,
        options: list[DeliveryPathOption],
        requested_date=None,
    ) -> list[DeliveryPathOption]:
        """Score all options, sort descending, return top 3 with labels."""
        if not options:
            return []

        scored = [(self._score(o, requested_date), o) for o in options]
        scored.sort(key=lambda x: x[0], reverse=True)

        top = scored[:3]
        result = []
        labels = [OptionLabel.FASTEST, OptionLabel.MOST_RELIABLE, OptionLabel.BEST_COMMERCIAL_BALANCE]

        # Assign labels based on dominant quality
        sorted_options = [o for _, o in top]
        labelled = self._assign_labels(sorted_options)

        for i, (score, option) in enumerate(top):
            option.score = round(score, 4)
            option.label = labelled[i]
            if not option.recommendation_reason:
                option.recommendation_reason = self._reason(option, score)
            result.append(option)

        return result

    def _score(self, option: DeliveryPathOption, requested_date=None) -> float:
        """Compute composite score for an option."""
        # On-time probability
        otp = option.on_time_probability or 0.5
        s_otp = W1_ON_TIME_PROB * otp

        # Evidence completeness (proxy: avg confidence of evidence items)
        if option.evidence_summary:
            avg_conf = sum(e.confidence for e in option.evidence_summary) / len(option.evidence_summary)
        else:
            avg_conf = 0.3
        s_evidence = W2_EVIDENCE_COMPLETENESS * avg_conf

        # Supplier reliability (proxy: inverse of risk flag count)
        high_risk_count = sum(
            1 for rf in option.risk_flags if rf.severity in ("HIGH", "CRITICAL")
        )
        reliability = max(0.0, 1.0 - 0.2 * high_risk_count)
        s_reliability = W3_SUPPLIER_RELIABILITY * reliability

        # Margin safety: buffer days between commitable and requested date
        if requested_date and option.commitable_date:
            buffer_days = (requested_date - option.commitable_date).days
            margin = min(1.0, max(0.0, buffer_days / 21.0))
        else:
            margin = 0.5
        s_margin = W4_MARGIN_SAFETY * margin

        # Delay risk penalty
        delay_risk_count = sum(
            1 for rf in option.risk_flags
            if rf.code in (RiskFlagCode.TIGHT_DEADLINE, RiskFlagCode.LOGISTICS_RISK)
        )
        s_delay = -W5_DELAY_RISK * min(1.0, delay_risk_count * 0.3)

        # QC risk penalty
        qc_risk_count = sum(
            1 for rf in option.risk_flags
            if rf.code in (RiskFlagCode.QC_RISK, RiskFlagCode.HIGH_REWORK_RISK)
        )
        s_qc = -W6_QC_RISK * min(1.0, qc_risk_count * 0.5)

        # Missing field penalty
        missing_count = len(option.missing_fields)
        s_missing = -W7_MISSING_FIELD_PENALTY * min(1.0, missing_count * 0.2)

        # Operational complexity (split shipments are harder)
        from ..models.enums import DeliveryMode
        if option.delivery_mode in (DeliveryMode.SPLIT_SHIPMENT, DeliveryMode.PARALLEL_FACTORY_PRODUCTION):
            s_complex = -W8_OPERATIONAL_COMPLEXITY
        else:
            s_complex = 0.0

        total = s_otp + s_evidence + s_reliability + s_margin + s_delay + s_qc + s_missing + s_complex
        return max(0.0, total)

    def _assign_labels(self, options: list[DeliveryPathOption]) -> list[OptionLabel | None]:
        """Assign semantic labels to ranked options."""
        if not options:
            return []

        labels: list[OptionLabel | None] = [None] * len(options)

        # Fastest = earliest commitable date
        if len(options) >= 1:
            from datetime import date as dmod
            fastest_idx = min(
                range(len(options)),
                key=lambda i: options[i].commitable_date or dmod.max,
            )
            labels[fastest_idx] = OptionLabel.FASTEST

        # Most reliable = highest on_time_probability
        if len(options) >= 2:
            remaining = [i for i in range(len(options)) if labels[i] is None]
            if remaining:
                reliable_idx = max(
                    remaining,
                    key=lambda i: options[i].on_time_probability or 0.0,
                )
                labels[reliable_idx] = OptionLabel.MOST_RELIABLE

        # Best commercial balance = remaining
        for i in range(len(options)):
            if labels[i] is None:
                labels[i] = OptionLabel.BEST_COMMERCIAL_BALANCE

        return labels

    def _reason(self, option: DeliveryPathOption, score: float) -> str:
        """Generate a short recommendation reason."""
        if option.label == OptionLabel.FASTEST:
            d = option.commitable_date
            return f"Fastest path — commitable by {d}."
        elif option.label == OptionLabel.MOST_RELIABLE:
            otp = option.on_time_probability
            s = f"{otp:.0%}" if otp else "high"
            return f"Most reliable option with {s} on-time probability."
        else:
            return f"Best commercial balance (score {score:.2f})."
