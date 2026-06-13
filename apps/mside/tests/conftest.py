"""
M-side test fixtures and shared configuration.
"""
import uuid
from pathlib import Path

import pytest

from src.core_schema.m_side_types import (
    MSideSupplierProfile,
    SupplierCapability,
    SupplierInquiryContext,
    MSideWorkspace,
    SupplierResponsePacket,
    CapacitySignal,
    ScheduleSignal,
    MaterialAvailability,
    SupplierQuote,
    QCCommitment,
    LogisticsCommitment,
)


@pytest.fixture(autouse=True)
def patch_m_event_logger(tmp_path, monkeypatch):
    """Redirect M-side event log to tmp_path in all tests."""
    import src.m_side.m_event_logger as mel
    monkeypatch.setattr(mel, "_EVENTS_FILE", tmp_path / "events.jsonl")


@pytest.fixture
def mw_id():
    return f"mw_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def bw_id():
    return f"bw_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def supplier_id():
    return f"sup_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def sample_supplier_profile(supplier_id):
    return MSideSupplierProfile(
        supplier_id=supplier_id,
        supplier_name="Shenzhen CNC Works Ltd",
        channel="mock",
        external_user_id=f"ext_{supplier_id}",
        language_preference="zh",
        region="Shenzhen",
        capability=SupplierCapability(
            categories=["cnc", "machining"],
            materials=["aluminum 6061", "stainless steel"],
            processes=["milling", "turning", "anodizing"],
        ),
    )


@pytest.fixture
def sample_inquiry_context(mw_id, bw_id, supplier_id):
    return SupplierInquiryContext(
        m_workspace_id=mw_id,
        b_workspace_id=bw_id,
        rfq_id="RFQ-TEST01",
        inquiry_id="INQ-TEST01",
        supplier_id=supplier_id,
        supplier_name="Shenzhen CNC Works Ltd",
        invitation_token="GQ-ABCD1234",
        inquiry_text_zh="你好，请问可以接受以下询盘？",
        inquiry_text_en="Hello, can you accept the following inquiry?",
    )


@pytest.fixture
def sample_m_workspace(mw_id, bw_id, supplier_id, sample_inquiry_context):
    return MSideWorkspace(
        m_workspace_id=mw_id,
        b_workspace_id=bw_id,
        rfq_id="RFQ-TEST01",
        inquiry_id="INQ-TEST01",
        supplier_id=supplier_id,
        supplier_name="Shenzhen CNC Works Ltd",
        invitation_token="GQ-ABCD1234",
        status="inquiry_received",
        inquiry_context=sample_inquiry_context,
        supplier_messages=[],
    )


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"
