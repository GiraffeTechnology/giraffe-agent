"""
Tests for M-side Pydantic v2 data models.
"""
from datetime import datetime
import pytest
from src.core_schema.m_side_types import (
    SupplierCapability,
    MSideSupplierProfile,
    SupplierInquiryContext,
    CapacitySignal,
    ScheduleSignal,
    MaterialAvailability,
    SupplierQuote,
    QCCommitment,
    LogisticsCommitment,
    SupplierResponsePacket,
    ProductionMilestone,
    OrderExecutionContext,
    ProductionUpdate,
    QCUpdate,
    LogisticsUpdate,
    ExceptionReport,
    MSideWorkspace,
)


class TestSupplierCapability:
    def test_minimal(self):
        cap = SupplierCapability()
        assert cap.categories == []

    def test_categories_list(self):
        cap = SupplierCapability(categories=["cnc", "machining"])
        assert "cnc" in cap.categories

    def test_materials_list(self):
        cap = SupplierCapability(materials=["aluminum 6061", "steel"])
        assert len(cap.materials) == 2

    def test_processes_list(self):
        cap = SupplierCapability(processes=["milling", "turning"])
        assert "milling" in cap.processes


class TestMSideSupplierProfile:
    def test_minimal_creation(self):
        p = MSideSupplierProfile(supplier_id="sup_001", supplier_name="Test Supplier")
        assert p.supplier_id == "sup_001"

    def test_default_language(self):
        p = MSideSupplierProfile(supplier_id="sup_001", supplier_name="Test")
        assert p.language_preference == "zh"

    def test_capability_nested(self):
        p = MSideSupplierProfile(
            supplier_id="sup_001",
            supplier_name="Test",
            capability=SupplierCapability(categories=["cnc"]),
        )
        assert "cnc" in p.capability.categories

    def test_created_at_datetime(self):
        p = MSideSupplierProfile(supplier_id="sup_001", supplier_name="Test")
        assert isinstance(p.created_at, datetime)

    def test_region_optional(self):
        p = MSideSupplierProfile(supplier_id="sup_001", supplier_name="Test", region="Shenzhen")
        assert p.region == "Shenzhen"


class TestSupplierInquiryContext:
    def _make(self, **kwargs):
        defaults = dict(
            m_workspace_id="mw_001",
            b_workspace_id="bw_001",
            rfq_id="RFQ-001",
            inquiry_id="INQ-001",
            supplier_id="sup_001",
            supplier_name="Test Supplier",
            invitation_token="GQ-ABCD1234",
            inquiry_text_zh="请报价",
            inquiry_text_en="Please quote",
        )
        defaults.update(kwargs)
        return SupplierInquiryContext(**defaults)

    def test_creation(self):
        ctx = self._make()
        assert ctx.m_workspace_id == "mw_001"

    def test_nda_not_required_by_default(self):
        ctx = self._make()
        assert ctx.nda_required is False

    def test_cap_level_zero_default(self):
        ctx = self._make()
        assert ctx.cap_level == 0

    def test_attachments_empty_by_default(self):
        ctx = self._make()
        assert ctx.attachments == []


class TestCapacitySignal:
    def test_can_make_none_default(self):
        s = CapacitySignal()
        assert s.can_make is None

    def test_can_make_true(self):
        s = CapacitySignal(can_make=True)
        assert s.can_make is True

    def test_bottlenecks_empty(self):
        s = CapacitySignal()
        assert s.bottlenecks == []

    def test_monthly_capacity_hint(self):
        s = CapacitySignal(monthly_capacity_hint=5000)
        assert s.monthly_capacity_hint == 5000


class TestScheduleSignal:
    def test_defaults_none(self):
        s = ScheduleSignal()
        assert s.estimated_lead_time_days is None

    def test_lead_time_set(self):
        s = ScheduleSignal(estimated_lead_time_days=30)
        assert s.estimated_lead_time_days == 30

    def test_schedule_risks_empty(self):
        s = ScheduleSignal()
        assert s.schedule_risks == []


