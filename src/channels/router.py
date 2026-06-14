"""
Channel router — routes normalized inbound messages to B-side or M-side,
and dispatches outbound messages via the correct adapter.
"""

from __future__ import annotations

from src.channels.base import (
    NormalizedChannelMessage,
    OutboundChannelMessage,
    ChannelDeliveryReceipt,
)
from src.channels.role_router import _contains_supplier_token, _contains_m_side_phrase


def _get_adapter(channel: str):
    """Lazy-load and return the adapter for the given channel name."""
    from src.channels.mock_adapter import MockAdapter
    from src.channels.email_adapter import EmailAdapter
    from src.channels.wechat_adapter import WeChatAdapter
    from src.channels.whatsapp_adapter import WhatsAppAdapter
    from src.channels.openclaw_adapter import OpenClawAdapter

    registry = {
        "mock": MockAdapter,
        "email": EmailAdapter,
        "wechat": WeChatAdapter,
        "whatsapp": WhatsAppAdapter,
        "openclaw": OpenClawAdapter,
    }
    cls = registry.get(channel.lower())
    if cls is None:
        return MockAdapter()
    return cls()


def route_inbound_message(msg: NormalizedChannelMessage) -> dict:
    """
    Route a normalized inbound message to the correct workflow side.

    Returns a dict with: route, reason, intent.

    Priority:
    1. Invitation token in text → m_side
    2. intent == "supply" → m_side
    3. Supplier phrase detected → m_side
    4. intent == "logistics" → logistics
    5. intent in ("upstream", "order_update") → b_side
    6. Default → b_side (AI Buyer)
    """
    text = msg.text or ""

    if _contains_supplier_token(text):
        return {
            "route": "m_side",
            "reason": "Invitation token in message",
            "intent": msg.intent or "supply",
        }

    if msg.intent == "supply":
        return {
            "route": "m_side",
            "reason": "Intent classified as supply",
            "intent": "supply",
        }

    if _contains_m_side_phrase(text):
        return {
            "route": "m_side",
            "reason": "Supplier phrase detected",
            "intent": "supply",
        }

    if msg.intent == "logistics":
        return {
            "route": "logistics",
            "reason": "Logistics intent",
            "intent": "logistics",
        }

    if msg.intent in ("upstream", "order_update"):
        return {
            "route": "b_side",
            "reason": f"Intent: {msg.intent}",
            "intent": msg.intent,
        }

    return {
        "route": "b_side",
        "reason": "Default: B-side AI Buyer",
        "intent": msg.intent or "buy",
    }


def send_outbound_message(
    channel: str, message: OutboundChannelMessage
) -> ChannelDeliveryReceipt:
    """Send an outbound message via the correct channel adapter."""
    adapter = _get_adapter(channel)
    return adapter.send_message(message)
