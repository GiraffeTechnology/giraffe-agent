"""
B-side test fixtures and shared configuration.
"""
import json
import uuid
from pathlib import Path

import pytest

from src.core_schema.b_side_types import (
    BuyerRequirement,
    BWWorkspace,
    SupplierResponseRecord,
    DeliveryPath,
    FeasibilityReport,
    SupplierInquiryDraft,
)


@pytest.fixture(autouse=True)
def patch_m_event_logger(tmp_path, monkeypatch):
    """Redirect M-side event log to tmp_path in all tests."""
    import src.m_side.m_event_logger as mel
    monkeypatch.setattr(mel, "_EVENTS_FILE", tmp_path / "events.jsonl")


@pytest.fixture
def bw_id():
    return f"bw_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def rfq_id():
    return f"RFQ-{uuid.uuid4().hex[:8].upper()}"


@pytest.fixture
def sample_requirement(bw_id, rfq_id):
    return BuyerRequirement(
        rfq_id=rfq_id,
        b_workspace_id=bw_id,
        raw_text="100 pcs aluminum 6061 CNC bracket, tolerance ±0.05 mm, delivery before September 30, to Munich",
        category="cnc",
        quantity=100,
        material="aluminum 6061",
        specs_json={"tolerance": "±0.05 mm"},
        deadline="September 30",
        destination="Munich",
        confidence_score=1.0,
    )


@pytest.fixture
def sample_response(bw_id, rfq_id):
    return SupplierResponseRecord(
        response_id=f"RSP-{uuid.uuid4().hex[:8].upper()}",
        rfq_id=rfq_id,
        b_workspace_id=bw_id,
        supplier_id="sup_001",
        supplier_name="Shenzhen CNC Works",
        can_make=True,
        capacity_available=True,
        material_available=True,
        estimated_lead_time_days=20,
        unit_price=12.50,
        total_price=1250.0,
        currency="USD",
        qc_available=True,
        confidence_score=0.9,
        completeness_score=0.9,
    )


@pytest.fixture
def sample_workspace(bw_id, rfq_id, sample_requirement, sample_response, tmp_path, monkeypatch):
    import src.b_side.workspace as ws_module
    monkeypatch.setattr(ws_module, "_DATA_DIR", tmp_path / "b_side_workspaces")
    workspace = BWWorkspace(
        b_workspace_id=bw_id,
        rfq_id=rfq_id,
        raw_requirement="100 pcs aluminum 6061 CNC bracket",
        status="collecting_responses",
        buyer_requirement=sample_requirement,
        supplier_responses=[sample_response],
    )
    ws_module._ensure_dir()
    ws_module.save_b_workspace(workspace)
    return workspace


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"
