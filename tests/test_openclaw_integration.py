"""
pytest tests for OpenClaw B-side and M-side integration.
"""

import sys
sys.path.insert(0, ".")

import pytest
from src.openclaw_skill.openclaw_event_adapter import (
    adapt_openclaw_event,
    _is_approval,
    _is_rejection,
    _detect_buyer_intent,
    _detect_supplier_reply_intent,
    _detect_mode_from_intent,
    _parse_destination_zh,
    _parse_deadline_zh,
    resolve_trade_salesperson_role,
)


# ─── Unit tests: intent detection ────────────────────────────────────────────

class TestIntentDetection:
    def test_approval_zh(self):
        assert _is_approval("确认发送")

    def test_approval_en(self):
        assert _is_approval("approve")
        assert _is_approval("send it")
        assert _is_approval("yes send")

    def test_rejection_zh(self):
        assert _is_rejection("取消")
        assert _is_rejection("不要发送")

    def test_rejection_en(self):
        assert _is_rejection("reject")
        assert _is_rejection("do not send")

    def test_buyer_intent_zh(self):
        assert _detect_buyer_intent("帮我询价 10000 件白色纯棉衬衣")
        assert _detect_buyer_intent("我需要采购 5000 件衬衫")

    def test_supplier_reply_intent_en(self):
        assert _detect_supplier_reply_intent(
            "We can make 10000 shirts. Lead time 38 days. USD 4.80/pc."
        )
        assert _detect_supplier_reply_intent("FOB Shenzhen. MOQ 1000 pcs.")

    def test_mode_detection_buyer(self):
        assert _detect_mode_from_intent("帮我询价 10000 件衬衣") == "b_side"

    def test_mode_detection_supplier(self):
        assert _detect_mode_from_intent("We can make it. Lead time 30 days. USD 4.50/pc.") == "m_side"


# ─── Unit tests: destination / deadline parsing ───────────────────────────────

class TestParsing:
    def test_destination_zh_vancouver(self):
        assert _parse_destination_zh("交温哥华") == "Vancouver"

    def test_destination_zh_shanghai(self):
        assert _parse_destination_zh("送往上海") == "Shanghai"

    def test_deadline_zh_within_days(self):
        assert _parse_deadline_zh("45 天内交货") == "within 45 days"
        assert _parse_deadline_zh("30天内") == "within 30 days"

    def test_deadline_en(self):
        result = _parse_deadline_zh("within 45 days")
        assert result == "within 45 days"


# ─── Integration tests: B-side flow ───────────────────────────────────────────

