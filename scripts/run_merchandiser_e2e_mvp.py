"""
AI Merchandiser E2E MVP — 15-step post-confirmation execution test.

Tests the complete order execution flow:
  Buyer confirms → Execution plan → M-side tasks → B-side tasks
  → Media upload → Milestone confirmation → Logistics handover
  → Tracking ingestion → Delivery → Sign-off → Supplier memory update
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.merchandiser.merchandiser_engine import create_execution_plan, update_order_state, update_supplier_memory
from src.merchandiser.task_planner import get_tasks_for_project
from src.merchandiser.milestone_manager import (
    get_milestones_for_project, request_milestone_media,
    upload_milestone_evidence, confirm_milestone,
)
from src.merchandiser.media_confirmation import upload_media_evidence
from src.merchandiser.m_side.m_progress_check import request_progress_update, log_progress_update
from src.merchandiser.m_side.m_media_request import request_milestone_media_upload
from src.merchandiser.m_side.m_logistics_handover import request_logistics_handover, log_logistics_handover_received
from src.merchandiser.b_side.b_milestone_confirmation import send_milestone_review_request
from src.merchandiser.b_side.b_logistics_updates import push_logistics_update
from src.merchandiser.b_side.b_signoff import request_buyer_signoff, receive_buyer_signoff
from src.logistics.logistics_ingestion_service import ingest_tracking_number, sync_tracking_from_provider
from src.logistics.logistics_models import get_events_for_shipment, get_shipment
from src.projects.project_graph import create_project, update_project_status, get_project
from src.b_side.workspace import create_b_workspace
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


BUYER_ID = "actor_buyer_merch_test"
SUPPLIER_ID = "actor_manufacturer_merch_test"
TRACKING_NO = "SF998877665544"


def main():
    print("=" * 70)
    print("AI MERCHANDISER E2E MVP — End-to-End Test")
    print("=" * 70)

    # ── Step 1: Buyer B confirms supplier selection ───────────────────────────
    step(1, "Buyer B confirms supplier selection — order confirmed")

    b_workspace = create_b_workspace("Polo shirt 100 pcs — confirmed order")
    project = create_project(
        original_buyer_actor_id=BUYER_ID,
        product_summary="Men's polo shirt 100pcs",
        category="apparel",
        quantity=100,
        main_supplier_actor_id=SUPPLIER_ID,
        b_workspace_id=b_workspace.b_workspace_id,
    )
    update_project_status(project.project_id, "ORDER_CONFIRMED")
    project_reloaded = get_project(project.project_id)
    check(project_reloaded.status == "ORDER_CONFIRMED", f"Project status: {project_reloaded.status}")

    log_m_event(
        event_type="ORDER_CONFIRMED_BY_BUYER",
        b_workspace_id=project.project_id,
        supplier_id=BUYER_ID,
        payload={"project_id": project.project_id},
    )

    # ── Step 2: System creates post-confirmation execution plan ──────────────
    step(2, "System creates post-confirmation execution plan")

    plan = create_execution_plan(
        project_id=project.project_id,
        supplier_actor_id=SUPPLIER_ID,
        buyer_actor_id=BUYER_ID,
        category="apparel",
    )
    check(plan.plan_id.startswith("EXECPLAN-"), f"Plan ID: {plan.plan_id}")
    check(len(plan.task_ids) >= 5, f"Tasks created: {len(plan.task_ids)}")
    check(len(plan.milestone_ids) >= 4, f"Milestones created: {len(plan.milestone_ids)}")
    check(plan.current_order_state == "ORDER_CONFIRMED", f"Initial order state: {plan.current_order_state}")

    # ── Step 3: M-side AI Merchandiser creates supplier tasks ─────────────────
    step(3, "M-side AI Merchandiser creates supplier tasks")

    all_tasks = get_tasks_for_project(project.project_id)
    m_tasks = [t for t in all_tasks if t.assigned_side == "M_SIDE"]
    check(len(m_tasks) >= 5, f"M-side tasks: {len(m_tasks)}")
    m_task_types = {t.task_type for t in m_tasks}
    check("supplier_acceptance" in m_task_types, "supplier_acceptance task exists")
    check("logistics_handover" in m_task_types, "logistics_handover task exists")
    check("milestone_media_upload" in m_task_types, "milestone_media_upload task exists")

    # ── Step 4: B-side AI Merchandiser creates buyer review tasks ─────────────
    step(4, "B-side AI Merchandiser creates buyer review tasks")

    b_tasks = [t for t in all_tasks if t.assigned_side == "B_SIDE"]
    check(len(b_tasks) >= 2, f"B-side tasks: {len(b_tasks)}")
    b_task_types = {t.task_type for t in b_tasks}
    check("buyer_milestone_review" in b_task_types, "buyer_milestone_review task exists")
    check("buyer_signoff" in b_task_types, "buyer_signoff task exists")

    # ── Step 5: M-side receives progress reminder ─────────────────────────────
    step(5, "M-side receives progress check reminder")

    progress_result = request_progress_update(project.project_id, SUPPLIER_ID, "material_confirmation")
    check(progress_result.get("status") == "sent", f"Progress check sent: {progress_result['status']}")
    check(len(progress_result.get("message", "")) > 10, "Progress check message generated")

    update_result = log_progress_update(
        project.project_id, SUPPLIER_ID, "布料已到仓，今天开始裁剪。Material arrived, cutting starts today."
    )
    check(update_result.get("status") == "received", f"Progress update received: {update_result['status']}")

    # ── Step 6: M-side uploads milestone media ────────────────────────────────
    step(6, "M-side uploads milestone media for cutting stage")

    milestones = get_milestones_for_project(project.project_id)
    cutting_milestone = next((m for m in milestones if m.milestone_type == "cutting"), None)
    check(cutting_milestone is not None, f"Cutting milestone exists")

    if cutting_milestone:
        # Request media upload via M-side service
        media_req = request_milestone_media_upload(
            project.project_id, SUPPLIER_ID,
            cutting_milestone.milestone_id, "cutting",
            cutting_milestone.required_media_types,
        )
        check(media_req.get("status") == "requested", "Media upload requested")

        # Upload 3 images
        media_list = upload_media_evidence(
            project_id=project.project_id,
            milestone_id=cutting_milestone.milestone_id,
            uploaded_by_actor_id=SUPPLIER_ID,
            media_type="image",
            count=3,
        )
        check(len(media_list) == 3, f"Media uploaded: {len(media_list)} images")
        check(all(m.media_id.startswith("MEDIA-") for m in media_list), "All media IDs correct")

        # Update milestone status
        updated_milestone = upload_milestone_evidence(
            cutting_milestone.milestone_id, project.project_id,
            [m.media_id for m in media_list],
        )
        check(updated_milestone.status == "UPLOADED", f"Milestone status: {updated_milestone.status}")

    # ── Step 7: B-side receives milestone review request ─────────────────────
    step(7, "B-side receives milestone review request")

    if cutting_milestone:
        review_result = send_milestone_review_request(
            project.project_id, BUYER_ID,
            cutting_milestone.milestone_id, "cutting", 3,
        )
        check(review_result.get("status") == "review_requested", f"Review request: {review_result['status']}")
        check("Confirm" in review_result.get("message", ""), "Review message has confirm option")

    # ── Step 8: Buyer confirms milestone ──────────────────────────────────────
    step(8, "Buyer confirms cutting milestone")

    if cutting_milestone:
        confirmed_milestone = confirm_milestone(cutting_milestone.milestone_id, project.project_id)
        check(confirmed_milestone.status == "CONFIRMED", f"Milestone status: {confirmed_milestone.status}")

    # ── Step 9: M-side reports logistics handover ─────────────────────────────
    step(9, "M-side reports logistics handover with tracking number")

    handover_req = request_logistics_handover(project.project_id, SUPPLIER_ID)
    check(handover_req.get("status") == "requested", f"Logistics handover requested")
    check("顺丰" in handover_req.get("message", "") or "SF Express" in handover_req.get("message", ""),
          "Handover message has example tracking")

    im_message = f"已发顺丰，单号 {TRACKING_NO}，今天下午发出"
    log_logistics_handover_received(project.project_id, SUPPLIER_ID, im_message)

    # ── Step 10: Logistics ingestion creates shipment and events ──────────────
    step(10, "Logistics ingestion creates LogisticsShipment and events")

    shipment = ingest_tracking_number(
        project_id=project.project_id,
        carrier_name="顺丰",
        carrier_code="SF",
        tracking_number=TRACKING_NO,
        source="im_message",
        actor_id=SUPPLIER_ID,
    )
    check(shipment.shipment_id.startswith("SHIP-"), f"Shipment: {shipment.shipment_id}")
    check(shipment.tracking_number == TRACKING_NO, f"Tracking: {shipment.tracking_number}")
    check(shipment.carrier_code == "SF", f"Carrier: {shipment.carrier_code}")

    # Sync tracking events
    events = sync_tracking_from_provider(shipment.shipment_id)
    check(len(events) >= 1, f"Events synced: {len(events)}")

    # ── Step 11: Order state updates from logistics events ────────────────────
    step(11, "Order state updates from logistics events")

    synced_shipment = get_shipment(shipment.shipment_id)
    check(synced_shipment.current_status in ("in_transit", "delivered", "picked_up", "label_created"),
          f"Shipment status updated: {synced_shipment.current_status}")

    state_update_events = read_events(event_type="ORDER_STATE_UPDATED_FROM_LOGISTICS",
                                       b_workspace_id=project.project_id)
    check(len(state_update_events) >= 1, f"Order state update events: {len(state_update_events)}")

    # Find delivered event
    all_events = get_events_for_shipment(shipment.shipment_id)
    delivered_events = [e for e in all_events if e.normalized_status == "delivered"]
    check(len(delivered_events) >= 1, f"Delivered event found: {len(delivered_events)}")

    # Update execution plan state
    plan = update_order_state(plan.plan_id, project.project_id, "DELIVERED", "logistics delivered")
    check(plan.current_order_state == "DELIVERED", f"Order state: {plan.current_order_state}")

    # ── Step 12: B-side receives delivery update and sign-off request ─────────
    step(12, "B-side receives delivery update and buyer sign-off request")

    delivery_update = push_logistics_update(
        project_id=project.project_id,
        buyer_actor_id=BUYER_ID,
        tracking_number=TRACKING_NO,
        carrier_name="顺丰",
        normalized_status="delivered",
        description="Delivered and signed",
    )
    check(delivery_update.get("status") == "sent", f"Logistics update to buyer: {delivery_update['status']}")

    signoff_req = request_buyer_signoff(project.project_id, BUYER_ID, TRACKING_NO)
    check(signoff_req.get("status") == "signoff_requested", f"Sign-off request: {signoff_req['status']}")
    check("Confirm received" in signoff_req.get("message", ""), "Sign-off message has confirm option")

    # ── Step 13: Buyer signs off ──────────────────────────────────────────────
    step(13, "Buyer signs off on delivery")

    signoff = receive_buyer_signoff(project.project_id, BUYER_ID, response="confirmed", notes="Goods received in good condition")
    check(signoff.get("status") in ("signoff_received", "order_closed"), f"Sign-off: {signoff['status']}")
    check(signoff.get("response") == "confirmed", f"Sign-off response: {signoff['response']}")

    plan = update_order_state(plan.plan_id, project.project_id, "BUYER_SIGNED_OFF", "buyer confirmed delivery")
    check(plan.current_order_state == "BUYER_SIGNED_OFF", f"Final order state: {plan.current_order_state}")

    # ── Step 14: Supplier Memory update ───────────────────────────────────────
    step(14, "Supplier Memory update is recorded after order closure")

    update_supplier_memory(
        project_id=project.project_id,
        supplier_actor_id=SUPPLIER_ID,
        notes="Order completed on time. Good quality polo shirts. Recommended lead time 25 days for 100 pcs.",
    )
    mem_events = read_events(event_type="SUPPLIER_MEMORY_UPDATED_FROM_ORDER", b_workspace_id=project.project_id)
    check(len(mem_events) >= 1, f"Supplier memory events: {len(mem_events)}")

    # ── Step 15: IEG records all events ──────────────────────────────────────
    step(15, "Industrial Execution Graph records all events")

    task_events = read_events(event_type="MERCHANDISER_TASK_CREATED", b_workspace_id=project.project_id)
    check(len(task_events) >= 8, f"Task creation events: {len(task_events)}")

    milestone_events = read_events(event_type="ORDER_MILESTONE_CREATED", b_workspace_id=project.project_id)
    check(len(milestone_events) >= 4, f"Milestone creation events: {len(milestone_events)}")

    milestone_confirmed = read_events(event_type="ORDER_MILESTONE_BUYER_CONFIRMED", b_workspace_id=project.project_id)
    check(len(milestone_confirmed) >= 1, f"Milestone confirmed events: {len(milestone_confirmed)}")

    signoff_events = read_events(event_type="BUYER_SIGNOFF_RECEIVED", b_workspace_id=project.project_id)
    check(len(signoff_events) >= 1, f"Buyer sign-off events: {len(signoff_events)}")

    logistics_events = read_events(event_type="TRACKING_NUMBER_INGESTED", b_workspace_id=project.project_id)
    check(len(logistics_events) >= 1, f"Tracking ingested events: {len(logistics_events)}")

    progress_events = read_events(event_type="M_SIDE_PROGRESS_CHECK_REQUESTED", b_workspace_id=project.project_id)
    check(len(progress_events) >= 1, f"Progress check events: {len(progress_events)}")

    handover_events = read_events(event_type="LOGISTICS_HANDOVER_REQUESTED", b_workspace_id=project.project_id)
    check(len(handover_events) >= 1, f"Logistics handover events: {len(handover_events)}")

    # ── Final Report ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"AI MERCHANDISER E2E COMPLETE: {_steps_passed} passed, {_steps_failed} failed")
    print(f"{'=' * 70}")
    if _steps_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
