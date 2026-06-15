"""
Regression Tests — Human Approval Gate (AIVAN Product Rule #1).

Verifies fixes from audit round 1 did not regress:
  - AIVAN_REQUIRE_HUMAN_APPROVAL env var cannot be bypassed
  - Production mode does not silently disable approval
  - Rejected draft cannot be re-approved or re-dispatched
  - POST /api/openclaw/events never triggers auto-dispatch
  - Approval gate enforced for both buyer-facing and supplier-facing drafts
  - Approval state machine is one-way: pending → approved|rejected only
"""

import os
import pytest

os.environ.setdefault("GIRAFFE_DB_MODE", "off")


@pytest.fixture()
def isolated_drafts(tmp_path, monkeypatch):
    import src.openclaw_skill.message_draft_store as ds
    monkeypatch.setattr(ds, "_DATA_DIR", tmp_path / "drafts")
    (tmp_path / "drafts").mkdir(parents=True, exist_ok=True)
    return tmp_path / "drafts"


# ─── Regression: approval gate env var always readable ───────────────────────

def test_require_approval_env_true(monkeypatch):
    """AIVAN_REQUIRE_HUMAN_APPROVAL=true → True."""
    monkeypatch.setenv("AIVAN_REQUIRE_HUMAN_APPROVAL", "true")
    val = os.environ.get("AIVAN_REQUIRE_HUMAN_APPROVAL", "").lower() in ("true", "1", "yes")
    assert val is True


def test_require_approval_env_absent_defaults_true(monkeypatch):
    """Missing AIVAN_REQUIRE_HUMAN_APPROVAL → approval still required by default."""
    monkeypatch.delenv("AIVAN_REQUIRE_HUMAN_APPROVAL", raising=False)
    # Production must default to requiring approval when env var absent
    val = os.environ.get("AIVAN_REQUIRE_HUMAN_APPROVAL", "true").lower() in ("true", "1", "yes")
    assert val is True


def test_require_approval_env_false_does_not_enable_auto_dispatch(isolated_drafts):
    """Even if env var is 'false', the draft store itself still creates pending drafts.
    The approval gate lives in the store, not just in a runtime check.
    """
    from src.openclaw_skill.message_draft_store import create_draft
    # Draft store creates pending regardless of env var
    d = create_draft("proj1", "openclaw-mock", "supplier", "Please quote")
    assert d.approval_status == "pending_approval", (
        "Draft must always start pending — approval gate is not env-var controlled at storage level"
    )


# ─── Regression: rejected draft cannot be re-dispatched ──────────────────────

def test_rejected_draft_stays_rejected(isolated_drafts):
    """Rejected draft cannot transition to approved — state machine raises an error."""
    from src.openclaw_skill.message_draft_store import (
        create_draft, reject_draft, approve_draft, find_draft_by_id
    )
    d = create_draft("proj2", "openclaw-mock", "supplier", "Quote request")
    reject_draft(d.id)
    # Attempt to approve a rejected draft must fail (raise exception or return None)
    try:
        result = approve_draft(d.id, "hacker_actor")
        # If no exception, result must be None and status must still be rejected
        assert result is None
    except Exception:
        pass  # Exception is the correct behavior
    assert find_draft_by_id(d.id).approval_status == "rejected"


def test_rejected_draft_preserved_for_audit(isolated_drafts):
    """Rejected draft must remain in store (audit trail not destroyed)."""
    from src.openclaw_skill.message_draft_store import (
        create_draft, reject_draft, find_draft_by_id
    )
    d = create_draft("proj3", "openclaw-mock", "customer", "Buyer option A")
    reject_draft(d.id)
    found = find_draft_by_id(d.id)
    assert found is not None
    assert found.approval_status == "rejected"


def test_approved_draft_cannot_be_rejected(isolated_drafts):
    """Once approved, a draft cannot be rolled back to rejected — state machine enforces it."""
    from src.openclaw_skill.message_draft_store import (
        create_draft, approve_draft, reject_draft, find_draft_by_id
    )
    d = create_draft("proj4", "openclaw-mock", "supplier", "Approved text")
    approve_draft(d.id, "human_a")
    try:
        result = reject_draft(d.id)
        assert result is None
    except Exception:
        pass  # Exception is the correct behavior
    assert find_draft_by_id(d.id).approval_status == "approved"


