"""Tests for Industrial Execution Graph v0.1 — ExecutionEvent logging."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.base import Base
import src.db.models  # noqa: F401
from src.db.repositories.actor_repo import ActorRepo
from src.db.repositories.project_repo import ProjectRepo
from src.db.repositories.graph_repo import GraphRepo
from src.db.repositories.role_repo import RoleRepo
from src.db.repositories.execution_event_repo import ExecutionEventRepo


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture
def setup(db):
    actors = ActorRepo(db)
    buyer = actors.create_actor(name="B", actor_type="buyer")
    mfr = actors.create_actor(name="M", actor_type="manufacturer")
    proj = ProjectRepo(db).create_project(original_buyer_actor_id=buyer.actor_id)
    edge = GraphRepo(db).create_edge(
        project_id=proj.project_id,
        from_actor_id=buyer.actor_id,
        to_actor_id=mfr.actor_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    rc = RoleRepo(db).create_role_context(
        project_id=proj.project_id,
        actor_id=mfr.actor_id,
        role="MAIN_M_SIDE",
        edge_id=edge.edge_id,
        role_reason="main supplier",
    )
    db.flush()
    return {"buyer": buyer, "mfr": mfr, "project": proj, "edge": edge, "role_context": rc}


def test_log_single_event(db, setup):
    repo = ExecutionEventRepo(db)
    event = repo.log_event(
        event_type="ROLE_CONTEXT_RESOLVED",
        project_id=setup["project"].project_id,
        actor_id=setup["mfr"].actor_id,
        role_context_id=setup["role_context"].role_context_id,
        payload_json={"role": "MAIN_M_SIDE"},
    )
    db.commit()
    assert event.event_id is not None
    assert event.event_type == "ROLE_CONTEXT_RESOLVED"


def test_list_project_events_ordered(db, setup):
    repo = ExecutionEventRepo(db)
    pid = setup["project"].project_id
    repo.log_event(event_type="B_INQUIRY_CREATED", project_id=pid)
    repo.log_event(event_type="M_SIDE_RECEIVED_BUYER_INQUIRY", project_id=pid)
    repo.log_event(event_type="UPSTREAM_DEPENDENCY_PLANNED", project_id=pid)
    db.commit()

    events = repo.list_project_events(pid)
    assert len(events) == 3
    types = [e.event_type for e in events]
    assert types[0] == "B_INQUIRY_CREATED"
    assert types[2] == "UPSTREAM_DEPENDENCY_PLANNED"


def test_list_events_by_type(db, setup):
    repo = ExecutionEventRepo(db)
    pid = setup["project"].project_id
    repo.log_event(event_type="ROLE_CONTEXT_RESOLVED", project_id=pid)
    repo.log_event(event_type="ROLE_CONTEXT_RESOLVED", project_id=pid)
    repo.log_event(event_type="B_INQUIRY_CREATED", project_id=pid)
    db.commit()

    resolved = repo.list_events_by_type("ROLE_CONTEXT_RESOLVED", project_id=pid)
    assert len(resolved) == 2


def test_execution_event_with_edge(db, setup):
    repo = ExecutionEventRepo(db)
    event = repo.log_event(
        event_type="UPSTREAM_INQUIRY_DISPATCHED",
        project_id=setup["project"].project_id,
        edge_id=setup["edge"].edge_id,
        actor_id=setup["mfr"].actor_id,
        source_channel="mock",
        payload_json={"dependency_type": "fabric"},
    )
    db.commit()
    assert event.edge_id == setup["edge"].edge_id
    assert event.source_channel == "mock"


def test_all_required_event_types_loggable(db, setup):
    """Verify all required workflow event types can be stored."""
    repo = ExecutionEventRepo(db)
    pid = setup["project"].project_id
    required_types = [
        "ROLE_CONTEXT_RESOLVED",
        "ROLE_SWITCH_OCCURRED",
        "B_INQUIRY_CREATED",
        "M_SIDE_RECEIVED_BUYER_INQUIRY",
        "UPSTREAM_DEPENDENCY_PLANNED",
        "UPSTREAM_INQUIRY_CREATED",
        "UPSTREAM_INQUIRY_DISPATCHED",
        "UPSTREAM_RESPONSE_RECEIVED",
        "UPSTREAM_OPTIONS_GENERATED",
        "UPSTREAM_OPTION_APPROVED",
        "SUPPLIER_RESPONSE_ROLLUP_GENERATED",
        "SUPPLIER_RESPONSE_ROLLUP_SUBMITTED_TO_B_SIDE",
        "CAD_REQUIREMENT_PACKET_CREATED",
        "CAD_CNC_MATCH_COMPLETED",
        "CAPABILITY_FIT_REPORT_CREATED",
        "PROFESSIONAL_FREE_FILE_WARNING_SHOWN",
        "ORDER_CONFIRMED",
        "ORDER_CLOSED",
    ]
    for et in required_types:
        repo.log_event(event_type=et, project_id=pid, payload_json={"test": True})
    db.commit()

    events = repo.list_project_events(pid)
    logged_types = {e.event_type for e in events}
    for et in required_types:
        assert et in logged_types, f"Event type {et} was not found in logged events"


def test_event_payload_json_preserved(db, setup):
    repo = ExecutionEventRepo(db)
    payload = {
        "role": "MAIN_M_SIDE",
        "counterparty": "buyer_b",
        "confidence": 0.95,
        "nested": {"key": "value"},
    }
    event = repo.log_event(
        event_type="ROLE_CONTEXT_RESOLVED",
        project_id=setup["project"].project_id,
        payload_json=payload,
    )
    db.commit()

    from src.db.models.execution_event import ExecutionEvent
    fetched = db.query(ExecutionEvent).filter(
        ExecutionEvent.event_id == event.event_id
    ).first()
    assert fetched.payload_json["role"] == "MAIN_M_SIDE"
    assert fetched.payload_json["nested"]["key"] == "value"
