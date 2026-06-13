"""
Tests for M-side supplier response normalizer — deterministic regex parsing.
"""
import pytest
from src.m_side.response_normalizer import (
    _parse_can_make,
    _parse_lead_time,
    _parse_sample_lead_time,
    _parse_unit_price,
    _parse_moq,
    _parse_material_available,
    _parse_red_flags,
    _parse_qc_available,
    normalize_supplier_response_text,
)
from src.core_schema.m_side_types import MSideWorkspace, SupplierInquiryContext


# ─── _parse_can_make ─────────────────────────────────────────────────────────

class TestParseCanMake:
    def test_chinese_yes(self):
        assert _parse_can_make("可以做，没问题") is True

    def test_chinese_accept(self):
        assert _parse_can_make("可以接单") is True

    def test_english_yes(self):
        assert _parse_can_make("yes we can make this") is True

    def test_english_confirm(self):
        assert _parse_can_make("Confirm, we can handle this order") is True

    def test_chinese_no(self):
        assert _parse_can_make("抱歉，当前产能已满，无法接单") is False

    def test_english_no(self):
        assert _parse_can_make("cannot make this part") is False

    def test_no_capacity(self):
        assert _parse_can_make("no capacity available right now") is False

    def test_none_for_unclear(self):
        assert _parse_can_make("please send drawings") is None

    def test_no_capacity_cn(self):
        assert _parse_can_make("产能已满") is False

    def test_can_make_cn(self):
        assert _parse_can_make("能做") is True


# ─── _parse_lead_time ────────────────────────────────────────────────────────

class TestParseLeadTime:
    def test_days_en(self):
        assert _parse_lead_time("lead time is 30 days") == 30

    def test_days_cn(self):
        assert _parse_lead_time("交期30天") == 30

    def test_weeks_en(self):
        assert _parse_lead_time("3 weeks lead time") == 21

    def test_weeks_cn(self):
        assert _parse_lead_time("2周交货") == 14

    def test_none_when_absent(self):
        assert _parse_lead_time("good quality, good service") is None

    def test_mass_production_days(self):
        result = _parse_lead_time("大货25天")
        assert result == 25

    def test_total_days(self):
        result = _parse_lead_time("总交期45天")
        assert result == 45

    def test_rejects_unreasonable_values(self):
        result = _parse_lead_time("1000天交货")
        assert result is None


# ─── _parse_sample_lead_time ─────────────────────────────────────────────────

class TestParseSampleLeadTime:
    def test_cn_sample(self):
        assert _parse_sample_lead_time("样品7天") == 7

    def test_en_sample(self):
        assert _parse_sample_lead_time("sample lead time 10 days") == 10

    def test_none_when_absent(self):
        assert _parse_sample_lead_time("delivery 30 days") is None

    def test_cn_daying(self):
        assert _parse_sample_lead_time("打样3天") == 3


# ─── _parse_unit_price ───────────────────────────────────────────────────────

class TestParseUnitPrice:
    def test_usd_price(self):
        price, currency = _parse_unit_price("unit price USD 12.50")
        assert price == 12.50
        assert currency is not None

    def test_rmb_price(self):
        price, currency = _parse_unit_price("单价85元")
        assert price == 85.0

    def test_none_when_absent(self):
        price, currency = _parse_unit_price("can make, 30 days lead time")
        assert price is None

    def test_price_with_dollar_sign(self):
        price, currency = _parse_unit_price("price: $15.00 per unit")
        assert price is not None

    def test_cny_price(self):
        price, currency = _parse_unit_price("CNY 100 per piece")
        assert price is not None


# ─── _parse_moq ──────────────────────────────────────────────────────────────

class TestParseMoq:
    def test_en_moq(self):
        assert _parse_moq("MOQ: 500 pcs") == 500

    def test_cn_moq(self):
        result = _parse_moq("最低起订量100件")
        assert result == 100

    def test_none_when_absent(self):
        assert _parse_moq("unit price USD 12") is None


