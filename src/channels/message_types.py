"""
Shared IM message types for Giraffe Agent channel adapters.
"""

from __future__ import annotations
from pydantic import BaseModel


class InboundMessage(BaseModel):
    channel: str
    external_user_id: str
    text: str | None = None
    attachments: list[dict] = []
    session_id: str | None = None
    m_workspace_id: str | None = None
    b_workspace_id: str | None = None
