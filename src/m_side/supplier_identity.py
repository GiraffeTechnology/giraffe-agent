"""
M-side supplier identity resolution and invitation token management.
Supports: known supplier mode, invitation token mode, manual mapping mode.
"""

from __future__ import annotations
import json
import random
import string
from pathlib import Path

from src.core_schema.m_side_types import MSideSupplierProfile
from src.m_side.supplier_profile import get_supplier_profile, save_supplier_profile

_TOKEN_STORE = Path("data/invitation_tokens/tokens.json")


def _ensure_dir() -> None:
    _TOKEN_STORE.parent.mkdir(parents=True, exist_ok=True)


def _load_tokens() -> dict:
    _ensure_dir()
    if _TOKEN_STORE.exists():
        with open(_TOKEN_STORE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_tokens(tokens: dict) -> None:
    _ensure_dir()
    with open(_TOKEN_STORE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)


def _generate_token() -> str:
    """Generate a short supplier invitation token. Format: GQ-XXXX (4 alphanumeric chars)."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=4))
    return f"GQ-{suffix}"


def create_invitation_token(
    b_workspace_id: str,
    inquiry_id: str,
    supplier_id: str,
) -> str:
    """
    Create a short-lived supplier invitation token linked to a B-side workspace and inquiry.
    Token format: GQ-XXXX
    """
    tokens = _load_tokens()

    # Generate unique token
    token = _generate_token()
    attempts = 0
    while token in tokens and attempts < 20:
        token = _generate_token()
        attempts += 1

    tokens[token] = {
        "b_workspace_id": b_workspace_id,
        "inquiry_id": inquiry_id,
        "supplier_id": supplier_id,
    }
    _save_tokens(tokens)
    return token


def resolve_supplier_from_message(
    channel: str,
    external_user_id: str,
    text: str | None = None,
) -> MSideSupplierProfile | None:
    """
    Resolve supplier identity from IM message or invitation token.
    Checks (in order):
    1. Token in message text → look up supplier_id from token store
    2. Channel + external_user_id → look up by profile binding
    """
    # Check for invitation token in message
    if text:
        import re
        token_match = re.search(r"\b(GQ-\w{4,}|GIRAFFE-M-\w{4,})\b", text, re.IGNORECASE)
        if token_match:
            token = token_match.group(0).upper()
            tokens = _load_tokens()
            token_data = tokens.get(token)
            if token_data:
                supplier_id = token_data.get("supplier_id")
                if supplier_id:
                    return get_supplier_profile(supplier_id)

    # Check by channel identity binding
    from src.m_side.supplier_profile import list_supplier_profiles
    for profile in list_supplier_profiles():
        if profile.channel == channel and profile.external_user_id == external_user_id:
            return profile

    return None


def bind_supplier_channel(
    supplier_id: str,
    channel: str,
    external_user_id: str,
) -> MSideSupplierProfile:
    """
    Bind a supplier profile to an IM channel identity (channel + external_user_id).
    """
    profile = get_supplier_profile(supplier_id)
    if profile is None:
        raise ValueError(f"Supplier profile not found: {supplier_id}")
    profile.channel = channel
    profile.external_user_id = external_user_id
    return save_supplier_profile(profile)


def lookup_token_data(token: str) -> dict | None:
    """Return token metadata (b_workspace_id, inquiry_id, supplier_id) or None."""
    tokens = _load_tokens()
    return tokens.get(token.upper())