class TestMaterialAvailability:
    def test_defaults_none(self):
        m = MaterialAvailability()
        assert m.material_available is None

    def test_available_true(self):
        m = MaterialAvailability(material_available=True)
        assert m.material_available is True

    def test_substitute_materials_empty(self):
        m = MaterialAvailability()
        assert m.substitute_materials == []


class TestSupplierQuote:
    def test_defaults(self):
        q = SupplierQuote()
        assert q.unit_price is None

    def test_price_set(self):
        q = SupplierQuote(unit_price=12.5, currency="USD")
        assert q.unit_price == 12.5

    def test_currency_default_none(self):
        q = SupplierQuote()
        assert q.currency is None


class TestQCCommitment:
    def test_defaults(self):
        qc = QCCommitment()
        assert qc.qc_available is None

    def test_photo_support_default(self):
        qc = QCCommitment()
        assert isinstance(qc.photo_or_video_update_supported, bool)


class TestSupplierResponsePacket:
    def _make(self, **kwargs):
        defaults = dict(
            response_id="RSP-001",
            m_workspace_id="mw_001",
            b_workspace_id="bw_001",
            rfq_id="RFQ-001",
            inquiry_id="INQ-001",
            supplier_id="sup_001",
            supplier_name="Test Supplier",
        )
        defaults.update(kwargs)
        return SupplierResponsePacket(**defaults)

    def test_creation(self):
        p = self._make()
        assert p.supplier_id == "sup_001"

    def test_default_scores_zero(self):
        p = self._make()
        assert p.completeness_score == 0.0
        assert p.confidence_score == 0.0

    def test_red_flags_empty(self):
        p = self._make()
        assert p.red_flags == []

    def test_nested_signals(self):
        p = self._make()
        assert p.capacity_signal is not None
        assert p.schedule_signal is not None

    def test_submitted_at_datetime(self):
        p = self._make()
        assert isinstance(p.submitted_at, datetime)


class TestProductionMilestone:
    def test_creation(self):
        m = ProductionMilestone(milestone_id="ms_001", name="order_acknowledgement")
        assert m.status == "pending"

    def test_status_options(self):
        for status in ["pending", "in_progress", "completed", "delayed"]:
            m = ProductionMilestone(milestone_id="ms_001", name="test", status=status)
            assert m.status == status


class TestOrderExecutionContext:
    def _make(self, **kwargs):
        defaults = dict(
            order_execution_id="ORD-001",
            b_workspace_id="bw_001",
            m_workspace_id="mw_001",
            supplier_id="sup_001",
        )
        defaults.update(kwargs)
        return OrderExecutionContext(**defaults)

    def test_creation(self):
        o = self._make()
        assert o.order_execution_id == "ORD-001"

    def test_default_status(self):
        o = self._make()
        assert o.status == "order_acknowledgement_pending"

    def test_milestones_empty(self):
        o = self._make()
        assert o.milestones == []

    def test_with_milestones(self):
        ms = ProductionMilestone(milestone_id="ms_001", name="order_acknowledgement")
        o = self._make(milestones=[ms])
        assert len(o.milestones) == 1


class TestMSideWorkspace:
    def _make(self, **kwargs):
        defaults = dict(
            m_workspace_id="mw_001",
            b_workspace_id="bw_001",
            rfq_id="RFQ-001",
            inquiry_id="INQ-001",
            supplier_id="sup_001",
            supplier_name="Test Supplier",
        )
        defaults.update(kwargs)
        return MSideWorkspace(**defaults)

    def test_creation(self):
        ws = self._make()
        assert ws.m_workspace_id == "mw_001"

    def test_default_status(self):
        ws = self._make()
        assert ws.status == "inquiry_received"

    def test_supplier_messages_empty(self):
        ws = self._make()
        assert ws.raw_supplier_messages == []

    def test_production_updates_empty(self):
        ws = self._make()
        assert ws.production_updates == []
