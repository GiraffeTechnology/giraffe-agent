"""
Tests for B+M bridge — inquiry dispatch and response push.
"""
import uuid
import pytest
from src.core_schema.b_side_types import (
    BWWorkspace, BuyerRequirement, SupplierResponseRecord, SupplierInquiryDraft
)


@pytest.fixture(autouse=True)
def patch_dirs(tmp_path, monkeypatch):
    import src.b_side.workspace as bw_mod
    import src.m_side.supplier_workspace as mw_mod
    import src.m_side.supplier_profile as sp_mod
    monkeypatch.setattr(bw_mod, "_DATA_DIR", tmp_path / "bw")
    monkeypatch.setattr(mw_mod, "_DATA_DIR", tmp_path / "mw")
    monkeypatch.setattr(sp_mod, "_DATA_DIR", tmp_path / "sp")


def _setup_bside_workspace(bw_id, tmp_path=None):
    from src.b_side.workspace import save_b_workspace, _ensure_dir
    _ensure_dir()
    req = BuyerRequirement(
        rfq_id="RFQ-BM01",
        b_workspace_id=bw_id,
        raw_text="100 pcs CNC bracket",
        quantity=100,
        category="cnc",
    )
    draft = SupplierInquiryDraft(
        rfq_id="RFQ-BM01",
        b_workspace_id=bw_id,
        inquiry_id="INQ-BM01",
        supplier_ids=["sup_001", "sup_002"],
        message_text_en="Please quote for CNC bracket",
        message_text_zh="请报价CNC支架",
    )
    ws = BWWorkspace(
        b_workspace_id=bw_id,
        rfq_id="RFQ-BM01",
        raw_requirement="100 pcs CNC bracket",
        buyer_requirement=req,
        supplier_inquiry_draft=draft,
    )
    return save_b_workspace(ws)


class TestDispatchSupplierInquiry:
    def test_dispatch_creates_m_workspaces(self, tmp_path):
        from src.bm_bridge.inquiry_dispatcher import dispatch_supplier_inquiry
        bw_id = "bw_bridge001"
        _setup_bside_workspace(bw_id)
        contexts = dispatch_supplier_inquiry(bw_id, ["sup_001", "sup_002"], channel="mock")
        assert len(contexts) == 2

    def test_dispatch_returns_contexts(self, tmp_path):
        from src.bm_bridge.inquiry_dispatcher import dispatch_supplier_inquiry
        bw_id = "bw_bridge002"
        _setup_bside_workspace(bw_id)
        contexts = dispatch_supplier_inquiry(bw_id, ["sup_001"], channel="mock")
        assert contexts[0].b_workspace_id == bw_id

    def test_dispatch_invitation_tokens(self, tmp_path):
        from src.bm_bridge.inquiry_dispatcher import dispatch_supplier_inquiry
        bw_id = "bw_bridge003"
        _setup_bside_workspace(bw_id)
        contexts = dispatch_supplier_inquiry(bw_id, ["sup_001"], channel="mock")
        assert contexts[0].invitation_token.startswith("GQ-")

    def test_dispatch_m_workspace_ids_unique(self, tmp_path):
        from src.bm_bridge.inquiry_dispatcher import dispatch_supplier_inquiry
        bw_id = "bw_bridge004"
        _setup_bside_workspace(bw_id)
        contexts = dispatch_supplier_inquiry(bw_id, ["s1", "s2", "s3"], channel="mock")
        m_ids = [c.m_workspace_id for c in contexts]
        assert len(set(m_ids)) == 3


