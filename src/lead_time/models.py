"""Lead Time Path Model — canonical data models."""
import math
from typing import Literal
from pydantic import BaseModel, Field


class LeadTimeComponent(BaseModel):
    component_id: str
    component_type: Literal["material", "trim", "subcontract", "production", "qc", "packaging", "logistics", "buffer"]
    source_actor_id: str | None = None
    source_response_id: str | None = None
    dependency_id: str | None = None
    duration_days: float
    earliest_start_day: float = 0.0
    earliest_finish_day: float = 0.0
    can_parallelize: bool = False
    evidence_type: Literal["supplier_stated", "ai_calculated", "human_confirmed", "default_assumption"]
    evidence_ref: str | None = None
    risk_flags: list[str] = Field(default_factory=list)


class ProductionCapacity(BaseModel):
    actor_id: str
    daily_capacity_units: float = 50.0
    setup_days: float = 1.0
    queue_days: float = 0.0
    working_days_per_week: int = 5
    minimum_batch_size: int = 1
    confidence_score: float = 0.5
    evidence_ref: str | None = None


class LeadTimePath(BaseModel):
    path_id: str
    project_id: str
    supplier_id: str
    supplier_name: str
    quantity: int | None = None
    components: list[LeadTimeComponent] = Field(default_factory=list)
    critical_path_days: float = 0.0
    total_lead_time_days: int = 0
    earliest_delivery_day: int = 0
    feasible_before_deadline: bool = True
    deadline_days: int | None = None
    slack_days: int | None = None
    total_price: float | None = None
    unit_price: float | None = None
    currency: str | None = None
    confidence_score: float = 0.5
    completeness_score: float = 0.5
    risk_score: float = 0.0
    risk_flags: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    rank: int = 0
    label: Literal["FASTEST", "LOWEST_COST", "SAFEST", "BEST_OVERALL", "BACKUP"] | None = None

    # GLTG integration fields.
    # AIVAN must surface GLTG as the lead-time / feasibility engine rather than
    # silently treating a simple supplier-stated lead time as final truth.
    model_name: str = "lead_time_calculator"
    model_version: str = "legacy"
    p50_lead_time_days: int | None = None
    p80_lead_time_days: int | None = None
    p90_lead_time_days: int | None = None
    feasibility_basis: Literal["p50", "p80", "p90", "deterministic"] = "deterministic"
    fallback_model_used: bool = False

    # Breakdown for transparency
    material_ready_days: float = 0.0
    production_days: float = 0.0
    post_production_days: float = 0.0
    risk_buffer_days: float = 0.0
    supplier_stated_lead_time_days: int | None = None
    lead_time_consistency_note: str | None = None


class LeadTimeScenario(BaseModel):
    scenario_id: str
    project_id: str
    selected_supplier_id: str | None = None
    upstream_option_ids: list[str] = Field(default_factory=list)
    production_capacity: ProductionCapacity | None = None
    components: list[LeadTimeComponent] = Field(default_factory=list)
    result_path: LeadTimePath | None = None
