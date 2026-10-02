"""English operator text without changes to routing, envelopes or event contracts."""
import asyncio
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from starlette.requests import Request


@pytest.mark.parametrize(
    "module_name,function_name,args,event_type,expected,status",
    [
        (
            "m_logistics_handover", "request_logistics_handover", ("project", "supplier"),
            "LOGISTICS_HANDOVER_REQUESTED",
            "The order has reached logistics handover. Please reply with the carrier name, "
            "tracking number, and upload a shipping label photo.\n"
            "Example: Shipped via SF Express, tracking SF123456789, dispatched this afternoon.",
            "requested",
        ),
        (
            "m_media_request", "request_milestone_media_upload",
            ("project", "supplier", "milestone", "final_qc", ["front photo", "back photo"]),
            "ORDER_MILESTONE_MEDIA_REQUESTED",
            "Please upload final qc stage media: front photo, back photo.", "requested",
        ),
        (
            "m_merchandiser_service", "send_m_side_progress_check",
            ("project", "supplier", "mid_production"), "M_SIDE_PROGRESS_CHECK_REQUESTED",
            "Progress check (mid production): Please update the current production status.", "sent",
        ),
        (
            "m_qc_followup", "request_qc_update", ("project", "supplier", "final_qc"),
            "M_QC_UPDATE_REQUESTED",
            "Please upload the final qc inspection report and proof of compliance.", "requested",
        ),
        (
            "m_upstream_followup", "send_upstream_followup",
            ("project", "supplier", "upstream", "fabric_supply"), "M_UPSTREAM_FOLLOWUP_SENT",
            "Please confirm progress and the delivery time for fabric supply.", "sent",
        ),
    ],
)
def test_supplier_requests_preserve_event_contract(
    monkeypatch, module_name, function_name, args, event_type, expected, status
):
    module = importlib.import_module(f"src.merchandiser.m_side.{module_name}")
    events = []
    monkeypatch.setattr(module, "log_m_event", lambda **event: events.append(event))

    result = getattr(module, function_name)(*args)

    assert result == {"status": status, "message": expected}
    assert len(events) == 1
    assert events[0]["event_type"] == event_type
    assert events[0]["b_workspace_id"] == "project"
    assert events[0]["supplier_id"] == "supplier"
    if "message" in events[0]["payload"]:
        assert events[0]["payload"]["message"] == expected


def test_skill_fallback_is_english_and_preserves_fields():
    from aivan.api.main import _skill_response

    result = SimpleNamespace(model_dump=lambda: {"project_id": "project", "action": "draft"})
    assert _skill_response(result) == {
        "project_id": "project", "action": "draft", "status": "ok",
        "reply_text": "Your request has been received.",
        "output": "Your request has been received.",
    }


def test_skill_error_is_english_without_exception_details():
    from aivan.api.main import ERROR_REPLY_TEXT, unhandled_exception_handler

    request = Request({"type": "http", "method": "POST", "path": "/invoke", "headers": []})
    response = asyncio.run(unhandled_exception_handler(request, RuntimeError("internal-sentinel")))
    assert response.status_code == 200
    assert json.loads(response.body) == {
        "status": "error", "output": ERROR_REPLY_TEXT, "reply_text": ERROR_REPLY_TEXT,
    }
    assert ERROR_REPLY_TEXT == (
        "AIVAN encountered a backend dependency error while processing your request. "
        "Please try again later."
    )
    assert b"internal-sentinel" not in response.body


def test_invalid_skill_format_preserves_error_envelope():
    from aivan.api.main import invoke

    class InvalidRequest:
        async def json(self):
            return {"unsupported": "value"}

    response = asyncio.run(invoke(InvalidRequest(), db=None))
    assert response.status_code == 200
    assert json.loads(response.body) == {
        "status": "error", "output": "Unrecognized request format.",
        "reply_text": "The request format was not recognized. Please check the message content.",
        "artifacts": [],
    }


def test_frontend_example_is_english():
    root = Path(__file__).resolve().parents[1]
    template = (root / "src/aivan/app/templates/index.html").read_text()
    assert "e.g. I need 10,000 white cotton men's shirts..." in template
