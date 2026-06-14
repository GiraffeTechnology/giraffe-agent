"""Tests for QC result store."""
import pytest
from src.merchandiser.qc.qc_result_store import (
    save_qc_report, get_qc_report, get_qc_reports_for_project, get_latest_qc_report_for_milestone
)
from src.merchandiser.qc.qc_models import QCComparisonReport

_PROJECT = "PROJ-QCR-STORE-01"

def _make_report(**kwargs) -> QCComparisonReport:
    defaults = dict(
        overall_result="pass",
        overall_score=0.9,
        severity="low",
        provider_name="mock",
        model_name="mock",
        requested_provider="qwen",
        m_side_feedback_zh="通过",
        m_side_feedback_en="Pass",
    )
    defaults.update(kwargs)
    return QCComparisonReport(**defaults)

def test_save_qc_report_returns_report_id():
    report = _make_report()
    report_id = save_qc_report(report, project_id=_PROJECT)
    assert report_id.startswith("QCR-")

def test_get_qc_report_returns_saved():
    report = _make_report()
    report_id = save_qc_report(report, project_id=_PROJECT, milestone_id="MILE-001")
    data = get_qc_report(report_id)
    assert data is not None
    assert data["report_id"] == report_id
    assert data["project_id"] == _PROJECT
    assert data["milestone_id"] == "MILE-001"

def test_get_qc_report_nonexistent_returns_none():
    assert get_qc_report("QCR-NONEXISTENT") is None

def test_get_qc_reports_for_project_returns_project_reports():
    project = "PROJ-QCR-LIST-01"
    report = _make_report()
    save_qc_report(report, project_id=project)
    reports = get_qc_reports_for_project(project)
    assert len(reports) >= 1
    assert all(r["project_id"] == project for r in reports)

def test_get_latest_qc_report_for_milestone():
    project = "PROJ-QCR-LATEST-01"
    milestone = "MILE-LATEST-01"
    report = _make_report(overall_result="needs_fix")
    save_qc_report(report, project_id=project, milestone_id=milestone)
    latest = get_latest_qc_report_for_milestone(project, milestone)
    assert latest is not None
    assert latest["milestone_id"] == milestone
    assert latest["overall_result"] == "needs_fix"