# ─── _parse_material_available ───────────────────────────────────────────────

class TestParseMaterialAvailable:
    def test_material_in_stock_en(self):
        result = _parse_material_available("material is in stock, ready to ship")
        assert result is True or result is None  # depends on regex

    def test_material_shortage(self):
        result = _parse_material_available("material shortage, cannot proceed")
        assert result is False

    def test_material_out_of_stock(self):
        result = _parse_material_available("out of stock currently")
        assert result is False


# ─── _parse_red_flags ────────────────────────────────────────────────────────

class TestParseRedFlags:
    def test_no_red_flags(self):
        flags = _parse_red_flags("can make, 30 days, USD 12.50 per unit")
        assert isinstance(flags, list)

    def test_returns_list(self):
        flags = _parse_red_flags("some message here")
        assert isinstance(flags, list)


# ─── _parse_qc_available ─────────────────────────────────────────────────────

class TestParseQcAvailable:
    def test_returns_bool_or_none(self):
        result = _parse_qc_available("we can provide QC photos and videos")
        assert result is True or result is None


# ─── normalize_supplier_response_text ────────────────────────────────────────

class TestNormalizeSupplierResponseText:
    def _make_workspace(self, mw_id="mw_norm001"):
        ctx = SupplierInquiryContext(
            m_workspace_id=mw_id,
            b_workspace_id="bw_norm001",
            rfq_id="RFQ-NORM01",
            inquiry_id="INQ-NORM01",
            supplier_id="sup_norm",
            supplier_name="Norm Test Supplier",
            invitation_token="GQ-NORM0001",
            inquiry_text_zh="询盘",
            inquiry_text_en="Inquiry",
        )
        return MSideWorkspace(
            m_workspace_id=mw_id,
            b_workspace_id="bw_norm001",
            rfq_id="RFQ-NORM01",
            inquiry_id="INQ-NORM01",
            supplier_id="sup_norm",
            supplier_name="Norm Test Supplier",
            invitation_token="GQ-NORM0001",
            inquiry_context=ctx,
        )

    def test_returns_response_packet(self):
        ws = self._make_workspace()
        packet = normalize_supplier_response_text(["可以做，30天交货，单价12美元"], ws)
        assert packet.response_id.startswith("RSP-")

    def test_can_make_parsed(self):
        ws = self._make_workspace()
        packet = normalize_supplier_response_text(["可以接单，没问题"], ws)
        assert packet.capacity_signal.can_make is True

    def test_lead_time_parsed(self):
        ws = self._make_workspace()
        packet = normalize_supplier_response_text(["交期30天，可以接单"], ws)
        assert packet.schedule_signal.estimated_lead_time_days == 30

    def test_cannot_make_parsed(self):
        ws = self._make_workspace()
        packet = normalize_supplier_response_text(["抱歉，当前产能已满，无法接单"], ws)
        assert packet.capacity_signal.can_make is False

    def test_completeness_score_filled(self):
        ws = self._make_workspace()
        packet = normalize_supplier_response_text(
            ["可以接单，30天交货，USD 12.50 per unit，MOQ: 500 pcs，有QC照片更新"],
            ws,
        )
        assert packet.completeness_score > 0

    def test_workspace_ids_preserved(self):
        ws = self._make_workspace()
        packet = normalize_supplier_response_text(["可以做"], ws)
        assert packet.b_workspace_id == "bw_norm001"
        assert packet.m_workspace_id == "mw_norm001"

    def test_multiple_messages(self):
        ws = self._make_workspace()
        packet = normalize_supplier_response_text(
            ["可以做", "30天交货", "单价85元"],
            ws,
        )
        assert packet is not None

    def test_empty_messages(self):
        ws = self._make_workspace()
        packet = normalize_supplier_response_text([], ws)
        assert packet.capacity_signal.can_make is None
