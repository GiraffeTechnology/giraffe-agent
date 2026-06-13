"""
Additional B-side tests covering edge cases and extended scenarios.
"""
import uuid
import json
import pytest
from src.core_schema.b_side_types import (
    BuyerRequirement, BWWorkspace, SupplierResponseRecord,
    DeliveryPath, FeasibilityReport, SupplierInquiryDraft,
)
from src.b_side.requirement_structurer import (
    _parse_quantity, _parse_material, _parse_tolerance,
    _parse_deadline, _parse_destination, _parse_category,
    structure_requirement,
)
from src.b_side.feasibility_engine import _score_response


@pytest.fixture(autouse=True)
def patch_event_logger(tmp_path, monkeypatch):
    import src.m_side.m_event_logger as mel
    monkeypatch.setattr(mel, "_EVENTS_FILE", tmp_path / "events.jsonl")


# ─── Extended Quantity Parsing ────────────────────────────────────────────────

class TestQuantityParsingExtended:
    def test_pcs_with_leading_spaces(self):
        assert _parse_quantity("  100 pcs") == 100

    def test_quantity_in_long_sentence(self):
        assert _parse_quantity("I need 250 units delivered by next month") == 250

    def test_chinese_tao(self):
        assert _parse_quantity("50套设备") == 50

    def test_quantity_with_thousand_separator(self):
        assert _parse_quantity("2,500 pcs") == 2500

    def test_small_quantity(self):
        assert _parse_quantity("1 pcs") == 1

    def test_large_quantity(self):
        assert _parse_quantity("100,000 pieces") == 100000


# ─── Extended Material Parsing ────────────────────────────────────────────────

class TestMaterialParsingExtended:
    def test_pom_plastic(self):
        assert _parse_material("POM gear component") == "POM"

    def test_hdpe_material(self):
        assert _parse_material("HDPE container") == "HDPE"

    def test_nylon_material(self):
        assert _parse_material("nylon thread") == "nylon"

    def test_6061_t6(self):
        result = _parse_material("6061-T6 aluminum")
        assert result is not None

    def test_aluminium_uk_spelling(self):
        result = _parse_material("aluminium alloy bracket")
        assert result is not None


# ─── Extended Deadline Parsing ────────────────────────────────────────────────

class TestDeadlineParsingExtended:
    def test_iso_date_format(self):
        result = _parse_deadline("delivery date: 2026-12-31")
        assert "2026-12-31" in result

    def test_before_month(self):
        result = _parse_deadline("before December 15")
        assert result is not None

    def test_by_specific_date(self):
        result = _parse_deadline("by November 1, 2026")
        assert result is not None


# ─── Extended Destination Parsing ────────────────────────────────────────────

class TestDestinationParsingExtended:
    def test_guangzhou(self):
        assert _parse_destination("shipped from Guangzhou factory") == "Guangzhou"

    def test_beijing(self):
        assert _parse_destination("delivery to Beijing warehouse") == "Beijing"

    def test_singapore(self):
        assert _parse_destination("export to Singapore") == "Singapore"

    def test_hong_kong(self):
        assert _parse_destination("ship to Hong Kong") == "Hong Kong"

    def test_tokyo(self):
        assert _parse_destination("destination: Tokyo") == "Tokyo"


# ─── Extended Category Parsing ───────────────────────────────────────────────

class TestCategoryParsingExtended:
    def test_machined_bracket_is_cnc(self):
        assert _parse_category("machined bracket component") == "cnc"

    def test_milled_is_cnc(self):
        assert _parse_category("CNC milled aluminum housing") == "cnc"

    def test_garment_is_apparel(self):
        assert _parse_category("garment manufacturing") == "apparel"

    def test_t_shirt_is_apparel(self):
        assert _parse_category("t-shirt printing order") == "apparel"

    def test_box_is_packaging(self):
        assert _parse_category("corrugated box manufacturer") == "packaging"


# ─── Extended structure_requirement ──────────────────────────────────────────

class TestStructureRequirementExtended:
    def test_cnc_with_anodizing_in_specs(self):
        req = structure_requirement(
            "bw_ext001",
            "50 pcs aluminum 6061 CNC bracket, black anodized, ±0.05mm"
        )
        assert "surface_finish" in req.specs_json

    def test_three_fields_confidence_075(self):
        req = structure_requirement(
            "bw_ext002",
            "100 pcs aluminum 6061 bracket, delivery before October 15"
        )
        # quantity + material + deadline but no destination = 3/4 = 0.75
        assert req.confidence_score == 0.75

    def test_two_fields_confidence_05(self):
        req = structure_requirement(
            "bw_ext003",
            "100 pcs bracket"  # only quantity
        )
        assert req.confidence_score <= 0.5


# ─── Extended Feasibility Engine ─────────────────────────────────────────────

class TestFeasibilityScoreExtended:
    def _make_response(self, **kwargs):
        defaults = dict(
            response_id="RSP-EXT",
            rfq_id="RFQ-EXT",
            b_workspace_id="bw_ext",
            supplier_id="sup_ext",
            supplier_name="Test",
            confidence_score=0.8,
        )
        defaults.update(kwargs)
        return SupplierResponseRecord(**defaults)

    def test_score_with_short_lead_time(self):
        r = self._make_response(estimated_lead_time_days=7)
        score = _score_response(r)
        assert score > 0.5

    def test_score_with_many_flags(self):
        r = self._make_response(red_flags=["f1", "f2", "f3", "f4", "f5"])
        score = _score_response(r)
        assert score < 0.5

    def test_perfect_score_conditions(self):
        r = self._make_response(
            confidence_score=1.0, estimated_lead_time_days=1, red_flags=[]
        )
        score = _score_response(r)
        assert score > 0.9


# ─── JSON Serialization ──────────────────────────────────────────────────────

class TestJSONSerialization:
    def test_buyer_requirement_json(self):
        req = BuyerRequirement(rfq_id="R1", b_workspace_id="b1", raw_text="test")
        data = req.model_dump(mode="json")
        assert json.dumps(data)  # should not raise

    def test_supplier_response_json(self):
        resp = SupplierResponseRecord(
            response_id="RSP-1", rfq_id="RFQ-1", b_workspace_id="bw_1",
            supplier_id="s1", supplier_name="S1"
        )
        data = resp.model_dump(mode="json")
        assert json.dumps(data)

    def test_delivery_path_json(self):
        path = DeliveryPath(
            path_id="PATH-1", rfq_id="RFQ-1", supplier_id="s1", supplier_name="S1"
        )
        data = path.model_dump(mode="json")
        assert json.dumps(data)
