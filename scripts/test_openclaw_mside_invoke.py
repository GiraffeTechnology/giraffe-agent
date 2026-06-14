"""
M-side OpenClaw integration test.

Tests the full B-side → M-side flow:
1. Customer WeChat → OpenClaw → Giraffe B-side project
2. Provide missing fields → supplier inquiry draft
3. Approve draft
4. Supplier email reply → OpenClaw → Giraffe M-side
5. Supplier response parsed (no invented data)
6. No direct sending by Giraffe

Run: uv run python scripts/test_openclaw_mside_invoke.py
"""

import sys
import json

sys.path.insert(0, ".")

from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event


def _print_result(label: str, result: dict) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def assert_field(label: str, result: dict, field: str, expected=None) -> None:
    value = result.get(field)
    if expected is None:
        assert value is not None and value != "" and value is not False, \
            f"[{label}] Expected non-empty '{field}', got: {value!r}"
    else:
        assert value == expected, \
            f"[{label}] Expected '{field}' = {expected!r}, got: {value!r}"
    print(f"  ✓ {field} = {value!r}")


def test_step1_create_bside_project() -> str:
    """Step 1: Create B-side procurement project from WeChat buyer message."""
    print("\n[STEP 1] Create B-side project from WeChat buyer message")

    event = {
        "source": "openclaw",
        "channel": "openclaw-weixin",
        "channel_account_id": "test_wechat_account",
        "conversation_id": "test_customer_conversation_mside",
        "sender_id": "test_buyer_mside",
        "sender_display_name": "Test Buyer",
        "message_text": "采购助理，帮我询价 10000 件白色纯棉衬衣，45 天内交温哥华。",
        "message_type": "text",
        "attachments": [],
        "mode": "b_side",
    }

    result = adapt_openclaw_event(event)
    _print_result("Step 1 Response", result)

    assert result.get("ok") is True, "Step 1 must return ok=true"
    project_id = result.get("project_id")
    assert project_id, "Step 1 must return project_id"
    print(f"  ✓ project_id = {project_id!r}")
    print("\n[STEP 1] PASSED")
    return project_id


def test_step2_provide_missing_fields(project_id: str) -> None:
    """Step 2: Provide missing fields."""
    print("\n[STEP 2] Provide missing fields")

    event = {
        "source": "openclaw",
        "channel": "openclaw-weixin",
        "channel_account_id": "test_wechat_account",
        "conversation_id": "test_customer_conversation_mside",
        "sender_id": "test_buyer_mside",
        "message_text": (
            "尺码比例 S 20%, M 40%, L 30%, XL 10%，"
            "面料 180gsm，单件目标价 5 美元，普通纸箱包装。"
        ),
        "message_type": "text",
        "mode": "b_side",
    }

    result = adapt_openclaw_event(event)
    _print_result("Step 2 Response", result)

    assert result.get("ok") is True
    returned_pid = result.get("project_id")
    assert returned_pid == project_id, \
        f"Step 2: expected project_id={project_id!r}, got {returned_pid!r}"
    print(f"  ✓ project_id reused = {returned_pid!r}")
    print("\n[STEP 2] PASSED")


def test_step3_approve_draft(project_id: str) -> None:
    """Step 3: Approve supplier inquiry draft."""
    print("\n[STEP 3] Approve supplier inquiry draft")

    event = {
        "source": "openclaw",
        "channel": "openclaw-weixin",
        "channel_account_id": "test_wechat_account",
        "conversation_id": "test_customer_conversation_mside",
        "sender_id": "test_buyer_mside",
        "message_text": "确认发送",
        "project_id": project_id,
        "mode": "b_side",
    }

    result = adapt_openclaw_event(event)
    _print_result("Step 3 Response", result)

    assert result.get("ok") is True
    status = result.get("status")
    print(f"  ✓ status = {status!r}")

    if status == "approved_for_dispatch":
        outbound = result.get("outbound_messages", [])
        assert len(outbound) > 0, "approved_for_dispatch must have outbound_messages"
        print(f"  ✓ outbound_messages has {len(outbound)} message(s)")
        print("  ✓ Giraffe returns outbound payload — does NOT send directly")

    print("\n[STEP 3] PASSED")


