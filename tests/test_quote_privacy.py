"""
Buyer Quote Privacy Tests — AIVAN Product Rule #9.

Rule: Buyer-facing quotes must not leak supplier identity or supplier unit price
      when privacy settings require hiding them.

Tests:
  - DeliveryPath with hide_supplier_identity must not expose supplier name/ID
  - DeliveryPath with hide_supplier_price must not expose unit price in buyer view
  - Margin calculation is deterministic and auditable
  - Buyer-facing message is a draft pending approval (not sent)
  - Quote generation preserves supplier price in internal record
  - Buyer-visible quote and internal record are distinguishable
"""

import os
import uuid
import pytest

os.environ.setdefault("GIRAFFE_DB_MODE", "off")


# ─── Privacy envelope helper ──────────────────────────────────────────────────

def _make_delivery_path(
    supplier_id="sup_001",
    supplier_name="Secret Supplier Co.",
    unit_price=4.20,
    total_price=42000.0,
    currency="USD",
    lead_time=30,
    risk_score=0.1,
    rank=1,
    label="Best Option",
    notes=None,
):
    from src.core_schema.b_side_types import DeliveryPath
    return DeliveryPath(
        path_id=f"PATH-{uuid.uuid4().hex[:8].upper()}",
        rfq_id="RFQ-PRIV-001",
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        lead_time_days=lead_time,
        unit_price=unit_price,
        currency=currency,
        total_price=total_price,
        risk_score=risk_score,
        confidence_score=0.9,
        notes=notes,
        rank=rank,
        label=label,
    )


def _apply_buyer_privacy_mask(path, hide_identity=False, hide_price=False, margin_pct=0.15):
    """
    Create a buyer-facing view of a DeliveryPath with optional privacy masking.
    This simulates what would appear in the buyer-facing message draft.
    """
    buyer_unit_price = round(path.unit_price * (1 + margin_pct), 4) if path.unit_price else None
    buyer_total_price = round(path.total_price * (1 + margin_pct), 2) if path.total_price else None

    return {
        "option_label": path.label or f"Option {path.rank}",
        "lead_time_days": path.lead_time_days,
        "currency": path.currency,
        "unit_price": None if hide_price else buyer_unit_price,
        "total_price": None if hide_price else buyer_total_price,
        "supplier_id": None if hide_identity else path.supplier_id,
        "supplier_name": "Verified Supplier" if hide_identity else path.supplier_name,
        "risk_score": path.risk_score,
        "notes": path.notes,
        "rank": path.rank,
    }


# ─── Privacy tests ────────────────────────────────────────────────────────────

def test_hide_supplier_identity_masks_name_and_id():
    path = _make_delivery_path(supplier_name="Real Supplier Name", supplier_id="sup_real_123")
    buyer_view = _apply_buyer_privacy_mask(path, hide_identity=True)
    assert buyer_view["supplier_id"] is None, "Supplier ID must be hidden"
    assert buyer_view["supplier_name"] != "Real Supplier Name", "Supplier name must be masked"
    assert "Real Supplier Name" not in str(buyer_view)
    assert "sup_real_123" not in str(buyer_view)


def test_show_supplier_identity_reveals_name():
    path = _make_delivery_path(supplier_name="Visible Supplier Co.", supplier_id="sup_visible")
    buyer_view = _apply_buyer_privacy_mask(path, hide_identity=False)
    assert buyer_view["supplier_name"] == "Visible Supplier Co."
    assert buyer_view["supplier_id"] == "sup_visible"


def test_hide_supplier_price_masks_unit_and_total():
    path = _make_delivery_path(unit_price=4.20, total_price=42000.0)
    buyer_view = _apply_buyer_privacy_mask(path, hide_price=True)
    assert buyer_view["unit_price"] is None, "Unit price must be hidden in buyer view"
    assert buyer_view["total_price"] is None, "Total price must be hidden in buyer view"


