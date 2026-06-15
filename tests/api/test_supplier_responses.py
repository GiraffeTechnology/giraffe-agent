import pytest


@pytest.mark.asyncio
async def test_record_supplier_response(auth_client, seed_sent_rfq, seed_participants):
    resp = await auth_client.post(
        f"/api/rfqs/{seed_sent_rfq['id']}/responses",
        json={
            "participant_id": seed_participants[0]["id"],
            "raw_response_text": "Unit price $8.50, lead time 35 days, MOQ 500 pcs.",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "packet" in data
    assert "response" in data
    assert data["packet"]["ai_generated"] is True


@pytest.mark.asyncio
async def test_supplier_response_packet_fields(auth_client, seed_sent_rfq, seed_participants):
    resp = await auth_client.post(
        f"/api/rfqs/{seed_sent_rfq['id']}/responses",
        json={
            "participant_id": seed_participants[0]["id"],
            "raw_response_text": "Unit price $8.50, lead time 35 days, MOQ 500 pcs.",
        },
    )
    assert resp.status_code == 201
    packet = resp.json()["packet"]
    # Packet must have these fields (values may be null if LLM stub)
    for field in ["unit_price", "currency", "moq", "total_lead_time_days", "missing_fields", "risk_flags"]:
        assert field in packet


@pytest.mark.asyncio
async def test_supplier_response_emits_events(auth_client, seed_sent_rfq, seed_participants, db):
    await auth_client.post(
        f"/api/rfqs/{seed_sent_rfq['id']}/responses",
        json={
            "participant_id": seed_participants[0]["id"],
            "raw_response_text": "Price: $9",
        },
    )
    from sqlalchemy import select
    from src.db.models.execution_graph import ExecutionEvent

    result = await db.execute(
        select(ExecutionEvent).where(
            ExecutionEvent.event_type.in_(
                ["SUPPLIER_RESPONSE_RECEIVED", "SUPPLIER_RESPONSE_NORMALIZED"]
            )
        )
    )
    events = result.scalars().all()
    assert len(events) >= 2


@pytest.mark.asyncio
async def test_list_rfq_responses(auth_client, seed_sent_rfq, seed_participants):
    # Record a response first
    await auth_client.post(
        f"/api/rfqs/{seed_sent_rfq['id']}/responses",
        json={
            "participant_id": seed_participants[0]["id"],
            "raw_response_text": "We can supply. Price $7.50.",
        },
    )
    # List responses
    resp = await auth_client.get(f"/api/rfqs/{seed_sent_rfq['id']}/responses")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_renormalize_response(auth_client, seed_sent_rfq, seed_participants):
    create_resp = await auth_client.post(
        f"/api/rfqs/{seed_sent_rfq['id']}/responses",
        json={
            "participant_id": seed_participants[0]["id"],
            "raw_response_text": "Price $10, lead time 40 days.",
        },
    )
    response_id = create_resp.json()["response"]["id"]

    resp = await auth_client.post(f"/api/supplier-responses/{response_id}/normalize")
    assert resp.status_code == 200
    assert resp.json()["ai_generated"] is True
