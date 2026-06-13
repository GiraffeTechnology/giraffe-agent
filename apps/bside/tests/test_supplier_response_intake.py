"""
Tests for B-side supplier response intake.
"""
import uuid
import pytest
from src.b_side.supplier_response_intake import intake_supplier_response
from src.core_schema.b_side_types import BWWorkspace, BuyerRequirement, SupplierResponseRecord


@pytest.fixture(autouse=True)
def patch_data_dir(tmp_path, monkeypatch):
    import src.b_side.workspace as ws_mod
    monkeypatch.setattr(ws_mod, "_DATA_DIR", tmp_path / "bw_intake")


def _create_workspace(bw_id="bw_intake001", status="inquiry_drafted"):
    from src.b_side.workspace import save_b_workspace, _ensure_dir
    _ensure_dir()
    req = BuyerRequirement(
        rfq_id="RFQ-INT01", b_workspace_id=bw_id, raw_text="100 pcs aluminum bracket"
    )
    ws = BWWorkspace(
        b_workspace_id=bw_id,
        rfq_id="RFQ-INT01",
        raw_requirement="100 pcs aluminum bracket",
        status=status,
        buyer_requirement=req,
    )
    return save_b_workspace(ws)


def _make_response(supplier_id, bw_id="bw_intake001", can_make=True):
    return SupplierResponseRecord(
        response_id=f"RSP-{uuid.uuid4().hex[:6].upper()}",
        rfq_id="RFQ-INT01",
        b_workspace_id=bw_id,
        supplier_id=supplier_id,
        supplier_name=f"Supplier {supplier_id}",
        can_make=can_make,
        confidence_score=0.8,
    )


class TestIntakeSupplierResponse:
    def test_appends_response(self):
        _create_workspace()
        r = _make_response("sup_001")
        ws = intake_supplier_response("bw_intake001", r)
        assert len(ws.supplier_responses) == 1

    def test_status_becomes_collecting(self):
        _create_workspace(status="inquiry_drafted")
        r = _make_response("sup_001")
        ws = intake_supplier_response("bw_intake001", r)
        assert ws.status == "collecting_responses"

    def test_multiple_suppliers(self):
        _create_workspace()
        for sid in ["s1", "s2", "s3"]:
            intake_supplier_response("bw_intake001", _make_response(sid))
        from src.b_side.workspace import get_b_workspace
        ws = get_b_workspace("bw_intake001")
        assert len(ws.supplier_responses) == 3

    def test_deduplication_same_supplier(self):
        _create_workspace()
        r1 = _make_response("sup_dup")
        r1_updated = _make_response("sup_dup")
        r1_updated.confidence_score = 0.95
        intake_supplier_response("bw_intake001", r1)
        intake_supplier_response("bw_intake001", r1_updated)
        from src.b_side.workspace import get_b_workspace
        ws = get_b_workspace("bw_intake001")
        assert len(ws.supplier_responses) == 1

    def test_deduplication_updates_latest(self):
        _create_workspace()
        r_old = _make_response("sup_upd")
        r_old.confidence_score = 0.5
        intake_supplier_response("bw_intake001", r_old)
        r_new = _make_response("sup_upd")
        r_new.confidence_score = 0.95
        intake_supplier_response("bw_intake001", r_new)
        from src.b_side.workspace import get_b_workspace
        ws = get_b_workspace("bw_intake001")
        assert ws.supplier_responses[0].confidence_score == 0.95

    def test_status_not_reset_when_already_collecting(self):
        _create_workspace(status="collecting_responses")
        r = _make_response("sup_001")
        ws = intake_supplier_response("bw_intake001", r)
        assert ws.status == "collecting_responses"

    def test_can_make_false_still_accepted(self):
        _create_workspace()
        r = _make_response("sup_cant", can_make=False)
        ws = intake_supplier_response("bw_intake001", r)
        assert len(ws.supplier_responses) == 1
        assert ws.supplier_responses[0].can_make is False

    def test_persisted_after_intake(self):
        _create_workspace()
        r = _make_response("sup_persist")
        intake_supplier_response("bw_intake001", r)
        from src.b_side.workspace import get_b_workspace
        ws = get_b_workspace("bw_intake001")
        assert any(r.supplier_id == "sup_persist" for r in ws.supplier_responses)
