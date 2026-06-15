from src.matching.scorer import score_participant_for_section, compute_risk_flags


def test_score_returns_all_dimensions():
    profile = {
        "product_categories": ["T-shirt"],
        "fabric_capabilities": ["cotton"],
        "moq": 500,
        "lead_time_days_min": 30,
        "lead_time_days_max": 45,
        "supported_trade_terms": ["FOB"],
        "country": "CN",
    }
    form_fields = {
        "product_type": "T-shirt",
        "fabric_type": "cotton",
        "quantity": 10000,
        "trade_term": "FOB",
        "destination": "Hamburg",
        "delivery_deadline": "2026-09-01",
    }
    section = {
        "section": "garment_manufacturing",
        "required_role": "MANUFACTURER",
        "form_fields": ["product_type"],
    }
    result = score_participant_for_section(profile, form_fields, None, section)
    assert "match_score" in result
    assert "score_breakdown" in result
    assert 0.0 <= result["match_score"] <= 1.0


def test_no_history_defaults_to_neutral():
    profile = {"product_categories": ["T-shirt"]}
    result = score_participant_for_section(profile, {}, None, {"section": "test", "form_fields": []})
    breakdown = result["score_breakdown"]
    assert breakdown["quality_history_fit"] == 0.5
    assert breakdown["on_time_delivery_fit"] == 0.5


def test_category_fit_exact_match():
    profile = {"product_categories": ["T-shirt"]}
    form_fields = {"product_type": "T-shirt"}
    result = score_participant_for_section(profile, form_fields, None, {"section": "test", "form_fields": []})
    assert result["score_breakdown"]["category_fit"] == 1.0


def test_category_fit_no_match():
    profile = {"product_categories": ["Jacket"]}
    form_fields = {"product_type": "T-shirt"}
    result = score_participant_for_section(profile, form_fields, None, {"section": "test", "form_fields": []})
    assert result["score_breakdown"]["category_fit"] == 0.0


def test_moq_fit_passes():
    profile = {"moq": 500}
    form_fields = {"quantity": 10000}
    result = score_participant_for_section(profile, form_fields, None, {"section": "test", "form_fields": []})
    assert result["score_breakdown"]["moq_fit"] == 1.0


def test_moq_fit_fails():
    profile = {"moq": 20000}
    form_fields = {"quantity": 1000}
    result = score_participant_for_section(profile, form_fields, None, {"section": "test", "form_fields": []})
    assert result["score_breakdown"]["moq_fit"] == 0.0


def test_quality_history_from_memory():
    profile = {}
    memory = {"qc_pass_rate": 0.95, "on_time_delivery_rate": 0.98, "quality_issue_count": 0}
    result = score_participant_for_section(profile, {}, memory, {"section": "test", "form_fields": []})
    assert result["score_breakdown"]["quality_history_fit"] == 0.95
    assert result["score_breakdown"]["on_time_delivery_fit"] == 0.98


def test_risk_penalty_applied_when_issues():
    profile = {}
    memory = {"quality_issue_count": 2, "qc_pass_rate": 0.5}
    result = score_participant_for_section(profile, {}, memory, {"section": "test", "form_fields": []})
    assert result["score_breakdown"]["risk_penalty"] == -1.0
    # Score must be < base score due to penalty
    assert result["match_score"] >= 0.0


def test_compute_risk_flags_no_history():
    flags = compute_risk_flags({}, None)
    assert "No quality history" in flags


def test_compute_risk_flags_low_qc():
    flags = compute_risk_flags({}, {"qc_pass_rate": 0.7, "quality_issue_count": 0})
    assert "Low QC pass rate" in flags


def test_compute_risk_flags_late_delivery():
    flags = compute_risk_flags({}, {"on_time_delivery_rate": 0.8, "quality_issue_count": 0})
    assert "Late delivery history" in flags


def test_compute_risk_flags_approaching_threshold():
    flags = compute_risk_flags({}, {"quality_issue_count": 2})
    assert "Approaching replacement threshold" in flags


def test_compute_risk_flags_incomplete_profile():
    flags = compute_risk_flags({"profile_completeness_score": 0.3}, None)
    assert "Incomplete profile" in flags


def test_missing_data_tracked():
    profile = {}  # no product_categories
    result = score_participant_for_section(profile, {}, None, {"section": "test", "form_fields": []})
    assert "product_categories" in result["missing_participant_data"]
