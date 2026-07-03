from typing import Optional
from pydantic import BaseModel, Field

class OpenClawEvent(BaseModel):
    source: str = "openclaw"
    channel: str = ""
    channel_account_id: str = ""
    conversation_id: str
    message_id: str = ""
    sender_id: str = ""
    sender_display_name: str = ""
    message_text: str = ""
    message_type: str = "text"
    attachments: list[dict] = Field(default_factory=list)
    timestamp: str = ""
    project_id: Optional[str] = None
    actor_id: Optional[str] = None
    role_context: Optional[str] = None
    mode: str = "auto"

class OpenClawManagedAccount(BaseModel):
    account_connection_id: str
    platform: str
    channel: str = ""
    channel_account_id: str = ""
    owner_user_id: Optional[str] = None
    display_name: Optional[str] = None
    status: str = "connected"
    permissions: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    expires_at: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    metadata: dict = Field(default_factory=dict)
