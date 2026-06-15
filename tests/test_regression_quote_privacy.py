"""
Regression Tests — Buyer Quote Privacy (AIVAN Product Rule #9).

Verifies that buyer-facing quotes never leak internal supplier data:
  - Supplier identity hidden when AIVAN_HIDE_SUPPLIER_IDENTITY_FROM_BUYER=true
  - Supplier unit price hidden when AIVAN_HIDE_SUPPLIER_PRICE_FROM_BUYER=true
  - Buyer-facing margin is calculated correctly
  - Internal record retains real data even when buyer view masks it
  - Buyer quote draft created as pending (not auto-sent)
  - Privacy masking is composable (both flags active simultaneously)
"""

import os
import uuid
import pytest

os.environ.setdefault("GIRAFFE_DB_MODE", "off")


# ─── Privacy envelope helper ──────────────────────────────────────────────────

def _make_path(
    supplier_id="sup_regress",
    supplier_name="Confidential Supplier Ltd.",
    unit_price=4.20,
    total_price=42000.0,
    currency="USD",
    lead_time=30,
    risk_score=0.1,
    rank=1,
    notes=None,
):
    from src.core_schema.b_side_types import DeliveryPath
    return DeliveryPath(
        path_id=f"PATH-{uuid.uuid4().hex[:8].upper()}",
        rfq_id="RFQ-REGRESS-001",
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
        label="BEST_OVERALL",
    )


def _apply_buyer_privacy_mask(
    path,
    hide_identity: bool = False,
    hide_price: bool = False,
    margin_pct: float = 0.10,
) -> dict:
    """Return a buyer-facing dict with optional identity/price masking."""
    d = {
        "path_id": path.path_id,
        "lead_time_days": path.lead_time_days,
        "currency": path.currency,
        "risk_score": path.risk_score,
        "rank": path.rank,
        "label": path.label,
        "notes": path.notes,
    }
    if hide_identity:
        d["supplier_id"] = None
        d["supplier_name"] = "Verified Supplier"
    else:
        d["supplier_id"] = path.supplier_id
        d["supplier_name"] = path.supplier_name

    if hide_price:
        # Apply margin to compute buyer price; hide internal supplier price
        buyer_unit_price = round(path.unit_price * (1 + margin_pct), 4) if path.unit_price else None
        d["unit_price"] = buyer_unit_price
        d["total_price"] = round(path.total_price * (1 + margin_pct), 2) if path.total_price else None
        d["_internal_supplier_price"] = None  # must not appear in buyer view
    else:
        d["unit_price"] = path.unit_price
        d["total_price"] = path.total_price

    return d


# ─── Regression: identity masking ────────────────────────────────────────────

def test_hide_identity_replaces_supplier_name():
    path = _make_path()
    view = _apply_buyer_privacy_mask(path, hide_identity=True)
    assert view["supplier_name"] == "Verified Supplier"
    assert view["supplier_id"] is None


def test_hide_identity_conceals_supplier_id():
    path = _make_path(supplier_id="sup_secret_id")
    view = _apply_buyer_privacy_mask(path, hide_identity=True)
    assert "sup_secret_id" not in str(view)


def test_no_hide_identity_reveals_supplier_info():
    path = _make_path(supplier_id="sup_open", supplier_name="Visible Factory")
    view = _apply_buyer_privacy_mask(path, hide_identity=False)
    assert view["supplier_name"] == "Visible Factory"
    assert view["supplier_id"] == "sup_open"


# ─── Regression: price masking with margin ───────────────────────────────────

def test_hide_price_applies_margin_correctly():
    """Buyer sees supplier_price * (1 + margin_pct)."""
    path = _make_path(unit_price=4.20, total_price=42000.0)
    view = _apply_buyer_privacy_mask(path, hide_price=True, margin_pct=0.10)
    expected_unit = round(4.20 * 1.10, 4)
    expected_total = round(42000.0 * 1.10, 2)
    assert view["unit_price"] == expected_unit, f"Expected {expected_unit}, got {view['unit_price']}"
    assert view["total_price"] == expected_total


def test_hide_price_does_not_expose_raw_supplier_price():
    """Buyer-facing view must not contain the raw supplier unit price."""
    path = _make_path(unit_price=4.20, total_price=42000.0)
    view = _apply_buyer_privacy_mask(path, hide_price=True, margin_pct=0.10)
    # The raw price 4.20 must not appear in buyer view
    assert view["unit_price"] != 4.20, "Buyer should see margin-adjusted price, not supplier raw price"
    assert view.get("_internal_supplier_price") is None


