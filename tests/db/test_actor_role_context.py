"""Tests for Actor creation and RoleContext resolution."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.base import Base
import src.db.models  # noqa: F401
from src.db.repositories.actor_repo import ActorRepo
from src.db.repositories.project_repo import ProjectRepo
from src.db.repositories.graph_repo import GraphRepo
from src.db.repositories.role_repo import RoleRepo


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def test_create_actor_basic(db):
    repo = ActorRepo(db)
    actor = repo.create_actor(name="Test Buyer", actor_type="buyer")
    db.commit()
    assert actor.actor_id is not None
    assert actor.name == "Test Buyer"
    assert actor.actor_type == "buyer"
    assert actor.is_active is True


def test_get_actor(db):
    repo = ActorRepo(db)
    created = repo.create_actor(name="Manufacturer M", actor_type="manufacturer")
    db.commit()
    fetched = repo.get_actor(created.actor_id)
    assert fetched is not None
    assert fetched.name == "Manufacturer M"


def test_list_actors_by_type(db):
    repo = ActorRepo(db)
    repo.create_actor(name="Buyer 1", actor_type="buyer")
    repo.create_actor(name="Buyer 2", actor_type="buyer")
    repo.create_actor(name="Mfr 1", actor_type="manufacturer")
    db.commit()
    buyers = repo.list_actors(actor_type="buyer")
    assert len(buyers) == 2
    mfrs = repo.list_actors(actor_type="manufacturer")
    assert len(mfrs) == 1


def test_same_actor_multiple_roles_in_project(db):
    actor_repo = ActorRepo(db)
    proj_repo = ProjectRepo(db)
    graph_repo = GraphRepo(db)
    role_repo = RoleRepo(db)

    buyer = actor_repo.create_actor(name="Buyer B", actor_type="buyer")
    mfr = actor_repo.create_actor(name="Manufacturer M", actor_type="manufacturer")
    fabric = actor_repo.create_actor(name="Fabric F1", actor_type="fabric_supplier")

    project = proj_repo.create_project(original_buyer_actor_id=buyer.actor_id)

    edge_bm = graph_repo.create_edge(
        project_id=project.project_id,
        from_actor_id=buyer.actor_id,
        to_actor_id=mfr.actor_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    edge_mf = graph_repo.create_edge(
        project_id=project.project_id,
        from_actor_id=mfr.actor_id,
        to_actor_id=fabric.actor_id,
        edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
        parent_edge_id=edge_bm.edge_id,
    )

    # M is MAIN_M_SIDE to Buyer
    rc_main = role_repo.create_role_context(
        project_id=project.project_id,
        actor_id=mfr.actor_id,
        role="MAIN_M_SIDE",
        edge_id=edge_bm.edge_id,
        counterparty_actor_id=buyer.actor_id,
        role_reason="Main supplier for shirt order",
        can_create_upstream_inquiry=True,
        can_submit_response_to_buyer=True,
    )
    # M is also UPSTREAM_B_SIDE to Fabric F1
    rc_upstream = role_repo.create_role_context(
        project_id=project.project_id,
        actor_id=mfr.actor_id,
        role="UPSTREAM_B_SIDE",
        edge_id=edge_mf.edge_id,
        counterparty_actor_id=fabric.actor_id,
        role_reason="M procuring fabric from F1",
        can_approve_upstream_option=True,
    )
    db.commit()

    roles = role_repo.list_actor_roles_in_project(project.project_id, mfr.actor_id)
    role_names = {r.role for r in roles}
    assert "MAIN_M_SIDE" in role_names
    assert "UPSTREAM_B_SIDE" in role_names
    assert len(roles) == 2


def test_role_context_resolution_by_edge(db):
    actor_repo = ActorRepo(db)
    proj_repo = ProjectRepo(db)
    graph_repo = GraphRepo(db)
    role_repo = RoleRepo(db)

    buyer = actor_repo.create_actor(name="B", actor_type="buyer")
    mfr = actor_repo.create_actor(name="M", actor_type="manufacturer")
    project = proj_repo.create_project(original_buyer_actor_id=buyer.actor_id)
    edge = graph_repo.create_edge(
        project_id=project.project_id,
        from_actor_id=buyer.actor_id,
        to_actor_id=mfr.actor_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    role_repo.create_role_context(
        project_id=project.project_id,
        actor_id=mfr.actor_id,
        role="MAIN_M_SIDE",
        edge_id=edge.edge_id,
        role_reason="resolved",
    )
    db.commit()

    rc = role_repo.resolve_role_context(project.project_id, mfr.actor_id, edge_id=edge.edge_id)
    assert rc is not None
    assert rc.role == "MAIN_M_SIDE"


def test_actor_contact_channels_json(db):
    repo = ActorRepo(db)
    channels = {"wechat": "wx_buyer_001", "email": "buyer@example.com"}
    actor = repo.create_actor(
        name="B with channels",
        actor_type="buyer",
        contact_channels_json=channels,
    )
    db.commit()
    fetched = repo.get_actor(actor.actor_id)
    assert fetched.contact_channels_json["wechat"] == "wx_buyer_001"
