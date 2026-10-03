"""Bounded default-language regressions; no live model or commercial send."""
from types import SimpleNamespace

import pytest


def test_order_acknowledgement_defaults_preserve_the_handler(monkeypatch):
    from api.main import AcknowledgeOrderRequest
    from src.openclaw_skill import m_side_actions

    assert AcknowledgeOrderRequest().message == "Order acknowledged."
    calls = []
    monkeypatch.setattr(
        m_side_actions, "acknowledge_order",
        lambda order_id, message: calls.append((order_id, message)) or
        SimpleNamespace(status="acknowledged"),
    )
    monkeypatch.setattr(m_side_actions, "format_order_execution", lambda order: {})
    m_side_actions.handle_m_side_submit_order_acknowledgement({"order_execution_id": "order-1"})
    assert calls == [("order-1", "Order acknowledged.")]


def test_supplier_questions_default_to_existing_english_copy():
    from src.m_side.supplier_clarification import generate_supplier_questions

    questions = generate_supplier_questions(SimpleNamespace(response_packet=None))
    assert questions[0] == {
        "field": "can_make", "question": "Can your company produce this item? (Yes / No)", "lang": "en",
    }
    assert {row["lang"] for row in questions} == {"en"}


def test_qwen_schema_instruction_is_english_without_an_external_call(monkeypatch):
    from src.llm.qwen_provider import QwenProvider
    import src.llm.qwen_provider as qwen

    prompts = []
    monkeypatch.setattr(qwen, "get_qwen_api_key", lambda: "")
    provider = QwenProvider()
    monkeypatch.setattr(
        provider, "complete_text",
        lambda prompt, **kwargs: prompts.append(prompt) or
        SimpleNamespace(text="{}", usage={}),
    )
    provider.extract_json("Inspect the supplied evidence.", schema_hint='{"type":"object"}')
    assert "Return only JSON matching the following schema, without additional text:" in prompts[0]
    assert '{"type":"object"}' in prompts[0]


def test_qc_prompt_and_mock_keep_the_report_schema_english():
    from src.llm.mock_provider import MockLLMProvider
    from src.merchandiser.qc.qc_prompt_builder import build_qc_system_prompt, build_qc_user_prompt

    system = build_qc_system_prompt()
    user = build_qc_user_prompt("final_qc", "Inspect cotton shirt seams.", "Check stitching.", 1, 2)
    assert "Use English for all business feedback and summaries." in system
    assert "m_side_feedback_zh field as empty" in system
    assert "the first 1 images" in user and "following 2 images" in user
    result = MockLLMProvider().extract_json("Inspect the sample.").data
    assert result["m_side_feedback_zh"] == ""
    assert "Images received" in result["m_side_feedback_en"]


@pytest.mark.parametrize("result", ["pass", "needs_fix", "buyer_review_required", "reject", "unknown"])
def test_qc_feedback_does_not_manufacture_a_localized_copy(result):
    from src.merchandiser.qc.qc_feedback_generator import generate_m_side_qc_feedback
    from src.merchandiser.qc.qc_models import QCComparisonReport

    report = QCComparisonReport(overall_result=result)
    feedback = generate_m_side_qc_feedback(report)
    assert feedback["feedback_zh"] == ""
    assert feedback["feedback_en"]
    assert "\u8bf7" not in feedback["feedback_en"]


def test_existing_localized_history_is_not_replaced_with_english():
    from src.merchandiser.qc.qc_feedback_generator import generate_m_side_qc_feedback
    from src.merchandiser.qc.qc_models import QCComparisonReport

    original = "\u68c0\u9a8c\u901a\u8fc7"
    report = QCComparisonReport(overall_result="pass", m_side_feedback_zh=original)
    assert generate_m_side_qc_feedback(report)["feedback_zh"] == original
    assert report.m_side_feedback_zh == original


def test_default_logistics_and_rfq_mock_packets_are_english():
    from src.logistics.providers.mock_provider import MockProvider
    from aivan.llm.providers.mock_provider import MOCK_RESPONSES

    assert [event["status_text"] for event in MockProvider().fetch_tracking_events("sf", "TEST-001")] == [
        "label created", "Picked up", "In transit", "Delivered",
    ]
    assert MOCK_RESPONSES["requirement_structuring"]["language"] == "en"
    assert MOCK_RESPONSES["missing_field_clarification"]["missing_fields"][0]["question"] == (
        "What is the fabric weight in GSM?"
    )


def test_escaped_input_recognition_vectors_retain_their_semantics():
    from aivan.agents.requirement_agent import _deterministic_parse

    parsed = _deterministic_parse("100\u4ef6 180gsm 45\u5929 \u7f8e\u51434.80 \u7a7a\u8fd0 DDP")
    assert parsed == {
        "quantity": 100, "gsm": 180, "delivery_days": 45,
        "target_unit_price": 4.8, "incoterms": "DDP", "logistics_preference": "air",
    }
