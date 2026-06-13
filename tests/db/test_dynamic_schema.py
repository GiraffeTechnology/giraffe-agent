"""Tests for dynamic self-learning schema layer."""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from src.db.base import Base
import src.db.models  # noqa: F401
from src.db.repositories.actor_repo import ActorRepo
from src.db.repositories.dynamic_schema_repo import DynamicSchemaRepo
from src.db.models.dynamic_schema import SchemaRegistry, FieldDefinition
from src.db.mixins import new_uuid
from datetime import datetime, timezone


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        engine_ref = engine
    Base.metadata.drop_all(engine_ref)


@pytest.fixture
def apparel_schema(db):
    now = datetime.now(timezone.utc)
    schema = SchemaRegistry(
        schema_id=new_uuid(),
        industry="apparel",
        category="shirt",
        schema_version="v0.1",
        status="active",
        created_at=now,
        updated_at=now,
        metadata_json={},
    )
    db.add(schema)
    db.flush()
    return schema


@pytest.fixture
def actor(db):
    a = ActorRepo(db).create_actor(name="Supplier S", actor_type="fabric_supplier")
    db.flush()
    return a


def test_observe_field_from_message(db, actor, apparel_schema):
    repo = DynamicSchemaRepo(db)
    obs = repo.observe_field(
        candidate_field_name="fabric_gsm",
        confidence_score=0.95,
        actor_id=actor.actor_id,
        candidate_value="160",
        candidate_unit="g/m²",
        evidence_text="Supplier said: 160 gsm cotton fabric",
    )
    db.commit()
    assert obs.observed_field_id is not None
    assert obs.candidate_field_name == "fabric_gsm"
    assert obs.confidence_score == 0.95


def test_observe_multiple_fields(db, actor, apparel_schema):
    repo = DynamicSchemaRepo(db)
    fields = [
        ("fabric_gsm", "160", "g/m²", 0.95),
        ("shrinkage_rate", "3%", "%", 0.88),
        ("color_fastness_grade", "4", None, 0.92),
    ]
    for name, val, unit, conf in fields:
        repo.observe_field(
            candidate_field_name=name,
            confidence_score=conf,
            actor_id=actor.actor_id,
            candidate_value=val,
            candidate_unit=unit,
        )
    db.commit()

    from src.db.models.dynamic_schema import ObservedField
    all_obs = db.query(ObservedField).all()
    assert len(all_obs) == 3


def test_propose_field(db, apparel_schema):
    repo = DynamicSchemaRepo(db)
    proposal = repo.propose_field(
        schema_id=apparel_schema.schema_id,
        candidate_field_name="fabric_gsm",
        normalized_field_name="fabric_gsm",
        field_type="float",
        suggested_unit="g/m²",
        business_reason="Fabric weight is critical for quality and price",
        example_count=7,
        project_count=5,
        supplier_count=3,
        confidence_score=0.93,
        risk_level="low",
    )
    db.commit()
    assert proposal.status == "proposed"
    assert proposal.example_count == 7


def test_auto_approve_low_risk_field(db, apparel_schema):
    repo = DynamicSchemaRepo(db)
    proposal = repo.propose_field(
        schema_id=apparel_schema.schema_id,
        candidate_field_name="fabric_gsm",
        normalized_field_name="fabric_gsm",
        field_type="float",
        suggested_unit="g/m²",
        example_count=5,
        confidence_score=0.93,
        risk_level="low",
    )
    db.flush()

    assert repo.can_auto_approve(proposal)

    field_def = repo.approve_field(
        proposal_id=proposal.proposal_id,
        schema_id=apparel_schema.schema_id,
        decided_by="auto",
        reason="Low risk, sufficient examples",
    )
    db.commit()
    assert field_def is not None
    assert field_def.normalized_field_name == "fabric_gsm"
    assert field_def.required_level == "learned"
    assert field_def.source == "dynamic_learning"


def test_medium_risk_field_not_auto_approved(db, apparel_schema):
    repo = DynamicSchemaRepo(db)
    proposal = repo.propose_field(
        schema_id=apparel_schema.schema_id,
        candidate_field_name="surface_roughness_ra",
        normalized_field_name="surface_roughness_ra",
        field_type="float",
        suggested_unit="µm",
        example_count=4,
        confidence_score=0.87,
        risk_level="medium",
    )
    db.flush()
    assert not repo.can_auto_approve(proposal)


def test_store_dynamic_value(db, apparel_schema, actor):
    repo = DynamicSchemaRepo(db)

    proposal = repo.propose_field(
        schema_id=apparel_schema.schema_id,
        candidate_field_name="fabric_gsm",
        normalized_field_name="fabric_gsm",
        field_type="float",
        suggested_unit="g/m²",
        example_count=5,
        risk_level="low",
        confidence_score=0.93,
    )
    db.flush()
    field_def = repo.approve_field(
        proposal_id=proposal.proposal_id,
        schema_id=apparel_schema.schema_id,
    )
    db.flush()

    value = repo.store_dynamic_value(
        entity_type="actor",
        entity_id=actor.actor_id,
        field_id=field_def.field_id,
        field_value="160",
        unit="g/m²",
        confidence_score=0.95,
        source="message",
    )
    db.commit()
    assert value.value_id is not None
    assert value.field_value == "160"


def test_no_physical_table_migration_for_dynamic_fields(db, apparel_schema):
    """Dynamic fields must NOT require new physical tables."""
    engine = db.get_bind()
    initial_tables = set(inspect(engine).get_table_names())

    repo = DynamicSchemaRepo(db)
    for i in range(3):
        repo.propose_field(
            schema_id=apparel_schema.schema_id,
            candidate_field_name=f"new_field_{i}",
            normalized_field_name=f"new_field_{i}",
            field_type="string",
            example_count=5,
            risk_level="low",
            confidence_score=0.9,
        )
    db.commit()

    final_tables = set(inspect(engine).get_table_names())
    assert initial_tables == final_tables, "Dynamic fields must not create new physical tables"


def test_field_traceability(db, actor, apparel_schema):
    """Every observed field must be traceable to a source."""
    repo = DynamicSchemaRepo(db)
    mock_message_id = new_uuid()
    obs = repo.observe_field(
        candidate_field_name="color_fastness_grade",
        confidence_score=0.92,
        actor_id=actor.actor_id,
        source_message_id=mock_message_id,
        candidate_value="4",
    )
    db.commit()
    assert obs.source_message_id == mock_message_id


def test_list_schema_fields(db, apparel_schema):
    repo = DynamicSchemaRepo(db)
    now = datetime.now(timezone.utc)
    for i in range(3):
        fd = FieldDefinition(
            field_id=new_uuid(),
            schema_id=apparel_schema.schema_id,
            field_name=f"field_{i}",
            normalized_field_name=f"field_{i}",
            field_type="string",
            required_level="optional",
            source="manual",
            status="approved",
            validation_rule_json={},
            example_values_json={},
            created_at=now,
            updated_at=now,
        )
        db.add(fd)
    db.flush()

    fields = repo.list_schema_fields(apparel_schema.schema_id)
    assert len(fields) == 3
