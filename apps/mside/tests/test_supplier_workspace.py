"""
Tests for M-side supplier workspace persistence.
"""
import uuid
import pytest
from src.m_side.supplier_workspace import (
    create_m_workspace,
    get_m_workspace,
    save_m_workspace,
    update_m_workspace_status,
)
from src.core_schema.m_side_types import (
    MSideSupplierProfile, SupplierCapability, SupplierInquiryContext,
)


@pytest.fixture(autouse=True)
def patch_dirs(tmp_path, monkeypatch):
    import src.m_side.supplier_workspace as mw_mod
    import src.m_side.supplier_profile as sp_mod
    monkeypatch.setattr(mw_mod, "_DATA_DIR", tmp_path / "mw")
    monkeypatch.setattr(sp_mod, "_DATA_DIR", tmp_path / "sp")


def _make_context(mw_id, bw_id="bw_001", sup_id="sup_001"):
    return SupplierInquiryContext(
        m_workspace_id=mw_id,
        b_workspace_id=bw_id,
        rfq_id="RFQ-WS01",
        inquiry_id="INQ-WS01",
        supplier_id=sup_id,
        supplier_name="Test Supplier",
        invitation_token="GQ-WS000001",
        inquiry_text_zh="询盘",
        inquiry_text_en="Inquiry",
    )


def _make_profile(sup_id="sup_001"):
    return MSideSupplierProfile(
        supplier_id=sup_id,
        supplier_name="Test Supplier",
        channel="mock",
    )


class TestCreateMWorkspace:
    def test_creates_workspace(self):
        mw_id = f"mw_{uuid.uuid4().hex[:10]}"
        ctx = _make_context(mw_id)
        profile = _make_profile()
        ws = create_m_workspace(ctx, profile)
        assert ws.m_workspace_id == mw_id

    def test_status_is_inquiry_received(self):
        mw_id = f"mw_{uuid.uuid4().hex[:10]}"
        ctx = _make_context(mw_id)
        ws = create_m_workspace(ctx, _make_profile())
        assert ws.status == "inquiry_received"

    def test_supplier_id_preserved(self):
        mw_id = f"mw_{uuid.uuid4().hex[:10]}"
        ctx = _make_context(mw_id, sup_id="sup_specific")
        ws = create_m_workspace(ctx, _make_profile("sup_specific"))
        assert ws.supplier_id == "sup_specific"

    def test_rfq_id_preserved(self):
        mw_id = f"mw_{uuid.uuid4().hex[:10]}"
        ctx = _make_context(mw_id)
        ws = create_m_workspace(ctx, _make_profile())
        assert ws.rfq_id == "RFQ-WS01"

    def test_invitation_token_preserved(self):
        mw_id = f"mw_{uuid.uuid4().hex[:10]}"
        ctx = _make_context(mw_id)
        ws = create_m_workspace(ctx, _make_profile())
        assert ws.invitation_token == "GQ-WS000001"

    def test_persisted_to_disk(self):
        mw_id = f"mw_{uuid.uuid4().hex[:10]}"
        ctx = _make_context(mw_id)
        create_m_workspace(ctx, _make_profile())
        loaded = get_m_workspace(mw_id)
        assert loaded is not None


class TestGetMWorkspace:
    def test_raises_on_missing(self):
        with pytest.raises(FileNotFoundError):
            get_m_workspace("mw_nonexistent_xyz")

    def test_round_trip_status(self):
        mw_id = f"mw_{uuid.uuid4().hex[:10]}"
        ctx = _make_context(mw_id)
        ws = create_m_workspace(ctx, _make_profile())
        ws.status = "response_submitted"
        save_m_workspace(ws)
        loaded = get_m_workspace(mw_id)
        assert loaded.status == "response_submitted"


class TestSaveMWorkspace:
    def test_update_status(self):
        mw_id = f"mw_{uuid.uuid4().hex[:10]}"
        ctx = _make_context(mw_id)
        ws = create_m_workspace(ctx, _make_profile())
        ws.status = "order_acknowledged"
        save_m_workspace(ws)
        loaded = get_m_workspace(mw_id)
        assert loaded.status == "order_acknowledged"

    def test_append_messages(self):
        mw_id = f"mw_{uuid.uuid4().hex[:10]}"
        ctx = _make_context(mw_id)
        ws = create_m_workspace(ctx, _make_profile())
        ws.raw_supplier_messages.append("可以做，30天交货")
        save_m_workspace(ws)
        loaded = get_m_workspace(mw_id)
        assert len(loaded.raw_supplier_messages) == 1


class TestUpdateMWorkspaceStatus:
    def test_status_updated(self):
        mw_id = f"mw_{uuid.uuid4().hex[:10]}"
        ctx = _make_context(mw_id)
        create_m_workspace(ctx, _make_profile())
        updated = update_m_workspace_status(mw_id, "response_submitted")
        assert updated.status == "response_submitted"

    def test_raises_on_missing(self):
        with pytest.raises(FileNotFoundError):
            update_m_workspace_status("mw_nonexistent_999", "response_submitted")
