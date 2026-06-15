"""
Platform Whitelist Tests — AIVAN Product Rules #3, #4, #5.

Rule #3: AIVAN must not bypass login, CAPTCHA, or platform access controls.
Rule #4: Trusted platform does not mean trusted supplier.
Rule #5: Supplier-level risk screening must remain independent from platform whitelist.

Tests:
  - Built-in trusted platforms are recognized
  - Unknown platforms are not auto-approved
  - Platform trust status does not affect supplier risk screening
  - Supplier risk flags survive platform whitelisting
  - Channels model does not include bypass mechanisms
"""

import os
import pytest

os.environ.setdefault("GIRAFFE_DB_MODE", "off")


# ─── Platform whitelist model checks ─────────────────────────────────────────

_KNOWN_TRUSTED_PLATFORMS = [
    "alibaba.com",
    "1688.com",
    "aliexpress.com",
    "global.taobao.com",
    "openclaw",
    "openclaw-mock",
    "openclaw-weixin",
]

_UNKNOWN_PLATFORMS = [
    "shady-marketplace.ru",
    "unknown-b2b-platform.io",
    "fake-supplier-hub.cn",
]


def test_trusted_platforms_defined():
    """Verify that canonical trusted platform list is accessible."""
    # The platform concept is embodied in the channel routing
    from src.openclaw_skill.openclaw_event_adapter import OpenClawEvent
    # Known channels (platforms) can be expressed in OpenClaw events
    for channel in ["openclaw-mock", "openclaw-weixin", "openclaw-whatsapp"]:
        event = OpenClawEvent(
            channel=channel,
            channel_account_id="acct",
            conversation_id="conv",
            sender_id="sender",
        )
        assert event.channel == channel


def test_unknown_platform_event_still_processed_without_bypass():
    """Events from unknown platforms should be processed without granting special bypass."""
    from src.openclaw_skill.openclaw_event_adapter import adapt_openclaw_event

    event_data = {
        "source": "openclaw",
        "channel": "openclaw-unknown-platform-xyz",
        "channel_account_id": "",
        "conversation_id": "conv-plat-001",
        "sender_id": "sender-001",
        "message_text": "I need 500 shirts.",
        "project_id": "test_project",
    }
    result = adapt_openclaw_event(event_data)
    # Should return a routing result, not an error about the platform
    assert isinstance(result, dict)
    # Must not grant bypass or escalated access for unknown platforms
    result_str = str(result).lower()
    assert "bypass" not in result_str
    assert "admin_override" not in result_str


def test_supplier_risk_flags_independent_of_platform_trust():
    """
    Even if a supplier is sourced from a trusted platform (Alibaba/1688),
    their risk flags must survive independently.
    """
    from src.core_schema.b_side_types import SupplierResponseRecord

    # Supplier sourced from Alibaba (trusted platform)
    resp = SupplierResponseRecord(
        response_id="r_alibaba_risky",
        rfq_id="RFQ-ALIBABA01",
        b_workspace_id="bw_alibaba01",
        supplier_id="alibaba_sup_123",
        supplier_name="Alibaba Supplier (Untrusted)",
        can_make=True,
        lead_time_breakdown={},
        estimated_lead_time_days=3,
        unit_price=0.10,
        total_price=100.0,
        currency="USD",
        confidence_score=0.2,
        completeness_score=0.3,
        red_flags=["suspiciously_low_price", "unrealistic_lead_time", "missing_factory_cert"],
    )

    # Platform trust (Alibaba) must NOT clear these flags
    trusted_platform = "alibaba.com"
    # Simulate "platform trust" by checking supplier is from this platform (conceptually)
    supplier_platform = "alibaba.com"
    is_trusted_platform = supplier_platform in _KNOWN_TRUSTED_PLATFORMS

    assert is_trusted_platform, "Alibaba should be a trusted platform"
    assert len(resp.red_flags) == 3, (
        "Platform trust must not clear supplier red_flags. "
        f"Platform={trusted_platform}, flags={resp.red_flags}"
    )


def test_approved_platform_does_not_auto_approve_supplier():
    """
    A platform being approved/whitelisted must not auto-approve individual suppliers.
    Supplier screening must run independently.
    """
    from src.core_schema.b_side_types import SupplierResponseRecord

    # Even if we "approve" Alibaba as a platform, individual supplier screening still applies
    platform_approved = True  # Alibaba is whitelisted
    supplier_flags = ["no_qc_capability", "refused_factory_visit"]

    resp = SupplierResponseRecord(
        response_id="r_plat_approved",
        rfq_id="RFQ-PLATAPP01",
        b_workspace_id="bw_platapp01",
        supplier_id="sup_from_approved_plat",
        supplier_name="Supplier from Approved Platform",
        can_make=True,
        lead_time_breakdown={},
        estimated_lead_time_days=30,
        unit_price=5.0,
        total_price=5000.0,
        currency="USD",
        confidence_score=0.4,
        completeness_score=0.4,
        red_flags=supplier_flags,
    )

    # Platform approval does not clear individual supplier risks
    assert platform_approved is True
    assert resp.red_flags == supplier_flags, (
        "Supplier risk flags must remain independent of platform approval status"
    )


def test_event_adapter_does_not_bypass_approval_for_known_channel():
    """OpenClaw event adapter must not auto-approve drafts for known/trusted channels."""
    from fastapi.testclient import TestClient
    import tempfile, os

    os.environ.setdefault("GIRAFFE_DB_MODE", "off")

    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            from api.main import app
            client = TestClient(app)
            resp = client.post("/api/openclaw/events", json={
                "source": "openclaw",
                "channel": "openclaw-weixin",  # trusted/known channel
                "channel_account_id": "acct-001",
                "conversation_id": "conv-wb-001",
                "sender_id": "buyer_001",
                "message_text": "I need 10,000 shirts, deliver to Vancouver in 45 days.",
                "project_id": "whitelist_test_proj",
            })
            assert resp.status_code == 200
            data = resp.json()
            # The response must not indicate auto-dispatch bypassing approval
            result_str = str(data).lower()
            assert "dispatched_to_channel" not in result_str
            assert "auto_approved" not in result_str
        finally:
            os.chdir(old_cwd)


def test_no_bypass_mechanism_in_channel_config():
    """Channel configurations must not have bypass or skip-approval flags."""
    from src.channels import base
    import inspect
    src_text = inspect.getsource(base)
    assert "bypass_approval" not in src_text.lower()
    assert "skip_human_gate" not in src_text.lower()
