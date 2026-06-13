"""
Tests for B-side inquiry drafter — bilingual supplier inquiry generation.
"""
import pytest
from src.b_side.inquiry_drafter import (
    _build_en_message,
    _build_zh_message,
    _REQUIRED_FIELDS,
    draft_supplier_inquiry,
)
from src.core_schema.b_side_types import BuyerRequirement, BWWorkspace


# ─── _build_en_message ───────────────────────────────────────────────────────

class TestBuildEnMessage:
    def _req(self, **kwargs):
        defaults = dict(
            rfq_id="RFQ-TEST01",
            b_workspace_id="bw_001",
            raw_text="100 pcs aluminum bracket",
            category="cnc",
            quantity=100,
            material="aluminum 6061",
        )
        defaults.update(kwargs)
        return BuyerRequirement(**defaults)

    def test_contains_rfq_id(self):
        msg = _build_en_message(self._req(), "RFQ-TEST01")
        assert "RFQ-TEST01" in msg

    def test_contains_giraffe_agent_header(self):
        msg = _build_en_message(self._req(), "RFQ-001")
        assert "Giraffe Agent" in msg

    def test_contains_category(self):
        msg = _build_en_message(self._req(category="cnc"), "RFQ-001")
        assert "cnc" in msg

    def test_contains_quantity(self):
        msg = _build_en_message(self._req(quantity=100), "RFQ-001")
        assert "100 pcs" in msg

    def test_contains_material(self):
        msg = _build_en_message(self._req(material="aluminum 6061"), "RFQ-001")
        assert "aluminum 6061" in msg

    def test_contains_deadline_when_present(self):
        msg = _build_en_message(self._req(deadline="September 30"), "RFQ-001")
        assert "September 30" in msg

    def test_contains_destination_when_present(self):
        msg = _build_en_message(self._req(destination="Munich"), "RFQ-001")
        assert "Munich" in msg

    def test_no_deadline_section_when_absent(self):
        msg = _build_en_message(self._req(deadline=None), "RFQ-001")
        assert "Delivery Deadline" not in msg

    def test_contains_reply_instructions(self):
        msg = _build_en_message(self._req(), "RFQ-001")
        assert "Can you produce" in msg

    def test_contains_qc_question(self):
        msg = _build_en_message(self._req(), "RFQ-001")
        assert "QC" in msg

    def test_contains_logistics_question(self):
        msg = _build_en_message(self._req(), "RFQ-001")
        assert "EXW" in msg or "FOB" in msg

    def test_specs_json_included(self):
        msg = _build_en_message(self._req(specs_json={"tolerance": "±0.05mm"}), "RFQ-001")
        assert "±0.05mm" in msg

    def test_raw_text_included(self):
        msg = _build_en_message(self._req(raw_text="custom raw buyer text"), "RFQ-001")
        assert "custom raw buyer text" in msg


# ─── _build_zh_message ───────────────────────────────────────────────────────

class TestBuildZhMessage:
    def _req(self, **kwargs):
        defaults = dict(
            rfq_id="RFQ-ZH01",
            b_workspace_id="bw_001",
            raw_text="100件铝合金支架",
            category="cnc",
            quantity=100,
            material="aluminum 6061",
        )
        defaults.update(kwargs)
        return BuyerRequirement(**defaults)

    def test_contains_chinese_header(self):
        msg = _build_zh_message(self._req(), "RFQ-001")
        assert "供应商询盘" in msg

    def test_contains_rfq_id(self):
        msg = _build_zh_message(self._req(), "RFQ-ZH01")
        assert "RFQ-ZH01" in msg

    def test_contains_quantity_in_jian(self):
        msg = _build_zh_message(self._req(quantity=100), "RFQ-001")
        assert "100 件" in msg

    def test_contains_material(self):
        msg = _build_zh_message(self._req(material="aluminum 6061"), "RFQ-001")
        assert "aluminum 6061" in msg

    def test_contains_zh_instructions(self):
        msg = _build_zh_message(self._req(), "RFQ-001")
        assert "是否可以生产" in msg or "接单" in msg

    def test_contains_qc_zh(self):
        msg = _build_zh_message(self._req(), "RFQ-001")
        assert "QC" in msg

    def test_contains_natural_language_note(self):
        msg = _build_zh_message(self._req(), "RFQ-001")
        assert "自然语言" in msg


# ─── _REQUIRED_FIELDS ────────────────────────────────────────────────────────

class TestRequiredFields:
    def test_can_make_in_required(self):
        assert "can_make" in _REQUIRED_FIELDS

    def test_lead_time_in_required(self):
        assert "lead_time_days" in _REQUIRED_FIELDS

    def test_unit_price_in_required(self):
        assert "unit_price" in _REQUIRED_FIELDS

    def test_qc_in_required(self):
        assert "qc_available" in _REQUIRED_FIELDS

    def test_red_flags_in_required(self):
        assert "red_flags" in _REQUIRED_FIELDS


# ─── draft_supplier_inquiry ──────────────────────────────────────────────────

class TestDraftSupplierInquiry:
    def test_generates_inquiry_with_workspace(self, tmp_path, monkeypatch):
        import src.b_side.workspace as ws_mod
        monkeypatch.setattr(ws_mod, "_DATA_DIR", tmp_path / "bw")

        from src.core_schema.b_side_types import BWWorkspace
        bw_id = "bw_draft_test"
        req = BuyerRequirement(
            rfq_id="RFQ-DRAFT01",
            b_workspace_id=bw_id,
            raw_text="100 pcs cotton shirt",
            category="apparel",
            quantity=100,
        )
        ws = BWWorkspace(b_workspace_id=bw_id, rfq_id="RFQ-DRAFT01",
                         raw_requirement="100 pcs cotton shirt", buyer_requirement=req)
        ws_mod._ensure_dir()
        ws_mod.save_b_workspace(ws)

        draft = draft_supplier_inquiry(bw_id, ["sup_001", "sup_002"])
        assert draft.inquiry_id.startswith("INQ-")
        assert len(draft.supplier_ids) == 2
        assert "Giraffe Agent" in draft.message_text_en
        assert "供应商询盘" in draft.message_text_zh

    def test_raises_when_no_requirement(self, tmp_path, monkeypatch):
        import src.b_side.workspace as ws_mod
        monkeypatch.setattr(ws_mod, "_DATA_DIR", tmp_path / "bw2")

        from src.core_schema.b_side_types import BWWorkspace
        bw_id = "bw_no_req"
        ws = BWWorkspace(b_workspace_id=bw_id, rfq_id="RFQ-X", raw_requirement="test")
        ws_mod._ensure_dir()
        ws_mod.save_b_workspace(ws)

        with pytest.raises(ValueError, match="no structured requirement"):
            draft_supplier_inquiry(bw_id, ["sup_001"])

    def test_required_fields_in_draft(self, tmp_path, monkeypatch):
        import src.b_side.workspace as ws_mod
        monkeypatch.setattr(ws_mod, "_DATA_DIR", tmp_path / "bw3")

        from src.core_schema.b_side_types import BWWorkspace
        bw_id = "bw_req_fields"
        req = BuyerRequirement(
            rfq_id="RFQ-RF01",
            b_workspace_id=bw_id,
            raw_text="50 pcs steel bracket",
        )
        ws = BWWorkspace(b_workspace_id=bw_id, rfq_id="RFQ-RF01",
                         raw_requirement="50 pcs steel bracket", buyer_requirement=req)
        ws_mod._ensure_dir()
        ws_mod.save_b_workspace(ws)

        draft = draft_supplier_inquiry(bw_id, ["sup_a"])
        assert "can_make" in draft.required_fields