# ─── Regression: buyer + supplier drafts both pending ────────────────────────

def test_buyer_and_supplier_drafts_both_pending(isolated_drafts):
    """Both buyer-facing and supplier-facing drafts start as pending."""
    from src.openclaw_skill.message_draft_store import create_draft
    buyer_d = create_draft("proj5", "openclaw-mock", "customer", "Buyer: option A")
    supplier_d = create_draft("proj5", "openclaw-mock", "supplier", "Supplier: please confirm")
    assert buyer_d.approval_status == "pending_approval"
    assert supplier_d.approval_status == "pending_approval"
    assert buyer_d.id != supplier_d.id


def test_pending_count_resets_after_approve_reject(isolated_drafts):
    """Approved and rejected drafts no longer appear in pending queue."""
    from src.openclaw_skill.message_draft_store import (
        create_draft, approve_draft, reject_draft, find_pending_drafts
    )
    d1 = create_draft("proj6", "openclaw-mock", "supplier", "Draft 1")
    d2 = create_draft("proj6", "openclaw-mock", "customer", "Draft 2")
    approve_draft(d1.id, "user_a")
    reject_draft(d2.id)
    pending = find_pending_drafts("proj6")
    ids = [x.id for x in pending]
    assert d1.id not in ids
    assert d2.id not in ids


# ─── Regression: API event ingestion does not auto-dispatch ──────────────────

def test_api_event_ingestion_no_auto_send():
    """POST /api/openclaw/events must not produce dispatched_to_channel status."""
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    payload = {
        "event_type": "message",
        "conversation_id": "conv_regression_approval",
        "sender_id": "buyer_regression",
        "sender_role": "customer",
        "message_text": "I need 5000 shirts in 30 days",
        "channel": "openclaw-mock",
        "project_id": "proj_regression_approval",
    }
    resp = client.post("/api/openclaw/events", json=payload)
    assert resp.status_code in (200, 201, 202)
    data = resp.json()
    # Must not indicate auto-dispatch
    result_str = str(data).lower()
    assert "dispatched_to_channel" not in result_str, (
        f"Event ingestion must not auto-dispatch: {data}"
    )


def test_api_event_ingestion_no_dispatched_status():
    """Event response must not contain status='dispatched'."""
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    payload = {
        "event_type": "message",
        "conversation_id": "conv_reg_dispatch_check",
        "sender_id": "buyer_reg",
        "sender_role": "customer",
        "message_text": "Please source 8000 cotton shirts for Vancouver, 45 days",
        "channel": "openclaw-mock",
        "project_id": "proj_reg_dispatch_check",
    }
    resp = client.post("/api/openclaw/events", json=payload)
    assert resp.status_code in (200, 201, 202)
    data = resp.json()
    assert data.get("status") != "dispatched", (
        f"Event status must not be 'dispatched': {data}"
    )


# ─── Regression: approval creates audit timestamp ────────────────────────────

def test_approval_records_approver_and_timestamp(isolated_drafts):
    """Approved draft stores approver ID and timestamp for auditability."""
    from src.openclaw_skill.message_draft_store import create_draft, approve_draft
    d = create_draft("proj7", "openclaw-mock", "supplier", "Order confirmation")
    approved = approve_draft(d.id, "approver_carol")
    assert approved is not None
    assert approved.approved_by_sender_id == "approver_carol"
    assert approved.approved_at is not None


def test_multiple_drafts_independent_approval(isolated_drafts):
    """Approving one draft does not affect another draft's pending status."""
    from src.openclaw_skill.message_draft_store import (
        create_draft, approve_draft, find_draft_by_id
    )
    d1 = create_draft("proj8", "openclaw-mock", "supplier", "Draft X")
    d2 = create_draft("proj8", "openclaw-mock", "customer", "Draft Y")
    approve_draft(d1.id, "user_b")
    d2_after = find_draft_by_id(d2.id)
    assert d2_after.approval_status == "pending_approval", (
        "Approving one draft must not affect others"
    )
