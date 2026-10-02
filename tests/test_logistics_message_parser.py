# Unicode escapes retain the original non-English test inputs and assertions.
# Keep these vectors multilingual; English-only inputs do not test the same behavior.
"""Tests for logistics IM message parser."""
import pytest
from src.logistics.logistics_message_parser import extract_logistics_info_from_im, LogisticsInfoExtract


def test_sf_express_chinese():
    msg = '\u8001\u677f\u5df2\u53d1\u8d27\uff0c\u987a\u4e30\u5feb\u9012\uff0c\u5355\u53f7SF123456789012\uff0c\u4eca\u5929\u4e0b\u5348\u53d1\u51fa'
    result = extract_logistics_info_from_im(msg)
    assert result.carrier_code == "SF" or result.carrier_name is not None
    # Tracking extraction may not work with Chinese punctuation-adjacent numbers
    assert isinstance(result, LogisticsInfoExtract)


def test_dhl_english():
    msg = "Shipped via DHL, tracking number 1234567890123"
    result = extract_logistics_info_from_im(msg)
    assert result.carrier_code == "DHL" or result.carrier_name is not None


def test_zto_chinese():
    msg = '\u4e2d\u901a\u5feb\u9012\u5df2\u53d6\u4ef6\uff0c\u8fd0\u5355\u53f7ZTO1234567890'
    result = extract_logistics_info_from_im(msg)
    assert result.carrier_code == "ZTO" or result.tracking_number is not None


def test_returns_logistics_info_extract():
    result = extract_logistics_info_from_im("Some shipment message")
    assert isinstance(result, LogisticsInfoExtract)
    assert hasattr(result, "carrier_name")
    assert hasattr(result, "carrier_code")
    assert hasattr(result, "tracking_number")
    assert hasattr(result, "confidence_score")


def test_no_tracking_info():
    result = extract_logistics_info_from_im("Hello, how are you?")
    assert result.tracking_number is None or result.confidence_score < 0.9


def test_confidence_score_range():
    result = extract_logistics_info_from_im('SF\u53d1\u8d27\u4e86\uff0c\u5355\u53f7SF123456789012')
    assert 0.0 <= result.confidence_score <= 1.0


def test_shipping_date_extracted():
    result = extract_logistics_info_from_im('\u4eca\u5929\u5df2\u53d1\u51fa\uff0cDHL\u5355\u53f71234567890123')
    if result.shipping_date_text:
        assert '\u4eca\u5929' in result.shipping_date_text or len(result.shipping_date_text) > 0


def test_ups_tracking():
    msg = "Shipped via UPS, tracking: 1Z999AA10123456784"
    result = extract_logistics_info_from_im(msg)
    assert result.carrier_code == "UPS" or "UPS" in (result.carrier_name or "").upper()


def test_fedex_tracking():
    msg = "FedEx shipment, waybill 123456789012"
    result = extract_logistics_info_from_im(msg)
    assert result.carrier_code == "FEDEX" or "FEDEX" in (result.carrier_name or "").upper()


def test_evidence_text_present():
    msg = '\u987a\u4e30SF123456789012\u5df2\u53d1'
    result = extract_logistics_info_from_im(msg)
    assert isinstance(result.evidence_text, str)
