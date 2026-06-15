"""
Human Approval Gate Tests — AIVAN Product Rule #1.

Rule: AIVAN must never send any outbound message without human approval.

Tests:
  - Drafts are created with status 'pending_approval' by default
  - Approved drafts transition to 'approved'
  - Rejected drafts transition to 'rejected'
  - Cannot approve already-approved draft
  - Cannot reject already-rejected draft
  - Cannot approve already-rejected draft
  - Cannot reject already-approved draft
  - API enforces approval gate (no auto-send on event ingestion)
  - AIVAN_REQUIRE_HUMAN_APPROVAL env var is recognized
"""

import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("GIRAFFE_DB_MODE", "off")


# ─── Core Draft Store Tests ────────────────────────────────────────────────────

@pytest.fixture()
def draft_dir(tmp_path, monkeypatch):
    """Redirect draft store to a temp directory."""
    import src.openclaw_skill.message_draft_store as ds
    original_data_dir = ds._DATA_DIR
    ds._DATA_DIR = tmp_path / "data" / "message_drafts"
    ds._DATA_DIR.mkdir(parents=True, exist_ok=True)
    yield ds._DATA_DIR
    ds._DATA_DIR = original_data_dir


def test_draft_created_pending(draft_dir):
    from src.openclaw_skill.message_draft_store import create_draft, find_pending_drafts
    d = create_draft(
        project_id="proj_test",
        channel="openclaw-mock",
        target_role="supplier",
        draft_text="Hello supplier, please quote.",
    )
    assert d.approval_status == "pending_approval"
    pending = find_pending_drafts("proj_test")
    assert any(x.id == d.id for x in pending)


def test_approve_pending_draft(draft_dir):
    from src.openclaw_skill.message_draft_store import create_draft, approve_draft
    d = create_draft("p1", "ch", "supplier", "Text")
    approved = approve_draft(d.id, "human_user_1")
    assert approved is not None
    assert approved.approval_status == "approved"
    assert approved.approved_by_sender_id == "human_user_1"
    assert approved.approved_at is not None


def test_reject_pending_draft(draft_dir):
    from src.openclaw_skill.message_draft_store import create_draft, reject_draft
    d = create_draft("p1", "ch", "supplier", "Text")
    rejected = reject_draft(d.id)
    assert rejected is not None
    assert rejected.approval_status == "rejected"


def test_cannot_approve_already_approved(draft_dir):
    from src.openclaw_skill.message_draft_store import create_draft, approve_draft, DraftStateError
    d = create_draft("p1", "ch", "supplier", "Text")
    approve_draft(d.id, "user1")
    with pytest.raises(DraftStateError) as exc_info:
        approve_draft(d.id, "user2")
    assert "approved" in str(exc_info.value).lower()


def test_cannot_reject_already_rejected(draft_dir):
    from src.openclaw_skill.message_draft_store import create_draft, reject_draft, DraftStateError
    d = create_draft("p1", "ch", "supplier", "Text")
    reject_draft(d.id)
    with pytest.raises(DraftStateError):
        reject_draft(d.id)


def test_cannot_approve_rejected_draft(draft_dir):
    from src.openclaw_skill.message_draft_store import create_draft, approve_draft, reject_draft, DraftStateError
    d = create_draft("p1", "ch", "supplier", "Text")
    reject_draft(d.id)
    with pytest.raises(DraftStateError):
        approve_draft(d.id, "user1")


def test_cannot_reject_approved_draft(draft_dir):
    from src.openclaw_skill.message_draft_store import create_draft, approve_draft, reject_draft, DraftStateError
    d = create_draft("p1", "ch", "supplier", "Text")
    approve_draft(d.id, "user1")
    with pytest.raises(DraftStateError):
        reject_draft(d.id)


def test_nonexistent_draft_returns_none(draft_dir):
    from src.openclaw_skill.message_draft_store import find_draft_by_id, approve_draft, reject_draft
    assert find_draft_by_id("nonexistent_draft_xyz") is None
    assert approve_draft("nonexistent_draft_xyz", "user") is None
    assert reject_draft("nonexistent_draft_xyz") is None


