# Unicode escapes retain the original non-English test inputs and assertions.
# Keep these vectors multilingual; English-only inputs do not test the same behavior.
"""Tests verifying existing M-side handlers still work correctly after merchandiser integration."""
import pytest
from src.m_side.logistics_update import submit_logistics_update
from src.m_side.order_acknowledger import save_order_execution, get_order_execution
from src.core_schema.m_side_types import OrderExecutionContext, ProductionMilestone
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc)


def _make_order(order_id: str, b_workspace_id: str = "BW-TEST-001") -> OrderExecutionContext:
    return OrderExecutionContext(
        order_execution_id=order_id,
        b_workspace_id=b_workspace_id,
        m_workspace_id=f"MW-TEST-{order_id[-3:]}",
        supplier_id="sup-handler-001",
        selected_path_id="PATH-001",
        status="order_acknowledgement_pending",
        milestones=[
            ProductionMilestone(
                milestone_id=f"MS-{order_id[-3:]}",
                name="logistics_handover",
                status="pending",
                evidence_required=True,
            ),
            ProductionMilestone(
                milestone_id=f"MS-{order_id[-3:]}B",
                name="shipped",
                status="pending",
                evidence_required=True,
            ),
        ],
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )


def test_logistics_update_shipped_sets_order_shipped():
    order = _make_order("OE-HAND-SHIPPED-001")
    save_order_execution(order)
    update = submit_logistics_update(
        order_execution_id=order.order_execution_id,
        supplier_id="sup-handler-001",
        message='\u5df2\u53d1\u8d27\uff0c\u987a\u4e30\u5feb\u9012 SF123456789012',
    )
    loaded = get_order_execution(order.order_execution_id)
    assert loaded.status == "shipped"


def test_logistics_update_delivered_sets_buyer_signoff_pending():
    order = _make_order("OE-HAND-DELIV-001", b_workspace_id="BW-TEST-DELIV")
    save_order_execution(order)
    update = submit_logistics_update(
        order_execution_id=order.order_execution_id,
        supplier_id="sup-handler-001",
        message='\u5df2\u7b7e\u6536\uff0c\u5ba2\u6237\u5df2\u6536\u8d27\uff0cdelivered',
    )
    loaded = get_order_execution(order.order_execution_id)
    assert loaded.status == "buyer_signoff_pending"
    assert loaded.status != "completed"
    assert loaded.status != "order_closed"


def test_logistics_update_delivered_never_sets_completed():
    order = _make_order("OE-HAND-COMP-001", b_workspace_id="BW-TEST-COMP")
    save_order_execution(order)
    submit_logistics_update(
        order_execution_id=order.order_execution_id,
        supplier_id="sup-handler-001",
        message="Delivered to customer",
    )
    loaded = get_order_execution(order.order_execution_id)
    assert loaded.status != "completed"


def test_logistics_update_no_match_preserves_status():
    order = _make_order("OE-HAND-NOOP-001", b_workspace_id="BW-TEST-NOOP")
    save_order_execution(order)
    original_status = order.status
    submit_logistics_update(
        order_execution_id=order.order_execution_id,
        supplier_id="sup-handler-001",
        message='\u5305\u88f9\u5df2\u6253\u5305\uff0c\u51c6\u5907\u53d1\u51fa',
    )
    loaded = get_order_execution(order.order_execution_id)
    assert loaded.status == "ready_for_pickup" or loaded.status == original_status


def test_order_execution_context_has_merchandiser_fields():
    order = OrderExecutionContext(
        order_execution_id="OE-FIELD-TEST",
        b_workspace_id="BW-FIELD-TEST",
        m_workspace_id="MW-FIELD-TEST",
        supplier_id="sup-field-001",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    assert hasattr(order, "merchandiser_plan_id")
    assert hasattr(order, "merchandiser_task_ids")
    assert hasattr(order, "merchandiser_milestone_ids")
    assert order.merchandiser_plan_id is None
    assert order.merchandiser_task_ids == []
    assert order.merchandiser_milestone_ids == []


def test_order_execution_context_merchandiser_fields_assignable():
    order = OrderExecutionContext(
        order_execution_id="OE-ASSIGN-TEST",
        b_workspace_id="BW-ASSIGN-TEST",
        m_workspace_id="MW-ASSIGN-TEST",
        supplier_id="sup-assign-001",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    order.merchandiser_plan_id = "EXECPLAN-TESTPLAN"
    order.merchandiser_task_ids = ["TASK-001", "TASK-002"]
    order.merchandiser_milestone_ids = ["MILE-001"]
    assert order.merchandiser_plan_id == "EXECPLAN-TESTPLAN"
    assert len(order.merchandiser_task_ids) == 2
    assert len(order.merchandiser_milestone_ids) == 1


def test_logistics_update_tracks_tracking_number():
    order = _make_order("OE-HAND-TRACK-001", b_workspace_id="BW-TRACK")
    save_order_execution(order)
    update = submit_logistics_update(
        order_execution_id=order.order_execution_id,
        supplier_id="sup-handler-001",
        message='SF\u5feb\u9012\u5df2\u53d1\u51fa\uff0c\u5355\u53f7SF123456789012',
    )
    assert update.tracking_number is not None
    assert "SF" in (update.tracking_number or "")


def test_logistics_update_extracts_carrier():
    order = _make_order("OE-HAND-CARR-001", b_workspace_id="BW-CARR")
    save_order_execution(order)
    update = submit_logistics_update(
        order_execution_id=order.order_execution_id,
        supplier_id="sup-handler-001",
        message='DHL\u5df2\u53d1\u51fa\uff0c\u5355\u53f71234567890123',
    )
    assert update.carrier is not None
