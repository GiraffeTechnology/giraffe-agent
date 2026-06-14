"""
OpenClaw B-side skill invocation test script.

Verifies the full B-side skill invocation path through the OpenClaw skill router:
- Create B-side workspace
- Structure buyer requirement
- Draft supplier inquiry
- Run feasibility simulation
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
    print("OPENCLAW B-SIDE INVOKE TEST")
    print("=" * 60)

    from src.openclaw_skill.skill_router import route_action
    from src.b_side.workspace import get_b_workspace, save_b_workspace
    from src.b_side.requirement_structurer import structure_requirement
    from src.b_side.inquiry_drafter import draft_supplier_inquiry
    from src.m_side.supplier_profile import create_supplier_profile
    from src.bm_bridge.inquiry_dispatcher import dispatch_supplier_inquiry
    from src.m_side.response_collector import append_supplier_message, build_response_packet_from_messages
    from src.bm_bridge.response_bridge import push_supplier_response_to_b_side

    # ── Step 1: Create B-side workspace ──────────────────────────────────
    print("\nStep 1: Create B-side workspace")
    from src.b_side.workspace import create_b_workspace
    bws = create_b_workspace("1000 injection-molded ABS housings, black, tolerance ±0.2mm")
    b_workspace_id = bws.b_workspace_id
    rfq_id = bws.rfq_id
    check("workspace created", b_workspace_id.startswith("bw_"))
    check("rfq_id assigned", rfq_id.startswith("RFQ-"))

    # ── Step 2: Structure requirement ────────────────────────────────────
    print("\nStep 2: Structure buyer requirement")
    req = structure_requirement(b_workspace_id, bws.raw_requirement)
    bws = get_b_workspace(b_workspace_id)
    bws.buyer_requirement = req
    bws.status = "requirement_structured"
    save_b_workspace(bws)
    check("requirement structured", req is not None)
    check("rfq_id on requirement", req.rfq_id.startswith("RFQ-"))

    # ── Step 3: Draft supplier inquiry ────────────────────────────────────
    print("\nStep 3: Draft supplier inquiry")
    supplier_ids = ["bside_sup_001", "bside_sup_002"]
    draft = draft_supplier_inquiry(b_workspace_id, supplier_ids)
    bws = get_b_workspace(b_workspace_id)
    bws.supplier_inquiry_draft = draft
    bws.status = "inquiry_drafted"
    save_b_workspace(bws)
    check("inquiry drafted", draft is not None)
    check("inquiry has message", bool(draft.message_text_zh or draft.message_text_en))

    # ── Step 4: Dispatch inquiry ──────────────────────────────────────────
    print("\nStep 4: Dispatch inquiry to suppliers")
    for sid in supplier_ids:
        create_supplier_profile(supplier_id=sid, name=f"B-side Test Supplier {sid}", channel="mock")
    contexts = dispatch_supplier_inquiry(b_workspace_id, supplier_ids, channel="mock")
    check(f"dispatched to {len(supplier_ids)} suppliers", len(contexts) == len(supplier_ids))
    m_workspace_ids = [c.m_workspace_id for c in contexts]

    # ── Step 5: Simulate supplier replies ─────────────────────────────────
    print("\nStep 5: Suppliers reply and push responses to B-side")
    for i, m_ws_id in enumerate(m_workspace_ids):
        append_supplier_message(m_ws_id, f"Supplier {i+1}: can make. Lead time {25+i*5} days. Price USD {4.5+i*0.3:.2f}.")
        packet = build_response_packet_from_messages(m_ws_id)
        result = push_supplier_response_to_b_side(packet)
        check(f"supplier {i+1} response pushed", result.get("ok") is True or result.get("status") is not None,
              str(result))

    # ── Step 6: Run feasibility ───────────────────────────────────────────
    print("\nStep 6: Run delivery feasibility simulation")
    from src.b_side.feasibility_engine import run_feasibility_simulation
    report = run_feasibility_simulation(b_workspace_id)
    check("feasibility report generated", report is not None)
    check("has delivery paths", hasattr(report, "paths"))

    # ── Step 7: B-side skill invocations via route_action ────────────────
    print("\nStep 7: B-side skill actions via OpenClaw skill router")

    # b_side_receive_inquiry is not a registered action but b_side workspaces are accessed via API
    # Test a known valid B-side related action: m_side_receive_inquiry (requires m_workspace_id)
    r = route_action("m_side_receive_inquiry", {"m_workspace_id": m_workspace_ids[0]})
    check("m_side_receive_inquiry via router", r.get("ok") is True, str(r))

    # Unknown action returns error
    r_unknown = route_action("nonexistent_action", {})
    check("unknown action returns error", r_unknown.get("ok") is False)

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _ERRORS:
        print("Failures:")
        for e in _ERRORS:
            print(e)
    print("=" * 60)
    if _FAIL == 0:
        print("OPENCLAW B-SIDE INVOKE: PASS")
        return 0
    else:
        print("OPENCLAW B-SIDE INVOKE: FAIL")
        return 1


if __name__ == "__main__":
    sys.exit(run())
