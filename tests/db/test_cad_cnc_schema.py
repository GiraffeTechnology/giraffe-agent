"""Tests for CAD/CNC schema and Professional Free file policy enforcement."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.base import Base
import src.db.models  # noqa: F401
from src.db.repositories.actor_repo import ActorRepo
from src.db.repositories.project_repo import ProjectRepo
from src.db.repositories.cad_cnc_repo import CADCNCRepo, PROFESSIONAL_FREE_WARNING


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
    db.flush()
    return {"buyer": buyer, "mfr": mfr}


@pytest.fixture
def cnc_project(db, actors):
    repo = ProjectRepo(db)
    p = repo.create_project(
        original_buyer_actor_id=actors["buyer"].actor_id,
        product_tier="professional_free",
        category="cnc",
    )
    db.flush()
    return p


def test_artifact_professional_free_flags(db, actors, cnc_project):
    repo = CADCNCRepo(db)
    artifact = repo.create_artifact(
        file_ref="s3://mock/bracket.step",
        artifact_type="step",
        project_id=cnc_project.project_id,
        owner_actor_id=actors["buyer"].actor_id,
        file_name="bracket.step",
        product_tier="professional_free",
        warning_acknowledged=False,
    )
    db.commit()

    assert artifact.encryption_enabled is False
    assert artifact.dynamic_watermark_enabled is False
    assert artifact.secure_viewer_enabled is False
    assert artifact.warning_acknowledged is False


def test_cad_packet_blocked_without_warning(db, actors, cnc_project):
    repo = CADCNCRepo(db)
    artifact = repo.create_artifact(
        file_ref="s3://mock/part.step",
        artifact_type="step",
        project_id=cnc_project.project_id,
        owner_actor_id=actors["buyer"].actor_id,
        product_tier="professional_free",
        warning_acknowledged=False,
    )
    db.flush()

    with pytest.raises(ValueError, match="Professional Free"):
        repo.create_cad_requirement_packet(
            project_id=cnc_project.project_id,
            original_buyer_actor_id=actors["buyer"].actor_id,
            artifact_id=artifact.artifact_id,
        )


def test_cad_packet_allowed_after_warning_acknowledged(db, actors, cnc_project):
    repo = CADCNCRepo(db)
    artifact = repo.create_artifact(
        file_ref="s3://mock/part.step",
        artifact_type="step",
        project_id=cnc_project.project_id,
        owner_actor_id=actors["buyer"].actor_id,
        product_tier="professional_free",
        warning_acknowledged=False,
    )
    db.flush()

    # Acknowledge warning
    artifact.warning_acknowledged = True
    db.flush()

    packet = repo.create_cad_requirement_packet(
        project_id=cnc_project.project_id,
        original_buyer_actor_id=actors["buyer"].actor_id,
        artifact_id=artifact.artifact_id,
        material="Aluminum 6061",
        quantity=5,
        extraction_confidence_score=0.85,
    )
    db.commit()
    assert packet.packet_id is not None
    assert packet.material == "Aluminum 6061"


def test_shop_capability_profile(db, actors):
    repo = CADCNCRepo(db)
    profile = repo.create_shop_capability_profile(
        actor_id=actors["mfr"].actor_id,
        profile_name="M Basic Shop",
        machines_json={
            "3_axis_cnc": {"count": 2, "model": "Haas VF2"},
        },
        material_inventory_json={"aluminum_6061": True, "steel": True},
        in_house_processes_json={"3_axis_milling": True, "turning": True},
        outsourced_processes_json={"anodizing": True, "heat_treatment": True},
    )
    db.commit()

    assert profile.profile_id is not None
    assert profile.machines_json["3_axis_cnc"]["count"] == 2
    assert profile.outsourced_processes_json["anodizing"] is True


def test_cad_cnc_match_result(db, actors, cnc_project):
    repo = CADCNCRepo(db)

    artifact = repo.create_artifact(
        file_ref="s3://mock/part.step",
        artifact_type="step",
        project_id=cnc_project.project_id,
        owner_actor_id=actors["buyer"].actor_id,
        product_tier="professional_free",
        warning_acknowledged=True,
    )
    packet = repo.create_cad_requirement_packet(
        project_id=cnc_project.project_id,
        original_buyer_actor_id=actors["buyer"].actor_id,
        artifact_id=artifact.artifact_id,
        material="Aluminum 6061",
        quantity=5,
    )
    profile = repo.create_shop_capability_profile(
        actor_id=actors["mfr"].actor_id,
        profile_name="M Basic",
        machines_json={"3_axis": {"count": 2}},
    )
    match = repo.create_match_result(
        project_id=cnc_project.project_id,
        actor_id=actors["mfr"].actor_id,
        cad_requirement_packet_id=packet.packet_id,
        shop_capability_profile_id=profile.profile_id,
        can_make_in_house=False,
        machine_fit_score=0.72,
        material_fit="yes",
        tolerance_fit="marginal",
        required_subcontract_dependencies_json={"anodizing": "outsourced"},
        confidence_score=0.80,
        explanation="3-axis can handle geometry; anodizing must be outsourced",
    )
    db.commit()

    assert match.match_id is not None
    assert match.can_make_in_house is False
    assert match.material_fit == "yes"
    assert "anodizing" in match.required_subcontract_dependencies_json


def test_capability_fit_report(db, actors, cnc_project):
    repo = CADCNCRepo(db)

    artifact = repo.create_artifact(
        file_ref="s3://mock/part.step",
        artifact_type="step",
        project_id=cnc_project.project_id,
        owner_actor_id=actors["buyer"].actor_id,
        product_tier="professional_free",
        warning_acknowledged=True,
    )
    packet = repo.create_cad_requirement_packet(
        project_id=cnc_project.project_id,
        original_buyer_actor_id=actors["buyer"].actor_id,
        artifact_id=artifact.artifact_id,
    )
    profile = repo.create_shop_capability_profile(
        actor_id=actors["mfr"].actor_id
    )
    match = repo.create_match_result(
        project_id=cnc_project.project_id,
        actor_id=actors["mfr"].actor_id,
        cad_requirement_packet_id=packet.packet_id,
        shop_capability_profile_id=profile.profile_id,
        can_make_in_house=False,
    )
    report = repo.create_capability_fit_report(
        project_id=cnc_project.project_id,
        actor_id=actors["mfr"].actor_id,
        cad_cnc_match_id=match.match_id,
        buyer_facing_summary_en="We can machine in-house but require outsourced anodizing.",
        can_quote_now=False,
        can_make_in_house=False,
        required_subcontractor_inquiries_json={"anodizing": "needed"},
        confidence_score=0.80,
    )
    db.commit()

    assert report.report_id is not None
    assert report.can_make_in_house is False
    assert report.can_quote_now is False
    assert "anodizing" in report.required_subcontractor_inquiries_json
