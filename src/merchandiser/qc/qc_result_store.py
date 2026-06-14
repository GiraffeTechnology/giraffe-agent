"""
QC result store — persists QCComparisonReport to data/merchandiser/qc/reports/.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from src.merchandiser.qc.qc_models import QCComparisonReport
from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/merchandiser/qc/reports")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_qc_report(
    report: QCComparisonReport,
    project_id: str,
    milestone_id: str | None = None,
) -> str:
    """Save a QCComparisonReport and return the report_id."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    report_id = f"QCR-{uuid.uuid4().hex[:10].upper()}"
    data = report.model_dump()
    data["report_id"] = report_id
    data["project_id"] = project_id
    data["milestone_id"] = milestone_id
    data["saved_at"] = _utcnow()
    (_DATA_DIR / f"{report_id}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log_m_event(
        event_type="QC_REPORT_SAVED",
        b_workspace_id=project_id,
        payload={"report_id": report_id, "milestone_id": milestone_id, "overall_result": report.overall_result},
    )
    return report_id


def get_qc_report(report_id: str) -> dict | None:
    p = _DATA_DIR / f"{report_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def get_qc_reports_for_project(project_id: str) -> list[dict]:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for p in _DATA_DIR.glob("QCR-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("project_id") == project_id:
                result.append(data)
        except Exception:
            pass
    return sorted(result, key=lambda x: x.get("saved_at", ""))


def get_latest_qc_report_for_milestone(project_id: str, milestone_id: str) -> dict | None:
    reports = [r for r in get_qc_reports_for_project(project_id) if r.get("milestone_id") == milestone_id]
    return reports[-1] if reports else None