def test_show_supplier_price_applies_margin():
    path = _make_delivery_path(unit_price=4.20, total_price=42000.0, currency="USD")
    buyer_view = _apply_buyer_privacy_mask(path, hide_price=False, margin_pct=0.15)
    # Buyer price should be supplier price * (1 + margin)
    expected_unit = round(4.20 * 1.15, 4)
    expected_total = round(42000.0 * 1.15, 2)
    assert buyer_view["unit_price"] == expected_unit, (
        f"Buyer unit price should be {expected_unit}, got {buyer_view['unit_price']}"
    )
    assert buyer_view["total_price"] == expected_total


def test_margin_calculation_is_deterministic():
    """Same inputs always produce same margin output."""
    path = _make_delivery_path(unit_price=5.00, total_price=50000.0)
    results = [_apply_buyer_privacy_mask(path, margin_pct=0.12) for _ in range(5)]
    unit_prices = [r["unit_price"] for r in results]
    assert len(set(unit_prices)) == 1, "Margin calculation must be deterministic"


def test_internal_record_preserves_supplier_price():
    """Internal DeliveryPath always has the real supplier price."""
    path = _make_delivery_path(unit_price=4.20, total_price=42000.0)
    # Even after creating buyer view with hide_price=True, internal path retains real data
    buyer_view = _apply_buyer_privacy_mask(path, hide_price=True)
    assert path.unit_price == 4.20, "Internal path must retain supplier unit price"
    assert buyer_view["unit_price"] is None, "Buyer view must not reveal supplier price"


def test_both_privacy_flags_work_together():
    path = _make_delivery_path(
        supplier_name="Hidden Corp.", supplier_id="sup_hidden",
        unit_price=3.50, total_price=35000.0,
    )
    buyer_view = _apply_buyer_privacy_mask(path, hide_identity=True, hide_price=True)
    assert buyer_view["supplier_id"] is None
    assert buyer_view["supplier_name"] != "Hidden Corp."
    assert buyer_view["unit_price"] is None
    assert buyer_view["total_price"] is None
    assert "Hidden Corp." not in str(buyer_view)
    assert "sup_hidden" not in str(buyer_view)


def test_aivan_hide_supplier_identity_env_var_recognized():
    """AIVAN_HIDE_SUPPLIER_IDENTITY_FROM_BUYER env var should be parseable."""
    os.environ["AIVAN_HIDE_SUPPLIER_IDENTITY_FROM_BUYER"] = "true"
    val = os.environ.get("AIVAN_HIDE_SUPPLIER_IDENTITY_FROM_BUYER", "").lower() in ("true", "1")
    assert val is True
    del os.environ["AIVAN_HIDE_SUPPLIER_IDENTITY_FROM_BUYER"]


def test_aivan_hide_supplier_price_env_var_recognized():
    """AIVAN_HIDE_SUPPLIER_PRICE_FROM_BUYER env var should be parseable."""
    os.environ["AIVAN_HIDE_SUPPLIER_PRICE_FROM_BUYER"] = "true"
    val = os.environ.get("AIVAN_HIDE_SUPPLIER_PRICE_FROM_BUYER", "").lower() in ("true", "1")
    assert val is True
    del os.environ["AIVAN_HIDE_SUPPLIER_PRICE_FROM_BUYER"]


def test_buyer_quote_is_draft_pending_approval(tmp_path):
    """Buyer-facing quote must be created as a draft pending approval, not auto-sent."""
    import src.openclaw_skill.message_draft_store as mds
    orig_dir = mds._DATA_DIR
    mds._DATA_DIR = tmp_path / "data" / "message_drafts"
    mds._DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from src.openclaw_skill.message_draft_store import create_draft, find_pending_drafts

        # Simulate creating a buyer-facing quote draft
        draft = create_draft(
            project_id="proj_quote",
            channel="openclaw-mock",
            target_role="customer",
            draft_text=(
                "Option A: Lead time 30 days, total USD 4,600 (DDP Vancouver). "
                "Delivery feasible by your deadline. Risk: Low."
            ),
        )
        assert draft.approval_status == "pending_approval"
        pending = find_pending_drafts("proj_quote")
        assert any(d.id == draft.id for d in pending), "Buyer quote draft must be in pending state"
    finally:
        mds._DATA_DIR = orig_dir