class TestPushResponseToBSide:
    def test_push_response_appends_to_workspace(self, tmp_path):
        from src.bm_bridge.response_bridge import push_supplier_response_to_b_side
        from src.core_schema.m_side_types import (
            SupplierResponsePacket, CapacitySignal, ScheduleSignal,
            MaterialAvailability, SupplierQuote, QCCommitment, LogisticsCommitment
        )
        bw_id = "bw_bridge_push001"
        _setup_bside_workspace(bw_id)

        packet = SupplierResponsePacket(
            response_id="RSP-BM01",
            m_workspace_id="mw_push_001",
            b_workspace_id=bw_id,
            rfq_id="RFQ-BM01",
            inquiry_id="INQ-BM01",
            supplier_id="sup_001",
            supplier_name="Test Supplier",
            capacity_signal=CapacitySignal(can_make=True),
            schedule_signal=ScheduleSignal(estimated_lead_time_days=25),
            quote=SupplierQuote(unit_price=12.5, currency="USD"),
            completeness_score=0.7,
            confidence_score=0.8,
        )
        result = push_supplier_response_to_b_side(packet)
        assert result.get("ok") is True

    def test_push_response_creates_b_side_record(self, tmp_path):
        from src.bm_bridge.response_bridge import push_supplier_response_to_b_side
        from src.b_side.workspace import get_b_workspace
        from src.core_schema.m_side_types import (
            SupplierResponsePacket, CapacitySignal, ScheduleSignal,
            MaterialAvailability, SupplierQuote
        )
        bw_id = "bw_bridge_push002"
        _setup_bside_workspace(bw_id)

        packet = SupplierResponsePacket(
            response_id="RSP-BM02",
            m_workspace_id="mw_push_002",
            b_workspace_id=bw_id,
            rfq_id="RFQ-BM01",
            inquiry_id="INQ-BM01",
            supplier_id="sup_push",
            supplier_name="Push Supplier",
            capacity_signal=CapacitySignal(can_make=True),
            schedule_signal=ScheduleSignal(estimated_lead_time_days=20),
            quote=SupplierQuote(unit_price=10.0, currency="USD"),
        )
        push_supplier_response_to_b_side(packet)
        ws = get_b_workspace(bw_id)
        assert any(r.supplier_id == "sup_push" for r in ws.supplier_responses)


class TestCoreSchemaIntegration:
    def test_workspace_with_draft_and_responses(self):
        req = BuyerRequirement(rfq_id="RFQ-I1", b_workspace_id="bw_i1", raw_text="test")
        draft = SupplierInquiryDraft(
            rfq_id="RFQ-I1", b_workspace_id="bw_i1", inquiry_id="INQ-I1",
            supplier_ids=["s1", "s2"],
        )
        resp = SupplierResponseRecord(
            response_id="RSP-I1", rfq_id="RFQ-I1", b_workspace_id="bw_i1",
            supplier_id="s1", supplier_name="S1", can_make=True,
        )
        ws = BWWorkspace(
            b_workspace_id="bw_i1", rfq_id="RFQ-I1", raw_requirement="test",
            buyer_requirement=req, supplier_inquiry_draft=draft, supplier_responses=[resp],
        )
        assert ws.supplier_inquiry_draft is not None
        assert len(ws.supplier_responses) == 1

    def test_workspace_json_serializable(self):
        import json
        req = BuyerRequirement(rfq_id="RFQ-J1", b_workspace_id="bw_j1", raw_text="test")
        ws = BWWorkspace(
            b_workspace_id="bw_j1", rfq_id="RFQ-J1", raw_requirement="test",
            buyer_requirement=req,
        )
        data = ws.model_dump(mode="json")
        json.dumps(data)  # should not raise

    def test_feasibility_report_in_workspace(self):
        from src.core_schema.b_side_types import FeasibilityReport, DeliveryPath
        path = DeliveryPath(
            path_id="PATH-F1", rfq_id="RFQ-F1", supplier_id="s1", supplier_name="S1",
            lead_time_days=20, rank=1,
        )
        report = FeasibilityReport(rfq_id="RFQ-F1", b_workspace_id="bw_f1", paths=[path])
        ws = BWWorkspace(
            b_workspace_id="bw_f1", rfq_id="RFQ-F1", raw_requirement="test",
            feasibility_report=report, status="feasibility_complete",
        )
        assert ws.feasibility_report is not None
        assert len(ws.feasibility_report.paths) == 1
