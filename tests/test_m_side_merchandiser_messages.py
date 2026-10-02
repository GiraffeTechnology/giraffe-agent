"""Tests for M-side merchandiser message templates and routing."""
import pytest
from src.merchandiser.message_templates import (
    M_PROGRESS_CHECK, M_MEDIA_UPLOAD, M_LOGISTICS_HANDOVER,
    M_MATERIAL_DELAY_RESPONSE, render,
)
from src.merchandiser.side_router import route_merchandiser_message, _build_m_side_message


def test_m_progress_check_template():
    msg = render(M_PROGRESS_CHECK, stage="cutting")
    assert "cutting" in msg
    assert "A. Completed" in msg


def test_m_media_upload_template():
    # Preserve the original Chinese parameter to verify Unicode interpolation.
    msg = render(M_MEDIA_UPLOAD, milestone_type="final_qc", media_desc="3\u5f20\u7167\u7247")
    assert "final_qc" in msg
    assert "3\u5f20\u7167\u7247" in msg


def test_m_logistics_handover_template():
    msg = M_LOGISTICS_HANDOVER
    assert "carrier" in msg and "tracking number" in msg


def test_m_material_delay_response_template():
    msg = M_MATERIAL_DELAY_RESPONSE
    assert "backup fabric" in msg and "delivery" in msg


def test_route_m_side_production():
    result = route_merchandiser_message(
        project_id="proj-m-002",
        actor_id="sup-m-001",
        event_or_task={"event_type": "production_start", "assigned_side": "M_SIDE"},
    )
    assert result["side"] == "M_SIDE"
    assert len(result["message"]) > 0


def test_route_m_side_logistics():
    result = route_merchandiser_message(
        project_id="proj-m-003",
        actor_id="sup-m-002",
        event_or_task={"event_type": "logistics_handover", "assigned_side": "M_SIDE"},
    )
    assert result["side"] == "M_SIDE"
    assert len(result["message"]) > 0


def test_build_m_side_material_delay():
    msg = _build_m_side_message("material_delay_reported", {})
    assert "backup fabric" in msg and "delivery" in msg


def test_build_m_side_milestone():
    msg = _build_m_side_message("milestone_update", {})
    assert "production progress" in msg and "photos" in msg


def test_build_m_side_logistics():
    msg = _build_m_side_message("logistics_handover", {})
    assert "carrier" in msg and "tracking number" in msg


def test_build_m_side_fallback():
    msg = _build_m_side_message("unknown_event_xyz", {})
    assert len(msg) > 0
    assert "Please update" in msg


def test_route_uses_task_type_fallback():
    result = route_merchandiser_message(
        project_id="proj-m-004",
        actor_id="sup-m-003",
        event_or_task={"task_type": "qc_update", "assigned_side": "M_SIDE"},
    )
    assert result["side"] == "M_SIDE"
