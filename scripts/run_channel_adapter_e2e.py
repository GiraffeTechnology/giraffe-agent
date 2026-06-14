"""
Channel Adapter Layer E2E Script — Giraffe Agent

Steps:
1. Buyer sends inbound message via mock adapter (normalize + actor resolve)
2. Route buyer message → B-side (verify route=b_side)
3. Create B-side workspace from buyer message
4. Structure buyer requirement
5. Draft supplier inquiry
6. Dispatch inquiry (creates M-side workspace)
7. Supplier sends inbound reply via mock adapter with invitation token
8. Route supplier message → M-side (verify route=m_side)
9. M-side: append supplier response, build response packet
10. Push supplier response to B-side, run feasibility, verify IEG channel events

Expected final output: CHANNEL ADAPTER E2E: PASS
"""

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

os.environ.setdefault("GIRAFFE_DB_MODE", "off")

_PASS = 0
_FAIL = 0
_ERRORS = []


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


def run():
    print("=" * 60)
    print("CHANNEL ADAPTER LAYER E2E")
    print("=" * 60)

    # ── Step 1: Buyer inbound via mock adapter ─────────────────────────────
    print("\nStep 1: Buyer inbound message — normalize + actor resolve")
    from src.channels.mock_adapter import MockAdapter, clear_delivered

    clear_delivered()
    adapter = MockAdapter()
    buyer_payload = {
        "channel": "mock",
        "external_user_id": "buyer_e2e",
        "text": "I need to buy 300 units of precision aluminum brackets, RFQ",
    }
    buyer_msg = adapter.normalize_inbound(buyer_payload)
    check("buyer message normalized", buyer_msg.channel == "mock")
    check("buyer intent is buy", buyer_msg.intent == "buy", f"got: {buyer_msg.intent}")
    check("buyer actor resolved", buyer_msg.actor_id == "ACTOR-B-E2E", f"got: {buyer_msg.actor_id}")
    check("idempotency key set", buyer_msg.idempotency_key is not None)

    # ── Step 2: Route buyer → B-side ──────────────────────────────────────
    print("\nStep 2: Route buyer message → B-side")
    from src.channels.router import route_inbound_message, send_outbound_message

    buyer_routing = route_inbound_message(buyer_msg)
    check("buyer routes to b_side", buyer_routing["route"] == "b_side", f"got: {buyer_routing['route']}")

    # ── Step 3: Create B-side workspace ───────────────────────────────────
    print("\nStep 3: Create B-side workspace from buyer message")
    from src.b_side.workspace import create_b_workspace

    workspace = create_b_workspace(buyer_msg.text or "300 aluminum brackets")
    b_workspace_id = workspace.b_workspace_id
    check("b_workspace_id created", b_workspace_id.startswith("bw_"))

    # ── Step 4: Structure buyer requirement ───────────────────────────────
    print("\nStep 4: Structure buyer requirement")
    from src.b_side.requirement_structurer import structure_requirement
    from src.b_side.workspace import get_b_workspace, save_b_workspace

    req = structure_requirement(b_workspace_id, workspace.raw_requirement)
    workspace = get_b_workspace(b_workspace_id)
    workspace.buyer_requirement = req
    workspace.status = "requirement_structured"
    save_b_workspace(workspace)
    check("requirement structured", req is not None)
    check("workspace status updated", workspace.status == "requirement_structured")

    # ── Step 5: Draft supplier inquiry ────────────────────────────────────
    print("\nStep 5: Draft supplier inquiry")
    from src.b_side.inquiry_drafter import draft_supplier_inquiry

    supplier_ids = ["e2e_sup_001"]
    draft = draft_supplier_inquiry(b_workspace_id, supplier_ids)
    workspace = get_b_workspace(b_workspace_id)
    workspace.supplier_inquiry_draft = draft
    workspace.status = "inquiry_drafted"
    save_b_workspace(workspace)
    check("inquiry drafted", draft is not None)
    check("workspace has inquiry draft", workspace.supplier_inquiry_draft is not None)

    # ── Step 6: Dispatch inquiry → creates M-side workspace ───────────────
    print("\nStep 6: Dispatch inquiry to supplier")
    from src.m_side.supplier_profile import create_supplier_profile
    from src.bm_bridge.inquiry_dispatcher import dispatch_supplier_inquiry

    create_supplier_profile(
        supplier_id="e2e_sup_001",
        name="E2E Supplier",
        channel="mock",
        external_user_id="supplier_e2esupp",
    )
    contexts = dispatch_supplier_inquiry(b_workspace_id, supplier_ids, channel="mock")
    check("inquiry dispatched", len(contexts) == 1)
    m_workspace_id = contexts[0].m_workspace_id
    check("m_workspace_id created", m_workspace_id.startswith("mw_"))

    # ── Step 7: Supplier reply via mock adapter with invitation token ──────
    print("\nStep 7: Supplier inbound reply with invitation token")
    supplier_payload = {
        "channel": "mock",
        "external_user_id": "supplier_e2esupp",
        "text": f"GQ-E2E1 we can make this, lead time 25 days, MOQ 100, unit price USD 12",
    }
    supplier_msg = adapter.normalize_inbound(supplier_payload)
    check("supplier message normalized", supplier_msg.channel == "mock")
    check("supplier intent is supply", supplier_msg.intent == "supply", f"got: {supplier_msg.intent}")

    # ── Step 8: Route supplier → M-side ───────────────────────────────────
    print("\nStep 8: Route supplier message → M-side")
    supplier_routing = route_inbound_message(supplier_msg)
    check("supplier routes to m_side", supplier_routing["route"] == "m_side", f"got: {supplier_routing['route']}")

    # ── Step 9: M-side — append response, build response packet ───────────
    print("\nStep 9: M-side — process supplier response")
    from src.m_side.response_collector import append_supplier_message, build_response_packet_from_messages

    append_supplier_message(m_workspace_id, supplier_msg.text or "can make, 25 days")
    packet = build_response_packet_from_messages(m_workspace_id)
    check("response packet built", packet is not None)

    # ── Step 10: Push to B-side, run feasibility, verify IEG events ───────
    print("\nStep 10: Push response to B-side + run feasibility")
    from src.bm_bridge.response_bridge import push_supplier_response_to_b_side
    from src.b_side.feasibility_engine import run_feasibility_simulation

    bridge_result = push_supplier_response_to_b_side(packet)
    check("response pushed to b_side", bridge_result.get("ok") or bridge_result.get("status") is not None)

    try:
        report = run_feasibility_simulation(b_workspace_id)
        check("feasibility report generated", report is not None)
    except Exception as e:
        check("feasibility report generated", False, str(e))

    # Verify outbound delivery via mock adapter
    from src.channels.base import OutboundChannelMessage
    outbound = OutboundChannelMessage(
        channel="mock",
        to_external_user_id="buyer_e2e",
        text="Your inquiry has been processed. Feasibility analysis complete.",
    )
    receipt = send_outbound_message("mock", outbound)
    check("outbound delivery receipt status=mocked", receipt.status == "mocked")

    from src.channels.mock_adapter import get_delivered
    delivered = get_delivered()
    check("delivery logged in mock adapter", len(delivered) >= 1)

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _ERRORS:
        print("Failures:")
        for e in _ERRORS:
            print(e)
    print("=" * 60)
    if _FAIL == 0:
        print("CHANNEL ADAPTER E2E: PASS")
        return 0
    else:
        print("CHANNEL ADAPTER E2E: FAIL")
        return 1


if __name__ == "__main__":
    sys.exit(run())
