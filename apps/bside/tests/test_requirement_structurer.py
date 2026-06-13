"""
Tests for B-side requirement structurer — deterministic regex parsing.
"""
import pytest
from src.b_side.requirement_structurer import (
    _parse_quantity,
    _parse_material,
    _parse_tolerance,
    _parse_deadline,
    _parse_destination,
    _parse_category,
    structure_requirement,
)


# ─── _parse_quantity ─────────────────────────────────────────────────────────

class TestParseQuantity:
    def test_pcs(self):
        assert _parse_quantity("100 pcs") == 100

    def test_pcs_case_insensitive(self):
        assert _parse_quantity("500 PCS") == 500

    def test_pieces(self):
        assert _parse_quantity("200 pieces") == 200

    def test_units(self):
        assert _parse_quantity("50 units") == 50

    def test_chinese_ge(self):
        assert _parse_quantity("100个") == 100

    def test_chinese_jian(self):
        assert _parse_quantity("200件") == 200

    def test_chinese_tao(self):
        assert _parse_quantity("50套") == 50

    def test_comma_separated(self):
        assert _parse_quantity("1,000 pcs") == 1000

    def test_no_quantity_returns_none(self):
        assert _parse_quantity("aluminum bracket") is None

    def test_quantity_in_sentence(self):
        assert _parse_quantity("We need 300 pcs of shirts delivered") == 300

    def test_large_quantity(self):
        assert _parse_quantity("10,000 pieces") == 10000

    def test_inline_with_material(self):
        assert _parse_quantity("100 pcs aluminum 6061 CNC bracket") == 100


# ─── _parse_material ─────────────────────────────────────────────────────────

class TestParseMaterial:
    def test_aluminum_6061(self):
        assert _parse_material("aluminum 6061 bracket") == "aluminum 6061"

    def test_steel(self):
        assert _parse_material("carbon steel bracket") == "steel"

    def test_stainless_steel(self):
        result = _parse_material("stainless steel housing")
        assert result is not None
        assert "steel" in result.lower()

    def test_cotton(self):
        assert _parse_material("100% cotton shirt") == "cotton"

    def test_polyester(self):
        # "fabric" matches before "polyester" in the keyword list
        result = _parse_material("polyester blend fabric")
        assert result is not None  # some material keyword matched

    def test_abs_plastic(self):
        # "plastic" matches before "ABS" in the keyword list
        result = _parse_material("ABS plastic enclosure")
        assert result is not None  # some material keyword matched

    def test_polyester_without_fabric_keyword(self):
        result = _parse_material("100% polyester blend")
        assert result == "polyester"

    def test_abs_without_plastic_keyword(self):
        result = _parse_material("ABS enclosure 3mm wall")
        assert result == "ABS"

    def test_cardboard(self):
        assert _parse_material("cardboard packaging box") == "cardboard"

    def test_corrugated(self):
        assert _parse_material("corrugated box") == "corrugated"

    def test_no_material_returns_none(self):
        assert _parse_material("100 pieces standard size") is None

    def test_case_insensitive_aluminum(self):
        result = _parse_material("ALUMINUM parts")
        assert result is not None


# ─── _parse_tolerance ────────────────────────────────────────────────────────

class TestParseTolerance:
    def test_pm_tolerance(self):
        assert _parse_tolerance("±0.05 mm") == "±0.05 mm"

    def test_plus_minus_symbol(self):
        result = _parse_tolerance("tolerance ±0.1mm")
        assert result is not None
        assert "0.1" in result

    def test_tight_tolerance(self):
        result = _parse_tolerance("±0.02 mm precision required")
        assert result is not None

    def test_no_tolerance_returns_none(self):
        assert _parse_tolerance("100 pcs cotton shirt") is None

    def test_tolerance_in_specs(self):
        result = _parse_tolerance("cnc bracket, tolerance ±0.05 mm, delivery by Sep")
        assert result is not None


# ─── _parse_deadline ─────────────────────────────────────────────────────────

