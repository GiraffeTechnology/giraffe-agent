"""Adapter between the Giraffe Agent's dynamic form and GLTG data models."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ..models.enums import (
    ApparelNodeType,
    ParticipantType,
)
from ..models.capability import Capability
from ..models.order import ApparelOrderInput
from ..models.packet import DeliveryFeasibilityPacket
from ..models.participant import ParticipantProfile
from ..packets.decision_packet import DecisionPacket


class GiraffeAgentAdapter:
    """Bridges the Giraffe Agent's JSON form data and the GLTG engine."""

    def dynamic_form_to_order(self, form_data: dict[str, Any]) -> ApparelOrderInput:
        """Convert a Giraffe Agent dynamic form payload to an ApparelOrderInput.

        Expected top-level keys:
          - order_id (str, required)
          - product_type (str, required)
          - quantity (int, required)
          - requested_delivery_date (str ISO 8601, optional)
          - trade_term (str, optional)
          - destination (str, optional)
          - participants (list[dict], optional) -- raw participant dicts
          - dynamic_form (dict, optional) -- pass-through form fields
        """
        participants = self._build_participants(form_data.get("participants", []))

        rdd = form_data.get("requested_delivery_date")
        if isinstance(rdd, str):
            rdd = date.fromisoformat(rdd)

        return ApparelOrderInput(
            order_id=form_data.get("order_id", "ORDER_UNKNOWN"),
            product_type=form_data.get("product_type", "unknown"),
            quantity=int(form_data.get("quantity", 0)),
            requested_delivery_date=rdd,
            trade_term=form_data.get("trade_term"),
            destination=form_data.get("destination"),
            dynamic_form=form_data.get("dynamic_form", {}),
            participants=participants,
        )

    def _build_participants(self, raw: list[dict]) -> list[ParticipantProfile]:
        """Convert raw participant dicts to ParticipantProfile objects."""
        profiles: list[ParticipantProfile] = []
        for p in raw:
            caps = self._build_capabilities(p.get("capabilities", []))
            available_from = p.get("available_from")
            if isinstance(available_from, str):
                available_from = date.fromisoformat(available_from)

            try:
                ptype = ParticipantType(p.get("participant_type", "GARMENT_FACTORY"))
            except ValueError:
                ptype = ParticipantType.GARMENT_FACTORY

            profile = ParticipantProfile(
                participant_id=p.get("participant_id", f"p_{id(p)}"),
                name=p.get("name", "Unknown"),
                participant_type=ptype,
                capabilities=caps,
                location=p.get("location"),
                capacity_per_day=p.get("capacity_per_day"),
                moq=p.get("moq"),
                available_from=available_from,
                reliability_score=p.get("reliability_score"),
                quality_score=p.get("quality_score"),
                on_time_delivery_rate=p.get("on_time_delivery_rate"),
                metadata=p.get("metadata", {}),
            )
            profiles.append(profile)
        return profiles

    def _build_capabilities(self, raw: list[dict]) -> list[Capability]:
        """Convert raw capability dicts to Capability objects."""
        caps = []
        for c in raw:
            try:
                nt = ApparelNodeType(c.get("node_type", "SEWING"))
            except ValueError:
                continue
            caps.append(Capability(
                capability_id=c.get("capability_id", f"cap_{id(c)}"),
                node_type=nt,
                description=c.get("description"),
                capacity_per_day=c.get("capacity_per_day"),
                min_order_qty=c.get("min_order_qty"),
                max_order_qty=c.get("max_order_qty"),
                typical_lead_days=c.get("typical_lead_days"),
                quality_grade=c.get("quality_grade"),
                certifications=c.get("certifications", []),
            ))
        return caps

    def packet_to_agent_response(self, packet: DeliveryFeasibilityPacket) -> dict:
        """Convert a DeliveryFeasibilityPacket to the Giraffe Agent response format.

        Returns a simplified dict suitable for the agent's output schema.
        """
        decision = DecisionPacket.from_packet(packet)
        return {
            "order_id": decision.order_id,
            "status": decision.status.value,
            "generated_at": decision.generated_at.isoformat(),
            "commitable_date": decision.commitable_date.isoformat() if decision.commitable_date else None,
            "most_likely_date": decision.most_likely_date.isoformat() if decision.most_likely_date else None,
            "on_time_probability": decision.on_time_probability,
            "recommended_action": decision.recommended_action,
            "human_review_required": decision.human_review_required,
            "top_risks": decision.top_risk_codes,
            "missing_fields": decision.missing_fields,
            "options": [
                {
                    "option_id": o.option_id,
                    "label": o.label,
                    "commitable_date": o.commitable_date.isoformat() if o.commitable_date else None,
                    "most_likely_date": o.most_likely_date.isoformat() if o.most_likely_date else None,
                    "on_time_probability": o.on_time_probability,
                    "recommendation_reason": o.recommendation_reason,
                    "score": o.score,
                }
                for o in decision.options
            ],
        }
