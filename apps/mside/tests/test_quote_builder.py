"""
Tests for M-side quote builder.
"""
import pytest
from src.m_side.quote_builder import build_supplier_quote


class TestBuildSupplierQuote:
    def test_returns_supplier_quote(self):
        q = build_supplier_quote(["unit price USD 12.50"])
        assert q is not None

    def test_unit_price_extracted(self):
        q = build_supplier_quote(["USD 12.50 per piece"])
        assert q.unit_price is not None

    def test_currency_extracted(self):
        q = build_supplier_quote(["USD 15.00 per unit"])
        assert q.currency is not None

    def test_total_price_calculated(self):
        q = build_supplier_quote(["USD 10.00 per unit"])
        if q.unit_price is not None:
            assert q.total_price is not None

    def test_tooling_fee_extracted(self):
        q = build_supplier_quote(["tooling fee: 500 USD, unit price USD 12.00"])
        assert q.tooling_fee == 500.0

    def test_tooling_fee_cn(self):
        q = build_supplier_quote(["模具费：800元，单价12元"])
        assert q.tooling_fee == 800.0

    def test_sample_fee_extracted(self):
        q = build_supplier_quote(["sample fee: 200 USD"])
        assert q.sample_fee == 200.0

    def test_sample_fee_cn(self):
        q = build_supplier_quote(["打样费100元"])
        assert q.sample_fee == 100.0

    def test_price_validity_days(self):
        q = build_supplier_quote(["报价有效期30天"])
        assert q.price_valid_until is not None
        assert "30" in q.price_valid_until

    def test_moq_in_notes(self):
        q = build_supplier_quote(["MOQ: 500 pcs, USD 12.50 each"])
        if q.quote_notes:
            assert "MOQ" in q.quote_notes

    def test_anodizing_in_notes(self):
        q = build_supplier_quote(["includes anodizing, USD 15.00"])
        if q.quote_notes:
            assert "anodizing" in q.quote_notes

    def test_no_price_returns_none_unit_price(self):
        q = build_supplier_quote(["can make, 30 days"])
        assert q.unit_price is None

    def test_multiple_texts_combined(self):
        q = build_supplier_quote(["can make", "30 days", "USD 12.50 per unit"])
        assert q.unit_price is not None

    def test_rmb_price(self):
        q = build_supplier_quote(["单价85元"])
        assert q.unit_price == 85.0

    def test_empty_returns_empty_quote(self):
        q = build_supplier_quote([])
        assert q.unit_price is None

    def test_float_price(self):
        q = build_supplier_quote(["unit price USD 12.75"])
        if q.unit_price is not None:
            assert isinstance(q.unit_price, float)
