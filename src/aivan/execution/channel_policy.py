from __future__ import annotations
from typing import Optional

from aivan.db.models.inquiry import InquiryDraftRecord

COUNTERPARTY_ROLES = {"customer", "supplier", "buyer", "seller"}
EMAIL_CHANNELS = {"email", "smtp"}
PERSONAL_IM_CHANNELS = {
    "wechat",
    "weixin",
    "line",
    "whatsapp",
    "telegram",
    "signal",
    "personal_im",
}
USER_CONTROL_CHANNELS = PERSONAL_IM_CHANNELS | {"im", "openclaw-im", "user-im"}


def normalize_channel(channel: Optional[str]) -> str:
    return (channel or "").strip().lower().replace("_", "-")


def is_email_channel(channel: Optional[str]) -> bool:
    return normalize_channel(channel) in EMAIL_CHANNELS


def is_personal_im_channel(channel: Optional[str]) -> bool:
    normalized = normalize_channel(channel)
    return normalized in PERSONAL_IM_CHANNELS or normalized in {"we-chat", "whats-app"}


def is_counterparty_role(role: Optional[str]) -> bool:
    return (role or "").strip().lower() in COUNTERPARTY_ROLES


def validate_counterparty_draft_channel(channel: Optional[str], target_role: Optional[str]) -> None:
    """Current deployment permits counterparty outbound commercial messages by email only."""
    if not is_counterparty_role(target_role):
        return
    if not is_email_channel(channel):
        raise ValueError(
            "AIVAN channel policy blocks counterparty outbound commercial messages "
            f"over '{channel or 'unknown'}'. Use email with human approval."
        )


def validate_draft_send_policy(draft: InquiryDraftRecord) -> None:
    validate_counterparty_draft_channel(draft.channel, draft.target_role)
