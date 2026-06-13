"""
Tests for logistics models and persistence.
"""
import uuid
import pytest
from src.logistics.logistics_models import (
    LogisticsShipment,
    LogisticsEvent,
    save_shipment,
    get_shipment,
    save_event,
    get_events_for_shipment,
    get_shipments_for_project,
)


@pytest.fixture(autouse=True)
def patch_logistics_dirs(tmp_path, monkeypatch):
    import src.logistics.logistics_models as lm_mod
    monkeypatch.setattr(lm_mod, "_SHIPMENT_DIR", tmp_path / "shipments")
    monkeypatch.setattr(lm_mod, "_EVENTS_DIR", tmp_path / "events")


def _make_shipment(shipment_id=None, project_id="PROJ-LOG01"):
    return LogisticsShipment(
        shipment_id=shipment_id or f"SHIP-{uuid.uuid4().hex[:6].upper()}",
        project_id=project_id,
        order_id="ORD-LOG01",
        tracking_number="SF1234567890",
        current_status="in_transit",
    )


def _make_event(event_id=None, shipment_id="SHIP-001", project_id="PROJ-LOG01"):
    return LogisticsEvent(
        logistics_event_id=event_id or f"LOGE-{uuid.uuid4().hex[:6].upper()}",
        shipment_id=shipment_id,
        project_id=project_id,
        tracking_number="SF1234567890",
        event_time="2026-06-13T10:00:00Z",
        status="in_transit",
        normalized_status="in_transit",
        source="mock",
        event_hash=uuid.uuid4().hex,
    )


class TestLogisticsShipment:
    def test_creation(self):
        s = _make_shipment("SHIP-001")
        assert s.shipment_id == "SHIP-001"

    def test_default_status_unknown(self):
        s = LogisticsShipment(
            shipment_id="SHIP-001",
            project_id="PROJ-001",
            tracking_number="SF123",
        )
        assert s.current_status == "unknown"

    def test_in_transit_status(self):
        s = _make_shipment("SHIP-002")
        assert s.current_status == "in_transit"

    def test_delivery_dates_optional(self):
        s = LogisticsShipment(
            shipment_id="SHIP-003", project_id="PROJ-001", tracking_number="SF123",
        )
        assert s.estimated_delivery_date is None
        assert s.actual_delivery_date is None

    def test_project_id_preserved(self):
        s = _make_shipment("SHIP-004", project_id="PROJ-SPECIFIC")
        assert s.project_id == "PROJ-SPECIFIC"


class TestSaveAndGetShipment:
    def test_round_trip(self):
        s = _make_shipment("SHIP-RT01")
        save_shipment(s)
        loaded = get_shipment("SHIP-RT01")
        assert loaded.shipment_id == "SHIP-RT01"

    def test_raises_on_missing(self):
        with pytest.raises(FileNotFoundError):
            get_shipment("SHIP-NONEXISTENT")

    def test_tracking_number_preserved(self):
        s = _make_shipment("SHIP-TN01")
        save_shipment(s)
        loaded = get_shipment("SHIP-TN01")
        assert loaded.tracking_number == "SF1234567890"

    def test_status_preserved(self):
        s = _make_shipment("SHIP-STS01")
        save_shipment(s)
        loaded = get_shipment("SHIP-STS01")
        assert loaded.current_status == "in_transit"

    def test_overwrite_updates(self):
        s = _make_shipment("SHIP-OW01")
        save_shipment(s)
        s.current_status = "delivered"
        save_shipment(s)
        loaded = get_shipment("SHIP-OW01")
        assert loaded.current_status == "delivered"


class TestLogisticsEvent:
    def test_creation(self):
        e = _make_event("EVT-001")
        assert e.logistics_event_id == "EVT-001"

    def test_source_api(self):
        e = _make_event()
        e.source = "api"
        assert e.source == "api"

    def test_not_duplicate_by_default(self):
        e = _make_event()
        assert e.is_duplicate is False

    def test_normalized_status_set(self):
        e = _make_event()
        assert e.normalized_status == "in_transit"


class TestSaveAndGetEvents:
    def test_save_and_retrieve(self):
        e = _make_event("LOGE-RT01", "SHIP-EV01")
        save_event(e)
        events = get_events_for_shipment("SHIP-EV01")
        assert len(events) == 1

    def test_multiple_events(self):
        for i in range(3):
            e = _make_event(f"LOGE-M0{i}X", "SHIP-ME01")
            save_event(e)
        events = get_events_for_shipment("SHIP-ME01")
        assert len(events) == 3

    def test_empty_for_unknown_shipment(self):
        events = get_events_for_shipment("SHIP-UNKNOWN")
        assert events == []

    def test_event_data_preserved(self):
        e = _make_event("LOGE-DP01", "SHIP-DP01")
        save_event(e)
        events = get_events_for_shipment("SHIP-DP01")
        assert events[0].logistics_event_id == "LOGE-DP01"


class TestGetShipmentsForProject:
    def test_empty_for_unknown_project(self):
        result = get_shipments_for_project("PROJ-UNKNOWN")
        assert result == []

    def test_finds_project_shipments(self):
        s = _make_shipment("SHIP-PJ01", project_id="PROJ-SPECIFIC")
        save_shipment(s)
        result = get_shipments_for_project("PROJ-SPECIFIC")
        assert len(result) == 1

    def test_multiple_shipments_for_project(self):
        for i in range(2):
            s = _make_shipment(f"SHIP-PJ{i:02d}", project_id="PROJ-MULTI")
            save_shipment(s)
        result = get_shipments_for_project("PROJ-MULTI")
        assert len(result) == 2

    def test_returns_correct_project_only(self):
        save_shipment(_make_shipment("SHIP-PA01", project_id="PROJ-A"))
        save_shipment(_make_shipment("SHIP-PB01", project_id="PROJ-B"))
        result = get_shipments_for_project("PROJ-A")
        assert all(s.project_id == "PROJ-A" for s in result)
