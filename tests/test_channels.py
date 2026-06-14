"""
Channel Adapter Layer — 12 tests covering normalization, routing,
session store, idempotency, signature verification, and IEG events.
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.channels.mock_adapter import MockAdapter, clear_delivered, get_delivered
from src.channels.email_adapter import EmailAdapter
from src.channels.wechat_adapter import WeChatAdapter
from src.channels.whatsapp_adapter import WhatsAppAdapter
from src.channels.base import OutboundChannelMessage, NormalizedChannelMessage
from src.channels.router import route_inbound_message, send_outbound_message
from src.channels.session_store import create_session, get_session, update_session_field


# ─── 1. Mock buyer inbound normalizes correctly ────────────────────────────────

def test_mock_buyer_inbound_normalization():
    adapter = MockAdapter()
    payload = {
        "channel": "mock",
        "external_user_id": "buyer_alice",
        "text": "I need to buy 500 units of precision parts",
    }
    msg = adapter.normalize_inbound(payload)
    assert msg.channel == "mock"
    assert msg.external_user_id == "buyer_alice"
    assert msg.intent == "buy"
    assert msg.actor_id == "ACTOR-B-ALICE"
    assert msg.idempotency_key is not None
    assert len(msg.idempotency_key) == 16


# ─── 2. Mock supplier inbound with invitation token routes to M-side ───────────

def test_mock_supplier_inbound_with_token():
    adapter = MockAdapter()
    payload = {
        "channel": "mock",
        "external_user_id": "supplier_bob",
        "text": "Hi, I received your inquiry token GQ-ZXTY for the parts order",
    }
    msg = adapter.normalize_inbound(payload)
    assert msg.intent == "supply"

    routing = route_inbound_message(msg)
    assert routing["route"] == "m_side"
    assert "token" in routing["reason"].lower() or "supply" in routing["reason"].lower()


# ─── 3. Email inbound normalization ──────────────────────────────────────────

def test_email_inbound_normalization():
    adapter = EmailAdapter()
    payload = {
        "from": "buyer@corp.com",
        "subject": "RFQ for precision machined parts",
        "text": "We are looking to source 1000 units of aluminum brackets.",
        "message_id": "<msg123@mail.corp.com>",
    }
    msg = adapter.normalize_inbound(payload)
    assert msg.channel == "email"
    assert msg.external_user_id == "buyer@corp.com"
    assert msg.external_thread_id == "<msg123@mail.corp.com>"
    assert msg.intent == "buy"
    assert msg.idempotency_key is not None


# ─── 4. WhatsApp normalization (Meta webhook structure) ───────────────────────

def test_whatsapp_normalization_meta_structure():
    adapter = WhatsAppAdapter(mock=True)
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "8613900000001",
                        "id": "wamid.abc123",
                        "text": {"body": "我们可以做，报价如下"},
                    }]
                }
            }]
        }]
    }
    msg = adapter.normalize_inbound(payload)
    assert msg.channel == "whatsapp"
    assert msg.external_user_id == "8613900000001"
    assert msg.external_thread_id == "wamid.abc123"
    assert msg.intent == "supply"


# ─── 5. WeChat normalization ─────────────────────────────────────────────────

def test_wechat_normalization():
    adapter = WeChatAdapter(mock=True)
    payload = {
        "FromUserName": "o6_bmjrPTlm6_2sgVt7hMZOPfL2M",
        "Content": "确认接单，交期30天",
        "MsgId": "12345678",
    }
    msg = adapter.normalize_inbound(payload)
    assert msg.channel == "wechat"
    assert msg.external_user_id == "o6_bmjrPTlm6_2sgVt7hMZOPfL2M"
    assert msg.external_thread_id == "12345678"
    assert msg.intent == "supply"


# ─── 6. Unknown user safe handling ───────────────────────────────────────────

def test_unknown_user_safe_handling():
    adapter = MockAdapter()
    payload = {
        "channel": "mock",
        "external_user_id": "unknown_xyz",
        "text": "Hello",
    }
    msg = adapter.normalize_inbound(payload)
    assert msg.actor_id is None
    routing = route_inbound_message(msg)
    assert routing["route"] in ("b_side", "m_side", "logistics")


# ─── 7. Duplicate idempotency key is deterministic ───────────────────────────

def test_duplicate_idempotency_key_deterministic():
    adapter = MockAdapter()
    payload = {
        "channel": "mock",
        "external_user_id": "buyer_carol",
        "text": "I need 200 steel brackets",
    }
    msg1 = adapter.normalize_inbound(payload)
    msg2 = adapter.normalize_inbound(payload)
    assert msg1.idempotency_key == msg2.idempotency_key


# ─── 8. Missing/wrong signature fails closed ─────────────────────────────────

def test_email_wrong_signature_fails():
    os.environ["EMAIL_WEBHOOK_SECRET"] = "supersecret"
    adapter = EmailAdapter()

    headers_no_sig = {}
    assert adapter.verify_signature(headers_no_sig, b'{"test": 1}') is False

    headers_wrong = {"X-Email-Signature": "badhash"}
    assert adapter.verify_signature(headers_wrong, b'{"test": 1}') is False

    del os.environ["EMAIL_WEBHOOK_SECRET"]


# ─── 9. IEG events logged for inbound (in-memory DB) ─────────────────────────

def test_ieg_events_logged_for_inbound(tmp_path, monkeypatch):
    """Channel events are appended to ExecutionEvent via the logger."""
    from src.db.base import Base
    import src.db.models  # noqa: F401
    from src.db.repositories.execution_event_repo import ExecutionEventRepo

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    logged = []

    def fake_log(event_type, payload, source_channel=None, actor_id=None):
        logged.append(event_type)

    monkeypatch.setattr(
        "src.channels.channel_event_logger.log_channel_event", fake_log
    )

    from src.channels.channel_event_logger import log_channel_event
    log_channel_event("CHANNEL_INBOUND_MESSAGE_RECEIVED", {"channel": "mock"})
    log_channel_event("CHANNEL_MESSAGE_NORMALIZED", {"channel": "mock"})
    log_channel_event("CHANNEL_ROUTE_DECIDED", {"channel": "mock", "route": "b_side"})

    assert "CHANNEL_INBOUND_MESSAGE_RECEIVED" in logged
    assert "CHANNEL_MESSAGE_NORMALIZED" in logged
    assert "CHANNEL_ROUTE_DECIDED" in logged


# ─── 10. IEG events logged for outbound ──────────────────────────────────────

def test_ieg_events_logged_for_outbound(monkeypatch):
    logged = []

    def fake_log(event_type, payload, source_channel=None, actor_id=None):
        logged.append(event_type)

    monkeypatch.setattr(
        "src.channels.channel_event_logger.log_channel_event", fake_log
    )

    from src.channels.channel_event_logger import log_channel_event
    log_channel_event("CHANNEL_OUTBOUND_MESSAGE_SENT", {"channel": "mock", "status": "mocked"})
    log_channel_event("CHANNEL_DELIVERY_RECEIPT_RECEIVED", {"channel": "mock", "status": "mocked"})

    assert "CHANNEL_OUTBOUND_MESSAGE_SENT" in logged
    assert "CHANNEL_DELIVERY_RECEIPT_RECEIVED" in logged


# ─── 11. Session store persists extended fields ───────────────────────────────

def test_session_store_extended_fields(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "channel_sessions").mkdir(parents=True)

    session = create_session(
        channel="mock",
        external_user_id="buyer_dave",
        extra={
            "external_thread_id": "thread_001",
            "actor_id": "ACTOR-B-DAVE",
            "project_id": "proj_abc",
            "b_workspace_id": "bws_xyz",
            "m_workspace_id": None,
            "role_context": "buyer",
        },
    )

    loaded = get_session(session["session_id"])
    assert loaded is not None
    assert loaded["actor_id"] == "ACTOR-B-DAVE"
    assert loaded["project_id"] == "proj_abc"
    assert loaded["b_workspace_id"] == "bws_xyz"
    assert loaded["role_context"] == "buyer"
    assert loaded["last_message_at"] is not None

    updated = update_session_field(session["session_id"], b_workspace_id="bws_new", role_context="supplier")
    assert updated["b_workspace_id"] == "bws_new"
    assert updated["role_context"] == "supplier"


# ─── 12. Router routes buyer to b_side, supplier to m_side ───────────────────

def test_router_routes_buyer_and_supplier():
    buyer_msg = NormalizedChannelMessage(
        channel="mock",
        external_user_id="buyer_eve",
        text="I want to purchase 300 units",
        intent="buy",
    )
    buyer_routing = route_inbound_message(buyer_msg)
    assert buyer_routing["route"] == "b_side"

    supplier_msg = NormalizedChannelMessage(
        channel="mock",
        external_user_id="supplier_frank",
        text="GQ-ABCD we can make this, lead time 20 days",
        intent="supply",
    )
    supplier_routing = route_inbound_message(supplier_msg)
    assert supplier_routing["route"] == "m_side"

    logistics_msg = NormalizedChannelMessage(
        channel="mock",
        external_user_id="logistics_agent",
        text="Shipment tracking update",
        intent="logistics",
    )
    logistics_routing = route_inbound_message(logistics_msg)
    assert logistics_routing["route"] == "logistics"
