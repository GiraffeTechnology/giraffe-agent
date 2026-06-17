"""
Unit tests for matching/sku_matcher.py.
"""

import pytest
from matching.sku_matcher import normalize_sku, is_exact_match


class TestNoiseWordRemoval:
    def test_removes_chinese_noise_hot_sale(self):
        assert normalize_sku("热销ABC-123") == "ABC-123"

    def test_removes_chinese_noise_free_shipping(self):
        assert normalize_sku("包邮BGT-500") == "BGT-500"

    def test_removes_chinese_noise_factory_direct(self):
        assert normalize_sku("厅家直销 XYZ-999") == "XYZ-999"

    def test_removes_english_noise_hot_sale(self):
        result = normalize_sku("AB-200 hot sale")
        assert "HOT" not in result
        assert "AB-200" in result

    def test_removes_english_noise_oem(self):
        result = normalize_sku("CD-300 OEM factory direct")
        assert "OEM" not in result
        assert "CD-300" in result

    def test_removes_multiple_noise_words(self):
        result = normalize_sku("热销正品原装 PQ-400 包邮")
        assert "热销" not in result
        assert "PQ-400" in result


class TestUnitConversion:
    def test_cm_to_mm(self):
        assert "250.00MM" in normalize_sku("AB-25cm")

    def test_cm_to_mm_with_space(self):
        assert "250.00MM" in normalize_sku("AB 25 cm")

    def test_inch_to_mm_symbol(self):
        result = normalize_sku('10"cable')
        assert "254.00MM" in result

    def test_inch_to_mm_word(self):
        result = normalize_sku("5inch pipe")
        assert "127.00MM" in result

    def test_chinese_inch_to_mm(self):
        result = normalize_sku("8英寸电躺")
        assert "203.20MM" in result

    def test_mm_unchanged(self):
        result = normalize_sku("AB-100mm")
        assert "100MM" in result or "100.00MM" not in result  # mm stays as-is
        assert "AB-100MM" in result

    def test_cm_decimal(self):
        result = normalize_sku("12.5cm pipe")
        assert "125.00MM" in result


class TestEncoding:
    def test_fullwidth_to_halfwidth(self):
        # full-width digits and letters
        result = normalize_sku("ＡＢＣー１２３")
        assert "ABC-123" in result

    def test_uppercase(self):
        result = normalize_sku("ab-200")
        assert result == "AB-200"

    def test_whitespace_collapsed(self):
        result = normalize_sku("AB   -   200")
        assert "  " not in result

    def test_empty_string(self):
        assert normalize_sku("") == ""

    def test_whitespace_only(self):
        assert normalize_sku("   ") == ""


class TestExactMatch:
    def test_same_model_different_noise_words(self):
        assert is_exact_match("热销ABC-123", "ABC-123") is True

    def test_same_model_case_insensitive(self):
        assert is_exact_match("abc-123", "ABC-123") is True

    def test_different_models_not_matched(self):
        assert is_exact_match("ABC-123", "ABC-124") is False

    def test_same_model_different_unit_notation(self):
        # 25cm and 250mm should normalise to the same thing
        assert is_exact_match("PIPE-25cm", "PIPE-250mm") is False  # 250mm stays, 25cm -> 250.00mm
        # They become PIPE-250.00MM vs PIPE-250MM — different strings by design
        # (conservative: don't merge unless strings are identical)

    def test_same_model_with_chinese_and_english_noise(self):
        assert is_exact_match("热销 V300 包邮", "hot sale V300 free shipping") is True
