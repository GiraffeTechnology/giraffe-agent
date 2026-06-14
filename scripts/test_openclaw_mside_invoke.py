"""
OpenClaw M-side skill invocation test script.

Verifies the full RFQ-based workspace lookup fix:
- Creates B-side workspace → dispatches inquiry → creates M-side workspace
- Simulates OpenClaw supplier reply using project_id (= rfq_id)
- Asserts workspace is found and message is appended

Also verifies negative cases (not found, ambiguous).
"""

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

os.environ.setdefault("GIRAFFE_DB_MODE", "off")

_PASS = 0
_FAIL = 0
_ERRORS: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"  [PASS] {label}")
    else:
        _FAIL += 1
        msg = f"  [FAIL] {label}" + (f" — {detail}" if detail else "")
        print(msg)
        _ERRORS.append(msg)


def run() -> int:
    print("=" * 60)
    print("OPENCLAW M-SIDE INVOKE TEST")
    print("=" * 60)

    # ── Setup: create B-side workspace ────────────────────────────────────
    print("\nSetup: Create B-side workspace and dispatch inquiry")
    from src.b_side.workspace import create_b_workspace, get_b_workspace, save_b_workspace
    from src.b_side.requirement_structurer import structure_requirement
    from src.b_side.inquiry_drafter import draft_supplier_inquiry
    from src.m_side.supplier_profile import create_supplier_profile
    from src.bm_bridge.inquiry_dispatcher import dispatch_supplier_inquiry
    from src.m_side.supplier_workspace import get_m_workspace

    bws = create_b_workspace("250 precision CNC machined aluminum brackets for automotive export")
    rfq_id = bws.rfq_id
    b_workspace_id = bws.b_workspace_id
    check("B-side workspace created", bws.b_workspace_id.startswith("bw_"))
    check("RFQ id assigned", rfq_id.startswith("RFQ-"))

    req = structure_requirement(b_workspace_id, bws.raw_requirement)
    bws = get_b_workspace(b_workspace_id)
    bws.buyer_requirement = req
    bws.status = "requirement_structured"
    save_b_workspace(bws)

    draft = draft_supplier_inquiry(b_workspace_id, ["oc_sup_001"])
    bws = get_b_workspace(b_workspace_id)
    bws.supplier_inquiry_draft = draft
    bws.status = "inquiry_drafted"
    save_b_workspace(bws)

    create_supplier_profile(
        supplier_id="oc_sup_001",
        name="OpenClaw Test Supplier",
        channel="openclaw-email",
        external_user_id="supplier@openclaw-test.com",
    )

    contexts = dispatch_supplier_inquiry(b_workspace_id, ["oc_sup_001"], channel="mock")
    check("Inquiry dispatched (1 supplier)", len(contexts) == 1)
    m_workspace_id = contexts[0].m_workspace_id
    check("M-side workspace created", m_workspace_id.startswith("mw_"))

    # Verify M-side workspace stores rfq_id in workspace.rfq_id
    # Note: rfq_id on M-side workspace comes from req.rfq_id (structure_requirement),
    # not from bws.rfq_id (create_b_workspace) — they are different values.
    m_ws = get_m_workspace(m_workspace_id)
    m_ws_rfq_id = m_ws.rfq_id  # this is the effective rfq_id for OpenClaw lookup
    check("M-side workspace.rfq_id is set", m_ws_rfq_id.startswith("RFQ-"),
          f"got {m_ws_rfq_id!r}")
    check("M-side workspace.b_workspace_id set", m_ws.b_workspace_id == b_workspace_id)

    # Use the rfq_id actually stored on the M-side workspace for all subsequent lookups
    rfq_id = m_ws_rfq_id

    # ── Test 1: OpenClaw supplier reply via project_id (the bug scenario) ────
    print("\nTest 1: OpenClaw supplier reply via project_id = rfq_id")
    from src.openclaw_skill.m_side_actions import handle_m_side_submit_supplier_response

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
    check("response ok=True", response.get("ok") is True, str(response))
    check("status=supplier_response_received", response.get("status") == "supplier_response_received",
          f"got status={response.get('status')!r}")

    m_ws = get_m_workspace(m_workspace_id)
    check("message appended to raw_supplier_messages",
          "We can make it" in "\n".join(m_ws.raw_supplier_messages),
          f"messages: {m_ws.raw_supplier_messages}")
    check("message count is 1", len(m_ws.raw_supplier_messages) == 1)

    # ── Test 2: Execution event logged ────────────────────────────────────
    print("\nTest 2: Execution event was appended")
    from src.m_side.m_event_logger import read_events
    events = read_events(m_workspace_id=m_workspace_id)
    event_types = {e["event_type"] for e in events}
    check("M_SUPPLIER_MESSAGE_RECEIVED event logged", "M_SUPPLIER_MESSAGE_RECEIVED" in event_types)

    # ── Test 3: Second message appends correctly ───────────────────────────
    print("\nTest 3: Second supplier message appends (count increases)")
    r2 = handle_m_side_submit_supplier_response({
        "project_id": rfq_id,
        "message_text": "MOQ is 50 pcs. Payment: T/T 30 days.",
    })
    check("second reply ok=True", r2.get("ok") is True, str(r2))
    m_ws = get_m_workspace(m_workspace_id)
    check("message count is 2 after second reply", len(m_ws.raw_supplier_messages) == 2)

    # ── Test 4: Explicit m_workspace_id still works ───────────────────────
    print("\nTest 4: Explicit m_workspace_id still works")
    r3 = handle_m_side_submit_supplier_response({
        "m_workspace_id": m_workspace_id,
        "message": "EXW Shanghai. No tooling fee.",
    })
    check("explicit m_workspace_id ok=True", r3.get("ok") is True, str(r3))
    check("status=supplier_response_received (explicit)", r3.get("status") == "supplier_response_received")

    # ── Test 5: Not found returns structured error ─────────────────────────
    print("\nTest 5: RFQ not found → structured error, no false success")
    r_not_found = handle_m_side_submit_supplier_response({
        "project_id": "RFQ-DOES-NOT-EXIST",
        "message_text": "We can make it.",
    })
    check("ok=False for not found", r_not_found.get("ok") is False, str(r_not_found))
    check("status=m_workspace_not_found",
          r_not_found.get("status") in ("m_workspace_not_found", "workspace_not_found"),
          f"got: {r_not_found.get('status')!r}")
    check("not returning supplier_response_received",
          r_not_found.get("status") != "supplier_response_received")

    # ── Test 6: Missing message returns error ─────────────────────────────
    print("\nTest 6: Missing message body → error")
    r_no_msg = handle_m_side_submit_supplier_response({
        "project_id": rfq_id,
    })
    check("ok=False when message missing", r_no_msg.get("ok") is False, str(r_no_msg))

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _ERRORS:
        print("Failures:")
        for e in _ERRORS:
            print(e)
    print("=" * 60)
    if _FAIL == 0:
        print("OPENCLAW M-SIDE INVOKE: PASS")
        return 0
    else:
        print("OPENCLAW M-SIDE INVOKE: FAIL")
        return 1


if __name__ == "__main__":
    sys.exit(run())