class TestBSideFlow:
    def _make_event(self, message_text: str, conversation_id: str = "conv_bside_test",
                    project_id: str = None, mode: str = "b_side") -> dict:
        event = {
            "source": "openclaw",
            "channel": "openclaw-weixin",
            "channel_account_id": "test_account",
            "conversation_id": conversation_id,
            "sender_id": f"buyer_{conversation_id}",
            "sender_display_name": "Test Buyer",
            "message_text": message_text,
            "message_type": "text",
            "attachments": [],
            "mode": mode,
        }
        if project_id:
            event["project_id"] = project_id
        return event

    def test_new_buyer_request_creates_project(self):
        import uuid
        conv_id = f"conv_new_{uuid.uuid4().hex[:8]}"
        result = adapt_openclaw_event(
            self._make_event(
                "采购助理，帮我询价 10000 件白色纯棉衬衣，45 天内交温哥华。",
                conversation_id=conv_id,
            )
        )
        assert result["ok"] is True
        assert result["project_id"]
        assert result["mode"] == "b_side"
        assert result["reply_text"]
        assert result["execution_event_id"]
        assert result["status"] in ("missing_fields", "draft_ready", "requirement_complete")

    def test_buyer_request_has_conversation_binding(self):
        import uuid
        conv_id = f"conv_bind_{uuid.uuid4().hex[:8]}"
        result = adapt_openclaw_event(
            self._make_event(
                "帮我询价 5000 件纯棉T恤",
                conversation_id=conv_id,
            )
        )
        assert result["ok"] is True
        # Binding created
        assert result.get("conversation_binding_id") or result.get("project_id")

    def test_missing_fields_response(self):
        import uuid
        conv_id = f"conv_missing_{uuid.uuid4().hex[:8]}"
        result = adapt_openclaw_event(
            self._make_event(
                "采购助理，帮我询价 10000 件白色纯棉衬衣，45 天内交温哥华。",
                conversation_id=conv_id,
            )
        )
        assert result["ok"] is True
        # If missing fields exist, they must be a list
        if result["status"] == "missing_fields":
            assert isinstance(result["missing_fields"], list)
            assert len(result["missing_fields"]) > 0

    def test_followup_reuses_same_project(self):
        import uuid
        conv_id = f"conv_followup_{uuid.uuid4().hex[:8]}"
        result1 = adapt_openclaw_event(
            self._make_event(
                "帮我询价 10000 件白色纯棉衬衣，45 天内交温哥华。",
                conversation_id=conv_id,
            )
        )
        project_id = result1["project_id"]

        result2 = adapt_openclaw_event(
            self._make_event(
                "尺码比例 S 20%, M 40%, L 30%, XL 10%，面料 180gsm，单价 5 美元，纸箱包装。",
                conversation_id=conv_id,
            )
        )
        assert result2["project_id"] == project_id, \
            f"Follow-up should reuse project {project_id!r}, got {result2['project_id']!r}"

    def test_draft_requires_approval(self):
        import uuid
        conv_id = f"conv_draft_{uuid.uuid4().hex[:8]}"

        # Create project with all fields
        result1 = adapt_openclaw_event(
            self._make_event(
                "帮我询价 10000 件白色纯棉衬衣，45 天内交温哥华。",
                conversation_id=conv_id,
            )
        )
        project_id = result1["project_id"]

        # Provide all missing fields
        result2 = adapt_openclaw_event(
            self._make_event(
                "尺码比例 S 20%, M 40%, L 30%, XL 10%，面料 180gsm，单价 5 美元，纸箱包装。",
                conversation_id=conv_id,
            )
        )

        # Find the draft_ready result
        draft_result = result2 if result2.get("status") == "draft_ready" else result1

        if draft_result.get("status") == "draft_ready":
            assert draft_result.get("approval_required") is True
            assert draft_result.get("outbound_messages") == []

    def test_approval_produces_outbound_messages(self):
        import uuid
        conv_id = f"conv_approve_{uuid.uuid4().hex[:8]}"

        result1 = adapt_openclaw_event(
            self._make_event(
                "帮我询价 10000 件白色纯棉衬衣，45 天内交温哥华。",
                conversation_id=conv_id,
            )
        )
        project_id = result1["project_id"]

        adapt_openclaw_event(
            self._make_event(
                "尺码比例 S 20%, M 40%, L 30%, XL 10%，面料 180gsm，单价 5 美元，纸箱包装。",
                conversation_id=conv_id,
            )
        )

        # Approve
        approval_result = adapt_openclaw_event(
            self._make_event(
                "确认发送",
                conversation_id=conv_id,
                project_id=project_id,
            )
        )

        assert approval_result["ok"] is True
        status = approval_result.get("status")
        if status == "approved_for_dispatch":
            assert approval_result.get("outbound_messages")
            assert approval_result.get("approval_required") is False


# ─── Integration tests: M-side flow ──────────────────────────────────────────

