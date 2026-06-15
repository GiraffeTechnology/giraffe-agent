"""Order input validation -- surfaces missing fields and structural risks."""

from __future__ import annotations

from ..models.enums import RiskFlagCode
from ..models.order import ApparelOrderInput
from ..models.risk import RiskFlag


class ApparelOrderValidator:
    """Validates an ApparelOrderInput and returns missing fields + risk flags."""

    REQUIRED_FIELDS = [
        ("order_id", "Order ID"),
        ("product_type", "Product type"),
        ("quantity", "Order quantity"),
    ]

    def validate(self, order: ApparelOrderInput) -> tuple[list[str], list[RiskFlag]]:
        """Return (missing_fields, risk_flags)."""
        missing: list[str] = []
        flags: list[RiskFlag] = []

        # Hard required fields
        for field, label in self.REQUIRED_FIELDS:
            val = getattr(order, field, None)
            if val is None or val == "" or val == 0:
                missing.append(label)

        if order.requested_delivery_date is None:
            missing.append("Requested delivery date")
            flags.append(RiskFlag(
                code=RiskFlagCode.MISSING_REQUIRED_FIELD,
                description="No requested delivery date provided -- cannot assess on-time probability.",
                severity="HIGH",
                mitigation_hint="Supply a target delivery date.",
            ))

        if not order.participants:
            flags.append(RiskFlag(
                code=RiskFlagCode.MISSING_PRODUCTION_CAPACITY,
                description="No participants provided -- cannot resolve production capacity.",
                severity="CRITICAL",
                mitigation_hint="Add at least one garment factory participant.",
            ))

        # Check for fabric supplier
        from ..models.enums import ParticipantType
        fabric_suppliers = [
            p for p in order.participants
            if p.participant_type == ParticipantType.FABRIC_SUPPLIER
        ]
        if not fabric_suppliers:
            flags.append(RiskFlag(
                code=RiskFlagCode.MISSING_FABRIC_SUPPLIER,
                description="No fabric supplier identified.",
                severity="HIGH",
                mitigation_hint="Assign a fabric supplier to the order.",
            ))

        # Check for garment factory
        factories = [
            p for p in order.participants
            if p.participant_type == ParticipantType.GARMENT_FACTORY
        ]
        if not factories:
            flags.append(RiskFlag(
                code=RiskFlagCode.MISSING_PRODUCTION_CAPACITY,
                description="No garment factory participant identified.",
                severity="CRITICAL",
                mitigation_hint="Assign a garment factory.",
            ))

        # Single-source risk
        if len(fabric_suppliers) == 1:
            flags.append(RiskFlag(
                code=RiskFlagCode.SINGLE_SOURCE_RISK,
                description="Only one fabric supplier available -- no alternative if this supplier fails.",
                severity="MEDIUM",
                affected_nodes=[],
                mitigation_hint="Identify a backup fabric supplier.",
            ))

        # Low supplier reliability
        for p in order.participants:
            if p.reliability_score is not None and p.reliability_score < 0.7:
                flags.append(RiskFlag(
                    code=RiskFlagCode.LOW_SUPPLIER_RELIABILITY,
                    description=f"Participant '{p.name}' has a low reliability score ({p.reliability_score:.0%}).",
                    severity="MEDIUM",
                    affected_nodes=[],
                    mitigation_hint="Consider sourcing from a more reliable supplier.",
                ))

        return missing, flags
