"""
Regression tests for OpenClaw M-side RFQ workspace matching.

Bug: When an OpenClaw supplier reply arrives with project_id = rfq_id,
the handler was unable to find the persisted MSideWorkspace because it
only accepted an explicit m_workspace_id — it had no lookup by rfq_id.

Fix: Added find_workspace_by_rfq_id() and find_active_workspace_for_supplier_and_rfq()
to supplier_workspace.py, and updated handle_m_side_submit_supplier_response() to
resolve the workspace by project_id/rfq_id when m_workspace_id is not supplied.

Note on rfq_id: create_b_workspace() assigns an initial rfq_id, but
structure_requirement() creates a BuyerRequirement with a *new* rfq_id.
dispatch_supplier_inquiry() passes req.rfq_id (from the structured requirement)
into SupplierInquiryContext and the resulting MSideWorkspace. Tests must use
this effective rfq_id, not bws.rfq_id.
"""

import pytest
from pathlib import Path


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def use_tmp_dir(tmp_path, monkeypatch):
    """Redirect all file storage to tmp_path for isolation."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "b_side_workspaces").mkdir(parents=True)
    (tmp_path / "data" / "m_side_workspaces").mkdir(parents=True)
    (tmp_path / "data" / "industrial_execution_graph").mkdir(parents=True)
    (tmp_path / "data" / "invitation_tokens").mkdir(parents=True)
    yield


def _make_full_m_workspace(b_workspace_id: str, supplier_id: str = "sup_001"):
    """
    Build the full chain: structure requirement → draft → dispatch → M-side workspace.
    Returns (m_workspace_id, rfq_id_on_m_workspace).

    Note: rfq_id_on_m_workspace comes from req.rfq_id (set by structure_requirement),
    NOT from bws.rfq_id (set by create_b_workspace). These are different values.
    """
    from src.m_side.supplier_profile import create_supplier_profile
    from src.bm_bridge.inquiry_dispatcher import dispatch_supplier_inquiry
    from src.b_side.workspace import get_b_workspace, save_b_workspace
    from src.b_side.requirement_structurer import structure_requirement
    from src.b_side.inquiry_drafter import draft_supplier_inquiry
    from src.m_side.supplier_workspace import get_m_workspace

    create_supplier_profile(
        supplier_id=supplier_id,
        name="Test Supplier",
        channel="openclaw-email",
        external_user_id="supplier_openclaw@test.com",
    )

    workspace = get_b_workspace(b_workspace_id)
    req = structure_requirement(b_workspace_id, workspace.raw_requirement)
    workspace.buyer_requirement = req
    workspace.status = "requirement_structured"
    save_b_workspace(workspace)

    draft = draft_supplier_inquiry(b_workspace_id, [supplier_id])
    workspace = get_b_workspace(b_workspace_id)
    workspace.supplier_inquiry_draft = draft
    workspace.status = "inquiry_drafted"
    save_b_workspace(workspace)

    contexts = dispatch_supplier_inquiry(b_workspace_id, [supplier_id], channel="mock")
    assert len(contexts) == 1
    m_workspace_id = contexts[0].m_workspace_id

    # The rfq_id on the M-side workspace is from the structured requirement, not bws.rfq_id
    m_ws = get_m_workspace(m_workspace_id)
    return m_workspace_id, m_ws.rfq_id


# ─── 1. Normal path: explicit m_workspace_id ──────────────────────────────────

def test_explicit_m_workspace_id_still_works():
    from src.b_side.workspace import create_b_workspace
    from src.openclaw_skill.m_side_actions import handle_m_side_submit_supplier_response

    bws = create_b_workspace("500 aluminum parts")
    m_workspace_id, rfq_id = _make_full_m_workspace(bws.b_workspace_id)

    response = handle_m_side_submit_supplier_response({
        "m_workspace_id": m_workspace_id,
        "message": "We can make it. Lead time 30 days. Unit price USD 5.00.",
    })

    assert response["ok"] is True, response
    assert response["status"] == "supplier_response_received"
    assert response["m_workspace_id"] == m_workspace_id


# ─── 2. Core bug fix: project_id resolves workspace by rfq_id ─────────────────

def test_project_id_resolves_workspace_by_rfq_id():
    """
    Reproduces the exact bug: OpenClaw event passes project_id = rfq_id,
    no m_workspace_id. The handler must find the M-side workspace via rfq_id.
    """
    from src.b_side.workspace import create_b_workspace
    from src.m_side.supplier_workspace import get_m_workspace
    from src.openclaw_skill.m_side_actions import handle_m_side_submit_supplier_response

    bws = create_b_workspace("300 steel brackets for export")
    m_workspace_id, rfq_id = _make_full_m_workspace(bws.b_workspace_id)

    # Confirm persisted workspace stores rfq_id in workspace.rfq_id
    m_ws = get_m_workspace(m_workspace_id)
    assert m_ws.rfq_id == rfq_id

    # Simulate OpenClaw event — no m_workspace_id, only project_id
    openclaw_event = {
        "source": "openclaw",
        "channel": "openclaw-email",
        "channel_account_id": "test_email_account",
        "conversation_id": "supplier_thread_001",
        "sender_id": "supplier_001",
        "sender_display_name": "Test Supplier",
        "message_text": "We can make it. Unit price USD 4.80. Lead time 38 days.",
        "message_type": "text",
        "attachments": [],
        "project_id": rfq_id,
        "mode": "m_side",
    }

    response = handle_m_side_submit_supplier_response(openclaw_event)
    assert response["ok"] is True, f"Expected ok=True, got: {response}"
    assert response["status"] == "supplier_response_received", response

    # Reload and verify message was actually appended
    m_ws = get_m_workspace(m_workspace_id)
    assert "We can make it" in "\n".join(m_ws.raw_supplier_messages)
    assert len(m_ws.raw_supplier_messages) == 1


# ─── 3. Message count increases after each append ─────────────────────────────

def test_supplier_reply_message_count_increases():
    from src.b_side.workspace import create_b_workspace
    from src.m_side.supplier_workspace import get_m_workspace
    from src.openclaw_skill.m_side_actions import handle_m_side_submit_supplier_response

    bws = create_b_workspace("200 precision machined parts")
    m_workspace_id, rfq_id = _make_full_m_workspace(bws.b_workspace_id)

    r1 = handle_m_side_submit_supplier_response({
        "project_id": rfq_id,
        "message_text": "We can make it. Lead time 25 days.",
    })
    assert r1["ok"] is True, r1

    ws = get_m_workspace(m_workspace_id)
    assert len(ws.raw_supplier_messages) == 1

    r2 = handle_m_side_submit_supplier_response({
        "project_id": rfq_id,
        "message_text": "MOQ is 100 pcs. Unit price USD 6.50.",
    })
    assert r2["ok"] is True, r2

    ws = get_m_workspace(m_workspace_id)
    assert len(ws.raw_supplier_messages) == 2


# ─── 4. Execution event is appended ──────────────────────────────────────────

def test_execution_event_appended_after_supplier_reply():
    from src.b_side.workspace import create_b_workspace
    from src.m_side.m_event_logger import read_events
    from src.openclaw_skill.m_side_actions import handle_m_side_submit_supplier_response

    bws = create_b_workspace("100 plastic housings")
    m_workspace_id, rfq_id = _make_full_m_workspace(bws.b_workspace_id)

    response = handle_m_side_submit_supplier_response({
        "project_id": rfq_id,
        "message_text": "We can supply. FOB price USD 3.20 per unit.",
    })
    assert response["ok"] is True, response

    events = read_events(m_workspace_id=m_workspace_id)
    event_types = {e["event_type"] for e in events}
    assert "M_SUPPLIER_MESSAGE_RECEIVED" in event_types


# ─── 5. No false success when workspace not found ─────────────────────────────

def test_no_supplier_response_received_if_workspace_not_found():
    from src.openclaw_skill.m_side_actions import handle_m_side_submit_supplier_response

    response = handle_m_side_submit_supplier_response({
        "project_id": "RFQ-DOES-NOT-EXIST",
        "message_text": "We can make it.",
    })

    assert response["ok"] is False
    assert response["status"] in ("m_workspace_not_found", "workspace_not_found")
    assert response.get("status") != "supplier_response_received"


# ─── 6. Negative: no matching workspace ───────────────────────────────────────

def test_no_matching_workspace_returns_not_found():
    from src.openclaw_skill.m_side_actions import handle_m_side_submit_supplier_response

    response = handle_m_side_submit_supplier_response({
        "project_id": "RFQ-DOES-NOT-EXIST",
        "mode": "m_side",
        "message_text": "We can make it.",
    })

    assert response["ok"] is False
    assert response["status"] in ("m_workspace_not_found", "workspace_not_found"), response
    assert "reply_text" in response
    assert "missing_fields" in response
    assert response.get("outbound_messages") == []


# ─── 7. Negative: ambiguous workspace ─────────────────────────────────────────

def test_ambiguous_workspace_returns_clear_error(monkeypatch):
    """
    If find_active_workspace_for_supplier_and_rfq raises ValueError (multiple matches),
    the handler must return ambiguous_m_workspace — not pick one silently.
    """
    # Patch the name as imported into m_side_actions (not the source module)
    import src.openclaw_skill.m_side_actions as actions_module

    def mock_find(channel, user_id, rfq_id):
        raise ValueError(f"ambiguous_m_workspace: 2 active workspaces share rfq_id={rfq_id!r}")

    monkeypatch.setattr(actions_module, "find_active_workspace_for_supplier_and_rfq", mock_find)

    from src.openclaw_skill.m_side_actions import handle_m_side_submit_supplier_response

    response = handle_m_side_submit_supplier_response({
        "project_id": "RFQ-AMBIGUOUS",
        "message_text": "We can make it.",
    })

    assert response["ok"] is False
    assert response["status"] == "ambiguous_m_workspace", response
    assert "reply_text" in response
    assert response.get("outbound_messages") == []


# ─── 8. rfq_id alias works as alternative to project_id ─────────────────────

def test_rfq_id_param_resolves_workspace():
    from src.b_side.workspace import create_b_workspace
    from src.m_side.supplier_workspace import get_m_workspace
    from src.openclaw_skill.m_side_actions import handle_m_side_submit_supplier_response

    bws = create_b_workspace("50 titanium bolts")
    m_workspace_id, rfq_id = _make_full_m_workspace(bws.b_workspace_id)

    response = handle_m_side_submit_supplier_response({
        "rfq_id": rfq_id,  # alternate key — not project_id
        "message_text": "Yes we can supply. Lead time 15 days. EXW.",
    })

    assert response["ok"] is True, response
    assert response["status"] == "supplier_response_received"

    ws = get_m_workspace(m_workspace_id)
    assert len(ws.raw_supplier_messages) == 1


# ─── 9. Lookup helper: find_workspace_by_rfq_id ───────────────────────────────

def test_find_workspace_by_rfq_id():
    from src.b_side.workspace import create_b_workspace
    from src.m_side.supplier_workspace import get_m_workspace, find_workspace_by_rfq_id

    bws = create_b_workspace("800 PCBs")
    m_workspace_id, rfq_id = _make_full_m_workspace(bws.b_workspace_id)

    found = find_workspace_by_rfq_id(rfq_id)
    assert found is not None
    assert found.m_workspace_id == m_workspace_id
    assert found.rfq_id == rfq_id

    not_found = find_workspace_by_rfq_id("RFQ-NONEXISTENT")
    assert not_found is None


# ─── 10. Lookup helper: find_active_workspace_for_supplier_and_rfq ───────────

def test_find_active_workspace_for_supplier_and_rfq():
    from src.b_side.workspace import create_b_workspace
    from src.m_side.supplier_workspace import (
        get_m_workspace,
        find_active_workspace_for_supplier_and_rfq,
    )

    bws = create_b_workspace("400 zinc die castings")
    m_workspace_id, rfq_id = _make_full_m_workspace(bws.b_workspace_id)

    # Lookup by rfq_id alone (no supplier identity) must work
    found_by_rfq = find_active_workspace_for_supplier_and_rfq(None, None, rfq_id)
    assert found_by_rfq is not None
    assert found_by_rfq.m_workspace_id == m_workspace_id

    # Lookup by non-existent rfq_id returns None
    not_found = find_active_workspace_for_supplier_and_rfq(None, None, "RFQ-GHOST")
    assert not_found is None
