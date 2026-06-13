from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class SchemaRegistryBase(BaseModel):
    industry: str
    category: str
    schema_version: str
    status: str = "active"
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SchemaRegistryCreate(SchemaRegistryBase):
    pass


class SchemaRegistryRead(SchemaRegistryBase):
    schema_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FieldDefinitionBase(BaseModel):
    schema_id: str
    field_name: str
    normalized_field_name: str
    field_type: str
    unit: str | None = None
    description: str | None = None
    required_level: str = "optional"
    validation_rule_json: dict[str, Any] = Field(default_factory=dict)
    example_values_json: dict[str, Any] = Field(default_factory=dict)
    source: str = "manual"
    status: str = "approved"


class FieldDefinitionCreate(FieldDefinitionBase):
    pass


class FieldDefinitionRead(FieldDefinitionBase):
    field_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ObservedFieldBase(BaseModel):
    project_id: str | None = None
    actor_id: str | None = None
    source_message_id: str | None = None
    source_artifact_id: str | None = None
    candidate_field_name: str
    normalized_field_name: str | None = None
    candidate_value: str | None = None
    candidate_unit: str | None = None
    normalized_value: str | None = None
    confidence_score: float = 0.0
    evidence_text: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ObservedFieldCreate(ObservedFieldBase):
    pass


class ObservedFieldRead(ObservedFieldBase):
    observed_field_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FieldProposalBase(BaseModel):
    schema_id: str
    candidate_field_name: str
    normalized_field_name: str
    field_type: str
    suggested_unit: str | None = None
    business_reason: str | None = None
    example_count: int = 0
    project_count: int = 0
    supplier_count: int = 0
    confidence_score: float = 0.0
    risk_level: str = "low"
    status: str = "proposed"
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FieldProposalCreate(FieldProposalBase):
    pass


class FieldProposalRead(FieldProposalBase):
    proposal_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EntityDynamicValueBase(BaseModel):
    entity_type: str
    entity_id: str
    field_id: str
    field_value: str
    unit: str | None = None
    confidence_score: float = 0.0
    source: str | None = None
    source_message_id: str | None = None
    source_artifact_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class EntityDynamicValueCreate(EntityDynamicValueBase):
    pass


class EntityDynamicValueRead(EntityDynamicValueBase):
    value_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
