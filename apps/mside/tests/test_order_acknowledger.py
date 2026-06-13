"""
Tests for M-side order acknowledger.
"""
import uuid
import pytest
from src.m_side.order_acknowledger import (
    get_order_execution,
    save_order_execution,
    acknowledge_order,
)
from src.core_schema.m_side_types import OrderExecutionContext, ProductionMilestone


@pytest.fixture(autouse=True)
def patch_order_dir(tmp_path, monkeypatch):
    import src.m_side.order_acknowledger as oa_mod
    monkeypatch.setattr(oa_mod, "_DATA_DIR", tmp_path / "order_execution")


def _make_order(order_id=None, with_milestones=True):
    oid = order_id or f"ORD-{uuid.uuid4().hex[:8].upper()}"
    milestones = []
    if with_milestones:
        milestones = [
            ProductionMilestone(milestone_id="ms_001", name="order_acknowledgement"),
            ProductionMilestone(milestone_id="ms_002", name="production_start"),
            ProductionMilestone(milestone_id="ms_003", name="completed"),
        ]
    return OrderExecutionContext(
        order_execution_id=oid,
        b_workspace_id="bw_ack001",
        m_workspace_id="mw_ack001",
        supplier_id="sup_001",
        milestones=milestones,
    )


class TestGetOrderExecution:
    def test_raises_on_missing(self):
        with pytest.raises(FileNotFoundError):
            get_order_execution("ORD-NONEXISTENT")

    def test_round_trip(self):
        order = _make_order()
        save_order_execution(order)
        loaded = get_order_execution(order.order_execution_id)
        assert loaded.order_execution_id == order.order_execution_id

    def test_status_preserved(self):
        order = _make_order()
        order.status = "production_in_progress"
        save_order_execution(order)
        loaded = get_order_execution(order.order_execution_id)
        assert loaded.status == "production_in_progress"

    def test_milestones_preserved(self):
        order = _make_order()
        save_order_execution(order)
        loaded = get_order_execution(order.order_execution_id)
        assert len(loaded.milestones) == 3


class TestSaveOrderExecution:
    def test_saves_successfully(self):
        order = _make_order()
        result = save_order_execution(order)
        assert result.order_execution_id == order.order_execution_id

    def test_updated_at_set(self):
        order = _make_order()
        result = save_order_execution(order)
        assert result.updated_at is not None

    def test_overwrites_existing(self):
        order = _make_order()
        save_order_execution(order)
        order.status = "order_acknowledged"
        save_order_execution(order)
        loaded = get_order_execution(order.order_execution_id)
        assert loaded.status == "order_acknowledged"


class TestAcknowledgeOrder:
    def test_status_updated_to_acknowledged(self):
        order = _make_order()
        save_order_execution(order)
        updated = acknowledge_order(order.order_execution_id, "确认接单，没问题")
        assert updated.status == "order_acknowledged"

    def test_milestone_completed(self):
        order = _make_order()
        save_order_execution(order)
        updated = acknowledge_order(order.order_execution_id, "确认接单")
        ack_ms = next(
            (m for m in updated.milestones if m.name == "order_acknowledgement"), None
        )
        assert ack_ms is not None
        assert ack_ms.status == "completed"

    def test_message_stored_in_milestone_notes(self):
        order = _make_order()
        save_order_execution(order)
        msg = "确认接单，我们接受这个订单"
        updated = acknowledge_order(order.order_execution_id, msg)
        ack_ms = next(
            (m for m in updated.milestones if m.name == "order_acknowledgement"), None
        )
        assert ack_ms is not None
        assert ack_ms.notes is not None

    def test_raises_on_missing_order(self):
        with pytest.raises(FileNotFoundError):
            acknowledge_order("ORD-NONEXISTENT", "confirm")

    def test_order_persisted_after_acknowledge(self):
        order = _make_order()
        save_order_execution(order)
        acknowledge_order(order.order_execution_id, "confirm")
        loaded = get_order_execution(order.order_execution_id)
        assert loaded.status == "order_acknowledged"
