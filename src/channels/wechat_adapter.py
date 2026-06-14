"""
WeChat channel adapter.
Mock mode prints to console. Production requires credentials via env vars.
Signature verification: TODO — implement WeChat Work HMAC when deploying.
"""

import hashlib
import os

from src.channels.base import (
    BaseChannelAdapter,
    OutboundChannelMessage,
    ChannelDeliveryReceipt,
    NormalizedChannelMessage,
)


class WeChatAdapter(BaseChannelAdapter):
    channel_name = "wechat"

    def __init__(self, mock: bool = True) -> None:
        self.mock = mock
        self._token = os.getenv("WECHAT_TOKEN", "")

    def normalize_inbound(self, payload: dict) -> NormalizedChannelMessage:
        openid = payload.get("FromUserName", payload.get("openid", "unknown_openid"))
        content = payload.get("Content", payload.get("text", ""))
        msg_id = payload.get("MsgId") or payload.get("msg_id")

        raw_key = f"wechat:{openid}:{content}"
        idempotency_key = hashlib.sha256(raw_key.encode()).hexdigest()[:16]

        return NormalizedChannelMessage(
            channel="wechat",
            external_user_id=openid,
            external_thread_id=str(msg_id) if msg_id else None,
            text=content or None,
            intent=self._detect_intent(content),
            attachments=payload.get("attachments", []),
            raw=payload,
            idempotency_key=idempotency_key,
        )

    def send_message(self, message: OutboundChannelMessage) -> ChannelDeliveryReceipt:
        if self.mock:
            print(f"[WeChat MOCK → {message.to_external_user_id}]\n{message.text}\n")
            return ChannelDeliveryReceipt(
                channel="wechat",
                external_user_id=message.to_external_user_id,
                message_id=f"wechat_mock_{abs(hash(message.text)):x}",
                status="mocked",
                provider_response={"mock": True},
            )
        # Production: call WeChat Work / Official Account API
        raise NotImplementedError("WeChat production mode requires credentials and API setup.")

    def verify_signature(self, headers: dict, payload: bytes | dict) -> bool:
        # TODO: implement WeChat Work HMAC-SHA1 signature check
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
