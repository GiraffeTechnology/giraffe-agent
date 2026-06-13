"""
Tests for M-side Industrial Execution Graph event logger.
"""
import json
import pytest
from src.m_side.m_event_logger import log_m_event, read_events


class TestLogMEvent:
    def test_log_creates_file(self, tmp_path, monkeypatch):
        import src.m_side.m_event_logger as mel
        events_file = tmp_path / "events.jsonl"
        monkeypatch.setattr(mel, "_EVENTS_FILE", events_file)

        log_m_event("TEST_EVENT", b_workspace_id="bw_001")
        assert events_file.exists()

    def test_log_writes_json_line(self, tmp_path, monkeypatch):
        import src.m_side.m_event_logger as mel
        events_file = tmp_path / "events.jsonl"
        monkeypatch.setattr(mel, "_EVENTS_FILE", events_file)

        log_m_event("TEST_EVENT", b_workspace_id="bw_001")
        lines = events_file.read_text().strip().splitlines()
        assert len(lines) == 1
        evt = json.loads(lines[0])
        assert evt["event_type"] == "TEST_EVENT"

    def test_log_includes_event_id(self, tmp_path, monkeypatch):
        import src.m_side.m_event_logger as mel
        events_file = tmp_path / "events.jsonl"
        monkeypatch.setattr(mel, "_EVENTS_FILE", events_file)

        log_m_event("TEST_EVENT")
        evt = json.loads(events_file.read_text().strip())
        assert "event_id" in evt
        assert evt["event_id"].startswith("EVT-")

    def test_multiple_events_appended(self, tmp_path, monkeypatch):
        import src.m_side.m_event_logger as mel
        events_file = tmp_path / "events.jsonl"
        monkeypatch.setattr(mel, "_EVENTS_FILE", events_file)

        log_m_event("EVENT_A")
        log_m_event("EVENT_B")
        log_m_event("EVENT_C")
        lines = events_file.read_text().strip().splitlines()
        assert len(lines) == 3

    def test_payload_stored(self, tmp_path, monkeypatch):
        import src.m_side.m_event_logger as mel
        events_file = tmp_path / "events.jsonl"
        monkeypatch.setattr(mel, "_EVENTS_FILE", events_file)

        log_m_event("TEST_EVENT", payload={"key": "value", "count": 42})
        evt = json.loads(events_file.read_text().strip())
        assert evt["payload"]["key"] == "value"
        assert evt["payload"]["count"] == 42

    def test_all_ids_stored(self, tmp_path, monkeypatch):
        import src.m_side.m_event_logger as mel
        events_file = tmp_path / "events.jsonl"
        monkeypatch.setattr(mel, "_EVENTS_FILE", events_file)

        log_m_event(
            "TEST_EVENT",
            m_workspace_id="mw_001",
            b_workspace_id="bw_001",
            supplier_id="sup_001",
            rfq_id="RFQ-001",
            order_execution_id="ORD-001",
        )
        evt = json.loads(events_file.read_text().strip())
        assert evt["m_workspace_id"] == "mw_001"
        assert evt["supplier_id"] == "sup_001"


class TestReadEvents:
    def _setup(self, tmp_path, monkeypatch):
        import src.m_side.m_event_logger as mel
        events_file = tmp_path / "events.jsonl"
        monkeypatch.setattr(mel, "_EVENTS_FILE", events_file)

    def test_empty_file_returns_empty(self, tmp_path, monkeypatch):
        self._setup(tmp_path, monkeypatch)
        events = read_events()
        assert events == []

    def test_returns_all_events(self, tmp_path, monkeypatch):
        self._setup(tmp_path, monkeypatch)
        log_m_event("EVT_A", b_workspace_id="bw_001")
        log_m_event("EVT_B", b_workspace_id="bw_002")
        events = read_events()
        assert len(events) == 2

    def test_filter_by_event_type(self, tmp_path, monkeypatch):
        self._setup(tmp_path, monkeypatch)
        log_m_event("EVT_A", b_workspace_id="bw_001")
        log_m_event("EVT_B", b_workspace_id="bw_001")
        events = read_events(event_type="EVT_A")
        assert len(events) == 1
        assert events[0]["event_type"] == "EVT_A"

    def test_filter_by_workspace(self, tmp_path, monkeypatch):
        self._setup(tmp_path, monkeypatch)
        log_m_event("EVT_A", b_workspace_id="bw_001")
        log_m_event("EVT_A", b_workspace_id="bw_002")
        events = read_events(b_workspace_id="bw_001")
        assert len(events) == 1

    def test_filter_by_m_workspace(self, tmp_path, monkeypatch):
        self._setup(tmp_path, monkeypatch)
        log_m_event("EVT_A", m_workspace_id="mw_001")
        log_m_event("EVT_A", m_workspace_id="mw_002")
        events = read_events(m_workspace_id="mw_001")
        assert len(events) == 1


class TestEventLoggerEdgeCases:
    def test_no_payload_stores_empty_dict(self, tmp_path, monkeypatch):
        import src.m_side.m_event_logger as mel
        events_file = tmp_path / "events.jsonl"
        monkeypatch.setattr(mel, "_EVENTS_FILE", events_file)
        import json
        log_m_event("TEST_EVENT")
        evt = json.loads(events_file.read_text().strip())
        assert evt["payload"] == {}

    def test_timestamp_is_iso_format(self, tmp_path, monkeypatch):
        import src.m_side.m_event_logger as mel
        events_file = tmp_path / "events.jsonl"
        monkeypatch.setattr(mel, "_EVENTS_FILE", events_file)
        import json
        log_m_event("TEST_EVENT")
        evt = json.loads(events_file.read_text().strip())
        assert "T" in evt["timestamp"]  # ISO format check

    def test_event_ids_unique(self, tmp_path, monkeypatch):
        import src.m_side.m_event_logger as mel
        events_file = tmp_path / "events.jsonl"
        monkeypatch.setattr(mel, "_EVENTS_FILE", events_file)
        import json
        for _ in range(5):
            log_m_event("TEST_EVENT")
        lines = events_file.read_text().strip().splitlines()
        event_ids = [json.loads(line)["event_id"] for line in lines]
        assert len(set(event_ids)) == 5

    def test_chinese_payload_stored(self, tmp_path, monkeypatch):
        import src.m_side.m_event_logger as mel
        events_file = tmp_path / "events.jsonl"
        monkeypatch.setattr(mel, "_EVENTS_FILE", events_file)
        import json
        log_m_event("TEST_EVENT", payload={"message": "你好，供应商"})
        evt = json.loads(events_file.read_text().strip())
        assert evt["payload"]["message"] == "你好，供应商"
