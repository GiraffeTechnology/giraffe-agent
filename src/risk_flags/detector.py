from datetime import date, datetime, timezone


def detect_decision_risk_flags(
    option_data: dict,
    form_fields: dict,
) -> list[str]:
    """Detect risk flags for a decision option."""
    flags: list[str] = []

    calc_total = option_data.get("calculated_total_lead_time_days")
    supplier_stated = option_data.get("supplier_stated_lead_time_days")
    unit_price = option_data.get("unit_price")
    capacity = option_data.get("capacity_available")
    valid_until = option_data.get("valid_until")
    missing_lt = option_data.get("missing_fields", [])

    # Deadline check
    deadline_raw = form_fields.get("delivery_deadline")
    if calc_total is not None and deadline_raw:
        try:
            if isinstance(deadline_raw, str):
                deadline = datetime.fromisoformat(deadline_raw).date()
            elif isinstance(deadline_raw, date):
                deadline = deadline_raw
            else:
                deadline = None
            if deadline:
                days_remaining = (deadline - date.today()).days
                if calc_total > days_remaining:
                    flags.append(
                        f"Total calculated lead time ({calc_total} days) "
                        f"exceeds delivery deadline ({days_remaining} days)"
                    )
        except (ValueError, TypeError):
            pass

    # Supplier stated vs calculated discrepancy
    if supplier_stated is not None and calc_total is not None:
        if supplier_stated < calc_total:
            flags.append(
                f"Supplier stated lead time ({supplier_stated}) less than "
                f"calculated lead time ({calc_total}) — verify"
            )

    # Missing lead time fields
    if missing_lt:
        flags.append(f"Missing lead time fields: {missing_lt}")

    # Price missing
    if unit_price is None:
        flags.append("Price missing — cannot compare cost")

    # No capacity confirmation
    if capacity is None:
        flags.append("No capacity confirmation")

    # Quote validity
    if valid_until:
        try:
            if isinstance(valid_until, str):
                vu_date = datetime.fromisoformat(valid_until)
            elif isinstance(valid_until, datetime):
                vu_date = valid_until
            else:
                vu_date = None
            if vu_date:
                now = datetime.now(timezone.utc)
                days_until_expiry = (vu_date.replace(tzinfo=timezone.utc) - now).days
                if days_until_expiry < 3:
                    flags.append("Quote validity expires before expected order confirmation")
        except (ValueError, TypeError):
            pass

    # Multiple risk flags on primary supplier
    supplier_flags = option_data.get("risk_flags", [])
    if len(supplier_flags) >= 2:
        flags.append("Multiple risk flags on primary supplier")

    return flags


def generate_comparison_summary(options: list[dict]) -> str:
    """Generate plain-text comparison summary across options."""
    if not options:
        return "No options available for comparison."

    lines = []
    sorted_by_price = sorted(
        [o for o in options if o.get("unit_price") is not None],
        key=lambda x: x["unit_price"],
    )
    sorted_by_lt = sorted(
        [o for o in options if o.get("calculated_total_lead_time_days") is not None],
        key=lambda x: x["calculated_total_lead_time_days"],
    )

    for i, opt in enumerate(options):
        idx = opt.get("option_index", i + 1)
        price = opt.get("unit_price")
        lt = opt.get("calculated_total_lead_time_days")
        risk_count = len(opt.get("risk_flags") or [])
        parts = [f"Option {idx}:"]
        if price:
            parts.append(f"${price:.2f}/{opt.get('currency', 'USD')}")
        if lt:
            parts.append(f"{lt}d lead time")
        if risk_count:
            parts.append(f"{risk_count} risk flag(s)")
        lines.append(" ".join(parts))

    if sorted_by_price:
        best_price_idx = sorted_by_price[0].get("option_index", 1)
        lines.append(f"Option {best_price_idx} offers the lowest price.")
    if sorted_by_lt:
        fastest_idx = sorted_by_lt[0].get("option_index", 1)
        lines.append(f"Option {fastest_idx} offers the fastest delivery.")

    return " | ".join(lines)
