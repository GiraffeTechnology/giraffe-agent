"""
Integrated Post-Confirmation MVP — 16-step ultimate acceptance test.

Runs the complete end-to-end production workflow:
  Buyer inquiry → Role-switch frame → Upstream inquiry + response
  → Rollup → Order confirmation → Execution plan → Progress task
  → Media upload → Milestone confirmation → Logistics handover
  → Cainiao-like tracking → Delivery → Sign-off → Supplier memory
  → IEG verification
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.m_side.communication.role_switch_frame import create_role_switch_frame, get_frames_for_project
from src.m_side.communication.thread_context import create_thread
from src.m_side.communication.correlation import generate_correlation_token
from src.m_side.communication.send_receive_state_machine import (
    create_send_receive_machine, transition_state,
)
from src.m_side.dependencies.dependency_planner import plan_upstream_dependencies
from src.m_side.upstream.inquiry_builder import build_upstream_inquiry
from src.m_side.upstream.dispatch_service import dispatch_upstream_inquiry
from src.m_side.upstream.response_parser import parse_upstream_response
from src.m_side.upstream.option_engine import generate_upstream_options
from src.m_side.upstream.approval_gate import request_upstream_option_approval, approve_upstream_option
from src.m_side.rollup.supplier_response_rollup import generate_supplier_response_rollup
from src.actors.role_resolver import resolve_role_context
from src.projects.project_graph import create_project, create_edge, update_project_status, get_project
from src.b_side.workspace import create_b_workspace
from src.merchandiser.merchandiser_engine import (
    create_execution_plan, update_order_state, update_supplier_memory,
)
from src.merchandiser.task_planner import get_tasks_for_project
from src.merchandiser.milestone_manager import (
    get_milestones_for_project, upload_milestone_evidence, confirm_milestone,
)
from src.merchandiser.media_confirmation import upload_media_evidence
from src.merchandiser.m_side.m_logistics_handover import request_logistics_handover, log_logistics_handover_received
from src.merchandiser.b_side.b_signoff import request_buyer_signoff, receive_buyer_signoff
from src.merchandiser.b_side.b_logistics_updates import push_logistics_update
from src.logistics.logistics_ingestion_service import (
    ingest_logistics_from_im_message, sync_tracking_from_provider,
)
from src.logistics.logistics_models import get_shipment, get_events_for_shipment
from src.logistics.logistics_state_mapper import map_logistics_status_to_order_state
from src.m_side.m_event_logger import log_m_event, read_events

_steps_passed = 0
_steps_failed = 0


def step(n, desc):
    print(f"\n--- Step {n}: {desc} ---")


def ok(msg):
    global _steps_passed
    _steps_passed += 1
    print(f"  ✓ {msg}")


def fail(msg):
    global _steps_failed
    _steps_failed += 1
    print(f"  ✗ FAIL: {msg}")


def check(condition, msg):
    if condition:
        ok(msg)
    else:
        fail(msg)


BUYER_ID = "actor_buyer_integrated"
SUPPLIER_ID = "actor_manufacturer_integrated"
F1_ID = "actor_fabric_integrated_f1"
IM_MSG = "已发顺丰，单号 SF200100300400，今天发出"
TRACKING_NO = "SF200100300400"


def main():
    print("=" * 70)
    print("INTEGRATED POST-CONFIRMATION MVP — Ultimate Acceptance Test")
    print("=" * 70)

    # ── Step 1: Buyer B sends inquiry ─────────────────────────────────────────
    step(1, "Buyer B sends inquiry — project created")

    b_workspace = create_b_workspace("Cotton polo shirt 100 pcs, need full production quotation")
    project = create_project(
        original_buyer_actor_id=BUYER_ID,
        product_summary="Cotton polo shirt 100 pcs",
        category="apparel",
        quantity=100,
        main_supplier_actor_id=SUPPLIER_ID,
        b_workspace_id=b_workspace.b_workspace_id,
    )
    check(project.project_id.startswith("PROJ-"), f"Project: {project.project_id}")

    buyer_edge = create_edge(
        project_id=project.project_id,
        from_actor_id=BUYER_ID,
        to_actor_id=SUPPLIER_ID,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )

    machine = create_send_receive_machine(project.project_id)
    machine = transition_state(project.project_id, "BUYER_INQUIRY_RECEIVED", "buyer sent inquiry")
    check(machine.current_state == "BUYER_INQUIRY_RECEIVED", f"State: {machine.current_state}")

    # ── Step 2: M receives + RoleSwitchFrame created ──────────────────────────
    step(2, "M receives inquiry and RoleSwitchFrame is created")

    rc_main = resolve_role_context(
        project_id=project.project_id,
        actor_id=SUPPLIER_ID,
        original_buyer_actor_id=BUYER_ID,
        main_supplier_actor_id=SUPPLIER_ID,
        edge_id=buyer_edge.edge_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    check(rc_main.role == "MAIN_M_SIDE", f"M role: {rc_main.role}")

    buyer_thread = create_thread(
        project_id=project.project_id,
        edge_id=buyer_edge.edge_id,
        from_actor_id=BUYER_ID,
        to_actor_id=SUPPLIER_ID,
        thread_type="buyer_main_supplier",
        active_role_context_id="rc-main",
    )

    frame_inbound = create_role_switch_frame(
        project_id=project.project_id,
        actor_id=SUPPLIER_ID,
        role_context_id="rc-main-in",
        business_role="MAIN_M_SIDE",
        communication_direction="INBOUND",
        message_purpose="buyer_inquiry_received",
        counterparty_actor_id=BUYER_ID,
        edge_id=buyer_edge.edge_id,
        conversation_thread_id=buyer_thread.thread_id,
    )
    check(frame_inbound.frame_id.startswith("FRAME-"), f"Frame: {frame_inbound.frame_id}")
    check(frame_inbound.business_role == "MAIN_M_SIDE", f"Frame role: {frame_inbound.business_role}")
    check(frame_inbound.communication_direction == "INBOUND", f"Frame direction")

    # ── Step 3: M sends upstream inquiry and receives response ────────────────
    step(3, "M sends upstream inquiry (UPSTREAM_B_SIDE/OUTBOUND) and receives response")

    # Plan dependencies
    deps = plan_upstream_dependencies(
        project_id=project.project_id,
        product_summary="Cotton polo shirt 100 pcs",
        category="apparel",
        quantity=100,
        main_supplier_actor_id=SUPPLIER_ID,
        candidate_fabric_ids=[F1_ID],
    )
    fabric_dep = next((d for d in deps if d.dependency_type == "fabric"), None)
    check(fabric_dep is not None, f"Fabric dependency planned")

    # Upstream edge + role
    upstream_edge = create_edge(
        project_id=project.project_id,
        from_actor_id=SUPPLIER_ID,
        to_actor_id=F1_ID,
        edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
        parent_edge_id=buyer_edge.edge_id,
    )
    rc_upstream = resolve_role_context(
        project_id=project.project_id,
        actor_id=SUPPLIER_ID,
        original_buyer_actor_id=BUYER_ID,
        main_supplier_actor_id=SUPPLIER_ID,
        edge_id=upstream_edge.edge_id,
        edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
    )
    check(rc_upstream.role == "UPSTREAM_B_SIDE", f"Upstream role: {rc_upstream.role}")

    # Correlation token
    token = generate_correlation_token(project.project_id, upstream_edge.edge_id, fabric_dep.dependency_id)
    check(token.startswith("GFR-"), f"Correlation token: {token[:20]}...")

    # Frame for OUTBOUND upstream
    upstream_thread = create_thread(
        project_id=project.project_id,
        edge_id=upstream_edge.edge_id,
        from_actor_id=SUPPLIER_ID,
        to_actor_id=F1_ID,
        thread_type="main_supplier_upstream",
        active_role_context_id="rc-upstream",
        correlation_token=token,
    )
    frame_upstream_out = create_role_switch_frame(
        project_id=project.project_id,
        actor_id=SUPPLIER_ID,
        role_context_id="rc-upstream-out",
        business_role="UPSTREAM_B_SIDE",
        communication_direction="OUTBOUND",
        message_purpose="upstream_inquiry_to_supplier",
        counterparty_actor_id=F1_ID,
        edge_id=upstream_edge.edge_id,
        conversation_thread_id=upstream_thread.thread_id,
    )
    check(frame_upstream_out.business_role == "UPSTREAM_B_SIDE", f"Upstream frame role")

    inquiry = build_upstream_inquiry(
        dependency=fabric_dep,
        upstream_actor_id=F1_ID,
        main_supplier_actor_id=SUPPLIER_ID,
        quantity=project.quantity,
    )
    dispatch_upstream_inquiry(inquiry, channel="mock")

    # Frame for INBOUND upstream response
    frame_upstream_in = create_role_switch_frame(
        project_id=project.project_id,
        actor_id=SUPPLIER_ID,
        role_context_id="rc-upstream-in",
        business_role="UPSTREAM_B_SIDE",
        communication_direction="INBOUND",
        message_purpose="upstream_response_received",
        counterparty_actor_id=F1_ID,
    )
    check(frame_upstream_in.communication_direction == "INBOUND", "Upstream INBOUND frame")

    # Parse F1 response
    f1_reply = f"可以供货，32支纯棉，RMB 12.5/米，起订量 500 米，交期 15 天。{token}"
    parsed_f1 = parse_upstream_response(
        raw_message=f1_reply, inquiry_id="INQ-F1-INT", project_id=project.project_id,
        upstream_actor_id=F1_ID, dependency_id=fabric_dep.dependency_id, dependency_type="fabric",
    )
    check(parsed_f1.can_supply is True, f"F1 can supply: {parsed_f1.can_supply}")

    machine = transition_state(project.project_id, "PREPARING_UPSTREAM_INQUIRIES", "deps planned")
    machine = transition_state(project.project_id, "AWAITING_MAIN_SUPPLIER_SEND_APPROVAL", "ready to send")
    machine = transition_state(project.project_id, "SENDING_UPSTREAM_INQUIRIES", "approved")
    machine = transition_state(project.project_id, "WAITING_FOR_UPSTREAM_RESPONSES", "sent")
    machine = transition_state(project.project_id, "UPSTREAM_RESPONSES_RECEIVED", "F1 replied")

    # ── Step 4: M generates Supplier Response Rollup ──────────────────────────
    step(4, "M generates Supplier Response Rollup")

    options = generate_upstream_options(
        project_id=project.project_id,
        dependency_id=fabric_dep.dependency_id,
        dependency_type="fabric",
        responses=[parsed_f1],
        main_supplier_actor_id=SUPPLIER_ID,
    )
    approval_req = request_upstream_option_approval(
        project_id=project.project_id,
        dependency_id=fabric_dep.dependency_id,
        dependency_type="fabric",
        options=options,
    )
    best_opt = next((o for o in options if o.option_label == "BEST"), options[0])
    approved = approve_upstream_option(
        approval_request=approval_req,
        approved_option_id=best_opt.option_id,
        approved_by=SUPPLIER_ID,
        mode="human",
    )

    rollup = generate_supplier_response_rollup(
        project_id=project.project_id,
        main_supplier_actor_id=SUPPLIER_ID,
        approval_results=[approved],
        product_summary=project.product_summary,
        quantity=project.quantity,
        main_capacity_available=True,
        main_capacity_note="Ready to produce 100 pcs polo shirts",
    )
    check(rollup.rollup_id.startswith("ROLLUP-"), f"Rollup: {rollup.rollup_id}")
    check(rollup.can_accept_order, "can_accept_order=True")

    machine = transition_state(project.project_id, "PREPARING_UPSTREAM_OPTIONS", "options ready")
    machine = transition_state(project.project_id, "AWAITING_OPTION_APPROVAL", "approval requested")
    machine = transition_state(project.project_id, "GENERATING_BUYER_ROLLUP", "option approved")
    machine = transition_state(project.project_id, "AWAITING_ROLLUP_APPROVAL", "rollup generated")
    machine = transition_state(project.project_id, "SENDING_ROLLUP_TO_BUYER", "rollup approved")

    # Frame for OUTBOUND rollup to buyer
    rollup_thread = create_thread(
        project_id=project.project_id,
        edge_id=buyer_edge.edge_id,
        from_actor_id=SUPPLIER_ID,
        to_actor_id=BUYER_ID,
        thread_type="buyer_rollup_review",
        active_role_context_id="rc-main-out",
    )
    frame_rollup_out = create_role_switch_frame(
        project_id=project.project_id,
        actor_id=SUPPLIER_ID,
        role_context_id="rc-main-out",
        business_role="MAIN_M_SIDE",
        communication_direction="OUTBOUND",
        message_purpose="supplier_response_rollup_to_buyer",
        counterparty_actor_id=BUYER_ID,
        edge_id=buyer_edge.edge_id,
        conversation_thread_id=rollup_thread.thread_id,
    )
    check(frame_rollup_out.business_role == "MAIN_M_SIDE", "Rollup frame = MAIN_M_SIDE/OUTBOUND")

    # ── Step 5: Buyer confirms order ──────────────────────────────────────────
    step(5, "Buyer confirms order")

    update_project_status(project.project_id, "ORDER_CONFIRMED")
    proj_status = get_project(project.project_id).status
    check(proj_status == "ORDER_CONFIRMED", f"Project status: {proj_status}")

    machine = transition_state(project.project_id, "WAITING_FOR_BUYER_CONFIRMATION", "rollup sent")
    machine = transition_state(project.project_id, "ORDER_CONFIRMED", "buyer confirmed")
    check(machine.current_state == "ORDER_CONFIRMED", f"State machine: {machine.current_state}")

    log_m_event(
        event_type="ORDER_CONFIRMED_BY_BUYER",
        b_workspace_id=project.project_id,
        supplier_id=BUYER_ID,
        payload={"project_id": project.project_id},
    )

    # ── Step 6: AI Merchandiser execution plan created ────────────────────────
    step(6, "AI Merchandiser execution plan created")

    plan = create_execution_plan(
        project_id=project.project_id,
        supplier_actor_id=SUPPLIER_ID,
        buyer_actor_id=BUYER_ID,
        category="apparel",
    )
    check(plan.plan_id.startswith("EXECPLAN-"), f"Plan: {plan.plan_id}")
    check(len(plan.task_ids) >= 5, f"Tasks: {len(plan.task_ids)}")
    check(len(plan.milestone_ids) >= 4, f"Milestones: {len(plan.milestone_ids)}")

    machine = transition_state(project.project_id, "EXECUTION_IN_PROGRESS", "execution plan created")
    check(machine.current_state == "EXECUTION_IN_PROGRESS", f"State: {machine.current_state}")

    # ── Step 7: M-side progress task created ─────────────────────────────────
    step(7, "M-side progress task created and sent")

    all_tasks = get_tasks_for_project(project.project_id)
    m_tasks = [t for t in all_tasks if t.assigned_side == "M_SIDE"]
    check(len(m_tasks) >= 5, f"M-side tasks: {len(m_tasks)}")

    from src.merchandiser.m_side.m_progress_check import request_progress_update
    progress_result = request_progress_update(project.project_id, SUPPLIER_ID, "material_confirmation")
    check(progress_result.get("status") == "sent", "Progress task sent to supplier")

    # ── Step 8: M-side uploads milestone media ────────────────────────────────
    step(8, "M-side uploads milestone media evidence")

    milestones = get_milestones_for_project(project.project_id)
    cutting_ms = next((m for m in milestones if m.milestone_type == "cutting"), milestones[0])
    check(cutting_ms is not None, f"Milestone found: {cutting_ms.milestone_type}")

    media_list = upload_media_evidence(
        project_id=project.project_id,
        milestone_id=cutting_ms.milestone_id,
        uploaded_by_actor_id=SUPPLIER_ID,
        media_type="image",
        count=3,
    )
    check(len(media_list) == 3, f"Media uploaded: {len(media_list)}")

    updated_ms = upload_milestone_evidence(
        cutting_ms.milestone_id, project.project_id, [m.media_id for m in media_list]
    )
    check(updated_ms.status == "UPLOADED", f"Milestone status: {updated_ms.status}")

    # ── Step 9: B-side confirms milestone ────────────────────────────────────
    step(9, "B-side buyer confirms cutting milestone")

    from src.merchandiser.b_side.b_milestone_confirmation import send_milestone_review_request
    review_req = send_milestone_review_request(
        project.project_id, BUYER_ID, cutting_ms.milestone_id, "cutting", 3
    )
    check(review_req.get("status") == "review_requested", "Review request sent to buyer")

    confirmed_ms = confirm_milestone(cutting_ms.milestone_id, project.project_id)
    check(confirmed_ms.status == "CONFIRMED", f"Milestone confirmed: {confirmed_ms.status}")

    # ── Step 10: M-side sends logistics handover message ─────────────────────
    step(10, "M-side sends logistics handover IM message")

    handover_req = request_logistics_handover(project.project_id, SUPPLIER_ID)
    check(handover_req.get("status") == "requested", "Logistics handover requested")

    log_logistics_handover_received(project.project_id, SUPPLIER_ID, IM_MSG)
    check(TRACKING_NO in IM_MSG, f"Tracking number in IM message: {TRACKING_NO}")

    machine = transition_state(project.project_id, "LOGISTICS_HANDOVER_PENDING", "handover message sent")

    # ── Step 11: Cainiao-like provider mock returns tracking events ───────────
    step(11, "Cainiao-like provider mock returns tracking events")

    shipment = ingest_logistics_from_im_message(
        project_id=project.project_id,
        raw_message=IM_MSG,
        actor_id=SUPPLIER_ID,
    )
    check(shipment is not None, f"Shipment created from IM: {shipment.shipment_id if shipment else None}")
    check(shipment.tracking_number == TRACKING_NO, f"Tracking: {shipment.tracking_number}")

    events = sync_tracking_from_provider(shipment.shipment_id)
    check(len(events) >= 1, f"Tracking events returned: {len(events)}")

    from src.logistics.providers.provider_registry import get_logistics_provider
    provider = get_logistics_provider()
    raw_events = provider.fetch_tracking_events(shipment.carrier_code, TRACKING_NO)
    check(len(raw_events) >= 3, f"Mock events returned: {len(raw_events)}")

    log_m_event(
        event_type="LOGISTICS_PROVIDER_API_CALLED",
        b_workspace_id=project.project_id,
        payload={"provider": provider.provider_name, "tracking": TRACKING_NO, "event_count": len(raw_events)},
    )

    machine = transition_state(project.project_id, "LOGISTICS_TRACKING_ACTIVE", "tracking events received")

    # ── Step 12: Order state reaches DELIVERED ────────────────────────────────
    step(12, "Order state reaches DELIVERED from logistics events")

    updated_shipment = get_shipment(shipment.shipment_id)
    check(updated_shipment.current_status in ("delivered", "in_transit", "out_for_delivery"),
          f"Shipment status: {updated_shipment.current_status}")

    all_events = get_events_for_shipment(shipment.shipment_id)
    delivered_events = [e for e in all_events if e.normalized_status == "delivered"]
    check(len(delivered_events) >= 1, f"Delivered events: {len(delivered_events)}")

    plan = update_order_state(plan.plan_id, project.project_id, "DELIVERED", "logistics delivered")
    check(plan.current_order_state == "DELIVERED", f"Order state: {plan.current_order_state}")

    push_logistics_update(
        project_id=project.project_id,
        buyer_actor_id=BUYER_ID,
        tracking_number=TRACKING_NO,
        carrier_name=shipment.carrier_name,
        normalized_status="delivered",
        description="已签收",
    )

    machine = transition_state(project.project_id, "BUYER_SIGNOFF_PENDING", "delivered — sign-off pending")

    # ── Step 13: B-side sign-off request generated ────────────────────────────
    step(13, "B-side buyer sign-off request generated")

    signoff_req = request_buyer_signoff(project.project_id, BUYER_ID, TRACKING_NO)
    check(signoff_req.get("status") == "signoff_requested", f"Sign-off request: {signoff_req['status']}")
    check("Confirm received" in signoff_req.get("message", ""), "Sign-off presents options")

    signoff_req_events = read_events(event_type="BUYER_SIGNOFF_REQUESTED", b_workspace_id=project.project_id)
    check(len(signoff_req_events) >= 1, f"Sign-off request events: {len(signoff_req_events)}")

    # ── Step 14: Buyer signs off ──────────────────────────────────────────────
    step(14, "Buyer signs off on delivery")

    signoff = receive_buyer_signoff(
        project.project_id, BUYER_ID, response="confirmed", notes="Received in good condition"
    )
    check(signoff.get("status") in ("signoff_received", "order_closed"), f"Sign-off: {signoff['status']}")
    check(signoff.get("response") == "confirmed", f"Sign-off response: {signoff['response']}")

    plan = update_order_state(plan.plan_id, project.project_id, "BUYER_SIGNED_OFF", "buyer signed off")
    check(plan.current_order_state == "BUYER_SIGNED_OFF", f"Final order state: {plan.current_order_state}")

    machine = transition_state(project.project_id, "CLOSED", "order closed")
    check(machine.current_state == "CLOSED", f"Final machine state: {machine.current_state}")

    # ── Step 15: Supplier Memory update recorded ──────────────────────────────
    step(15, "Supplier Memory update recorded after order closure")

    update_supplier_memory(
        project_id=project.project_id,
        supplier_actor_id=SUPPLIER_ID,
        notes="Delivered on time. Buyer satisfied. Cotton polo shirt, 100 pcs, 25 days.",
    )
    mem_events = read_events(event_type="SUPPLIER_MEMORY_UPDATED_FROM_ORDER", b_workspace_id=project.project_id)
    check(len(mem_events) >= 1, f"Supplier memory events: {len(mem_events)}")

    # ── Step 16: IEG contains role-switching, merchandiser, and logistics events
    step(16, "IEG contains role-switching, merchandiser, and logistics events")

    # Role-switching events
    frame_events = read_events(event_type="M_ROLE_SWITCH_FRAME_CREATED", b_workspace_id=project.project_id)
    check(len(frame_events) >= 4, f"Role-switch frame events: {len(frame_events)}")

    state_change_events = read_events(event_type="M_ROLE_SEND_RECEIVE_STATE_CHANGED", b_workspace_id=project.project_id)
    check(len(state_change_events) >= 5, f"State machine transitions: {len(state_change_events)}")

    token_events = read_events(event_type="MESSAGE_CORRELATION_TOKEN_CREATED", b_workspace_id=project.project_id)
    check(len(token_events) >= 1, f"Correlation token events: {len(token_events)}")

    # Merchandiser events
    task_events = read_events(event_type="MERCHANDISER_TASK_CREATED", b_workspace_id=project.project_id)
    check(len(task_events) >= 5, f"Merchandiser task events: {len(task_events)}")

    milestone_events = read_events(event_type="ORDER_MILESTONE_CREATED", b_workspace_id=project.project_id)
    check(len(milestone_events) >= 4, f"Milestone creation events: {len(milestone_events)}")

    milestone_confirmed = read_events(event_type="ORDER_MILESTONE_BUYER_CONFIRMED", b_workspace_id=project.project_id)
    check(len(milestone_confirmed) >= 1, f"Milestone confirmed events: {len(milestone_confirmed)}")

    # Logistics events
    tracking_events = read_events(event_type="TRACKING_NUMBER_INGESTED", b_workspace_id=project.project_id)
    check(len(tracking_events) >= 1, f"Tracking ingested events: {len(tracking_events)}")

    ingestion_events = read_events(event_type="LOGISTICS_EVENT_INGESTED", b_workspace_id=project.project_id)
    check(len(ingestion_events) >= 3, f"Logistics event ingested: {len(ingestion_events)}")

    order_update_events = read_events(event_type="ORDER_STATE_UPDATED_FROM_LOGISTICS", b_workspace_id=project.project_id)
    check(len(order_update_events) >= 1, f"Order state update events: {len(order_update_events)}")

    signoff_events = read_events(event_type="BUYER_SIGNOFF_RECEIVED", b_workspace_id=project.project_id)
    check(len(signoff_events) >= 1, f"Buyer sign-off events: {len(signoff_events)}")

    supplier_mem_events = read_events(event_type="SUPPLIER_MEMORY_UPDATED_FROM_ORDER", b_workspace_id=project.project_id)
    check(len(supplier_mem_events) >= 1, f"Supplier memory events: {len(supplier_mem_events)}")

    # ── Final Report ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"INTEGRATED POST-CONFIRMATION MVP COMPLETE: {_steps_passed} passed, {_steps_failed} failed")
    print(f"{'=' * 70}")
    if _steps_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
