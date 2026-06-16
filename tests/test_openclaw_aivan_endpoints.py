"""
Tests for AIVAN /api/openclaw/* endpoints.

Covers:
  - API key guard (no key set → open; key set → 401/403 on wrong/missing header)
  - POST /api/openclaw/events
  - GET  /api/openclaw/drafts/pending
  - POST /api/openclaw/drafts/{id}/approve  — state transition guards
  - POST /api/openclaw/drafts/{id}/reject   — state transition guards
"""

import os
import pytest
from fastapi.testclient import TestClient

# Ensure DB-off mode so no DB setup is needed
os.environ.setdefault("GIRAFFE_DB_MODE", "off")


@pytest.fixture()
def client(monkeypatch, tmp_path):
    """TestClient with an isolated message-draft data directory."""
    monkeypatch.delenv("AIVAN_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    # Import app AFTER setting env / cwd so the draft store picks up tmp_path
    from api.main import app
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture()
def client_with_key(monkeypatch, tmp_path):
    """TestClient with AIVAN_API_KEY='testkey' configured."""
    monkeypatch.setenv("AIVAN_API_KEY", "testkey")
    monkeypatch.chdir(tmp_path)
    from api.main import app
    return TestClient(app, raise_server_exceptions=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_event(project_id: str = "proj_test") -> dict:
    return {
        "source": "openclaw",
        "channel": "openclaw-mock",
        "channel_account_id": "acct-001",
        "conversation_id": "conv-001",
        "sender_id": "sender-001",
        "message_text": "Hello, I need 100 units of cotton fabric.",
        "project_id": project_id,
    }


def _seed_pending_draft(tmp_path, project_id: str = "proj_test") -> str:
    """Write a pending draft JSON directly into the draft store dir and return its id."""
    import json, uuid
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    draft_dir = tmp_path / "data" / "message_drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft = {
        "id": draft_id,
        "project_id": project_id,
        "channel": "openclaw-mock",
        "target_role": "supplier",
        "draft_text": "Dear supplier, please send a quote.",
        "approval_status": "pending_approval",
        "created_at": "2026-06-15T00:00:00+00:00",
        "updated_at": "2026-06-15T00:00:00+00:00",
    }
    (draft_dir / f"{draft_id}.json").write_text(json.dumps(draft), encoding="utf-8")
    return draft_id


def _seed_draft_with_status(tmp_path, status: str, project_id: str = "proj_test") -> str:
    import json, uuid
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    draft_dir = tmp_path / "data" / "message_drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft = {
        "id": draft_id,
        "project_id": project_id,
        "channel": "openclaw-mock",
        "target_role": "supplier",
        "draft_text": "Test draft.",
        "approval_status": status,
        "created_at": "2026-06-15T00:00:00+00:00",
        "updated_at": "2026-06-15T00:00:00+00:00",
    }
    (draft_dir / f"{draft_id}.json").write_text(json.dumps(draft), encoding="utf-8")
    return draft_id


# ─── API key guard — no key configured (open access) ─────────────────────────

class TestApiKeyGuardOpen:
    def test_events_no_key_required(self, client):
        resp = client.post("/api/openclaw/events", json=_make_event())
        assert resp.status_code == 200

    def test_pending_drafts_no_key_required(self, client):
        resp = client.get("/api/openclaw/drafts/pending", params={"project_id": "proj_test"})
        assert resp.status_code == 200

    def test_approve_no_key_required(self, client, tmp_path):
        draft_id = _seed_pending_draft(tmp_path)
        resp = client.post(
            f"/api/openclaw/drafts/{draft_id}/approve",
            json={"approved_by": "user1"},
        )
        assert resp.status_code == 200

    def test_reject_no_key_required(self, client, tmp_path):
        draft_id = _seed_pending_draft(tmp_path)
        resp = client.post(f"/api/openclaw/drafts/{draft_id}/reject")
        assert resp.status_code == 200


# ─── API key guard — key configured ──────────────────────────────────────────