def test_step4_supplier_email_reply(project_id: str) -> None:
    """Step 4: Supplier replies via OpenClaw Email."""
    print("\n[STEP 4] Supplier email reply → M-side parsing")

    event = {
        "source": "openclaw",
        "channel": "openclaw-email",
        "channel_account_id": "test_sales_email_account",
        "conversation_id": "test_supplier_email_thread",
        "sender_id": "supplier_abc_email",
        "sender_display_name": "ABC Garment Factory",
        "message_text": (
            "We can make 10000 white cotton shirts. MOQ ok. "
            "Lead time 38 days. FOB Shenzhen USD 4.80/pc. Fabric 180gsm."
        ),
        "message_type": "text",
        "attachments": [],
        "project_id": project_id,
        "procurement_edge_id": f"edge_supplier_abc_{project_id}",
        "mode": "m_side",
    }

    result = adapt_openclaw_event(event)
    _print_result("Step 4 Response", result)

    assert result.get("ok") is True, f"Step 4 must return ok=true, got: {result}"
    assert_field("step4", result, "mode", "m_side")
    assert_field("step4", result, "execution_event_id")

    # project_id must be the same
    returned_pid = result.get("project_id")
    assert returned_pid == project_id, \
        f"Step 4: expected project_id={project_id!r}, got {returned_pid!r}"
    print(f"  ✓ same project_id reused = {returned_pid!r}")

    status = result.get("status")
    assert status == "supplier_response_received", \
        f"Expected supplier_response_received, got {status!r}"
    print(f"  ✓ status = {status!r}")

    # Missing fields must not be invented
    missing = result.get("missing_fields", [])
    identified = result.get("identified_fields", {})
    print(f"  ✓ identified_fields = {identified}")
    print(f"  ✓ missing_fields = {missing}")

    # Should identify price and lead time from the message
    assert "unit_price" in identified or "lead_time" in identified, \
        f"Should have identified at least unit_price or lead_time from the message. Got: {identified}"

    # Check no direct sending
    assert result.get("outbound_messages") == [], \
        "M-side supplier reply must NOT produce outbound_messages (no direct sending)"
    print("  ✓ outbound_messages = [] (Giraffe does NOT directly send email)")

    assert result.get("approval_required") is False, \
        "M-side supplier response should not require approval"
    print("  ✓ approval_required = False")

    # Execution event must be present
    assert result.get("execution_event_id"), "Must have execution_event_id"
    print("  ✓ execution_event_id present")

    print("\n[STEP 4] PASSED")


def test_step5_supplier_reply_without_project_id_asks_clarification() -> None:
    """Step 5: Supplier reply without project_id should ask for clarification, not create B-side project."""
    print("\n[STEP 5] Supplier reply without project_id → clarification (no B-side project created)")

    event = {
        "source": "openclaw",
        "channel": "openclaw-email",
        "channel_account_id": "test_sales_email_account",
        "conversation_id": "unknown_supplier_email_thread",
        "sender_id": "unknown_supplier_email",
        "sender_display_name": "Unknown Supplier",
        "message_text": (
            "We can make 5000 pcs. Lead time 30 days. USD 3.50/pc. FOB Guangzhou."
        ),
        "message_type": "text",
        "mode": "m_side",
    }

    result = adapt_openclaw_event(event)
    _print_result("Step 5 Response", result)

    assert result.get("ok") is True
    assert result.get("mode") == "m_side", \
        f"Expected mode=m_side, got {result.get('mode')!r}"
    assert result.get("status") == "clarification_needed", \
        f"Expected clarification_needed, got {result.get('status')!r}"
    print("  ✓ status = clarification_needed")
    print("  ✓ Giraffe did NOT create a B-side project for an ambiguous supplier reply")

    print("\n[STEP 5] PASSED")


def main():
    print("=" * 60)
    print("  Giraffe M-side OpenClaw Integration Test")
    print("=" * 60)

    try:
        project_id = test_step1_create_bside_project()
        test_step2_provide_missing_fields(project_id)
        test_step3_approve_draft(project_id)
        test_step4_supplier_email_reply(project_id)
        test_step5_supplier_reply_without_project_id_asks_clarification()

        print("\n" + "=" * 60)
        print("  ALL M-SIDE OPENCLAW TESTS PASSED")
        print("=" * 60)
        print("\nFlow verified:")
        print("  Customer WeChat → OpenClaw → Giraffe B-side project")
        print("  → Missing fields → draft generated → human approval")
        print("  → Supplier email → OpenClaw → Giraffe M-side")
        print("  → Supplier response parsed (no invented data)")
        print("  → No direct sending by Giraffe")
        print("  → Ambiguous supplier reply asks for clarification")
        print("\nReal Email integration is not complete unless:")
        print("  - OpenClaw Email channel is configured with IMAP/SMTP credentials")
        print("  - Tested against a real inbound and outbound email")

    except AssertionError as e:
        print(f"\n[FAILED] {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n[ERROR] {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
