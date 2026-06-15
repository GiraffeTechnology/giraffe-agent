import pytest


@pytest.mark.asyncio
async def test_project_events_chronological_order(auth_client, seed_project):
    resp = await auth_client.get(f"/api/execution-graph/projects/{seed_project['id']}")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1
    # Events should be in chronological order
    occurred_ats = [e["occurred_at"] for e in events]
    assert occurred_ats == sorted(occurred_ats)


@pytest.mark.asyncio
async def test_project_created_event_present(auth_client, seed_project):
    resp = await auth_client.get(f"/api/execution-graph/projects/{seed_project['id']}")
    assert resp.status_code == 200
    events = resp.json()
    event_types = [e["event_type"] for e in events]
    assert "PROJECT_CREATED" in event_types


@pytest.mark.asyncio
async def test_order_events_full_payload(auth_client, seed_confirmed_order):
    order_id = seed_confirmed_order["id"]
    resp = await auth_client.get(f"/api/execution-graph/orders/{order_id}")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1
    for event in events:
        assert "id" in event
        assert "event_type" in event
        assert "payload" in event
        assert "occurred_at" in event
        assert isinstance(event["payload"], dict)


@pytest.mark.asyncio
async def test_single_event_fetch(auth_client, seed_project):
    events_resp = await auth_client.get(f"/api/execution-graph/projects/{seed_project['id']}")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) >= 1

    event_id = events[0]["id"]
    resp = await auth_client.get(f"/api/execution-graph/events/{event_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == event_id
    assert data["event_type"] == events[0]["event_type"]
