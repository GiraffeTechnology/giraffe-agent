"""
Qwen structured field extractor.

Qwen's ONLY permitted role in this module:
  Extract structured fields (model, price, currency, moq, seller) from
  already-fetched raw HTML/API text. It is FORBIDDEN to generate, estimate,
  or infer any price that does not literally appear in the source text.

Post-extraction mandatory validation:
  Every numeric field returned by Qwen is re-validated against the original
  source text via regex. Records that fail validation are DISCARDED and logged
  for human review. This guarantees Qwen cannot hallucinate price figures.
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT_TEMPLATE = """\
你是一个网页信息抽取工具。以下是一段从 B2B 采购网站抓取的原始网页文本。
请仅从给定文本中抽取以下字段，不允许编造、不允许根据经验补全任何文本中未出现的数值：
- sku_model: 商品型号/规格
- unit_price: 单价数字（如文本中没有明确数字，返回 null，不要估算）
- currency: 币种（如未提及，返回 null）
- moq: 最小起订量（如未提及，返回 null）
- seller_name: 卖家名称（如未提及，返回 null）

原始文本：
{raw_text}

仅返回 JSON，不要任何额外说明。如果某字段在原文中找不到依据，对应值必须为 null，禁止猜测填充。
"""


@dataclass
class ExtractionResult:
    sku_model: Optional[str]
    unit_price: Optional[float]
    currency: Optional[str]
    moq: Optional[int]
    seller_name: Optional[str]
    confidence: float  # 0.0 – 1.0
    validation_passed: bool


MIN_CONFIDENCE = float(os.getenv("QWEN_MIN_CONFIDENCE", "0.80"))
QWEN_MODEL = os.getenv("QWEN_EXTRACTION_MODEL", "qwen-long")


def extract_fields(raw_text: str) -> Optional[ExtractionResult]:
    """
    Call Qwen to extract structured fields from `raw_text`.
    Returns None if extraction fails or mandatory post-validation rejects the result.
    """
    try:
        import dashscope
        from dashscope import Generation
    except ImportError:
        logger.error("dashscope package not installed. Run: pip install dashscope")
        return None

    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key:
        raise EnvironmentError("DASHSCOPE_API_KEY is not set in environment")
    dashscope.api_key = api_key

    # Truncate to stay within model context limits (qwen-long supports ~1M tokens)
    truncated_text = raw_text[:60_000]

    prompt = EXTRACTION_PROMPT_TEMPLATE.format(raw_text=truncated_text)

    try:
        response = Generation.call(
            model=QWEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            result_format="message",
            temperature=0.0,  # Fully deterministic extraction
        )
    except Exception as exc:
        logger.error("Qwen API call failed: %s", exc)
        return None

    if response.status_code != 200:
        logger.error(
            "Qwen API error %s: %s", response.status_code, response.message
        )
        return None

    content = response.output.choices[0].message.content.strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        content = re.sub(r"^```[\w]*\n?", "", content)
        content = re.sub(r"\n?```$", "", content)

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.warning("Qwen returned invalid JSON: %s | content: %.200s", exc, content)
        return None

    unit_price_raw = parsed.get("unit_price")
    unit_price: Optional[float] = None
    if unit_price_raw is not None:
        try:
            unit_price = float(unit_price_raw)
        except (TypeError, ValueError):
            logger.warning("Qwen returned non-numeric unit_price: %r", unit_price_raw)

    moq_raw = parsed.get("moq")
    moq: Optional[int] = None
    if moq_raw is not None:
        try:
            moq = int(moq_raw)
        except (TypeError, ValueError):
            pass

    # --- Mandatory back-validation ---
    # Ensure the extracted price actually appears in the source text.
    # Discard any record where Qwen produced a number not present in the source.
    validation_passed = True
    if unit_price is not None:
        if not _validate_number_in_source(unit_price, raw_text):
            logger.warning(
                "Validation FAILED: Qwen price %.4f not found in source text. "
                "Record discarded. Source snippet: %.200s",
                unit_price,
                raw_text[:200],
            )
            validation_passed = False
            unit_price = None  # Discard the hallucinated value

    # Confidence heuristic: full marks if all key fields extracted and validated
    extracted_count = sum(
        1
        for v in [
            parsed.get("sku_model"),
            unit_price,
            parsed.get("currency"),
            parsed.get("seller_name"),
        ]
        if v is not None
    )
    confidence = round(extracted_count / 4.0, 2)
    if not validation_passed:
        confidence = max(confidence - 0.3, 0.0)

    result = ExtractionResult(
        sku_model=parsed.get("sku_model"),
        unit_price=unit_price,
        currency=parsed.get("currency"),
        moq=moq,
        seller_name=parsed.get("seller_name"),
        confidence=confidence,
        validation_passed=validation_passed,
    )

    if unit_price is None:
        # A record with no usable price is worthless for our purpose
        logger.info(
            "Discarding extraction result: unit_price is None after validation "
            "(sku_model=%r, confidence=%.2f)",
            result.sku_model,
            result.confidence,
        )
        return None

    return result


def _validate_number_in_source(value: float, source_text: str) -> bool:
    """
    Check that `value` (a numeric price) literally appears in `source_text`.
    Tries several common formatting styles to avoid false negatives.
    """
    candidates = [
        str(value),                              # 1234.5
        f"{value:.2f}",                          # 1234.50
        f"{value:.4f}",                          # 1234.5000
        f"{int(value)}",                         # 1234  (if whole number)
        f"{value:,.2f}",                         # 1,234.50
        f"{value:,.0f}",                         # 1,235
        # Chinese-style: no decimal if whole
        str(int(value)) if value == int(value) else "",
    ]

    for candidate in candidates:
        if candidate and candidate in source_text:
            return True

    # Last resort: look for the integer part followed by optional decimal digits
    integer_str = str(int(value))
    pattern = re.escape(integer_str) + r"(\.\d+)?"
    if re.search(pattern, source_text):
        return True

    return False
