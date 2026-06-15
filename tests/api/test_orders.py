import pytest


@pytest.mark.asyncio
async def test_create_order_locks_form(auth_client, seed_approved_packet):
    resp = await auth_client.post(
        f"/api/projects/{seed_approved_packet['project_id']}/orders/from-approved-option",
        json={
            "packet_id": seed_approved_packet["id"],
            "option_id": seed_approved_packet["recommended_option_id"],
            "approval_id": seed_approved_packet["approval_request_id"],
        },
    )
    assert resp.status_code == 201, resp.text
    order = resp.json()
    assert order["status"] == "DRAFT_FROM_APPROVED_QUOTE"
    assert order["locked_form_version_id"] is not None
    assert order["order_number"].startswith("ORD-")


@pytest.mark.asyncio
async def test_create_order_requires_approved_packet(
    auth_client, seed_decision_packet
):
    """Cannot create order from an unapproved DecisionPacket."""
    resp = await auth_client.post(
        f"/api/projects/{seed_decision_packet['project_id']}/orders/from-approved-option",
        json={
            "packet_id": seed_decision_packet["id"],
            "option_id": seed_decision_packet["options"][0]["id"],
            "approval_id": seed_decision_packet["approval_request_id"],
        },
    )
    # ApprovalRequest is PENDING → 403
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_order(auth_client, seed_draft_order):
    resp = await auth_client.get(f"/api/orders/{seed_draft_order['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == seed_draft_order["id"]


@pytest.mark.asyncio
async def test_confirm_order_transitions_to_in_production(auth_client, seed_draft_order):
    resp = await auth_client.post(f"/api/orders/{seed_draft_order['id']}/confirm")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "IN_PRODUCTION"


@pytest.mark.asyncio
async def test_order_creates_12_milestones(auth_client, seed_approved_packet, db):
    resp = await auth_client.post(
        f"/api/projects/{seed_approved_packet['project_id']}/orders/from-approved-option",
        json={
            "packet_id": seed_approved_packet["id"],
            "option_id": seed_approved_packet["recommended_option_id"],
            "approval_id": seed_approved_packet["approval_request_id"],
        },
    )
    assert resp.status_code == 201
    order_id = resp.json()["id"]

    from sqlalchemy import select
    from src.db.models.production import Milestone

    result = await db.execute(
        select(Milestone).where(Milestone.order_id == order_id)
    )
    milestones = result.scalars().all()
    assert len(milestones) == 12


@pytest.mark.asyncio
async def test_invalid_order_state_transition(auth_client, seed_confirmed_order):
    """IN_PRODUCTION order cannot be buyer-signed-off directly."""
    resp = await auth_client.post(f"/api/orders/{seed_confirmed_order['id']}/buyer-sign-off")
    assert resp.status_code in (400, 409)