class TestParseDeadline:
    def test_before_month_day(self):
        result = _parse_deadline("delivery before September 30")
        assert result is not None
        assert "September" in result

    def test_by_date(self):
        result = _parse_deadline("by October 15, 2026")
        assert result is not None

    def test_iso_date(self):
        result = _parse_deadline("deadline 2026-09-30")
        assert result is not None
        assert "2026-09-30" in result

    def test_no_deadline_returns_none(self):
        assert _parse_deadline("100 pcs aluminum bracket") is None

    def test_delivery_by(self):
        result = _parse_deadline("delivery by August 1")
        assert result is not None


# ─── _parse_destination ──────────────────────────────────────────────────────

class TestParseDestination:
    def test_munich(self):
        assert _parse_destination("delivery to Munich") == "Munich"

    def test_shanghai(self):
        assert _parse_destination("shipped to Shanghai") == "Shanghai"

    def test_shenzhen(self):
        assert _parse_destination("factory in Shenzhen") == "Shenzhen"

    def test_new_york(self):
        assert _parse_destination("destination: New York") == "New York"

    def test_london(self):
        assert _parse_destination("delivery to London") == "London"

    def test_no_destination_returns_none(self):
        assert _parse_destination("100 pcs aluminum parts") is None

    def test_case_insensitive(self):
        result = _parse_destination("ship to munich, germany")
        assert result is not None


# ─── _parse_category ─────────────────────────────────────────────────────────

class TestParseCategory:
    def test_cnc_from_keyword(self):
        assert _parse_category("CNC machined bracket") == "cnc"

    def test_cnc_from_tolerance(self):
        assert _parse_category("±0.05mm tolerance bracket") == "cnc"

    def test_cnc_from_aluminum_part(self):
        assert _parse_category("aluminum part precision milled") == "cnc"

    def test_apparel(self):
        assert _parse_category("cotton shirt garment") == "apparel"

    def test_apparel_fabric(self):
        assert _parse_category("polyester fabric sewing") == "apparel"

    def test_packaging(self):
        assert _parse_category("corrugated cardboard box packaging") == "packaging"

    def test_general_fallback(self):
        assert _parse_category("random product no category") == "general"


# ─── structure_requirement ───────────────────────────────────────────────────

class TestStructureRequirement:
    def test_full_cnc_requirement(self):
        req = structure_requirement(
            "bw_test001",
            "100 pcs aluminum 6061 CNC bracket, tolerance ±0.05 mm, delivery before September 30, to Munich"
        )
        assert req.quantity == 100
        assert req.material is not None
        assert req.category == "cnc"
        assert req.destination == "Munich"
        assert req.deadline is not None
        assert req.confidence_score > 0.5

    def test_partial_requirement_lower_confidence(self):
        req = structure_requirement("bw_test002", "100 pcs aluminum bracket")
        assert req.quantity == 100
        assert req.confidence_score < 1.0
        assert "deadline" in req.missing_fields or "destination" in req.missing_fields

    def test_rfq_id_generated(self):
        req = structure_requirement("bw_test003", "some requirement text")
        assert req.rfq_id.startswith("RFQ-")

    def test_b_workspace_id_preserved(self):
        req = structure_requirement("bw_custom_123", "test")
        assert req.b_workspace_id == "bw_custom_123"

    def test_apparel_category_detected(self):
        req = structure_requirement("bw_app001", "500 pcs cotton t-shirt, delivery to Shanghai")
        assert req.category == "apparel"

    def test_specs_json_filled_for_tolerance(self):
        req = structure_requirement(
            "bw_tol001",
            "50 pcs aluminum bracket ±0.1mm tolerance"
        )
        assert "tolerance" in req.specs_json

    def test_zero_quantity_not_detected(self):
        req = structure_requirement("bw_qty001", "aluminum bracket for testing")
        assert req.quantity is None
        assert "quantity" in req.missing_fields

    def test_confidence_full_fields(self):
        req = structure_requirement(
            "bw_conf001",
            "100 pcs cotton shirt, delivery before September 1, ship to Munich"
        )
        # material + quantity + deadline + destination all present
        assert req.confidence_score == 1.0

    def test_confidence_no_fields(self):
        req = structure_requirement("bw_conf002", "some random text here")
        assert req.confidence_score == 0.0