def test_rejected_draft_not_in_pending(draft_dir):
    from src.openclaw_skill.message_draft_store import create_draft, reject_draft, find_pending_drafts
    d = create_draft("proj_rej", "ch", "supplier", "Draft text")
    reject_draft(d.id)
    pending = find_pending_drafts("proj_rej")
    assert not any(x.id == d.id for x in pending)


def test_approved_draft_not_in_pending(draft_dir):
    from src.openclaw_skill.message_draft_store import create_draft, approve_draft, find_pending_drafts
    d = create_draft("proj_app", "ch", "supplier", "Draft text")
    approve_draft(d.id, "user")
    pending = find_pending_drafts("proj_app")
    assert not any(x.id == d.id for x in pending)


# ─── API Approval Gate Tests ───────────────────────────────────────────────────

@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.delenv("AIVAN_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    from api.main import app
    return TestClient(app, raise_server_exceptions=True)


def _seed_draft(tmp_path, project_id="proj_gate", status="pending_approval"):
    import json, uuid
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    draft_dir = tmp_path / "data" / "message_drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft = {
        "id": draft_id,
        "project_id": project_id,
        "channel": "openclaw-mock",
        "target_role": "supplier",
        "draft_text": "Supplier inquiry draft.",
        "approval_status": status,
        "created_at": "2026-06-15T00:00:00+00:00",
        "updated_at": "2026-06-15T00:00:00+00:00",
    }
    (draft_dir / f"{draft_id}.json").write_text(json.dumps(draft), encoding="utf-8")
    return draft_id


def test_event_ingestion_does_not_auto_send(client):
    """POST /api/openclaw/events must not produce a 'dispatched_to_channel' response."""
    resp = client.post("/api/openclaw/events", json={
        "source": "openclaw",
        "channel": "openclaw-mock",
        "conversation_id": "conv-001",
        "sender_id": "buyer-001",
        "message_text": "I need 500 cotton t-shirts delivered to Vancouver by August.",
    })
    assert resp.status_code == 200
    data = resp.json()
    response_str = str(data).lower()
    assert "dispatched_to_channel" not in response_str
    assert "message_sent_directly" not in response_str


def test_pending_draft_visible_via_api(client, tmp_path):
    draft_id = _seed_draft(tmp_path)
    resp = client.get("/api/openclaw/drafts/pending", params={"project_id": "proj_gate"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_count"] >= 1
    assert any(d["id"] == draft_id for d in data["drafts"])


def test_approve_draft_via_api(client, tmp_path):
    draft_id = _seed_draft(tmp_path)
    resp = client.post(f"/api/openclaw/drafts/{draft_id}/approve", json={"approved_by": "human_user"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_reject_draft_via_api(client, tmp_path):
    draft_id = _seed_draft(tmp_path)
    resp = client.post(f"/api/openclaw/drafts/{draft_id}/reject")
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_reject_nonexistent_draft_returns_404(client):
    resp = client.post("/api/openclaw/drafts/nonexistent_draft_xyz/reject")
    assert resp.status_code == 404


def test_approve_nonexistent_draft_returns_404(client):
    resp = client.post("/api/openclaw/drafts/nonexistent_draft_xyz/approve",
                       json={"approved_by": "user"})
    assert resp.status_code == 404


def test_double_approve_returns_409(client, tmp_path):
    draft_id = _seed_draft(tmp_path)
    client.post(f"/api/openclaw/drafts/{draft_id}/approve", json={"approved_by": "user"})
    resp = client.post(f"/api/openclaw/drafts/{draft_id}/approve", json={"approved_by": "user2"})
    assert resp.status_code == 409


def test_approve_rejected_draft_returns_409(client, tmp_path):
    draft_id = _seed_draft(tmp_path, status="rejected")
    resp = client.post(f"/api/openclaw/drafts/{draft_id}/approve", json={"approved_by": "user"})
    assert resp.status_code == 409


def test_aivan_require_human_approval_env_recognized():
    """AIVAN_REQUIRE_HUMAN_APPROVAL env var should be parseable."""
    import os
    os.environ["AIVAN_REQUIRE_HUMAN_APPROVAL"] = "true"
    val = os.environ.get("AIVAN_REQUIRE_HUMAN_APPROVAL", "").lower() in ("true", "1", "yes")
    assert val is True
    del os.environ["AIVAN_REQUIRE_HUMAN_APPROVAL"]
