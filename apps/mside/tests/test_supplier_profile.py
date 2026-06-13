"""
Tests for M-side supplier profile CRUD.
"""
import uuid
import pytest
from src.m_side.supplier_profile import (
    create_supplier_profile,
    get_supplier_profile,
    save_supplier_profile,
    list_supplier_profiles,
)
from src.core_schema.m_side_types import SupplierCapability


@pytest.fixture(autouse=True)
def patch_supplier_dir(tmp_path, monkeypatch):
    import src.m_side.supplier_profile as sp_mod
    monkeypatch.setattr(sp_mod, "_DATA_DIR", tmp_path / "supplier_profiles")


class TestCreateSupplierProfile:
    def test_creates_profile(self):
        p = create_supplier_profile(
            name="Shenzhen CNC Works",
            channel="mock",
            external_user_id="ext_001",
        )
        assert p.supplier_name == "Shenzhen CNC Works"

    def test_supplier_id_assigned(self):
        p = create_supplier_profile(name="Test Supplier")
        assert p.supplier_id.startswith("sup_")

    def test_channel_stored(self):
        p = create_supplier_profile(name="Test", channel="wechat")
        assert p.channel == "wechat"

    def test_capability_stored(self):
        cap = SupplierCapability(categories=["cnc"], materials=["aluminum 6061"])
        p = create_supplier_profile(name="Test", capability=cap)
        assert "cnc" in p.capability.categories

    def test_persisted_to_disk(self):
        p = create_supplier_profile(name="Persist Test")
        loaded = get_supplier_profile(p.supplier_id)
        assert loaded is not None
        assert loaded.supplier_name == "Persist Test"


class TestGetSupplierProfile:
    def test_returns_none_for_missing(self):
        result = get_supplier_profile("sup_nonexistent_xyz")
        assert result is None

    def test_round_trip(self):
        p = create_supplier_profile(name="Round Trip Test")
        loaded = get_supplier_profile(p.supplier_id)
        assert loaded.supplier_id == p.supplier_id

    def test_capability_preserved(self):
        cap = SupplierCapability(categories=["apparel", "garment"])
        p = create_supplier_profile(name="Garment", capability=cap)
        loaded = get_supplier_profile(p.supplier_id)
        assert "apparel" in loaded.capability.categories


class TestSaveSupplierProfile:
    def test_update_name(self):
        p = create_supplier_profile(name="Original Name")
        p.supplier_name = "Updated Name"
        save_supplier_profile(p)
        loaded = get_supplier_profile(p.supplier_id)
        assert loaded.supplier_name == "Updated Name"

    def test_update_channel(self):
        p = create_supplier_profile(name="Channel Test", channel="mock")
        p.channel = "wechat"
        save_supplier_profile(p)
        loaded = get_supplier_profile(p.supplier_id)
        assert loaded.channel == "wechat"


class TestListSupplierProfiles:
    def test_empty_list(self):
        profiles = list_supplier_profiles()
        assert profiles == []

    def test_lists_created_profiles(self):
        create_supplier_profile(name="Supplier A")
        create_supplier_profile(name="Supplier B")
        profiles = list_supplier_profiles()
        assert len(profiles) == 2

    def test_returns_list(self):
        create_supplier_profile(name="Test")
        result = list_supplier_profiles()
        assert isinstance(result, list)
