from src.lead_time.calculator import calculate_path_lead_time


def test_parallel_stages_take_maximum():
    packets = [{
        "fabric_lead_time_days": 20,
        "trim_lead_time_days": 15,
        "production_time_days": 25,
        "qc_time_days": 5,
        "logistics_time_days": 7,
    }]
    result = calculate_path_lead_time(packets)
    assert result["parallel_max_days"] == 20  # max(20, 15)
    assert result["calculated_total_lead_time_days"] == 20 + 25 + 5 + 7  # = 57


def test_missing_value_returns_none_not_sentinel():
    packets = [{"fabric_lead_time_days": None, "production_time_days": 25}]
    result = calculate_path_lead_time(packets)
    assert result["calculated_total_lead_time_days"] is None
    assert result["has_missing_values"] is True


def test_sequential_stages_are_summed():
    packets = [{
        "production_time_days": 25,
        "qc_time_days": 5,
        "logistics_time_days": 7,
        "fabric_lead_time_days": 10,
        "trim_lead_time_days": 8,
    }]
    result = calculate_path_lead_time(packets)
    seq = result["sequential_days"]
    assert seq["production_time_days"] + seq["qc_time_days"] + seq["logistics_time_days"] == 37


def test_no_sentinel_values():
    """calculated_total_lead_time_days must never be 999, -1, or 0 for missing data."""
    packets = [{"fabric_lead_time_days": None, "trim_lead_time_days": None}]
    result = calculate_path_lead_time(packets)
    assert result["calculated_total_lead_time_days"] is None
    # Never 999, -1
    assert result["calculated_total_lead_time_days"] != 999
    assert result["calculated_total_lead_time_days"] != -1


def test_missing_fields_listed():
    packets = [{
        "production_time_days": 25,
        "qc_time_days": 5,
        "logistics_time_days": 7,
        "fabric_lead_time_days": None,
        "trim_lead_time_days": 15,
    }]
    result = calculate_path_lead_time(packets)
    assert "fabric_lead_time_days" in result["missing_fields"]
    assert result["has_missing_values"] is True


def test_risk_flag_added_for_missing():
    packets = [{"fabric_lead_time_days": None}]
    result = calculate_path_lead_time(packets)
    assert any("incomplete" in f.lower() for f in result["risk_flags"])


def test_complete_calculation():
    packets = [{
        "fabric_lead_time_days": 20,
        "trim_lead_time_days": 15,
        "production_time_days": 30,
        "qc_time_days": 5,
        "logistics_time_days": 10,
    }]
    result = calculate_path_lead_time(packets)
    assert result["has_missing_values"] is False
    assert result["calculated_total_lead_time_days"] == 20 + 30 + 5 + 10  # 65


def test_multiple_packets_aggregate():
    """Multiple packets contribute their best values per field."""
    packets = [
        {"fabric_lead_time_days": 20, "production_time_days": 30},
        {"trim_lead_time_days": 15, "qc_time_days": 5, "logistics_time_days": 7},
    ]
    result = calculate_path_lead_time(packets)
    assert result["parallel_breakdown"]["fabric_lead_time_days"] == 20
    assert result["parallel_breakdown"]["trim_lead_time_days"] == 15
