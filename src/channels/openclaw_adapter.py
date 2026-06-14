"""
OpenClaw channel adapter — bridges channel webhook calls into the OpenClaw
skill router for B-side and M-side skill invocations.
"""

import hashlib

from src.channels.base import (
    BaseChannelAdapter,
    OutboundChannelMessage,
    ChannelDeliveryReceipt,
    NormalizedChannelMessage,
)


class OpenClawAdapter(BaseChannelAdapter):
    channel_name = "openclaw"

    def normalize_inbound(self, payload: dict) -> NormalizedChannelMessage:
        action = payload.get("action", "")
        external_user_id = payload.get("external_user_id", "openclaw_user")

        raw_key = f"openclaw:{external_user_id}:{action}"
        idempotency_key = hashlib.sha256(raw_key.encode()).hexdigest()[:16]

        return NormalizedChannelMessage(
            channel="openclaw",
            external_user_id=external_user_id,
            text=action or None,
            intent=self._action_to_intent(action),
            raw=payload,
            idempotency_key=idempotency_key,
        )

    def send_message(self, message: OutboundChannelMessage) -> ChannelDeliveryReceipt:
        print(f"[OpenClaw → {message.to_external_user_id}] {message.text[:120]}")
        return ChannelDeliveryReceipt(
            channel="openclaw",
            external_user_id=message.to_external_user_id,
            status="sent",
            provider_response={"channel": "openclaw"},
        )

    def invoke_skill(self, action: str, params: dict) -> dict:
        """Invoke an OpenClaw skill action directly (in-process)."""
        from src.openclaw_skill.skill_router import route_action
        return route_action(action, params)

    def _action_to_intent(self, action: str) -> str | None:
        if action.startswith("b_side_"):
            return "buy"
        if action.startswith("m_side_"):
            return "supply"
        if "logistics" in action:
            return "logistics"
        return None
