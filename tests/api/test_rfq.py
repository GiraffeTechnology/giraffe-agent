import pytest


@pytest.mark.asyncio
async def test_create_rfq_creates_approval_request(
    auth_client, seed_project_with_form, seed_participants
):
    resp = await auth_client.post(
        f"/api/projects/{seed_project_with_form['id']}/rfqs",
        json={
            "form_version_id": seed_project_with_form["form_version_id"],
            "recipient_participant_ids": [seed_participants[0]["id"]],
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["rfq"]["status"] == "PENDING_APPROVAL"
    assert "approval_request_id" in data
    assert data["approval_request_id"] is not None


@pytest.mark.asyncio
async def test_cannot_send_rfq_without_approval(auth_client, seed_rfq):
    resp = await auth_client.post(
        f"/api/rfqs/{seed_rfq['id']}/send",
        json={"approval_id": str(seed_rfq["approval_request_id"])},
    )
    # approval is PENDING, not APPROVED
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_send_rfq_after_approval(auth_client, seed_rfq):
    # Approve first
    approve_resp = await auth_client.post(
        f"/api/approval-requests/{seed_rfq['approval_request_id']}/approve",
        json={"review_notes": "Approved for test"},
    )
    assert approve_resp.status_code == 200, approve_resp.text

    resp = await auth_client.post(
        f"/api/rfqs/{seed_rfq['id']}/send",
        json={"approval_id": str(seed_rfq["approval_request_id"])},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "SENT"


@pytest.mark.asyncio
async def test_get_rfq(auth_client, seed_rfq):
    resp = await auth_client.get(f"/api/rfqs/{seed_rfq['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == seed_rfq["id"]


@pytest.mark.asyncio
async def test_approve_and_reject_approval_request(
    auth_client, seed_project_with_form, seed_participants
):
    # Create one RFQ to get an approval request
    rfq_resp = await auth_client.post(
        f"/api/projects/{seed_project_with_form['id']}/rfqs",
        json={
            "form_version_id": seed_project_with_form["form_version_id"],
            "recipient_participant_ids": [seed_participants[0]["id"]],
        },
    )
    approval_id = rfq_resp.json()["approval_request_id"]

    # List pending
    list_resp = await auth_client.get("/api/approval-requests")
    assert list_resp.status_code == 200
    pending = list_resp.json()
    assert any(r["id"] == approval_id for r in pending)

    # Reject it
    reject_resp = await auth_client.post(
        f"/api/approval-requests/{approval_id}/reject",
        json={"review_notes": "Not ready"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "REJECTED"
