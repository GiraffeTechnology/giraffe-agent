"""
Tests for B-side Pydantic v2 data models.
"""
import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.core_schema.b_side_types import (
    BuyerRequirement,
    BWWorkspace,
    DeliveryPath,
    FeasibilityReport,
    SupplierInquiryDraft,
    SupplierResponseRecord,
)


# ─── BuyerRequirement ───────────────────────────────────────────────────────

class TestBuyerRequirement:
    def test_minimal_creation(self):
        req = BuyerRequirement(
            rfq_id="RFQ-001",
            b_workspace_id="bw_001",
            raw_text="100 pcs cotton shirt",
        )
        assert req.rfq_id == "RFQ-001"
        assert req.b_workspace_id == "bw_001"
        assert req.raw_text == "100 pcs cotton shirt"

    def test_default_confidence_is_zero(self):
        req = BuyerRequirement(rfq_id="RFQ-002", b_workspace_id="bw_002", raw_text="test")
        assert req.confidence_score == 0.0

    def test_default_missing_fields_empty(self):
        req = BuyerRequirement(rfq_id="RFQ-003", b_workspace_id="bw_003", raw_text="test")
        assert req.missing_fields == []

    def test_default_specs_json_empty(self):
        req = BuyerRequirement(rfq_id="RFQ-004", b_workspace_id="bw_004", raw_text="test")
        assert req.specs_json == {}

    def test_full_requirement(self):
        req = BuyerRequirement(
            rfq_id="RFQ-FULL",
            b_workspace_id="bw_full",
            raw_text="100 pcs aluminum CNC bracket ±0.05mm",
            category="cnc",
            quantity=100,
            material="aluminum 6061",
            specs_json={"tolerance": "±0.05mm"},
            deadline="2026-09-30",
            destination="Munich",
            confidence_score=1.0,
        )
        assert req.quantity == 100
        assert req.category == "cnc"
        assert req.material == "aluminum 6061"
        assert req.confidence_score == 1.0

    def test_confidence_score_range(self):
        req = BuyerRequirement(
            rfq_id="R1", b_workspace_id="b1", raw_text="t", confidence_score=0.75
        )
        assert 0.0 <= req.confidence_score <= 1.0

    def test_created_at_is_datetime(self):
        req = BuyerRequirement(rfq_id="R1", b_workspace_id="b1", raw_text="t")
        assert isinstance(req.created_at, datetime)

    def test_missing_fields_list(self):
        req = BuyerRequirement(
            rfq_id="R1",
            b_workspace_id="b1",
            raw_text="t",
            missing_fields=["quantity", "material"],
        )
        assert "quantity" in req.missing_fields
        assert "material" in req.missing_fields

    def test_specs_json_arbitrary_keys(self):
        req = BuyerRequirement(
            rfq_id="R1",
            b_workspace_id="b1",
            raw_text="t",
            specs_json={"surface": "anodized", "threads": "M6"},
        )
        assert req.specs_json["surface"] == "anodized"


# ─── SupplierResponseRecord ──────────────────────────────────────────────────

class TestSupplierResponseRecord:
    def _make(self, **kwargs):
        defaults = dict(
            response_id="RSP-001",
            rfq_id="RFQ-001",
            b_workspace_id="bw_001",
            supplier_id="sup_001",
            supplier_name="Test Supplier",
        )
        defaults.update(kwargs)
        return SupplierResponseRecord(**defaults)

    def test_minimal_creation(self):
        r = self._make()
        assert r.supplier_name == "Test Supplier"

    def test_default_red_flags_empty(self):
        r = self._make()
        assert r.red_flags == []

    def test_can_make_true(self):
        r = self._make(can_make=True)
        assert r.can_make is True

    def test_can_make_false(self):
        r = self._make(can_make=False)
        assert r.can_make is False

    def test_can_make_none_by_default(self):
        r = self._make()
        assert r.can_make is None

    def test_confidence_score_default(self):
        r = self._make()
        assert r.confidence_score == 0.0

    def test_lead_time_stored(self):
        r = self._make(estimated_lead_time_days=30)
        assert r.estimated_lead_time_days == 30

    def test_price_stored(self):
        r = self._make(unit_price=12.50, total_price=1250.0, currency="USD")
        assert r.unit_price == 12.50
        assert r.currency == "USD"

    def test_red_flags_list(self):
        r = self._make(red_flags=["capacity uncertain", "price valid 15 days"])
        assert len(r.red_flags) == 2

    def test_submitted_at_is_datetime(self):
        r = self._make()
        assert isinstance(r.submitted_at, datetime)


