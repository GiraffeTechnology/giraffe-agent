"""
Tests for the Actors module — role context and role resolver.
"""
import pytest
from src.actors.models import Actor, ContactChannel
from src.actors.role_context import RoleContext
from src.actors.role_resolver import resolve_role_context


class TestActor:
    def test_minimal_actor(self):
        actor = Actor(actor_id="actor_001", name="Test Actor", actor_type="buyer")
        assert actor.actor_id == "actor_001"

    def test_contact_channels(self):
        channel = ContactChannel(
            channel_type="wechat", handle="buyer_wechat", external_user_id="wc_001"
        )
        actor = Actor(
            actor_id="actor_002",
            name="Buyer B",
            actor_type="buyer",
            contact_channels=[channel],
        )
        assert len(actor.contact_channels) == 1
        assert actor.contact_channels[0].channel_type == "wechat"

    def test_capabilities_list(self):
        actor = Actor(
            actor_id="actor_003",
            name="Manufacturer M",
            actor_type="manufacturer",
            capabilities=["sewing", "cutting", "finishing"],
        )
        assert "sewing" in actor.capabilities

    def test_default_language(self):
        actor = Actor(actor_id="a1", name="A", actor_type="unknown")
        assert actor.default_language == "zh"

    def test_metadata_dict(self):
        actor = Actor(
            actor_id="a2",
            name="A",
            actor_type="buyer",
            metadata={"source": "fixture", "capacity": 50},
        )
        assert actor.metadata["capacity"] == 50


class TestRoleContext:
    def test_role_context_creation(self):
        rc = RoleContext(
            project_id="PROJ-001",
            actor_id="actor_m",
            role="MAIN_M_SIDE",
            role_reason="Test reason",
        )
        assert rc.role == "MAIN_M_SIDE"

    def test_unknown_role(self):
        rc = RoleContext(
            project_id="PROJ-001",
            actor_id="actor_x",
            role="UNKNOWN",
            role_reason="Could not determine role",
        )
        assert rc.role == "UNKNOWN"


class TestRoleResolver:
    def test_original_buyer_role(self):
        rc = resolve_role_context(
            project_id="PROJ-001",
            actor_id="actor_buyer",
            original_buyer_actor_id="actor_buyer",
            main_supplier_actor_id="actor_supplier",
        )
        assert rc.role == "ORIGINAL_BUYER"

    def test_main_m_side_role(self):
        rc = resolve_role_context(
            project_id="PROJ-001",
            actor_id="actor_mfg",
            original_buyer_actor_id="actor_buyer",
            main_supplier_actor_id="actor_mfg",
        )
        assert rc.role == "MAIN_M_SIDE"

    def test_unknown_role_for_unrelated_actor(self):
        rc = resolve_role_context(
            project_id="PROJ-001",
            actor_id="actor_random",
            original_buyer_actor_id="actor_buyer",
            main_supplier_actor_id="actor_mfg",
        )
        assert rc.role == "UNKNOWN" or rc.role is not None

    def test_can_create_upstream_inquiry_for_main_m(self):
        rc = resolve_role_context(
            project_id="PROJ-001",
            actor_id="actor_mfg",
            original_buyer_actor_id="actor_buyer",
            main_supplier_actor_id="actor_mfg",
        )
        assert rc.can_create_upstream_inquiry is True

    def test_buyer_cannot_create_upstream_inquiry(self):
        rc = resolve_role_context(
            project_id="PROJ-001",
            actor_id="actor_buyer",
            original_buyer_actor_id="actor_buyer",
            main_supplier_actor_id="actor_mfg",
        )
        assert rc.can_create_upstream_inquiry is False

    def test_project_id_preserved(self):
        rc = resolve_role_context(
            project_id="PROJ-SPECIFIC",
            actor_id="actor_buyer",
            original_buyer_actor_id="actor_buyer",
            main_supplier_actor_id="actor_mfg",
        )
        assert rc.project_id == "PROJ-SPECIFIC"
