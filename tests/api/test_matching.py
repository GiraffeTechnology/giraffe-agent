import pytest


@pytest.mark.asyncio
async def test_run_matching_empty_returns_list(auth_client, seed_project_with_form):
    resp = await auth_client.post(
        f"/api/projects/{seed_project_with_form['id']}/run-participant-matching"
    )
    assert resp.status_code == 200
    matches = resp.json()
    assert isinstance(matches, list)


@pytest.mark.asyncio
async def test_run_matching_with_participants(auth_client, seed_project_with_form, seed_participants):
    resp = await auth_client.post(
        f"/api/projects/{seed_project_with_form['id']}/run-participant-matching"
    )
    assert resp.status_code == 200
    matches = resp.json()
    assert isinstance(matches, list)
    assert len(matches) > 0


@pytest.mark.asyncio
async def test_all_matches_require_human_approval(auth_client, seed_project_with_form, seed_participants):
    resp = await auth_client.post(
        f"/api/projects/{seed_project_with_form['id']}/run-participant-matching"
    )
    assert resp.status_code == 200
    matches = resp.json()
    assert all(m["requires_human_approval"] is True for m in matches)


@pytest.mark.asyncio
async def test_match_score_between_0_and_1(auth_client, seed_project_with_form, seed_participants):
    resp = await auth_client.post(
        f"/api/projects/{seed_project_with_form['id']}/run-participant-matching"
    )
    assert resp.status_code == 200
    for match in resp.json():
        assert 0.0 <= match["match_score"] <= 1.0


@pytest.mark.asyncio
async def test_get_matches_for_project(auth_client, seed_project_with_form, seed_participants):
    # Run matching first
    await auth_client.post(
        f"/api/projects/{seed_project_with_form['id']}/run-participant-matching"
    )
    # Then retrieve
    resp = await auth_client.get(
        f"/api/projects/{seed_project_with_form['id']}/participant-matches"
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
