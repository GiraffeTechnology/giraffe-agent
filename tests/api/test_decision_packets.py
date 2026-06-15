import pytest


@pytest.mark.asyncio
async def test_generate_decision_packet(auth_client, seed_rfq_with_responses, seed_project_with_form):
    resp = await auth_client.post(
        f"/api/projects/{seed_project_with_form['id']}/decision-packets",
        json={"rfq_id": seed_rfq_with_responses["rfq_id"]},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    packet = data["packet"]
    assert len(packet["options"]) >= 1
    assert packet["human_approval_status"] == "PENDING"
    assert "approval_request_id" in data


@pytest.mark.asyncio
async def test_calculated_lead_time_is_not_sentinel():
    from src.lead_time.calculator import calculate_path_lead_time

    packets = [{
        "production_time_days": 25,
        "qc_time_days": 5,
        "logistics_time_days": 7,
        "fabric_lead_time_days": 20,
        "trim_lead_time_days": None,
    }]
    result = calculate_path_lead_time(packets)
    assert result["calculated_total_lead_time_days"] is None
    assert result["has_missing_values"] is True
    assert "trim_lead_time_days" in result["missing_fields"]


@pytest.mark.asyncio
async def test_supplier_stated_vs_calculated_preserved(
    auth_client, seed_rfq_with_responses, seed_project_with_form
):
    # Create packet
    create_resp = await auth_client.post(
        f"/api/projects/{seed_project_with_form['id']}/decision-packets",
        json={"rfq_id": seed_rfq_with_responses["rfq_id"]},
    )
    assert create_resp.status_code == 201

    # Get latest
    resp = await auth_client.get(
        f"/api/projects/{seed_project_with_form['id']}/decision-packets/latest"
    )
    assert resp.status_code == 200
    packet = resp.json()
    for option in packet["options"]:
        assert "calculated_total_lead_time_days" in option
        assert "supplier_stated_lead_time_days" in option


@pytest.mark.asyncio
async def test_approve_option_requires_approval(auth_client, seed_decision_packet):
    resp = await auth_client.post(
        f"/api/decision-packets/{seed_decision_packet['id']}/approve-option",
        json={
            "option_id": seed_decision_packet["options"][0]["id"],
            "approval_id": seed_decision_packet["approval_request_id"],
        },
    )
    # ApprovalRequest is still PENDING, not APPROVED
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_approve_option_after_approval(auth_client, seed_decision_packet):
    packet_id = seed_decision_packet["id"]
    approval_id = seed_decision_packet["approval_request_id"]
    option_id = seed_decision_packet["options"][0]["id"]

    # Approve the request
    await auth_client.post(
        f"/api/approval-requests/{approval_id}/approve",
        json={"review_notes": "Looks good"},
    )

    # Now approve the option
    resp = await auth_client.post(
        f"/api/decision-packets/{packet_id}/approve-option",
        json={"option_id": option_id, "approval_id": approval_id},
    )
    assert resp.status_code == 200
    assert resp.json()["human_approval_status"] == "APPROVED"
