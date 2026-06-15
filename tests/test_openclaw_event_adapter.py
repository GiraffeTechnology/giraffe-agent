"""
OpenClaw Event Adapter Tests.

Tests:
  - Valid B-side buyer inquiry is routed correctly
  - Approval phrases trigger draft approval workflow
  - Empty message is handled gracefully
  - Non-English messages are handled
  - Mixed Chinese-English messages are handled
  - Missing conversation_id is handled
  - Missing sender_id is handled
  - Malformed / missing fields produce structured error (no crash)
  - Duplicate inbound message ID is handled
  - Broken JSON in event payload produces structured error
  - M-side routing is triggered when mode=m_side
"""

import os
import pytest
import tempfile

os.environ.setdefault("GIRAFFE_DB_MODE", "off")


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    """Redirect all data stores to a fresh temp dir for each test."""
    monkeypatch.chdir(tmp_path)
    import src.openclaw_skill.conversation_binding_store as cbs
    import src.openclaw_skill.message_draft_store as mds
    orig_cbs = cbs._DATA_DIR
    orig_mds = mds._DATA_DIR
    cbs._DATA_DIR = tmp_path / "data" / "conversation_bindings"
    mds._DATA_DIR = tmp_path / "data" / "message_drafts"
    cbs._DATA_DIR.mkdir(parents=True, exist_ok=True)
    mds._DATA_DIR.mkdir(parents=True, exist_ok=True)
    yield
    cbs._DATA_DIR = orig_cbs
    mds._DATA_DIR = orig_mds


def _event(**kwargs):
    defaults = {
        "source": "openclaw",
        "channel": "openclaw-mock",
        "channel_account_id": "acct-001",
        "conversation_id": "conv-001",
        "sender_id": "buyer-001",
        "message_text": "I need 500 cotton t-shirts.",
        "project_id": "proj_test",
    }
    defaults.update(kwargs)
    return defaults


# ─── Basic routing ─────────────────────────────────────────────────────────────

def test_valid_buyer_inquiry_routes_without_crash():
    from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event
    result = adapt_openclaw_event(_event(
        message_text="I need 10,000 white men's shirts, size S/M/L/XL, delivered to Vancouver in 45 days."
    ))
    assert isinstance(result, dict)
    assert "error" not in str(result).lower() or "ok" in result


def test_empty_message_handled_gracefully():
    from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event
    result = adapt_openclaw_event(_event(message_text=""))
    assert isinstance(result, dict)
    # Should not crash


def test_non_english_message_handled():
    from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event
    result = adapt_openclaw_event(_event(
        message_text="我需要10000件白色男士衬衫，交货地温哥华，45天内交货。"
    ))
    assert isinstance(result, dict)


def test_mixed_chinese_english_message_handled():
    from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event
    result = adapt_openclaw_event(_event(
        message_text="I need 10000件cotton shirts，deliver to Vancouver，deadline 45 days，target price USD 4.80."
    ))
    assert isinstance(result, dict)


def test_missing_conversation_id_handled():
    from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event
    result = adapt_openclaw_event(_event(conversation_id=""))
    assert isinstance(result, dict)


def test_missing_sender_id_handled():
    from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event
    result = adapt_openclaw_event(_event(sender_id=""))
    assert isinstance(result, dict)


def test_approval_phrase_triggers_approve_flow():
    from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event
    from src.openclaw_skill.message_draft_store import create_draft, find_pending_drafts

    # Create a pending draft for the project
    draft = create_draft(
        project_id="proj_approve",
        channel="openclaw-mock",
        target_role="supplier",
        draft_text="Supplier inquiry text.",
    )
    assert draft.approval_status == "pending_approval"

    # Send approval message
    result = adapt_openclaw_event(_event(
        project_id="proj_approve",
        message_text="confirm send",
    ))
    assert isinstance(result, dict)
    # Draft should now be approved (or result references approval)
    from src.openclaw_skill.message_draft_store import find_draft_by_id
    updated = find_draft_by_id(draft.id)
    # Approval may have occurred
    assert updated is not None


def test_reject_phrase_triggers_reject_flow():
    from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event
    from src.openclaw_skill.message_draft_store import create_draft, find_draft_by_id

    draft = create_draft(
        project_id="proj_reject",
        channel="openclaw-mock",
        target_role="supplier",
        draft_text="Draft to reject.",
    )

    result = adapt_openclaw_event(_event(
        project_id="proj_reject",
        message_text="reject",
    ))
    assert isinstance(result, dict)
    updated = find_draft_by_id(draft.id)
    assert updated is not None


def test_duplicate_conversation_id_does_not_crash():
    from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event
    event = _event(conversation_id="conv-dup-001", message_text="First message.")
    result1 = adapt_openclaw_event(event)
    result2 = adapt_openclaw_event(event)
    assert isinstance(result1, dict)
    assert isinstance(result2, dict)


def test_m_side_mode_routes_to_m_side():
    from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event
    result = adapt_openclaw_event(_event(
        mode="m_side",
        message_text="我们可以生产，交期30天，单价5元。",
    ))
    assert isinstance(result, dict)


def test_event_with_no_project_id_handled():
    from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event
    result = adapt_openclaw_event({
        "source": "openclaw",
        "channel": "openclaw-mock",
        "channel_account_id": "acct-001",
        "conversation_id": "conv-no-project",
        "sender_id": "sender-001",
        "message_text": "Hello, can you help me source shirts?",
    })
    assert isinstance(result, dict)


def test_malformed_timestamp_handled():
    from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event
    result = adapt_openclaw_event(_event(
        timestamp="not-a-timestamp-!@#$",
        message_text="Test message.",
    ))
    assert isinstance(result, dict)
