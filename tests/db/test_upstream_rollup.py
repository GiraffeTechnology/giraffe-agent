"""Tests for upstream inquiry loop and Supplier Response Rollup."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.base import Base
import src.db.models  # noqa: F401
from src.db.repositories.actor_repo import ActorRepo
from src.db.repositories.project_repo import ProjectRepo
from src.db.repositories.graph_repo import GraphRepo
from src.db.repositories.inquiry_repo import InquiryRepo
from src.db.repositories.response_repo import ResponseRepo
from src.db.repositories.rollup_repo import RollupRepo
from src.db.models.upstream import DependencyNeed
from src.db.models.approval import ApprovalRequest
from src.db.mixins import new_uuid


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture
def actors(db):
    repo = ActorRepo(db)
    buyer = repo.create_actor(name="Buyer B", actor_type="buyer")
    mfr = repo.create_actor(name="Manufacturer M", actor_type="manufacturer")
    f1 = repo.create_actor(name="Fabric F1", actor_type="fabric_supplier")
    db.flush()
    return {"buyer": buyer, "mfr": mfr, "f1": f1}


@pytest.fixture
def project(db, actors):
    repo = ProjectRepo(db)
    p = repo.create_project(original_buyer_actor_id=actors["buyer"].actor_id)
    db.flush()
    return p


@pytest.fixture
def main_edge(db, actors, project):
    repo = GraphRepo(db)
    edge = repo.create_edge(
        project_id=project.project_id,
        from_actor_id=actors["buyer"].actor_id,
        to_actor_id=actors["mfr"].actor_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    db.flush()
    return edge


def _make_dependency(db, project_id, actor_id, dep_type):
    from datetime import datetime, timezone
    dep = DependencyNeed(
        dependency_id=new_uuid(),
        project_id=project_id,
        created_by_actor_id=actor_id,
        dependency_type=dep_type,
        description=f"Need {dep_type}",
        required_specs_json={},
        risk_level="medium",
        why_needed=f"required for {dep_type}",
        candidate_actor_ids_json={},
        source="m_side_planner",
        status="pending",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(dep)
    db.flush()
    return dep


def test_dependency_need_creation(db, actors, project):
    dep = _make_dependency(db, project.project_id, actors["mfr"].actor_id, "fabric")
    db.commit()
    assert dep.dependency_id is not None
    assert dep.dependency_type == "fabric"


def test_upstream_inquiry_and_response(db, actors, project, main_edge):
    graph = GraphRepo(db)
    inq_repo = InquiryRepo(db)
    resp_repo = ResponseRepo(db)

    dep = _make_dependency(db, project.project_id, actors["mfr"].actor_id, "fabric")

    upstream_edge = graph.create_edge(
        project_id=project.project_id,
        from_actor_id=actors["mfr"].actor_id,
        to_actor_id=actors["f1"].actor_id,
        edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
        parent_edge_id=main_edge.edge_id,
    )

    uinq = inq_repo.create_upstream_inquiry(
        project_id=project.project_id,
        edge_id=upstream_edge.edge_id,
        dependency_id=dep.dependency_id,
        parent_main_supplier_actor_id=actors["mfr"].actor_id,
        upstream_actor_id=actors["f1"].actor_id,
        message_text_en="Can you supply 180gsm cotton?",
    )

    uresp = resp_repo.create_upstream_response(
        project_id=project.project_id,
        edge_id=upstream_edge.edge_id,
        upstream_inquiry_id=uinq.upstream_inquiry_id,
        dependency_id=dep.dependency_id,
        from_actor_id=actors["f1"].actor_id,
        can_supply=True,
        price=4.5,
        currency="USD",
        lead_time_days=14,
        confidence_score=0.9,
    )
    db.commit()

    assert uresp.can_supply is True
    assert uresp.price == 4.5
    assert uresp.lead_time_days == 14


def test_upstream_options_best_and_fastest(db, actors, project):
    resp_repo = ResponseRepo(db)
    dep = _make_dependency(db, project.project_id, actors["mfr"].actor_id, "fabric")

    opt_best = resp_repo.create_upstream_option(
        project_id=project.project_id,
        dependency_id=dep.dependency_id,
        upstream_actor_id=actors["f1"].actor_id,
        option_label="BEST",
        score=0.92,
        price_summary="USD 4.50/m",
        lead_time_summary="14 days",
    )
    opt_fastest = resp_repo.create_upstream_option(
        project_id=project.project_id,
        dependency_id=dep.dependency_id,
        upstream_actor_id=actors["f1"].actor_id,
        option_label="FASTEST",
        score=0.78,
        price_summary="USD 5.20/m",
        lead_time_summary="7 days",
    )
    db.commit()
    assert opt_best.option_label == "BEST"
    assert opt_fastest.option_label == "FASTEST"


def test_approval_request_and_approve(db, actors, project):
    from datetime import datetime, timezone
    dep = _make_dependency(db, project.project_id, actors["mfr"].actor_id, "fabric")
    resp_repo = ResponseRepo(db)
    opt = resp_repo.create_upstream_option(
        project_id=project.project_id,
        dependency_id=dep.dependency_id,
        upstream_actor_id=actors["f1"].actor_id,
        option_label="BEST",
        score=0.92,
    )
    db.flush()

    now = datetime.now(timezone.utc)
    approval = ApprovalRequest(
        approval_request_id=new_uuid(),
        project_id=project.project_id,
        dependency_id=dep.dependency_id,
        requested_by_actor_id=actors["mfr"].actor_id,
        approval_mode="human",
        status="PENDING",
        options_json={"options": [opt.option_id]},
        approved_option_id=None,
        approved_by_actor_id=None,
        approved_by_mode=None,
        created_at=now,
        updated_at=now,
        metadata_json={},
    )
    db.add(approval)
    db.flush()

    approval.status = "APPROVED"
    approval.approved_option_id = opt.option_id
    approval.approved_by_actor_id = actors["buyer"].actor_id
    approval.approved_by_mode = "human"
    db.commit()

    assert approval.status == "APPROVED"
    assert approval.approved_option_id == opt.option_id


def test_supplier_response_rollup_created(db, actors, project):
    rollup_repo = RollupRepo(db)
    rollup = rollup_repo.create_rollup(
        project_id=project.project_id,
        main_supplier_actor_id=actors["mfr"].actor_id,
        can_accept_order=True,
        main_capacity_summary="100 pcs in 21 days",
        approved_upstream_options_json={"fabric": "opt_best_id"},
        completeness_score=0.95,
        confidence_score=0.88,
        recommended_response_to_buyer_en="We can fulfill 100 pcs in 21 days.",
    )
    db.commit()
    fetched = rollup_repo.get_rollup(rollup.rollup_id)
    assert fetched is not None
    assert fetched.can_accept_order is True
    assert fetched.completeness_score == 0.95


def test_rollup_with_cad_cnc_evidence(db, actors, project):
    rollup_repo = RollupRepo(db)
    rollup = rollup_repo.create_rollup(
        project_id=project.project_id,
        main_supplier_actor_id=actors["mfr"].actor_id,
        can_accept_order=True,
        cad_cnc_match_id="mock-match-id",
        capability_fit_report_id="mock-report-id",
        can_make_in_house=False,
        capability_gaps_json={"anodizing": "outsourced"},
    )
    db.commit()
    fetched = rollup_repo.get_project_rollup(project.project_id)
    assert fetched.cad_cnc_match_id == "mock-match-id"
    assert fetched.can_make_in_house is False
