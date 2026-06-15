from src.llm import get_llm_provider

_REQUIRED_FIELDS = [
    "unit_price", "currency", "moq", "sample_time_days",
    "fabric_lead_time_days", "trim_lead_time_days", "production_time_days",
    "qc_time_days", "packaging_time_days", "logistics_time_days",
    "total_lead_time_days", "payment_terms", "trade_terms",
    "capacity_available", "valid_until", "supplier_notes",
]


async def normalize_supplier_response(raw_text: str, rfq_content: dict) -> dict:
    """
    Extract structured response fields from raw supplier reply using LLM.
    Never invents data; sets missing fields to null and lists them in missing_fields.
    """
    llm = get_llm_provider()

    system = (
        "You are an expert apparel procurement analyst extracting structured data from supplier responses. "
        "Extract only what is explicitly stated. Set missing fields to null. "
        "Return ONLY valid JSON with exact field names requested."
    )
    prompt = (
        f"RFQ context: {rfq_content.get('rfq_subject', '')}\n"
        f"Supplier response:\n{raw_text}\n\n"
        f"Extract these fields: {', '.join(_REQUIRED_FIELDS)}\n"
        "Also include: missing_fields (list of field names not found), "
        "risk_flags (list of anomalies e.g. 'total lead time < sum of parts'), "
        "evidence_source (dict with source and excerpt)."
    )

    result = await llm.extract_json(prompt, system=system)

    if result.get("_stub"):
        missing = list(_REQUIRED_FIELDS)
        return {
            "_ai_generated": True,
            "_stub": True,
            "unit_price": None,
            "currency": None,
            "moq": None,
            "sample_time_days": None,
            "fabric_lead_time_days": None,
            "trim_lead_time_days": None,
            "production_time_days": None,
            "qc_time_days": None,
            "packaging_time_days": None,
            "logistics_time_days": None,
            "total_lead_time_days": None,
            "payment_terms": None,
            "trade_terms": None,
            "capacity_available": None,
            "valid_until": None,
            "supplier_notes": None,
            "missing_fields": missing,
            "risk_flags": [],
            "evidence_source": {"source": "supplier_raw_text", "excerpt": raw_text[:200]},
        }

    result["_ai_generated"] = True
    result.setdefault("evidence_source", {
        "source": "supplier_raw_text",
        "excerpt": raw_text[:200],
    })

    # Compute missing_fields based on nulls
    missing = [f for f in _REQUIRED_FIELDS if result.get(f) is None]
    result["missing_fields"] = missing

    # Basic risk flag: total lead time < sum of parts
    risk_flags = list(result.get("risk_flags", []))
    tlt = result.get("total_lead_time_days")
    parts = [
        result.get("sample_time_days") or 0,
        result.get("fabric_lead_time_days") or 0,
        result.get("trim_lead_time_days") or 0,
        result.get("production_time_days") or 0,
        result.get("qc_time_days") or 0,
        result.get("packaging_time_days") or 0,
        result.get("logistics_time_days") or 0,
    ]
    if tlt is not None and sum(parts) > 0 and tlt < sum(parts):
        risk_flags.append("total lead time < sum of parts")
    result["risk_flags"] = risk_flags

    return result