class TestMSideFlow:
    def test_supplier_reply_with_project_id(self):
        result = adapt_openclaw_event({
            "source": "openclaw",
            "channel": "openclaw-email",
            "channel_account_id": "sales_inbox",
            "conversation_id": "email_thread_abc",
            "sender_id": "supplier_abc",
            "sender_display_name": "ABC Garment Factory",
            "message_text": (
                "We can make 10000 white cotton shirts. MOQ ok. "
                "Lead time 38 days. FOB Shenzhen USD 4.80/pc. Fabric 180gsm."
            ),
            "project_id": "TEST-PROJECT-001",
            "mode": "m_side",
        })
        assert result["ok"] is True
        assert result["mode"] == "m_side"
        assert result["status"] == "supplier_response_received"
        assert result["project_id"] == "TEST-PROJECT-001"
        assert result["execution_event_id"]
        assert result.get("outbound_messages") == []
        assert result.get("approval_required") is False

    def test_supplier_reply_identifies_fields(self):
        result = adapt_openclaw_event({
            "source": "openclaw",
            "channel": "openclaw-email",
            "channel_account_id": "sales_inbox",
            "conversation_id": "email_thread_xyz",
            "sender_id": "supplier_xyz",
            "sender_display_name": "XYZ Factory",
            "message_text": "Lead time 38 days. USD 4.80/pc. Fabric 180gsm. FOB Shenzhen.",
            "project_id": "TEST-PROJECT-002",
            "mode": "m_side",
        })
        assert result["ok"] is True
        identified = result.get("identified_fields", {})
        # Should identify at least one field
        assert len(identified) > 0, f"Expected identified fields, got: {identified}"

    def test_supplier_reply_preserves_missing_fields(self):
        """Missing supplier data must NOT be invented."""
        result = adapt_openclaw_event({
            "source": "openclaw",
            "channel": "openclaw-email",
            "channel_account_id": "sales_inbox",
            "conversation_id": "email_thread_partial",
            "sender_id": "supplier_partial",
            "sender_display_name": "Partial Factory",
            "message_text": "We can make it. USD 4.80/pc.",
            "project_id": "TEST-PROJECT-003",
            "mode": "m_side",
        })
        assert result["ok"] is True
        missing = result.get("missing_fields", [])
        # Lead time was not provided — must be missing, not invented
        assert "lead_time" in missing or "moq" in missing or "packaging" in missing, \
            f"Expected some missing fields, got: {missing}"

    def test_supplier_reply_without_project_id_asks_clarification(self):
        """Supplier reply without project context must ask for clarification."""
        result = adapt_openclaw_event({
            "source": "openclaw",
            "channel": "openclaw-email",
            "channel_account_id": "sales_inbox_unknown",
            "conversation_id": "unknown_email_thread",
            "sender_id": "unknown_supplier",
            "message_text": "We can make 5000 pcs. Lead time 30 days.",
            "mode": "m_side",
        })
        assert result["ok"] is True
        assert result["mode"] == "m_side"
        assert result["status"] == "clarification_needed"

    def test_supplier_reply_does_not_create_bside_project(self):
        """Ambiguous supplier reply must NOT create a B-side project."""
        result = adapt_openclaw_event({
            "source": "openclaw",
            "channel": "openclaw-email",
            "channel_account_id": "sales_inbox_unknown2",
            "conversation_id": "unknown_email_thread2",
            "sender_id": "unknown_supplier2",
            "message_text": "FOB Shenzhen. Lead time 30 days. USD 5.00/pc. MOQ 500.",
            "mode": "m_side",
        })
        assert result["ok"] is True
        assert result["status"] == "clarification_needed"
        # project_id must be None (not created)
        assert result.get("project_id") is None


# ─── Feasibility engine tests ─────────────────────────────────────────────────

