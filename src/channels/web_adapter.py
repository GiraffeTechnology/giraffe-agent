"""
Web fallback channel adapter — mock mode prints to console.
Used when WeChat / WhatsApp are unavailable or for browser-based sessions.
"""

import hashlib

from src.channels.base import (
    BaseChannelAdapter,
    OutboundChannelMessage,
    ChannelDeliveryReceipt,
    NormalizedChannelMessage,
)


class WebAdapter(BaseChannelAdapter):
    channel_name = "web"

    def __init__(self, mock: bool = True) -> None:
        self.mock = mock

    def normalize_inbound(self, payload: dict) -> NormalizedChannelMessage:
        user_id = payload.get("user_id", payload.get("external_user_id", "web_user"))
        text = payload.get("text", payload.get("message", ""))
        session_id = payload.get("session_id")

        raw_key = f"web:{user_id}:{text}"
        idempotency_key = hashlib.sha256(raw_key.encode()).hexdigest()[:16]

        return NormalizedChannelMessage(
            channel="web",
            external_user_id=user_id,
            external_thread_id=session_id,
            text=text or None,
            intent=None,
            attachments=payload.get("attachments", []),
            raw=payload,
            idempotency_key=idempotency_key,
        )

    def send_message(self, message: OutboundChannelMessage) -> ChannelDeliveryReceipt:
        if self.mock:
            print(f"[Web MOCK → {message.to_external_user_id}]\n{message.text}\n")
            return ChannelDeliveryReceipt(
                channel="web",
                external_user_id=message.to_external_user_id,
                message_id=f"web_mock_{abs(hash(message.text)):x}",
                status="mocked",
                provider_response={"mock": True},
            )
        raise NotImplementedError("Web production push not implemented — use WebSocket/SSE.")
