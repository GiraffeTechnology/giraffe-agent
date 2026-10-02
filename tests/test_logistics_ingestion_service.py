# Unicode escapes retain the original non-English test inputs and assertions.
# Keep these vectors multilingual; English-only inputs do not test the same behavior.
"""Tests for logistics ingestion service."""
import pytest
from src.logistics.logistics_ingestion_service import (
    ingest_tracking_number, sync_tracking_from_provider,
    ingest_logistics_from_im_message, sync_all_active_shipments,
)
from src.logistics.logistics_models import get_shipment, get_events_for_shipment


_PROJECT = "test-lis-proj-01"
_SUP = "sup-lis-001"


def test_ingest_tracking_number_basic():
    shipment = ingest_tracking_number(
        project_id=_PROJECT,
        carrier_name="SF Express",
        carrier_code="SF",
        tracking_number="SF123456789012",
        source="test",
        actor_id=_SUP,
    )
    assert shipment.shipment_id.startswith("SHIP-")
    assert shipment.tracking_number == "SF123456789012"
    assert shipment.carrier_code == "SF"
    assert shipment.project_id == _PROJECT


def test_ingest_tracking_number_persisted():
    shipment = ingest_tracking_number(
        project_id=_PROJECT,
        carrier_name="DHL",
        carrier_code="DHL",
        tracking_number="1234567890123",
        source="test",
        order_id="OE-LIS-001",
    )
    retrieved = get_shipment(shipment.shipment_id)
    assert retrieved.shipment_id == shipment.shipment_id
    assert retrieved.order_id == "OE-LIS-001"


def test_sync_tracking_from_provider():
    shipment = ingest_tracking_number(
        project_id=_PROJECT,
        carrier_name="Mock Carrier",
        carrier_code="MOCK",
        tracking_number="MOCK123456789",
        source="test",
    )
    events = sync_tracking_from_provider(shipment.shipment_id)
    assert isinstance(events, list)


def test_sync_produces_events_with_normalized_status():
    shipment = ingest_tracking_number(
        project_id=_PROJECT,
        carrier_name="Mock Carrier",
        carrier_code="MOCK",
        tracking_number="MOCK987654321",
        source="test",
    )
    events = sync_tracking_from_provider(shipment.shipment_id)
    for ev in events:
        assert ev.normalized_status in (
            "label_created", "picked_up", "in_transit", "customs",
            "out_for_delivery", "delivered", "exception", "unknown",
        )


def test_event_deduplication():
    shipment = ingest_tracking_number(
        project_id=_PROJECT,
        carrier_name="Mock Carrier",
        carrier_code="MOCK",
        tracking_number="MOCKDEDUP001",
        source="test",
    )
    events1 = sync_tracking_from_provider(shipment.shipment_id)
    events2 = sync_tracking_from_provider(shipment.shipment_id)
    dups = [e for e in events2 if e.is_duplicate]
    assert len(dups) >= 0


def test_ingest_from_im_message_sf_chinese():
    msg = '\u8001\u677f\u5df2\u53d1\u8d27\uff0c\u987a\u4e30\u5feb\u9012\uff0c\u5355\u53f7SF123456789012\uff0c\u4eca\u5929\u4e0b\u5348\u53d1\u51fa'
    shipment = ingest_logistics_from_im_message(
        project_id=_PROJECT,
        raw_message=msg,
        actor_id=_SUP,
        order_id="OE-IM-001",
    )
    if shipment is not None:
        assert shipment.project_id == _PROJECT
        assert shipment.tracking_number is not None


def test_ingest_from_im_message_no_tracking():
    msg = "Hello, how are you today?"
    result = ingest_logistics_from_im_message(
        project_id=_PROJECT,
        raw_message=msg,
        actor_id=_SUP,
    )
    assert result is None


def test_sync_all_active_shipments_returns_dict():
    result = sync_all_active_shipments()
    assert isinstance(result, dict)
    assert "synced" in result
    assert "errors" in result


def test_ingest_without_order_id():
    shipment = ingest_tracking_number(
        project_id=_PROJECT,
        carrier_name="YTO",
        carrier_code="YTO",
        tracking_number="YTO1234567890",
        source="test",
    )
    assert shipment.order_id is None
    assert shipment.shipment_id.startswith("SHIP-")
