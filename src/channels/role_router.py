# Unicode escapes preserve the original multilingual parser vocabulary.
# This source representation does not translate the accepted input values.
"""
Role-aware IM router — routes inbound messages to B-side or M-side workflow.
"""

from __future__ import annotations
import re
from src.channels.message_types import InboundMessage

# Supplier token patterns: GQ-XXXX or GIRAFFE-M-XXXX
_TOKEN_PATTERN = re.compile(r"\b(GQ-\w{4,}|GIRAFFE-M-\w{4,})\b", re.IGNORECASE)

_M_SIDE_PHRASES_ZH = [
    '\u53ef\u4ee5\u505a', '\u4e0d\u80fd\u505a', '\u62a5\u4ef7', '\u4ea4\u671f', "MOQ", '\u6750\u6599', '\u4ea7\u80fd',
    '\u5f00\u5de5', '\u6837\u54c1', '\u5927\u8d27', "QC", '\u7269\u6d41', "EXW", "FOB", "DDP",
    '\u63a5\u5355', '\u786e\u8ba4', '\u53d1\u8d27', '\u8d28\u68c0', '\u5feb\u9012',
]

_M_SIDE_PHRASES_EN = [
    "we can make", "cannot make", "can make", "quote", "lead time",
    "moq", "material available", "capacity", "sample", "mass production",
    "qc", "shipping", "exw", "fob", "ddp", "acknowledge", "production",
]


def _contains_supplier_token(text: str | None) -> str | None:
    """Return the matched invitation token if found, else None."""
    if not text:
        return None
    m = _TOKEN_PATTERN.search(text)
    return m.group(0) if m else None


def _contains_m_side_phrase(text: str | None) -> bool:
    """Return True if text contains M-side supplier phrases."""
    if not text:
        return False
    tl = text.lower()
    for phrase in _M_SIDE_PHRASES_ZH + _M_SIDE_PHRASES_EN:
        if phrase.lower() in tl:
            return True
    return False


def route_inbound_message_by_role(inbound: InboundMessage) -> dict:
    """
    Route an inbound IM message to B-side or M-side workflow.

    Rules (priority order):
    1. Message contains invitation token → M-side
    2. Message has m_workspace_id set → M-side
    3. Message contains M-side supplier phrases → M-side (likely supplier reply)
    4. Default → B-side AI Buyer
    """
    text = inbound.text or ""

    # Rule 1: invitation token
    token = _contains_supplier_token(text)
    if token:
        return {
            "route": "m_side",
            "reason": f"Invitation token detected: {token}",
            "token": token,
        }

    # Rule 2: explicit m_workspace_id
    if inbound.m_workspace_id:
        return {
            "route": "m_side",
            "reason": "m_workspace_id is set in message context",
        }

    # Rule 3: M-side supplier phrases
    if _contains_m_side_phrase(text):
        return {
            "route": "m_side",
            "reason": "Supplier response phrase detected in message",
        }

    # Default: B-side AI Buyer
    return {
        "route": "b_side",
        "reason": "No M-side signals detected; routing to B-side AI Buyer",
    }
