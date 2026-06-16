"""
Supplier Discovery Tests — AIVAN supplier discovery module.

Tests parsing logic against captured real Alibaba showroom HTML, and the
graceful-fallback contract for unreachable / anti-bot-blocked pages.
"""
import httpx
import pytest

from src.b_side.supplier_discovery import (
    discover_suppliers,
    fetch_showroom_html,
    parse_showroom_cards,
)

SAMPLE_HTML = """
<html><body>
<a data-component="ProductTitle" rel="noreferrer"><h2>Low MOQ custom <strong>cotton</strong> T-shirt</h2></a>
<div data-component="ProductPrice">$3.50-6.20</div>
<div data-component="ProductMoq">MOQ: 2 pieces</div>
<span data-component="ProductSales">5,949 sold</span>
<a href="//wellone.en.alibaba.com/company_profile.html" title="Guangzhou Wellone Garment Co., Ltd." data-component="SupplierNameLink">link</a>
<span>10 yrs</span>
<a data-component="ProductTitle" rel="noreferrer"><h2>HIC Custom Wholesale Cotton T-Shirt</h2></a>
<div data-component="ProductPrice">$3.45-3.90</div>
<div data-component="ProductMoq">MOQ: 3 pieces</div>
<a href="//haixin.en.alibaba.com/company_profile.html" title="Quanzhou Haixin Garment Technology Co., Ltd." data-component="SupplierNameLink">link</a>
<span>6 yrs</span>
</body></html>
"""

ANTI_BOT_HTML = '<html><head><script src="//g.alicdn.com/sd/punish/0.0.1/qrcode.min.js"></script><punish-component /></head></html>'


def test_parse_showroom_cards_extracts_supplier_and_product():
    cards = parse_showroom_cards(SAMPLE_HTML, source_url="https://www.alibaba.com/showroom/cotton-shirt.html")
    assert len(cards) == 2
    assert cards[0].supplier_name == "Guangzhou Wellone Garment Co., Ltd."
    assert cards[0].product_title == "Low MOQ custom cotton T-shirt"
    assert cards[0].moq == "2 pieces"
    assert cards[0].sold_count == "5,949 sold"
    assert cards[0].years_on_platform == 10


def test_parse_showroom_cards_extracts_price_when_present():
    cards = parse_showroom_cards(SAMPLE_HTML, source_url="https://www.alibaba.com/showroom/cotton-shirt.html")
    assert cards[1].supplier_name == "Quanzhou Haixin Garment Technology Co., Ltd."
    assert cards[1].price_range_usd == "3.45-3.90"


def test_parse_showroom_cards_respects_limit():
    cards = parse_showroom_cards(SAMPLE_HTML, source_url="https://example.com", limit=1)
    assert len(cards) == 1


def test_parse_showroom_cards_empty_html_returns_empty_list():
    assert parse_showroom_cards("<html></html>", source_url="https://example.com") == []


def test_fetch_showroom_html_returns_none_on_anti_bot_challenge(monkeypatch):
    class FakeResponse:
        status_code = 200
        text = ANTI_BOT_HTML

    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse())
    assert fetch_showroom_html("https://www.alibaba.com/product-detail/blocked.html") is None


def test_fetch_showroom_html_returns_none_on_non_200(monkeypatch):
    class FakeResponse:
        status_code = 403
        text = "forbidden"

    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse())
    assert fetch_showroom_html("https://www.alibaba.com/showroom/x.html") is None


def test_fetch_showroom_html_returns_none_on_network_error(monkeypatch):
    def raise_timeout(*a, **k):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(httpx, "get", raise_timeout)
    assert fetch_showroom_html("https://www.alibaba.com/showroom/x.html") is None


def test_discover_suppliers_returns_empty_list_when_fetch_fails(monkeypatch):
    monkeypatch.setattr("src.b_side.supplier_discovery.fetch_showroom_html", lambda url: None)
    result = discover_suppliers("https://www.alibaba.com/showroom/x.html")
    assert result == []


def test_discover_suppliers_does_not_raise_on_blocked_page(monkeypatch):
    monkeypatch.setattr("src.b_side.supplier_discovery.fetch_showroom_html", lambda url: None)
    # Should not raise even though the underlying page was an anti-bot wall.
    result = discover_suppliers("https://www.alibaba.com/product-detail/blocked.html")
    assert result == []
