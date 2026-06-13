"""
Tests for B-side workspace persistence (JSON file store).
"""
import json
import uuid
from pathlib import Path

import pytest
from src.b_side.workspace import (
    create_b_workspace,
    get_b_workspace,
    save_b_workspace,
    update_b_workspace_status,
    _workspace_path,
)
from src.core_schema.b_side_types import BWWorkspace, BuyerRequirement, SupplierResponseRecord


@pytest.fixture(autouse=True)
def patch_data_dir(tmp_path, monkeypatch):
    import src.b_side.workspace as ws_mod
    monkeypatch.setattr(ws_mod, "_DATA_DIR", tmp_path / "bw")


class TestCreateBWorkspace:
    def test_creates_workspace(self):
        ws = create_b_workspace("100 pcs aluminum bracket")
        assert ws.b_workspace_id.startswith("bw_")
        assert ws.raw_requirement == "100 pcs aluminum bracket"

    def test_status_is_created(self):
        ws = create_b_workspace("test requirement")
        assert ws.status == "created"

    def test_rfq_id_assigned(self):
        ws = create_b_workspace("100 pcs cotton shirt")
        assert ws.rfq_id.startswith("RFQ-") or len(ws.rfq_id) > 0

    def test_workspace_id_unique(self):
        ws1 = create_b_workspace("req1")
        ws2 = create_b_workspace("req2")
        assert ws1.b_workspace_id != ws2.b_workspace_id

    def test_persisted_to_disk(self, tmp_path):
        ws = create_b_workspace("test req")
        import src.b_side.workspace as ws_mod
        path = ws_mod._DATA_DIR / f"{ws.b_workspace_id}.json"
        assert path.exists()


class TestGetBWorkspace:
    def test_round_trip(self):
        ws = create_b_workspace("round trip test")
        loaded = get_b_workspace(ws.b_workspace_id)
        assert loaded.b_workspace_id == ws.b_workspace_id
        assert loaded.raw_requirement == "round trip test"

    def test_raises_on_missing(self):
        with pytest.raises(FileNotFoundError):
            get_b_workspace("bw_nonexistent_xyz")

    def test_status_preserved(self):
        ws = create_b_workspace("status test")
        ws.status = "inquiry_drafted"
        save_b_workspace(ws)
        loaded = get_b_workspace(ws.b_workspace_id)
        assert loaded.status == "inquiry_drafted"

    def test_requirement_preserved(self):
        ws = create_b_workspace("req preserved test")
        req = BuyerRequirement(
            rfq_id="RFQ-TEST",
            b_workspace_id=ws.b_workspace_id,
            raw_text="req text",
            quantity=100,
        )
        ws.buyer_requirement = req
        save_b_workspace(ws)
        loaded = get_b_workspace(ws.b_workspace_id)
        assert loaded.buyer_requirement is not None
        assert loaded.buyer_requirement.quantity == 100

    def test_supplier_responses_preserved(self):
        ws = create_b_workspace("resp preserved test")
        resp = SupplierResponseRecord(
            response_id="RSP-001",
            rfq_id="RFQ-001",
            b_workspace_id=ws.b_workspace_id,
            supplier_id="sup_001",
            supplier_name="Test Supplier",
            can_make=True,
        )
        ws.supplier_responses = [resp]
        save_b_workspace(ws)
        loaded = get_b_workspace(ws.b_workspace_id)
        assert len(loaded.supplier_responses) == 1
        assert loaded.supplier_responses[0].supplier_id == "sup_001"


class TestSaveBWorkspace:
    def test_overwrites_existing(self):
        ws = create_b_workspace("overwrite test")
        ws.status = "collecting_responses"
        save_b_workspace(ws)
        ws.status = "feasibility_complete"
        save_b_workspace(ws)
        loaded = get_b_workspace(ws.b_workspace_id)
        assert loaded.status == "feasibility_complete"

    def test_returns_workspace(self):
        ws = create_b_workspace("returns test")
        result = save_b_workspace(ws)
        assert result.b_workspace_id == ws.b_workspace_id

    def test_json_file_valid(self, tmp_path):
        import src.b_side.workspace as ws_mod
        ws = create_b_workspace("json valid test")
        path = ws_mod._DATA_DIR / f"{ws.b_workspace_id}.json"
        data = json.loads(path.read_text())
        assert "b_workspace_id" in data


class TestUpdateBWorkspaceStatus:
    def test_status_updated(self):
        ws = create_b_workspace("status update test")
        updated = update_b_workspace_status(ws.b_workspace_id, "inquiry_drafted")
        assert updated.status == "inquiry_drafted"

    def test_update_persisted(self):
        ws = create_b_workspace("status persist test")
        update_b_workspace_status(ws.b_workspace_id, "collecting_responses")
        loaded = get_b_workspace(ws.b_workspace_id)
        assert loaded.status == "collecting_responses"

    def test_raises_on_missing_workspace(self):
        with pytest.raises(FileNotFoundError):
            update_b_workspace_status("bw_nonexistent_99", "created")
