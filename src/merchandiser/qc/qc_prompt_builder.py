"""Builds QC comparison prompts — Chinese-first / bilingual."""

_QC_SYSTEM_PROMPT = (
    "你是 Giraffe Agent 的 AI QC 助理。请对比：\n"
    "1. M 端上传的生产图片 / 视频帧；\n"
    "2. 标准图 / approved sample / golden sample；\n"
    "3. 工艺卡 / process card；\n"
    "4. 订单要求。\n"
    "请判断实际生产是否与标准一致，并输出严格 JSON。\n"
    "要求：\n"
    "- 不要虚构无法从图片判断的尺寸；\n"
    "- 如果看不清，请要求 M 端补充近照；\n"
    "- 不要作最终法律验收；\n"
    "- 重点生成可执行的 M 端返工 / 补图 / 复检建议；\n"
    "- 严重问题才要求 buyer review；\n"
    "- 输出中必须包含中文 M-side feedback。\n"
)

_QC_JSON_SCHEMA = """\
{
  "overall_result": "pass | needs_fix | buyer_review_required | reject | unknown",
  "overall_score": 0.0,
  "severity": "low | medium | high | critical | unknown",
  "detected_deviations": [
    {"field": "", "expected": "", "actual": "", "severity": "low|medium|high|critical", "note": ""}
  ],
  "process_card_violations": [],
  "buyer_confirmation_required": false,
  "human_review_required": false,
  "m_side_feedback_zh": "",
  "m_side_feedback_en": "",
  "b_side_summary": ""
}\
"""


def build_qc_system_prompt() -> str:
    return _QC_SYSTEM_PROMPT


def build_qc_user_prompt(
    milestone_type: str | None = None,
    order_requirements: str | None = None,
    process_card_notes: str | None = None,
    standard_image_count: int = 0,
    production_image_count: int = 0,
) -> str:
    parts = []
    if milestone_type:
        parts.append(f"生产阶段 / Milestone: {milestone_type}")
    if order_requirements:
        parts.append(f"订单要求 / Order requirements:\n{order_requirements}")
    if process_card_notes:
        parts.append(f"工艺卡 / Process card:\n{process_card_notes}")
    parts.append(
        f"图片说明: 前 {standard_image_count} 张为标准图 / golden sample，"
        f"后 {production_image_count} 张为实际生产图。"
    )
    parts.append(f"\n请严格按以下 JSON schema 输出，不含 markdown fences：\n{_QC_JSON_SCHEMA}")
    return "\n\n".join(parts)
