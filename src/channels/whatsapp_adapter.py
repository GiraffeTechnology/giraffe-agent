"""
WhatsApp channel adapter.
Mock mode prints to console. Production requires Meta Cloud API credentials via env vars.
Signature verification: TODO — implement Meta webhook HMAC-SHA256 when deploying.
"""

import hashlib
import os

from src.channels.base import (
    BaseChannelAdapter,
    OutboundChannelMessage,
    ChannelDeliveryReceipt,
    NormalizedChannelMessage,
)


class WhatsAppAdapter(BaseChannelAdapter):
    channel_name = "whatsapp"

    def __init__(self, mock: bool = True) -> None:
        self.mock = mock
        self._app_secret = os.getenv("WHATSAPP_APP_SECRET", "")

    def normalize_inbound(self, payload: dict) -> NormalizedChannelMessage:
        # Meta webhook structure: entry[0].changes[0].value.messages[0]
        try:
            msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
            phone = msg.get("from", "unknown")
            text = msg.get("text", {}).get("body", "")
            msg_id = msg.get("id")
        except (KeyError, IndexError):
            phone = payload.get("from", payload.get("phone", "unknown"))
            text = payload.get("text", payload.get("body", ""))
            msg_id = payload.get("id")

        raw_key = f"whatsapp:{phone}:{text}"
        idempotency_key = hashlib.sha256(raw_key.encode()).hexdigest()[:16]

        return NormalizedChannelMessage(
            channel="whatsapp",
            external_user_id=phone,
            external_thread_id=msg_id,
            text=text or None,
            intent=self._detect_intent(text),
            attachments=payload.get("attachments", []),
            raw=payload,
            idempotency_key=idempotency_key,
        )

    def send_message(self, message: OutboundChannelMessage) -> ChannelDeliveryReceipt:
        if self.mock:
            print(f"[WhatsApp MOCK → {message.to_external_user_id}]\n{message.text}\n")
            return ChannelDeliveryReceipt(
                channel="whatsapp",
                external_user_id=message.to_external_user_id,
                message_id=f"wa_mock_{abs(hash(message.text)):x}",
                status="mocked",
                provider_response={"mock": True},
            )
        # Production: call Meta Cloud API / WhatsApp Business API
        raise NotImplementedError("WhatsApp production mode requires Meta API credentials.")

    def verify_signature(self, headers: dict, payload: bytes | dict) -> bool:
        # TODO: implement Meta webhook HMAC-SHA256 signature check using WHATSAPP_APP_SECRET
        return True

    def _detect_intent(self, text: str) -> str | None:
        if not text:
            return None
        from src.channels.role_router import _contains_supplier_token, _contains_m_side_phrase
        if _contains_supplier_token(text):
            return "supply"
        if _contains_m_side_phrase(text):
            return "supply"
        return None
