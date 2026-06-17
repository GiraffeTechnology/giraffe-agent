"""Tests for QC process card."""
import pytest
from src.merchandiser.qc.qc_process_card import (
    create_process_card, get_process_card, render_process_card_for_llm,
    redact_process_card_for_llm, QCProcessCard
)

_PROJECT = "PROJ-PC-01"

def test_create_process_card_returns_card():
    card = create_process_card(
        project_id=_PROJECT,
        category="apparel",
        material_spec="100% cotton",
        color_spec="Navy blue",
        defect_criteria="No pilling, no loose threads",
        unit_price=12.5,
        supplier_contact="factory@example.com",
    )
    assert isinstance(card, QCProcessCard)
    assert card.process_card_id.startswith("PC-")
    assert card.category == "apparel"
    assert card.unit_price == 12.5

def test_get_process_card_returns_most_recent():
    project = "PROJ-PC-GET-01"
    card = create_process_card(project_id=project, category="apparel")
    retrieved = get_process_card(project)
    assert retrieved is not None
    assert retrieved.process_card_id == card.process_card_id

def test_get_process_card_missing_project_returns_none():
    result = get_process_card("PROJ-NONEXISTENT-CARD-99999")
    assert result is None

def test_render_process_card_for_llm_excludes_pricing(monkeypatch):
    monkeypatch.setenv("QC_ALLOW_EXTERNAL_LLM", "false")
    monkeypatch.setenv("QC_ALLOW_CAD_TO_LLM", "false")
    card = create_process_card(
        project_id="PROJ-PC-RENDER-01",
        category="apparel",
        unit_price=99.99,
        supplier_contact="secret@factory.com",
        color_spec="Red",
    )
    rendered = render_process_card_for_llm(card)
    assert "99.99" not in rendered
    assert "secret@factory.com" not in rendered
    assert "Red" in rendered

def test_render_process_card_redacts_material_by_default(monkeypatch):
    monkeypatch.setenv("QC_ALLOW_CAD_TO_LLM", "false")
    monkeypatch.setenv("QC_ALLOW_EXTERNAL_LLM", "false")
    card = create_process_card("PROJ-PC-RMAT-01", "apparel", material_spec="100% silk")
    rendered = render_process_card_for_llm(card)
    assert "100% silk" not in rendered
    assert "redacted" in rendered

def test_redact_process_card_for_llm_never_exposes_pricing():
    card = create_process_card(
        project_id="PROJ-PC-REDACT-01",
        category="apparel",
        unit_price=150.0,
        supplier_contact="contact@mfg.com",
        contract_terms="Net 30 days",
        color_spec="White",
    )
    redacted = redact_process_card_for_llm(card)
    assert "unit_price" not in redacted or redacted.get("unit_price") is None
    assert "supplier_contact" not in redacted
    assert "contract_terms" not in redacted
    assert redacted["color_spec"] == "White"
