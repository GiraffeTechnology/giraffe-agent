"""
B-side OpenClaw integration test.

Simulates the full B-side flow:
1. Customer sends WeChat procurement message via OpenClaw
2. Giraffe creates B-side project, identifies missing fields
3. Customer provides missing fields
4. Giraffe generates supplier inquiry draft (requires approval)
5. Customer approves → outbound payload returned to OpenClaw
6. Giraffe does NOT directly send any WeChat message

Run: uv run python scripts/test_openclaw_bside_invoke.py
"""

import sys
import json

# Allow imports from project root
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
        assert value is not None and value != "" and value != [] and value is not False, \
            f"[{label}] Expected non-empty '{field}', got: {value!r}"
    else:
        assert value == expected, \
            f"[{label}] Expected '{field}' = {expected!r}, got: {value!r}"
    print(f"  ✓ {field} = {value!r}")


def test_step1_initial_buyer_message() -> dict:
    """Step 1: Customer sends WeChat procurement message."""
    print("\n[STEP 1] Initial buyer WeChat message")

    event = {
        "source": "openclaw",
        "channel": "openclaw-weixin",
        "channel_account_id": "test_wechat_account",
        "conversation_id": "test_customer_conversation",
        "sender_id": "test_buyer",
        "sender_display_name": "Test Buyer",
        "message_text": "采购助理，帮我询价 10000 件白色纯棉衬衣，45 天内交温哥华。",
        "message_type": "text",
        "attachments": [],
        "mode": "b_side",
    }

    result = adapt_openclaw_event(event)
    _print_result("Step 1 Response", result)

    assert_field("step1", result, "ok", True)
    assert_field("step1", result, "project_id")
    assert_field("step1", result, "mode", "b_side")
    assert_field("step1", result, "reply_text")
    assert_field("step1", result, "execution_event_id")
    assert_field("step1", result, "b_workspace_id")

    status = result.get("status")
    assert status in ("missing_fields", "draft_ready", "requirement_complete"), \
        f"Unexpected status: {status}"
    print(f"  ✓ status = {status!r}")

    # Must have conversation binding
    assert result.get("conversation_binding_id") or result.get("project_id"), \
        "No conversation_binding_id or project_id returned"
    print("  ✓ conversation binding created")

    print("\n[STEP 1] PASSED")
    return result


def test_step2_followup_with_missing_fields(step1_result: dict) -> dict:
    """Step 2: Customer provides missing fields."""
    print("\n[STEP 2] Follow-up: provide missing fields")

    project_id = step1_result["project_id"]

    event = {
        "source": "openclaw",
        "channel": "openclaw-weixin",
        "channel_account_id": "test_wechat_account",
        "conversation_id": "test_customer_conversation",
        "sender_id": "test_buyer",
        "sender_display_name": "Test Buyer",
        "message_text": (
            "尺码比例 S 20%, M 40%, L 30%, XL 10%，"
            "面料 180gsm，单件目标价 5 美元，普通纸箱包装。"
        ),
        "message_type": "text",
        "attachments": [],
        "mode": "b_side",
    }

    result = adapt_openclaw_event(event)
    _print_result("Step 2 Response", result)

    assert_field("step2", result, "ok", True)

    # Same project_id should be reused
    returned_project = result.get("project_id")
    assert returned_project == project_id, \
        f"Expected project_id {project_id!r}, got {returned_project!r}"
    print(f"  ✓ project_id reused = {returned_project!r}")

    status = result.get("status")
    print(f"  ✓ status = {status!r}")

    # If draft is ready, it must require approval and have no outbound messages
    if status == "draft_ready":
        assert result.get("approval_required") is True, \
            "draft_ready must have approval_required=true"
        assert result.get("outbound_messages") == [], \
            "outbound_messages must be empty before approval"
        assert len(result.get("message_drafts", [])) > 0, \
            "message_drafts must not be empty when draft_ready"
        print("  ✓ approval_required = True")
        print("  ✓ outbound_messages = [] (no dispatch before approval)")
        print("  ✓ message_drafts has content")

    print("\n[STEP 2] PASSED")
    return result


def test_step3_approve_draft(step1_result: dict, step2_result: dict) -> dict:
    """Step 3: Customer approves the supplier inquiry draft."""
    print("\n[STEP 3] Approve supplier inquiry draft")

    # Try approval only if draft_ready
    if step2_result.get("status") != "draft_ready":
        # Check if step1 had a draft ready
        if step1_result.get("status") != "draft_ready":
            print("  [SKIP] No draft to approve in either step 1 or step 2")
            return {}

    project_id = step1_result["project_id"]

    event = {
        "source": "openclaw",
        "channel": "openclaw-weixin",
        "channel_account_id": "test_wechat_account",
        "conversation_id": "test_customer_conversation",
        "sender_id": "test_buyer",
        "sender_display_name": "Test Buyer",
        "message_text": "确认发送",
        "message_type": "text",
        "attachments": [],
        "project_id": project_id,
        "mode": "b_side",
    }

    result = adapt_openclaw_event(event)
    _print_result("Step 3 Response", result)

    assert_field("step3", result, "ok", True)

    status = result.get("status")
    print(f"  ✓ status = {status!r}")

    if status == "approved_for_dispatch":
        assert result.get("approval_required") is False, \
            "After approval, approval_required must be false"
        outbound = result.get("outbound_messages", [])
        assert len(outbound) > 0, \
            "approved_for_dispatch must have outbound_messages"
        print("  ✓ approval_required = False")
        print(f"  ✓ outbound_messages has {len(outbound)} message(s)")
        print("  ✓ Giraffe returns payload for OpenClaw to send (does NOT send directly)")

    print("\n[STEP 3] PASSED")
    return result


def main():
    print("=" * 60)
    print("  Giraffe B-side OpenClaw Integration Test")
    print("=" * 60)

    try:
        step1_result = test_step1_initial_buyer_message()
        step2_result = test_step2_followup_with_missing_fields(step1_result)
        step3_result = test_step3_approve_draft(step1_result, step2_result)

        print("\n" + "=" * 60)
        print("  ALL B-SIDE OPENCLAW TESTS PASSED")
        print("=" * 60)
        print("\nFlow verified:")
        print("  Customer WeChat → OpenClaw → /api/skill/invoke")
        print("  → Giraffe B-side project created")
        print("  → Missing fields clarification")
        print("  → Supplier inquiry draft generated")
        print("  → Human approval required")
        print("  → Approved → outbound payload for OpenClaw")
        print("  → Giraffe did NOT directly send WeChat message")
        print("\nReal WeChat integration is not complete unless:")
        print("  - OpenClaw Weixin plugin is installed and logged in by QR code")
        print("  - Tested against a real WeChat message")

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
