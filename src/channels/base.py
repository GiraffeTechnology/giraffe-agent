"""
Channel adapter base types and abstract interface for Giraffe Agent.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel


# ─── Data types ───────────────────────────────────────────────────────────────

class ChannelIdentity(BaseModel):
    channel: str
    external_user_id: str
    external_thread_id: str | None = None
    display_name: str | None = None


class InboundChannelMessage(BaseModel):
    channel: str
    external_user_id: str
    external_thread_id: str | None = None
    text: str | None = None
    html: str | None = None
    subject: str | None = None
    attachments: list[dict] = []
    raw_payload: dict = {}
    received_at: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.received_at:
            self.received_at = datetime.now(timezone.utc).isoformat()


class OutboundChannelMessage(BaseModel):
    channel: str
    to_external_user_id: str
    to_external_thread_id: str | None = None
    text: str
    html: str | None = None
    subject: str | None = None
    attachments: list[dict] = []
    metadata: dict = {}


class ChannelDeliveryReceipt(BaseModel):
    channel: str
    external_user_id: str
    message_id: str | None = None
    status: str  # "sent" | "delivered" | "failed" | "mocked"
    provider_response: dict = {}
    sent_at: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.sent_at:
            self.sent_at = datetime.now(timezone.utc).isoformat()


class NormalizedChannelMessage(BaseModel):
    """Canonical internal representation after normalization."""
    channel: str
    external_user_id: str
    external_thread_id: str | None = None
    actor_id: str | None = None
    text: str | None = None
    intent: str | None = None          # "buy", "supply", "logistics", "upstream", "order_update"
    attachments: list[dict] = []
    raw: dict = {}
    normalized_at: str = ""
    idempotency_key: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if not self.normalized_at:
            self.normalized_at = datetime.now(timezone.utc).isoformat()


# ─── Abstract adapter ─────────────────────────────────────────────────────────

class BaseChannelAdapter(ABC):
    """Abstract channel adapter — concrete implementations per provider."""

    channel_name: str = "base"

    @abstractmethod
    def normalize_inbound(self, payload: dict) -> NormalizedChannelMessage:
        """Parse provider-specific webhook payload → NormalizedChannelMessage."""
        ...

    @abstractmethod
    def send_message(self, message: OutboundChannelMessage) -> ChannelDeliveryReceipt:
        """Send an outbound message and return a delivery receipt."""
        ...

    def verify_signature(self, headers: dict, payload: bytes | dict) -> bool:
        """Verify provider webhook signature. Override per provider."""
        return True

    def resolve_actor_identity(
        self, channel: str, external_user_id: str
    ) -> str | None:
        """Map channel identity to internal actor_id. Override for DB lookup."""
        return None
