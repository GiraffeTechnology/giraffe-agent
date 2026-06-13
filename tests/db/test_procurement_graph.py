"""Tests for ProcurementEdge graph structure and parent-child edges."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.base import Base
import src.db.models  # noqa: F401
from src.db.repositories.actor_repo import ActorRepo
from src.db.repositories.project_repo import ProjectRepo
from src.db.repositories.graph_repo import GraphRepo


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture
def base_actors(db):
    repo = ActorRepo(db)
    buyer = repo.create_actor(name="Buyer B", actor_type="buyer")
    mfr = repo.create_actor(name="Manufacturer M", actor_type="manufacturer")
    f1 = repo.create_actor(name="Fabric F1", actor_type="fabric_supplier")
    f2 = repo.create_actor(name="Fabric F2", actor_type="fabric_supplier")
    t1 = repo.create_actor(name="Trim T1", actor_type="trim_supplier")
    db.flush()
    return {"buyer": buyer, "mfr": mfr, "f1": f1, "f2": f2, "t1": t1}


@pytest.fixture
def project(db, base_actors):
    repo = ProjectRepo(db)
    p = repo.create_project(original_buyer_actor_id=base_actors["buyer"].actor_id)
    db.flush()
    return p


def test_create_buyer_to_main_supplier_edge(db, base_actors, project):
    graph = GraphRepo(db)
    edge = graph.create_edge(
        project_id=project.project_id,
        from_actor_id=base_actors["buyer"].actor_id,
        to_actor_id=base_actors["mfr"].actor_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    db.commit()
    assert edge.edge_id is not None
    assert edge.edge_type == "BUYER_TO_MAIN_SUPPLIER"
    assert edge.parent_edge_id is None
    assert edge.status == "DRAFT"


def test_parent_child_edges(db, base_actors, project):
    graph = GraphRepo(db)
    main_edge = graph.create_edge(
        project_id=project.project_id,
        from_actor_id=base_actors["buyer"].actor_id,
        to_actor_id=base_actors["mfr"].actor_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    child1 = graph.create_edge(
        project_id=project.project_id,
        from_actor_id=base_actors["mfr"].actor_id,
        to_actor_id=base_actors["f1"].actor_id,
        edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
        parent_edge_id=main_edge.edge_id,
    )
    child2 = graph.create_edge(
        project_id=project.project_id,
        from_actor_id=base_actors["mfr"].actor_id,
        to_actor_id=base_actors["f2"].actor_id,
        edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
        parent_edge_id=main_edge.edge_id,
    )
    db.commit()

    children = graph.get_child_edges(main_edge.edge_id)
    assert len(children) == 2
    child_ids = {c.edge_id for c in children}
    assert child1.edge_id in child_ids
    assert child2.edge_id in child_ids


def test_get_project_edges(db, base_actors, project):
    graph = GraphRepo(db)
    graph.create_edge(
        project_id=project.project_id,
        from_actor_id=base_actors["buyer"].actor_id,
        to_actor_id=base_actors["mfr"].actor_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    graph.create_edge(
        project_id=project.project_id,
        from_actor_id=base_actors["mfr"].actor_id,
        to_actor_id=base_actors["t1"].actor_id,
        edge_type="MAIN_SUPPLIER_TO_TRIM_SUPPLIER",
    )
    db.commit()

    edges = graph.get_project_edges(project.project_id)
    assert len(edges) == 2


def test_update_edge_status(db, base_actors, project):
    graph = GraphRepo(db)
    edge = graph.create_edge(
        project_id=project.project_id,
        from_actor_id=base_actors["buyer"].actor_id,
        to_actor_id=base_actors["mfr"].actor_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    db.flush()
    graph.update_edge_status(edge.edge_id, "SENT")
    db.commit()

    refreshed = graph.get_edge(edge.edge_id)
    assert refreshed.status == "SENT"


def test_edge_metadata_json(db, base_actors, project):
    graph = GraphRepo(db)
    edge = graph.create_edge(
        project_id=project.project_id,
        from_actor_id=base_actors["buyer"].actor_id,
        to_actor_id=base_actors["mfr"].actor_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
        metadata_json={"note": "first contact via WeChat"},
    )
    db.commit()
    fetched = graph.get_edge(edge.edge_id)
    assert fetched.metadata_json["note"] == "first contact via WeChat"


def test_recursive_depth_three(db, base_actors, project):
    """B→M→F1 is depth 2; ensure graph supports it cleanly."""
    graph = GraphRepo(db)
    sub = ActorRepo(db).create_actor(name="Sub Knit", actor_type="subcontractor")
    db.flush()

    e_bm = graph.create_edge(
        project_id=project.project_id,
        from_actor_id=base_actors["buyer"].actor_id,
        to_actor_id=base_actors["mfr"].actor_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    e_mf = graph.create_edge(
        project_id=project.project_id,
        from_actor_id=base_actors["mfr"].actor_id,
        to_actor_id=base_actors["f1"].actor_id,
        edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
        parent_edge_id=e_bm.edge_id,
    )
    e_fs = graph.create_edge(
        project_id=project.project_id,
        from_actor_id=base_actors["f1"].actor_id,
        to_actor_id=sub.actor_id,
        edge_type="MAIN_SUPPLIER_TO_SUBCONTRACTOR",
        parent_edge_id=e_mf.edge_id,
    )
    db.commit()

    assert e_fs.parent_edge_id == e_mf.edge_id
    assert e_mf.parent_edge_id == e_bm.edge_id
    assert e_bm.parent_edge_id is None
