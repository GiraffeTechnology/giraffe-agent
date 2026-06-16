"""
Supplier Evaluation Tests — AIVAN supplier evaluation + Qwen ranking + persistence.

Uses a fake QwenProvider (no real network calls) to test the orchestration,
persistence, and malformed-output fallback contract.
"""
import os
import pytest

os.environ.setdefault("GIRAFFE_DB_MODE", "off")

from src.llm.provider_base import LLMJsonResult
from src.b_side.supplier_evaluation import (
    SupplierCandidate,
    evaluate_suppliers,
    get_supplier_evaluation,
    save_supplier_evaluation,
)


@pytest.fixture()
def eval_dir(tmp_path, monkeypatch):
    import src.b_side.supplier_evaluation as mod
    original = mod._DATA_DIR
    mod._DATA_DIR = tmp_path / "supplier_evaluations"
    yield mod._DATA_DIR
    mod._DATA_DIR = original


class FakeProviderWellFormed:
    provider_name = "qwen"

    def extract_json(self, prompt, schema_hint=None, **kwargs):
        return LLMJsonResult(
            data={
                "ranked_suppliers": [
                    {"supplier_name": "Acme Garment Co.", "rank": 1, "score_0_100": 90, "reason_zh": "经验丰富"},
                ],
                "recommended_supplier": "Acme Garment Co.",
                "overall_risk_notes_zh": "无明显风险",
            },
            provider_name="qwen",
            model_name="qwen-turbo",
            raw_text='{"ranked_suppliers": [...]}',
            usage={"total_tokens": 123},
        )


class FakeProviderMalformed:
    provider_name = "qwen"

    def extract_json(self, prompt, schema_hint=None, **kwargs):
        # Mirrors _extract_json_from_text's fallback shape for non-JSON output.
        return LLMJsonResult(
            data={"raw_text": "I cannot produce JSON right now."},
            provider_name="qwen",
            model_name="qwen-turbo",
            raw_text="I cannot produce JSON right now.",
            usage={},
        )


def _candidate():
    return SupplierCandidate(
        supplier_name="Acme Garment Co.",
        product_title="Cotton T-Shirt",
        moq="2 pieces",
        price_range_usd="3.00-4.00",
        years_on_platform=10,
        source_url="https://www.alibaba.com/showroom/cotton-shirt.html",
    )


def test_evaluate_suppliers_parses_wellformed_response_and_persists(eval_dir):
    report = evaluate_suppliers(
        candidates=[_candidate()],
        rfq_id="RFQ-1",
        b_workspace_id="bw_1",
        category="棉质T恤",
        provider=FakeProviderWellFormed(),
    )
    assert report.parse_ok is True
    assert report.recommended_supplier == "Acme Garment Co."
    assert report.ranked_suppliers[0].score_0_100 == 90
    assert (eval_dir / f"{report.evaluation_id}.json").exists()


def test_evaluate_suppliers_falls_back_on_malformed_llm_output(eval_dir):
    report = evaluate_suppliers(
        candidates=[_candidate()],
        rfq_id="RFQ-2",
        b_workspace_id="bw_1",
        provider=FakeProviderMalformed(),
    )
    assert report.parse_ok is False
    assert report.recommended_supplier is None
    assert report.ranked_suppliers == []
    assert "cannot produce JSON" in report.llm_raw_text


def test_evaluate_suppliers_raises_when_llm_call_fails(eval_dir):
    class FailingProvider:
        provider_name = "qwen"

        def extract_json(self, prompt, schema_hint=None, **kwargs):
            raise RuntimeError("Qwen API call failed after 3 attempts")

    with pytest.raises(RuntimeError):
        evaluate_suppliers(
            candidates=[_candidate()],
            rfq_id="RFQ-3",
            b_workspace_id="bw_1",
            provider=FailingProvider(),
        )


def test_get_supplier_evaluation_roundtrip(eval_dir):
    report = evaluate_suppliers(
        candidates=[_candidate()],
        rfq_id="RFQ-4",
        b_workspace_id="bw_1",
        provider=FakeProviderWellFormed(),
    )
    fetched = get_supplier_evaluation(report.evaluation_id)
    assert fetched is not None
    assert fetched.evaluation_id == report.evaluation_id
    assert fetched.recommended_supplier == "Acme Garment Co."


def test_get_supplier_evaluation_returns_none_for_missing_id(eval_dir):
    assert get_supplier_evaluation("SEV-DOES-NOT-EXIST") is None