class TestFeasibilityEngine:
    def test_single_supplier_path(self):
        from src.b_side.workspace import create_b_workspace, save_b_workspace
        from src.b_side.requirement_structurer import structure_requirement
        from src.b_side.feasibility_engine import run_feasibility_simulation, get_feasibility_status
        from src.core_schema.b_side_types import SupplierResponseRecord
        import uuid

        ws = create_b_workspace("10000 pcs shirts")
        req = structure_requirement(ws.b_workspace_id, "10000 pcs shirts")
        ws.buyer_requirement = req
        ws.supplier_responses = [
            SupplierResponseRecord(
                response_id=f"resp_{uuid.uuid4().hex[:8]}",
                rfq_id=req.rfq_id,
                b_workspace_id=ws.b_workspace_id,
                supplier_id="sup_001",
                supplier_name="Factory A",
                can_make=True,
                estimated_lead_time_days=38,
                unit_price=4.80,
                currency="USD",
                confidence_score=0.8,
            )
        ]
        save_b_workspace(ws)

        report = run_feasibility_simulation(ws.b_workspace_id)
        assert len(report.paths) == 1
        assert get_feasibility_status(report.paths) == "single_supplier_option_ready"

    def test_two_suppliers_work(self):
        from src.b_side.workspace import create_b_workspace, save_b_workspace
        from src.b_side.requirement_structurer import structure_requirement
        from src.b_side.feasibility_engine import run_feasibility_simulation, get_feasibility_status
        from src.core_schema.b_side_types import SupplierResponseRecord
        import uuid

        ws = create_b_workspace("5000 pcs hats")
        req = structure_requirement(ws.b_workspace_id, "5000 pcs hats")
        ws.buyer_requirement = req
        ws.supplier_responses = [
            SupplierResponseRecord(
                response_id=f"resp_{uuid.uuid4().hex[:8]}",
                rfq_id=req.rfq_id,
                b_workspace_id=ws.b_workspace_id,
                supplier_id="sup_001",
                supplier_name="Factory A",
                can_make=True,
                estimated_lead_time_days=30,
                unit_price=3.50,
                currency="USD",
                confidence_score=0.9,
            ),
            SupplierResponseRecord(
                response_id=f"resp_{uuid.uuid4().hex[:8]}",
                rfq_id=req.rfq_id,
                b_workspace_id=ws.b_workspace_id,
                supplier_id="sup_002",
                supplier_name="Factory B",
                can_make=True,
                estimated_lead_time_days=40,
                unit_price=3.20,
                currency="USD",
                confidence_score=0.7,
            ),
        ]
        save_b_workspace(ws)

        report = run_feasibility_simulation(ws.b_workspace_id)
        assert len(report.paths) == 2
        assert get_feasibility_status(report.paths) == "available_supplier_options_ready"

    def test_no_supplier_does_not_fail(self):
        from src.b_side.workspace import create_b_workspace, save_b_workspace
        from src.b_side.requirement_structurer import structure_requirement
        from src.b_side.feasibility_engine import run_feasibility_simulation, get_feasibility_status

        ws = create_b_workspace("3000 pcs jackets")
        req = structure_requirement(ws.b_workspace_id, "3000 pcs jackets")
        ws.buyer_requirement = req
        ws.supplier_responses = []  # No responses yet
        save_b_workspace(ws)

        report = run_feasibility_simulation(ws.b_workspace_id)
        assert len(report.paths) == 0
        assert get_feasibility_status(report.paths) == "no_supplier_response_yet"

    def test_more_than_three_suppliers_ranked(self):
        from src.b_side.workspace import create_b_workspace, save_b_workspace
        from src.b_side.requirement_structurer import structure_requirement
        from src.b_side.feasibility_engine import run_feasibility_simulation, get_feasibility_status
        from src.core_schema.b_side_types import SupplierResponseRecord
        import uuid

        ws = create_b_workspace("2000 pcs bags")
        req = structure_requirement(ws.b_workspace_id, "2000 pcs bags")
        ws.buyer_requirement = req
        responses = []
        for i in range(5):
            responses.append(SupplierResponseRecord(
                response_id=f"resp_{uuid.uuid4().hex[:8]}",
                rfq_id=req.rfq_id,
                b_workspace_id=ws.b_workspace_id,
                supplier_id=f"sup_{i:03d}",
                supplier_name=f"Factory {chr(65 + i)}",
                can_make=True,
                estimated_lead_time_days=25 + i * 5,
                unit_price=2.0 + i * 0.5,
                currency="USD",
                confidence_score=0.9 - i * 0.05,
            ))
        ws.supplier_responses = responses
        save_b_workspace(ws)

        report = run_feasibility_simulation(ws.b_workspace_id)
        assert len(report.paths) == 5
        assert get_feasibility_status(report.paths) == "ranked_delivery_paths_ready"

        # Verify ranking is correct (highest score first)
        for i in range(len(report.paths) - 1):
            assert report.paths[i].rank <= report.paths[i + 1].rank

        # Test with max_recommended cap
        report_capped = run_feasibility_simulation(ws.b_workspace_id, max_recommended=3)
        assert len(report_capped.paths) == 3


