"""Regression tests for the WeChat 16:33 failure.

Real WeChat messages to WeixinClawBot ("帮我询价，1000件纯棉T恤，交加拿大" and
"询价5000件格子衬衫，45天交东京，高品质") returned "Agent couldn't generate a
response." because a backend-dependency error in the skill pipeline produced a
raw HTTP 500, which the OpenClaw bridge turned into an empty agent result.

These tests lock in the fail-soft contract: skill routes must answer HTTP 200
with a {status, output, reply_text} envelope even when the pipeline raises, and
the /healthz and /invoke routes must exist.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import api.main as main


@pytest.fixture
def client():
    # raise_server_exceptions=False mirrors a real server: an unhandled pipeline
    # error flows through the registered fail-soft handler instead of bubbling up.
    with TestClient(main.app, raise_server_exceptions=False) as c:
        yield c


WECHAT_MESSAGES = [
    "帮我询价，1000件纯棉T恤，交加拿大",
    "询价5000件格子衬衫，45天交东京，高品质",
]


def _assert_envelope(resp):
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] in ("ok", "error")
    assert isinstance(body["output"], str) and body["output"].strip()
    assert isinstance(body["reply_text"], str) and body["reply_text"].strip()
    lowered = body["output"].lower()
    assert "traceback" not in lowered


def test_healthz_exists(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_invoke_route_exists(client):
    # Must not 404; even a garbage body fails soft with a 200 envelope.
    resp = client.post("/invoke", json={"weird": "x"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


@pytest.mark.parametrize("message", WECHAT_MESSAGES)
def test_skill_invoke_failsoft_on_dependency_error(client, monkeypatch, message):
    # Force the pipeline to raise like a down GLTG/DB/LLM dependency would.
    def _boom(*_a, **_k):
        raise RuntimeError("GLTG service needs to be started")

    monkeypatch.setattr(
        "src.openclaw_skill.openclaw_event_adapter.adapt_openclaw_event", _boom
    )

    resp = client.post(
        "/api/skill/invoke",
        json={
            "source": "openclaw",
            "channel": "weixin",
            "conversation_id": "real-wechat-1633",
            "sender_id": "wechat-user",
            "message_text": message,
            "message_type": "text",
        },
    )
    _assert_envelope(resp)
    # The degraded reply, never a raw 500 / empty body.
    assert resp.json()["status"] == "error"


@pytest.mark.parametrize("message", WECHAT_MESSAGES)
def test_invoke_wechat_webhook_shape_failsoft(client, monkeypatch, message):
    def _boom(*_a, **_k):
        raise RuntimeError("dependency down")

    monkeypatch.setattr(
        "src.openclaw_skill.openclaw_event_adapter.adapt_openclaw_event", _boom
    )
    resp = client.post(
        "/invoke",
        json={"content": message, "from_user": "wxid_test", "room_id": "room@chatroom"},
    )
    _assert_envelope(resp)