class TestApiKeyGuardEnforced:
    def test_events_missing_key_returns_401(self, client_with_key):
        resp = client_with_key.post("/api/openclaw/events", json=_make_event())
        assert resp.status_code == 401
        assert "X-AIVAN-API-Key" in resp.json()["detail"]

    def test_events_wrong_key_returns_403(self, client_with_key):
        resp = client_with_key.post(
            "/api/openclaw/events",
            json=_make_event(),
            headers={"X-AIVAN-API-Key": "wrongkey"},
        )
        assert resp.status_code == 403

    def test_events_correct_key_returns_200(self, client_with_key):
        resp = client_with_key.post(
            "/api/openclaw/events",
            json=_make_event(),
            headers={"X-AIVAN-API-Key": "testkey"},
        )
        assert resp.status_code == 200

    def test_pending_drafts_missing_key_returns_401(self, client_with_key):
        resp = client_with_key.get(
            "/api/openclaw/drafts/pending",
            params={"project_id": "proj_test"},
        )
        assert resp.status_code == 401

    def test_pending_drafts_wrong_key_returns_403(self, client_with_key):
        resp = client_with_key.get(
            "/api/openclaw/drafts/pending",
            params={"project_id": "proj_test"},
            headers={"X-AIVAN-API-Key": "wrongkey"},
        )
        assert resp.status_code == 403

    def test_pending_drafts_correct_key_returns_200(self, client_with_key):
        resp = client_with_key.get(
            "/api/openclaw/drafts/pending",
            params={"project_id": "proj_test"},
            headers={"X-AIVAN-API-Key": "testkey"},
        )
        assert resp.status_code == 200

    def test_approve_missing_key_returns_401(self, client_with_key, tmp_path):
        draft_id = _seed_pending_draft(tmp_path)
        resp = client_with_key.post(
            f"/api/openclaw/drafts/{draft_id}/approve",
            json={"approved_by": "user1"},
        )
        assert resp.status_code == 401

    def test_reject_missing_key_returns_401(self, client_with_key, tmp_path):
        draft_id = _seed_pending_draft(tmp_path)
        resp = client_with_key.post(f"/api/openclaw/drafts/{draft_id}/reject")
        assert resp.status_code == 401


# ─── Events endpoint ──────────────────────────────────────────────────────────

class TestOpenClawEventsEndpoint:
    def test_returns_200_and_dict(self, client):
        resp = client.post("/api/openclaw/events", json=_make_event())
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_missing_channel_returns_422(self, client):
        resp = client.post("/api/openclaw/events", json={"source": "openclaw"})
        assert resp.status_code == 422


# ─── Pending drafts endpoint ──────────────────────────────────────────────────