# ─── Variable-M salesperson tests ────────────────────────────────────────────

class TestVariableMSalesperson:
    def test_customer_facing_role(self):
        role = resolve_trade_salesperson_role("customer_facing", "customer")
        assert role == "CUSTOMER_FACING_M_SIDE"

    def test_supplier_facing_role(self):
        role = resolve_trade_salesperson_role("supplier_facing", "supplier")
        assert role == "UPSTREAM_B_SIDE"

    def test_factory_facing_role(self):
        role = resolve_trade_salesperson_role("supplier_facing", "factory")
        assert role == "UPSTREAM_B_SIDE"

    def test_execution_role(self):
        role = resolve_trade_salesperson_role("execution", "")
        assert role == "TRADE_MERCHANDISER"

    def test_salesperson_receives_customer_message(self):
        """Salesperson receiving customer message → B-side project."""
        import uuid
        conv_id = f"conv_salesperson_{uuid.uuid4().hex[:8]}"
        result = adapt_openclaw_event({
            "source": "openclaw",
            "channel": "openclaw-weixin",
            "channel_account_id": "salesperson_account",
            "conversation_id": conv_id,
            "sender_id": "customer_abc",
            "sender_display_name": "Customer ABC",
            "message_text": "帮我询价 10000 件白色纯棉衬衣，45 天内交温哥华。",
            "mode": "b_side",
        })
        assert result["ok"] is True
        assert result["mode"] == "b_side"
        assert result["project_id"]

    def test_salesperson_handles_supplier_reply(self):
        """Same salesperson account receives supplier reply → M-side."""
        result = adapt_openclaw_event({
            "source": "openclaw",
            "channel": "openclaw-email",
            "channel_account_id": "salesperson_email",
            "conversation_id": "supplier_conv_for_salesperson",
            "sender_id": "supplier_for_salesperson",
            "sender_display_name": "Factory for Salesperson Test",
            "message_text": "We can make it. USD 4.80/pc. Lead time 38 days.",
            "project_id": "TRADE-PROJ-001",
            "mode": "m_side",
        })
        assert result["ok"] is True
        assert result["mode"] == "m_side"
        assert result["status"] == "supplier_response_received"

    def test_neutral_actor_model_preserved(self):
        """B-side / M-side are contextual roles — same sender can switch."""
        import uuid
        conv_id_customer = f"conv_cust_{uuid.uuid4().hex[:8]}"
        conv_id_supplier = f"conv_supp_{uuid.uuid4().hex[:8]}"

        # Same channel_account_id (salesperson account) receives customer message
        result_customer = adapt_openclaw_event({
            "source": "openclaw",
            "channel": "openclaw-weixin",
            "channel_account_id": "trade_salesperson_account",
            "conversation_id": conv_id_customer,
            "sender_id": "customer_xyz",
            "message_text": "帮我采购 5000 件T恤",
            "mode": "b_side",
        })
        assert result_customer["mode"] == "b_side"
        project_id = result_customer["project_id"]

        # Same salesperson receives supplier reply → M-side (different conversation)
        result_supplier = adapt_openclaw_event({
            "source": "openclaw",
            "channel": "openclaw-email",
            "channel_account_id": "trade_salesperson_account",
            "conversation_id": conv_id_supplier,
            "sender_id": "factory_abc",
            "message_text": "We can make 5000 T-shirts. USD 2.50/pc. Lead time 25 days.",
            "project_id": project_id,
            "mode": "m_side",
        })
        assert result_supplier["mode"] == "m_side"
        assert result_supplier["project_id"] == project_id
        # Neutral Actor Model: same salesperson, two contextual roles, same project
