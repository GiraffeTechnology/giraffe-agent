"""
B-side supplier evaluation — turns discovered/structured supplier candidates
into a Qwen-ranked comparison, with file-backed persistence
(data/b_side/supplier_evaluations/), mirroring the qc_result_store pattern.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from src.llm.qwen_provider import QwenProvider
from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/b_side/supplier_evaluations")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SupplierCandidate(BaseModel):
    supplier_name: str
    product_title: str
    moq: str | None = None
    price_range_usd: str | None = None
    sold_count: str | None = None
    years_on_platform: int | None = None
    source_url: str = ""


class RankedSupplier(BaseModel):
    supplier_name: str
    rank: int
    score_0_100: float
    reason_zh: str = ""


class SupplierEvaluationReport(BaseModel):
    evaluation_id: str
    rfq_id: str
    b_workspace_id: str
    candidates: list[SupplierCandidate]
    ranked_suppliers: list[RankedSupplier] = Field(default_factory=list)
    recommended_supplier: str | None = None
    overall_risk_notes_zh: str = ""
    provider_name: str = "qwen"
    model_name: str = ""
    llm_raw_text: str = ""
    parse_ok: bool = True
    usage: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)


def _data_dir() -> Path:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR


def _report_path(evaluation_id: str) -> Path:
    return _data_dir() / f"{evaluation_id}.json"


def save_supplier_evaluation(report: SupplierEvaluationReport) -> SupplierEvaluationReport:
    with open(_report_path(report.evaluation_id), "w", encoding="utf-8") as f:
        json.dump(report.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
    log_m_event(
        event_type="SUPPLIER_EVALUATION_SAVED",
        b_workspace_id=report.b_workspace_id,
        rfq_id=report.rfq_id,
        payload={"evaluation_id": report.evaluation_id, "recommended_supplier": report.recommended_supplier},
    )
    return report


def get_supplier_evaluation(evaluation_id: str) -> SupplierEvaluationReport | None:
    path = _report_path(evaluation_id)
    if not path.exists():
        return None
    return SupplierEvaluationReport.model_validate_json(path.read_text(encoding="utf-8"))


_PROMPT_TEMPLATE = (
    "你是AIVAN贸易助手的供应商评估模块。基于以下供应商公开信息，"
    "为买家(采购{category})生成供应商对比评估。\n"
    "供应商数据：\n{candidates_json}\n\n"
    '请严格输出JSON，字段：ranked_suppliers(数组，每项含supplier_name, rank, score_0_100, reason_zh), '
    "recommended_supplier, overall_risk_notes_zh。"
)


def evaluate_suppliers(
    candidates: list[SupplierCandidate],
    rfq_id: str,
    b_workspace_id: str,
    category: str = "商品",
    provider: QwenProvider | None = None,
) -> SupplierEvaluationReport:
    """
    Calls Qwen (or an injected provider) to rank supplier candidates.
    Never raises on malformed LLM output — falls back to parse_ok=False with
    the raw text preserved so a human/downstream step can inspect it.
    Raises only if the LLM call itself fails (network/auth) — same as
    QwenProvider's own contract — so callers can apply retry/fallback policy.
    """
    provider = provider or QwenProvider()
    candidates_json = json.dumps([c.model_dump() for c in candidates], ensure_ascii=False)
    prompt = _PROMPT_TEMPLATE.format(category=category, candidates_json=candidates_json)

    result = provider.extract_json(
        prompt,
        schema_hint='{"ranked_suppliers": [...], "recommended_supplier": "...", "overall_risk_notes_zh": "..."}',
    )

    data = result.data
    parse_ok = "raw_text" not in data  # _extract_json_from_text wraps failures as {"raw_text": ...}
    ranked = []
    recommended = None
    notes = ""
    if parse_ok:
        try:
            ranked = [RankedSupplier(**r) for r in data.get("ranked_suppliers", [])]
            recommended = data.get("recommended_supplier")
            notes = data.get("overall_risk_notes_zh", "")
        except Exception:
            parse_ok = False

    report = SupplierEvaluationReport(
        evaluation_id=f"SEV-{uuid.uuid4().hex[:10].upper()}",
        rfq_id=rfq_id,
        b_workspace_id=b_workspace_id,
        candidates=candidates,
        ranked_suppliers=ranked,
        recommended_supplier=recommended,
        overall_risk_notes_zh=notes,
        provider_name=result.provider_name,
        model_name=result.model_name,
        llm_raw_text=result.raw_text,
        parse_ok=parse_ok,
        usage=result.usage,
    )
    return save_supplier_evaluation(report)
