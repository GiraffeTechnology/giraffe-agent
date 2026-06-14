"""
Deterministic mock channel adapter for local tests and CI.
Simulates buyer/supplier message flows without external APIs.
"""

import hashlib
from src.channels.base import (
    BaseChannelAdapter,
    OutboundChannelMessage,
    ChannelDeliveryReceipt,
    NormalizedChannelMessage,
)

# In-memory delivery log — cleared per test run, inspectable by tests
_DELIVERED: list[dict] = []


def clear_delivered() -> None:
    _DELIVERED.clear()


def get_delivered() -> list[dict]:
    return list(_DELIVERED)


class MockAdapter(BaseChannelAdapter):
    """
    Deterministic mock adapter that simulates:
    - Inbound buyer messages (intent=buy)
    - Inbound supplier messages with invitation tokens (intent=supply)
    - Outbound supplier inquiry dispatch
    - Outbound buyer-facing responses
    - Delivery receipts (status=mocked)
    """

    channel_name = "mock"

    def normalize_inbound(self, payload: dict) -> NormalizedChannelMessage:
        text = payload.get("text", "")
        external_user_id = payload.get("external_user_id", "mock_user")
        channel = payload.get("channel", "mock")

        intent = self._detect_intent(text)
        actor_id = self.resolve_actor_identity(channel, external_user_id)

        raw_key = f"{channel}:{external_user_id}:{text}"
        idempotency_key = hashlib.sha256(raw_key.encode()).hexdigest()[:16]

        return NormalizedChannelMessage(
            channel=channel,
            external_user_id=external_user_id,
            external_thread_id=payload.get("external_thread_id"),
            actor_id=actor_id,
            text=text or None,
            intent=intent,
            attachments=payload.get("attachments", []),
            raw=payload,
            idempotency_key=idempotency_key,
        )

    def send_message(self, message: OutboundChannelMessage) -> ChannelDeliveryReceipt:
        print(f"[Mock → {message.to_external_user_id}] {message.text}")
        receipt = ChannelDeliveryReceipt(
            channel=message.channel,
            external_user_id=message.to_external_user_id,
            message_id=f"mock_{abs(hash(message.text)):x}",
            status="mocked",
            provider_response={"mock": True},
        )
        _DELIVERED.append(receipt.model_dump())
        return receipt

    def verify_signature(self, headers: dict, payload: bytes | dict) -> bool:
        return True

    def resolve_actor_identity(self, channel: str, external_user_id: str) -> str | None:
        if external_user_id.startswith("buyer_"):
            return f"ACTOR-B-{external_user_id[6:].upper()}"
        if external_user_id.startswith("supplier_"):
            return f"ACTOR-M-{external_user_id[9:].upper()}"
        return None

    def _detect_intent(self, text: str) -> str | None:
        if not text:
            return None
        from src.channels.role_router import _contains_supplier_token, _contains_m_side_phrase
        if _contains_supplier_token(text):
            return "supply"
        if _contains_m_side_phrase(text):
            return "supply"
        tl = text.lower()
        if any(w in tl for w in ["buy", "purchase", "order", "need", "want", "sourcing", "rfq"]):
            return "buy"
        if any(w in tl for w in ["logistics", "shipping", "tracking", "delivery", "carrier"]):
            return "logistics"
        if any(w in tl for w in ["upstream"]):
            return "upstream"
        if any(w in tl for w in ["update", "status"]):
            return "order_update"
        return None
