from src.llm import get_llm_provider


async def draft_rfq_content(form_version: dict, participants: list[dict]) -> dict:
    """
    Draft RFQ content from the current form version using LLM.
    Asks suppliers to provide all required response fields.
    """
    llm = get_llm_provider()

    system = (
        "You are an expert apparel & textile procurement specialist drafting a Request for Quotation. "
        "Draft a professional RFQ based on the order requirements provided. "
        "The RFQ must ask suppliers to provide: unit price, currency, MOQ, sample lead time, "
        "fabric lead time, trim lead time, production time, QC time, packaging time, logistics time, "
        "total lead time, payment terms, trade terms, capacity available, valid until date. "
        "Return ONLY valid JSON."
    )
    prompt = (
        f"Order requirements: {form_version}\n"
        f"Recipients: {[p.get('name', '') for p in participants]}\n"
        "Draft a professional RFQ in JSON format with keys: "
        "rfq_subject, rfq_body, required_response_fields, form_version_snapshot, _ai_generated."
    )

    result = await llm.extract_json(prompt, system=system)

    if result.get("_stub"):
        return {
            "_stub": True,
            "_ai_generated": True,
            "rfq_subject": "[STUB] Manual RFQ subject required",
            "rfq_body": "[STUB] Manual RFQ input required.",
            "required_response_fields": [
                "unit_price", "currency", "moq", "sample_time_days",
                "fabric_lead_time_days", "trim_lead_time_days", "production_time_days",
                "qc_time_days", "packaging_time_days", "logistics_time_days",
                "total_lead_time_days", "payment_terms", "trade_terms",
                "capacity_available", "valid_until",
            ],
            "form_version_snapshot": form_version,
        }

    result["_ai_generated"] = True
    result.setdefault("form_version_snapshot", form_version)
    result.setdefault("required_response_fields", [
        "unit_price", "currency", "moq", "sample_time_days",
        "fabric_lead_time_days", "trim_lead_time_days", "production_time_days",
        "qc_time_days", "packaging_time_days", "logistics_time_days",
        "total_lead_time_days", "payment_terms", "trade_terms",
        "capacity_available", "valid_until",
    ])
    return result
