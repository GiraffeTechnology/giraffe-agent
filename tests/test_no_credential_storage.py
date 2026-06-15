"""
No Credential Storage Tests — AIVAN Product Rules #2 and #8.

Rule #2: AIVAN must never store platform passwords, cookies, session tokens,
         or credential material.
Rule #8: API keys and secrets must never be logged.

Tests:
  - Message drafts do not store credential fields
  - Conversation bindings do not store credential fields
  - Supplier profiles do not store platform passwords or session tokens
  - .env.example contains only placeholders (no real secrets)
  - No hardcoded secret patterns in source files
  - OpenClaw event model does not include channel tokens
  - AIVAN API response does not echo back secret values
"""

import os
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent

os.environ.setdefault("GIRAFFE_DB_MODE", "off")

# ─── Field-level credential exclusion tests ───────────────────────────────────

def test_message_draft_has_no_credential_fields():
    """MessageDraft schema must not include fields for credentials."""
    from src.openclaw_skill.message_draft_store import MessageDraft
    field_names = set(MessageDraft.model_fields.keys())
    forbidden = {"password", "token", "cookie", "session", "secret", "api_key", "auth"}
    overlap = field_names & forbidden
    assert not overlap, f"MessageDraft has forbidden credential fields: {overlap}"


def test_conversation_binding_has_no_credential_fields():
    from src.openclaw_skill.conversation_binding_store import ConversationBinding
    field_names = set(ConversationBinding.model_fields.keys())
    forbidden = {"password", "token", "cookie", "session", "secret", "api_key", "auth"}
    overlap = field_names & forbidden
    assert not overlap, f"ConversationBinding has forbidden credential fields: {overlap}"


def test_supplier_profile_has_no_credential_fields():
    from src.core_schema.m_side_types import MSideSupplierProfile
    field_names = set(MSideSupplierProfile.model_fields.keys())
    forbidden = {"password", "cookie", "session_token", "platform_token", "login_token"}
    overlap = field_names & forbidden
    assert not overlap, f"MSideSupplierProfile has forbidden credential fields: {overlap}"


def test_openclaw_event_model_no_channel_tokens():
    """OpenClaw event must not accept raw IM tokens or cookies."""
    from src.openclaw_skill.openclaw_event_adapter import OpenClawEvent
    field_names = set(OpenClawEvent.model_fields.keys())
    forbidden = {"wechat_token", "whatsapp_token", "session_cookie", "auth_token",
                 "platform_password", "bearer_token"}
    overlap = field_names & forbidden
    assert not overlap, f"OpenClawEvent has forbidden credential fields: {overlap}"


# ─── .env.example audit ───────────────────────────────────────────────────────

def test_env_example_has_no_real_secrets():
    """All values in .env.example must be placeholders or empty."""
    env_path = ROOT / ".env.example"
    assert env_path.exists(), ".env.example must exist"
    content = env_path.read_text(encoding="utf-8")

    real_secret_patterns = [
        r"sk-[A-Za-z0-9]{20,}",       # OpenAI-style keys
        r"AKIA[A-Za-z0-9]{16}",        # AWS access key
        r"ghp_[A-Za-z0-9]{36}",        # GitHub token
        r"[0-9a-f]{40}",               # 40-char hex (e.g. git tokens)
    ]
    for pattern in real_secret_patterns:
        matches = re.findall(pattern, content)
        assert not matches, f".env.example contains potential real secret: {matches}"


def test_env_example_uses_placeholder_values():
    """Values that look like API keys should be 'your-*-here' or empty."""
    env_path = ROOT / ".env.example"
    content = env_path.read_text(encoding="utf-8")
    # Check that any line with KEY= only has placeholders
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if not value:
            continue
        if any(kw in key.upper() for kw in ["KEY", "SECRET", "PASSWORD", "TOKEN"]):
            assert "your-" in value.lower() or value.startswith("http"), (
                f"Non-placeholder value for {key}: '{value}'"
            )


# ─── Source file secret scan ───────────────────────────────────────────────────

_HARDCODED_SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{20,}",
    r"AKIA[A-Za-z0-9]{16}",
    r"ghp_[A-Za-z0-9]{36}",
    r"password\s*=\s*['\"][^'\"]{8,}['\"]",
    r"api_key\s*=\s*['\"][^'\"]{8,}['\"]",
]

_SKIP_DIRS = {".venv", ".git", "__pycache__", "node_modules", "dist", "build", ".pytest_cache"}


def _iter_source_files():
    for d in ["src", "scripts", "tests", "api"]:
        base = ROOT / d
        if not base.exists():
            continue
        for fpath in base.rglob("*.py"):
            if any(part in _SKIP_DIRS for part in fpath.parts):
                continue
            yield fpath


def test_no_hardcoded_secrets_in_source():
    """No hardcoded API keys or passwords in Python source files."""
    violations = []
    for fpath in _iter_source_files():
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for pat in _HARDCODED_SECRET_PATTERNS:
            matches = re.findall(pat, content)
            if matches:
                violations.append(f"{fpath.relative_to(ROOT)}: {matches}")
    assert not violations, f"Hardcoded secrets found:\n" + "\n".join(violations)


# ─── Log leakage tests ────────────────────────────────────────────────────────

def test_api_key_not_echoed_in_responses():
    """Setting AIVAN_API_KEY should not cause the server to echo it in responses."""
    import os
    os.environ["AIVAN_API_KEY"] = "super_secret_key_123"
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        resp = client.get("/health", headers={"X-AIVAN-API-Key": "super_secret_key_123"})
        assert resp.status_code == 200
        assert "super_secret_key_123" not in resp.text
    finally:
        del os.environ["AIVAN_API_KEY"]


def test_missing_api_key_header_returns_401_not_secret():
    """When API key is required, 401 response must not reveal the key value."""
    import os
    os.environ["AIVAN_API_KEY"] = "hidden_key_abc"
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)
        resp = client.post("/api/openclaw/events", json={
            "source": "openclaw",
            "channel": "openclaw-mock",
        })
        assert resp.status_code == 401
        assert "hidden_key_abc" not in resp.text
    finally:
        del os.environ["AIVAN_API_KEY"]


# ─── OpenClaw account model tests ─────────────────────────────────────────────

def test_openclaw_event_never_contains_wechat_credentials():
    """An OpenClaw event forwarded to AIVAN must not carry IM platform credentials."""
    from src.openclaw_skill.openclaw_event_adapter import OpenClawEvent
    event = OpenClawEvent(
        channel="openclaw-weixin",
        channel_account_id="acct-001",
        conversation_id="conv-001",
        sender_id="user-001",
        message_text="I need 1000 shirts.",
    )
    # Serialize and check no credential fields leaked in
    event_dict = event.model_dump()
    assert "password" not in event_dict
    assert "cookie" not in event_dict
    assert "token" not in event_dict or event_dict.get("token") is None
    assert "wechat_session" not in event_dict
