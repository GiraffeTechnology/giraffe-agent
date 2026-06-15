def calculate_path_lead_time(supplier_packets: list[dict]) -> dict:
    """
    Compute lead time from a list of SupplierResponsePacket-like dicts.

    Parallel stages (take the max): fabric_lead_time_days, trim_lead_time_days,
    packaging_lead_time_days (from packaging supplier).
    Sequential stages (sum): production_time_days, qc_time_days, logistics_time_days.

    If any required value is None, calculated_total_lead_time_days = None.
    Never uses sentinel values (999, -1, 0) for missing data.
    """
    # Collect values across all packets
    def _get(field: str) -> int | None:
        for p in supplier_packets:
            val = p.get(field)
            if val is not None:
                return int(val)
        return None

    fabric = _get("fabric_lead_time_days")
    trim = _get("trim_lead_time_days")
    packaging = _get("packaging_lead_time_days") or _get("packaging_time_days")
    production = _get("production_time_days")
    qc = _get("qc_time_days")
    logistics = _get("logistics_time_days")

    parallel_breakdown = {
        "fabric_lead_time_days": fabric,
        "trim_lead_time_days": trim,
        "packaging_lead_time_days": packaging,
    }
    sequential_days = {
        "production_time_days": production,
        "qc_time_days": qc,
        "logistics_time_days": logistics,
    }

    # Determine which parallel values are present
    parallel_values = [v for v in parallel_breakdown.values() if v is not None]
    parallel_max = max(parallel_values) if parallel_values else None

    # Determine missing fields
    missing_fields: list[str] = []
    # For total lead time we need at minimum production + qc + logistics and one parallel
    if production is None:
        missing_fields.append("production_time_days")
    if qc is None:
        missing_fields.append("qc_time_days")
    if logistics is None:
        missing_fields.append("logistics_time_days")
    if fabric is None:
        missing_fields.append("fabric_lead_time_days")
    if trim is None:
        missing_fields.append("trim_lead_time_days")

    has_missing_values = len(missing_fields) > 0

    # Only compute total if ALL required fields are present
    if has_missing_values:
        calculated_total = None
    else:
        calculated_total = parallel_max + production + qc + logistics

    risk_flags: list[str] = []
    if has_missing_values:
        risk_flags.append(f"Lead time calculation incomplete due to missing: {missing_fields}")

    return {
        "parallel_max_days": parallel_max,
        "parallel_breakdown": parallel_breakdown,
        "sequential_days": sequential_days,
        "calculated_total_lead_time_days": calculated_total,
        "has_missing_values": has_missing_values,
        "missing_fields": missing_fields,
        "risk_flags": risk_flags,
    }
