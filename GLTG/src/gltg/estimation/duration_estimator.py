"""Duration estimator -- blends all evidence sources into a final DurationEstimate."""

from __future__ import annotations

import uuid
from datetime import datetime

from ..models.duration import DurationEstimate
from ..models.enums import ApparelNodeType, EvidenceSourceType
from ..models.evidence import EvidenceItem
from ..models.participant import ParticipantProfile, SupplierMemoryRecord, SupplierResponse
from ..models.reforecast import CalendarConfig, ProgressEvent
from ..apparel.baselines import get_baseline
from .evidence_weighting import EvidenceWeighter
from .supplier_memory import SupplierMemoryAnalyzer
from .confidence import ConfidenceCalculator


def _ev_id() -> str:
    return f"ev_{uuid.uuid4().hex[:8]}"


class DurationEstimator:
    """Computes a final DurationEstimate for a node using the evidence hierarchy.

    Formula:
        Final = supplier_claim * w1 + memory_estimate * w2 + capacity_calc * w3
                + baseline * w4 + progress_adj * w5
    Weights sum to 1 and are derived from evidence quality.
    """

    def __init__(self) -> None:
        self._weighter = EvidenceWeighter()
        self._memory_analyzer = SupplierMemoryAnalyzer()
        self._confidence_calc = ConfidenceCalculator()

    def estimate(
        self,
        node_type: ApparelNodeType,
        participant: ParticipantProfile | None,
        supplier_response: SupplierResponse | None,
        memory_records: list[SupplierMemoryRecord],
        progress_events: list[ProgressEvent],
        quantity: int = 1000,
        calendar: CalendarConfig | None = None,
    ) -> DurationEstimate:
        """Return a blended DurationEstimate for this node."""
        baseline = get_baseline(node_type, quantity)
        evidence_items: list[EvidenceItem] = []
        components: list[tuple[float, EvidenceSourceType, float]] = []  # (days, source, conf)

        # --- 1. Category baseline (always present) ---
        components.append((baseline["p50"], EvidenceSourceType.CATEGORY_BASELINE, 0.4))
        evidence_items.append(EvidenceItem(
            evidence_id=_ev_id(),
            source_type=EvidenceSourceType.CATEGORY_BASELINE,
            description=f"Category baseline p50 for {node_type.value}",
            value=baseline,
            confidence=0.4,
            created_at=datetime.utcnow(),
        ))

        # --- 2. Supplier capability baseline ---
        if participant is not None:
            cap = participant.get_capability(node_type)
            if cap and cap.typical_lead_days is not None:
                components.append((cap.typical_lead_days, EvidenceSourceType.SUPPLIER_QUOTE, 0.5))
                evidence_items.append(EvidenceItem(
                    evidence_id=_ev_id(),
                    source_type=EvidenceSourceType.SUPPLIER_QUOTE,
                    source_id=participant.participant_id,
                    description=f"{participant.name} typical lead days from capability profile",
                    value=cap.typical_lead_days,
                    confidence=0.5,
                    created_at=datetime.utcnow(),
                ))

        # --- 3. Supplier response (confirmed quote) ---
        if supplier_response and supplier_response.confirmed_days is not None:
            components.append((supplier_response.confirmed_days, EvidenceSourceType.SUPPLIER_CONFIRMATION, 0.75))
            evidence_items.append(EvidenceItem(
                evidence_id=_ev_id(),
                source_type=EvidenceSourceType.SUPPLIER_CONFIRMATION,
                source_id=supplier_response.participant_id,
                description=f"Supplier confirmed {supplier_response.confirmed_days} days",
                value=supplier_response.confirmed_days,
                confidence=0.75,
                created_at=datetime.utcnow(),
            ))

        # --- 4. Historical memory ---
        if participant and memory_records:
            mem = self._memory_analyzer.analyze(
                participant.participant_id, node_type, memory_records, quantity
            )
            if mem:
                mem_days = mem["memory_adjusted_days"]
                mem_conf = mem["confidence"]
                components.append((mem_days, EvidenceSourceType.HISTORICAL_MEMORY, mem_conf))
                evidence_items.append(EvidenceItem(
                    evidence_id=_ev_id(),
                    source_type=EvidenceSourceType.HISTORICAL_MEMORY,
                    source_id=participant.participant_id,
                    description=f"Memory-adjusted from {mem['record_count']} past records",
                    value={"days": mem_days, "on_time_rate": mem.get("on_time_rate")},
                    confidence=mem_conf,
                    created_at=datetime.utcnow(),
                ))

        # --- 5. Progress events (actual progress adjustments) ---
        relevant_events = [e for e in progress_events if e.node_id is not None]
        if relevant_events:
            # Use the most recent event's remaining_days if present
            latest = relevant_events[-1]
            remaining = latest.payload.get("remaining_days")
            if remaining is not None:
                components.append((float(remaining), EvidenceSourceType.ACTUAL_PROGRESS, 0.95))
                evidence_items.append(EvidenceItem(
                    evidence_id=_ev_id(),
                    source_type=EvidenceSourceType.ACTUAL_PROGRESS,
                    description=f"Actual remaining days from progress event {latest.event_id}",
                    value=remaining,
                    confidence=0.95,
                    created_at=datetime.utcnow(),
                ))

        # --- Blend ---
        blended_p50 = self._weighter.blend(components)
        if blended_p50 is None:
            blended_p50 = baseline["p50"]

        # Scale p80 / p90 proportionally from baseline ratios
        ratio_80 = baseline["p80"] / max(baseline["p50"], 0.1)
        ratio_90 = baseline["p90"] / max(baseline["p50"], 0.1)

        p80 = blended_p50 * ratio_80
        p90 = blended_p50 * ratio_90
        min_days = blended_p50 * (baseline["min"] / max(baseline["p50"], 0.1))
        max_days = blended_p50 * (baseline["max"] / max(baseline["p50"], 0.1))

        overall_conf = self._weighter.overall_confidence(
            [(s, c) for _, s, c in components]
        )

        # Pull supplier_claim from response if available
        supplier_claim = (
            supplier_response.confirmed_days if supplier_response else None
        )
        # Memory adjusted from memory analysis
        mem_result = None
        if participant and memory_records:
            mem_result = self._memory_analyzer.analyze(
                participant.participant_id, node_type, memory_records, quantity
            )

        return DurationEstimate(
            p50_days=round(blended_p50, 1),
            p80_days=round(p80, 1),
            p90_days=round(p90, 1),
            min_days=round(min_days, 1),
            max_days=round(max_days, 1),
            supplier_claim_days=supplier_claim,
            computed_days=blended_p50,
            memory_adjusted_days=mem_result["memory_adjusted_days"] if mem_result else None,
            confidence=round(overall_conf, 3),
            evidence_summary=evidence_items,
        )
