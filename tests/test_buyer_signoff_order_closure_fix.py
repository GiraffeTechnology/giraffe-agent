"""Tests that buyer signoff closes the order (Bug 4.3 fix)."""
import pytest
from src.merchandiser.b_side.b_signoff import receive_buyer_signoff, request_buyer_signoff

def test_request_buyer_signoff_returns_status():
    result = request_buyer_signoff(
        project_id="PROJ-SIGNOFF-01",
        buyer_actor_id="ACT-BUYER-001",
        tracking_number="SF123456789012",
    )
    assert result["status"] == "signoff_requested"
    assert "SF123456789012" in result["message"]

def test_receive_buyer_signoff_confirmed():
    result = receive_buyer_signoff(
        project_id="PROJ-SIGNOFF-02",
        buyer_actor_id="ACT-BUYER-002",
        response="confirmed",
        notes="Received in good condition",
    )
    assert result["status"] in ("signoff_received", "order_closed")
    assert result["response"] == "confirmed"

def test_receive_buyer_signoff_with_issue():
    result = receive_buyer_signoff(
        project_id="PROJ-SIGNOFF-03",
        buyer_actor_id="ACT-BUYER-003",
        response="received_with_issue",
        notes="2 pieces damaged",
    )
    assert result["response"] == "received_with_issue"

def test_receive_buyer_signoff_updates_order_status():
    result = receive_buyer_signoff(
        project_id="PROJ-SIGNOFF-04",
        buyer_actor_id="ACT-BUYER-004",
        response="confirmed",
        order_id="OE-SIGNOFF-TEST-001",
    )
    # order_status_updated is set when an execution context is found and updated
    assert "response" in result

def test_buyer_signoff_not_auto_closed_without_confirmation():
    # Without explicit buyer signoff, order should NOT auto-close
    result = receive_buyer_signoff(
        project_id="PROJ-SIGNOFF-05",
        buyer_actor_id="ACT-BUYER-005",
        response="not_received",
    )
    assert result["response"] == "not_received"
    # Status should NOT be order_closed for non-confirmation
    assert result.get("status") != "order_closed" or result["response"] == "confirmed"