# ─── DeliveryPath ────────────────────────────────────────────────────────────

class TestDeliveryPath:
    def _make(self, **kwargs):
        defaults = dict(
            path_id="PATH-001",
            rfq_id="RFQ-001",
            supplier_id="sup_001",
            supplier_name="Supplier One",
        )
        defaults.update(kwargs)
        return DeliveryPath(**defaults)

    def test_creation(self):
        p = self._make()
        assert p.path_id == "PATH-001"

    def test_default_rank_zero(self):
        p = self._make()
        assert p.rank == 0

    def test_rank_set(self):
        p = self._make(rank=1)
        assert p.rank == 1

    def test_risk_score_default_zero(self):
        p = self._make()
        assert p.risk_score == 0.0

    def test_lead_time_set(self):
        p = self._make(lead_time_days=21)
        assert p.lead_time_days == 21

    def test_price_fields(self):
        p = self._make(unit_price=10.0, total_price=1000.0, currency="USD")
        assert p.total_price == 1000.0


# ─── FeasibilityReport ───────────────────────────────────────────────────────

class TestFeasibilityReport:
    def test_empty_paths(self):
        r = FeasibilityReport(rfq_id="RFQ-001", b_workspace_id="bw_001")
        assert r.paths == []

    def test_with_paths(self):
        path = DeliveryPath(
            path_id="PATH-001", rfq_id="RFQ-001", supplier_id="s1", supplier_name="S1"
        )
        r = FeasibilityReport(rfq_id="RFQ-001", b_workspace_id="bw_001", paths=[path])
        assert len(r.paths) == 1

    def test_generated_at_is_datetime(self):
        r = FeasibilityReport(rfq_id="RFQ-001", b_workspace_id="bw_001")
        assert isinstance(r.generated_at, datetime)


# ─── BWWorkspace ─────────────────────────────────────────────────────────────

class TestBWWorkspace:
    def test_creation(self):
        ws = BWWorkspace(
            b_workspace_id="bw_001",
            rfq_id="RFQ-001",
            raw_requirement="test",
        )
        assert ws.status == "created"

    def test_default_status(self):
        ws = BWWorkspace(b_workspace_id="bw_001", rfq_id="RFQ-001", raw_requirement="t")
        assert ws.status == "created"

    def test_supplier_responses_empty_by_default(self):
        ws = BWWorkspace(b_workspace_id="bw_001", rfq_id="RFQ-001", raw_requirement="t")
        assert ws.supplier_responses == []

    def test_workspace_id_preserved(self):
        ws = BWWorkspace(b_workspace_id="bw_custom_id", rfq_id="RFQ-001", raw_requirement="t")
        assert ws.b_workspace_id == "bw_custom_id"


# ─── SupplierInquiryDraft ────────────────────────────────────────────────────

class TestSupplierInquiryDraft:
    def test_creation(self):
        d = SupplierInquiryDraft(
            rfq_id="RFQ-001",
            b_workspace_id="bw_001",
            inquiry_id="INQ-001",
        )
        assert d.inquiry_id == "INQ-001"

    def test_default_empty_messages(self):
        d = SupplierInquiryDraft(
            rfq_id="RFQ-001", b_workspace_id="bw_001", inquiry_id="INQ-001"
        )
        assert d.message_text_en == ""
        assert d.message_text_zh == ""

    def test_supplier_ids(self):
        d = SupplierInquiryDraft(
            rfq_id="RFQ-001",
            b_workspace_id="bw_001",
            inquiry_id="INQ-001",
            supplier_ids=["s1", "s2", "s3"],
        )
        assert len(d.supplier_ids) == 3