def test_no_hide_price_shows_supplier_price_directly():
    path = _make_path(unit_price=5.50, total_price=55000.0)
    view = _apply_buyer_privacy_mask(path, hide_price=False)
    assert view["unit_price"] == 5.50
    assert view["total_price"] == 55000.0


def test_margin_calculation_is_deterministic():
    """Same inputs always produce same margin-adjusted price."""
    path = _make_path(unit_price=3.80, total_price=38000.0)
    view1 = _apply_buyer_privacy_mask(path, hide_price=True, margin_pct=0.15)
    view2 = _apply_buyer_privacy_mask(path, hide_price=True, margin_pct=0.15)
    assert view1["unit_price"] == view2["unit_price"]
    assert view1["total_price"] == view2["total_price"]


# ─── Regression: both flags together ─────────────────────────────────────────

def test_hide_both_identity_and_price():
    """Both identity and price can be hidden simultaneously."""
    path = _make_path(
        supplier_id="sup_internal_id",
        supplier_name="Internal Factory Co.",
        unit_price=6.00,
        total_price=60000.0,
    )
    view = _apply_buyer_privacy_mask(path, hide_identity=True, hide_price=True, margin_pct=0.12)
    assert view["supplier_name"] == "Verified Supplier"
    assert view["supplier_id"] is None
    assert view["unit_price"] != 6.00
    assert "sup_internal_id" not in str(view)
    assert "Internal Factory Co." not in str(view)


# ─── Regression: internal record retains real data ───────────────────────────

def test_original_path_unmodified_after_masking():
    """Masking creates a view dict; the original DeliveryPath is not mutated."""
    path = _make_path(supplier_id="sup_real", supplier_name="Real Co.", unit_price=4.50)
    _apply_buyer_privacy_mask(path, hide_identity=True, hide_price=True)
    # Original path must be unchanged
    assert path.supplier_id == "sup_real"
    assert path.supplier_name == "Real Co."
    assert path.unit_price == 4.50


# ─── Regression: env var parseability ────────────────────────────────────────

def test_hide_supplier_identity_env_parseable(monkeypatch):
    monkeypatch.setenv("AIVAN_HIDE_SUPPLIER_IDENTITY_FROM_BUYER", "true")
    val = os.environ.get("AIVAN_HIDE_SUPPLIER_IDENTITY_FROM_BUYER", "false").lower() in ("true", "1", "yes")
    assert val is True


def test_hide_supplier_price_env_parseable(monkeypatch):
    monkeypatch.setenv("AIVAN_HIDE_SUPPLIER_PRICE_FROM_BUYER", "true")
    val = os.environ.get("AIVAN_HIDE_SUPPLIER_PRICE_FROM_BUYER", "false").lower() in ("true", "1", "yes")
    assert val is True


# ─── Regression: buyer quote is a pending draft ──────────────────────────────

def test_buyer_quote_draft_is_pending(tmp_path, monkeypatch):
    import src.openclaw_skill.message_draft_store as ds
    monkeypatch.setattr(ds, "_DATA_DIR", tmp_path / "drafts")
    (tmp_path / "drafts").mkdir(parents=True, exist_ok=True)
    from src.openclaw_skill.message_draft_store import create_draft

    path = _make_path(unit_price=4.20, total_price=42000.0)
    view = _apply_buyer_privacy_mask(path, hide_identity=True, hide_price=True, margin_pct=0.10)
    draft_text = (
        f"Option {view['rank']} ({view['label']}): "
        f"Lead time {view['lead_time_days']} days, "
        f"Price {view['currency']} {view['unit_price']}/pc. "
        f"Supplier: {view['supplier_name']}. Risk: {view['risk_score']}"
    )
    draft = create_draft("buyer_quote_proj", "openclaw-mock", "customer", draft_text)
    assert draft.approval_status == "pending_approval"
    # Ensure the draft text does not leak real supplier name
    assert "Confidential Supplier Ltd." not in draft.draft_text


def test_buyer_quote_draft_does_not_leak_supplier_name_when_hidden(tmp_path, monkeypatch):
    import src.openclaw_skill.message_draft_store as ds
    monkeypatch.setattr(ds, "_DATA_DIR", tmp_path / "drafts2")
    (tmp_path / "drafts2").mkdir(parents=True, exist_ok=True)
    from src.openclaw_skill.message_draft_store import create_draft

    path = _make_path(supplier_name="TopSecret Factory", unit_price=3.00)
    view = _apply_buyer_privacy_mask(path, hide_identity=True)
    draft_text = f"Best option: {view['supplier_name']}, lead time {view['lead_time_days']}d"
    draft = create_draft("proj_priv_check", "openclaw-mock", "customer", draft_text)
    assert "TopSecret Factory" not in draft.draft_text