class TestPendingDraftsEndpoint:
    def test_empty_project_returns_zero_count(self, client):
        resp = client.get("/api/openclaw/drafts/pending", params={"project_id": "empty_proj"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["pending_count"] == 0
        assert body["drafts"] == []

    def test_seeded_draft_appears(self, client, tmp_path):
        _seed_pending_draft(tmp_path, "proj_seed")
        resp = client.get("/api/openclaw/drafts/pending", params={"project_id": "proj_seed"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["pending_count"] == 1
        assert len(body["drafts"]) == 1
        assert body["drafts"][0]["approval_status"] == "pending_approval"

    def test_approved_draft_not_in_pending(self, client, tmp_path):
        _seed_draft_with_status(tmp_path, "approved", "proj_approved")
        resp = client.get("/api/openclaw/drafts/pending", params={"project_id": "proj_approved"})
        assert resp.status_code == 200
        assert resp.json()["pending_count"] == 0

    def test_missing_project_id_returns_422(self, client):
        resp = client.get("/api/openclaw/drafts/pending")
        assert resp.status_code == 422


# ─── Approve endpoint — state transitions ─────────────────────────────────────

class TestApproveStateTransitions:
    def test_approve_pending_draft_succeeds(self, client, tmp_path):
        draft_id = _seed_pending_draft(tmp_path)
        resp = client.post(
            f"/api/openclaw/drafts/{draft_id}/approve",
            json={"approved_by": "human_user"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["status"] == "approved"

    def test_approve_already_approved_draft_returns_409(self, client, tmp_path):
        draft_id = _seed_draft_with_status(tmp_path, "approved")
        resp = client.post(
            f"/api/openclaw/drafts/{draft_id}/approve",
            json={"approved_by": "human_user"},
        )
        assert resp.status_code == 409
        assert "approved" in resp.json()["detail"]

    def test_approve_rejected_draft_returns_409(self, client, tmp_path):
        draft_id = _seed_draft_with_status(tmp_path, "rejected")
        resp = client.post(
            f"/api/openclaw/drafts/{draft_id}/approve",
            json={"approved_by": "human_user"},
        )
        assert resp.status_code == 409
        assert "rejected" in resp.json()["detail"]

    def test_approve_nonexistent_draft_returns_404(self, client):
        resp = client.post(
            "/api/openclaw/drafts/nonexistent_draft_xyz/approve",
            json={"approved_by": "human_user"},
        )
        assert resp.status_code == 404

    def test_approve_requires_approved_by(self, client, tmp_path):
        draft_id = _seed_pending_draft(tmp_path)
        resp = client.post(
            f"/api/openclaw/drafts/{draft_id}/approve",
            json={},
        )
        assert resp.status_code == 422


# ─── Reject endpoint — state transitions ──────────────────────────────────────

class TestRejectStateTransitions:
    def test_reject_pending_draft_succeeds(self, client, tmp_path):
        draft_id = _seed_pending_draft(tmp_path)
        resp = client.post(f"/api/openclaw/drafts/{draft_id}/reject")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["status"] == "rejected"

    def test_reject_already_rejected_draft_returns_409(self, client, tmp_path):
        draft_id = _seed_draft_with_status(tmp_path, "rejected")
        resp = client.post(f"/api/openclaw/drafts/{draft_id}/reject")
        assert resp.status_code == 409
        assert "rejected" in resp.json()["detail"]

    def test_reject_already_approved_draft_returns_409(self, client, tmp_path):
        draft_id = _seed_draft_with_status(tmp_path, "approved")
        resp = client.post(f"/api/openclaw/drafts/{draft_id}/reject")
        assert resp.status_code == 409
        assert "approved" in resp.json()["detail"]

    def test_reject_nonexistent_draft_returns_404(self, client):
        resp = client.post("/api/openclaw/drafts/nonexistent_draft_xyz/reject")
        assert resp.status_code == 404


# ─── Regression: double-approve is idempotent at the store level ─────────────

class TestDraftStateRegressions:
    def test_draft_status_persists_after_approve(self, client, tmp_path):
        """Approved status must be durable — re-reading the draft shows 'approved'."""
        draft_id = _seed_pending_draft(tmp_path)
        client.post(
            f"/api/openclaw/drafts/{draft_id}/approve",
            json={"approved_by": "user_a"},
        )
        # Second approve must be blocked
        resp2 = client.post(
            f"/api/openclaw/drafts/{draft_id}/approve",
            json={"approved_by": "user_b"},
        )
        assert resp2.status_code == 409

    def test_draft_status_persists_after_reject(self, client, tmp_path):
        """Rejected status must be durable — re-rejecting must be blocked."""
        draft_id = _seed_pending_draft(tmp_path)
        client.post(f"/api/openclaw/drafts/{draft_id}/reject")
        resp2 = client.post(f"/api/openclaw/drafts/{draft_id}/reject")
        assert resp2.status_code == 409

    def test_approved_draft_not_in_pending_after_approve(self, client, tmp_path):
        """After approval the draft must no longer appear in the pending list."""
        draft_id = _seed_pending_draft(tmp_path, "proj_persist")
        client.post(
            f"/api/openclaw/drafts/{draft_id}/approve",
            json={"approved_by": "user_a"},
        )
        resp = client.get("/api/openclaw/drafts/pending", params={"project_id": "proj_persist"})
        assert resp.status_code == 200
        assert resp.json()["pending_count"] == 0


# ─── API key guard — /api/skill/invoke ───────────────────────────────────────

def _make_skill_invoke_payload() -> dict:
    return {
        "source": "openclaw",
        "channel": "openclaw-mock",
        "channel_account_id": "acct-001",
        "conversation_id": "conv-001",
        "sender_id": "sender-001",
        "message_text": "I need 100 cotton shirts.",
        "project_id": "proj_skill_test",
    }


class TestSkillInvokeApiKeyGuard:
    def test_no_key_configured_passes(self, client):
        """When AIVAN_API_KEY is unset, /api/skill/invoke must accept any request."""
        resp = client.post("/api/skill/invoke", json=_make_skill_invoke_payload())
        assert resp.status_code == 200

    def test_key_configured_missing_header_returns_401(self, client_with_key):
        resp = client_with_key.post("/api/skill/invoke", json=_make_skill_invoke_payload())
        assert resp.status_code == 401
        assert "X-AIVAN-API-Key" in resp.json()["detail"]

    def test_key_configured_wrong_key_returns_403(self, client_with_key):
        resp = client_with_key.post(
            "/api/skill/invoke",
            json=_make_skill_invoke_payload(),
            headers={"X-AIVAN-API-Key": "wrongkey"},
        )
        assert resp.status_code == 403

    def test_key_configured_correct_key_returns_200(self, client_with_key):
        resp = client_with_key.post(
            "/api/skill/invoke",
            json=_make_skill_invoke_payload(),
            headers={"X-AIVAN-API-Key": "testkey"},
        )
        assert resp.status_code == 200
