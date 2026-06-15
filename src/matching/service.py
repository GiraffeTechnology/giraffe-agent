import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.matching import ParticipantMatch
from src.db.models.participant import Participant, ParticipantRole, ParticipantProfile
from src.db.models.dynamic_form import DynamicOrderForm, DynamicOrderFormVersion
from src.db.models.logistics import SupplierMemoryRecord, ReplacementAlert
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import PARTICIPANT_MATCHED
from src.matching.sections import PRODUCTION_SECTIONS
from src.matching.scorer import score_participant_for_section, compute_risk_flags


async def _load_current_form_fields(db: AsyncSession, project_id: uuid.UUID) -> dict:
    result = await db.execute(
        select(DynamicOrderForm).where(DynamicOrderForm.project_id == project_id)
    )
    form = result.scalar_one_or_none()
    if not form:
        return {}
    ver_result = await db.execute(
        select(DynamicOrderFormVersion)
        .where(
            DynamicOrderFormVersion.form_id == form.id,
            DynamicOrderFormVersion.version_number == form.current_version,
        )
    )
    version = ver_result.scalar_one_or_none()
    return version.fields if version else {}


async def _load_supplier_memory(db: AsyncSession, participant_id: uuid.UUID) -> dict | None:
    result = await db.execute(
        select(SupplierMemoryRecord)
        .where(SupplierMemoryRecord.participant_id == participant_id)
        .order_by(SupplierMemoryRecord.recorded_at.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()

    alert_result = await db.execute(
        select(ReplacementAlert)
        .where(ReplacementAlert.participant_id == participant_id)
        .order_by(ReplacementAlert.created_at.desc())
        .limit(1)
    )
    alert = alert_result.scalar_one_or_none()
    quality_issue_count = alert.quality_issue_count if alert else 0

    if not record:
        return {"quality_issue_count": quality_issue_count} if quality_issue_count else None

    # on_time_delivery is a bool; convert to float for scorer
    otd_rate = 1.0 if record.on_time_delivery else 0.0 if record.on_time_delivery is not None else None
    return {
        "on_time_delivery_rate": otd_rate,
        "qc_pass_rate": record.qc_pass_rate,
        "response_time_hours": record.response_time_hours,
        "price_competitiveness": record.price_competitiveness,
        "quality_issue_count": quality_issue_count,
    }


async def run_participant_matching(
    db: AsyncSession,
    project_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[ParticipantMatch]:
    form_fields = await _load_current_form_fields(db, project_id)

    all_matches: list[ParticipantMatch] = []
    top_per_section: dict[str, dict] = {}

    for section in PRODUCTION_SECTIONS:
        role = section["required_role"]

        # Load participants with this role in this tenant
        role_result = await db.execute(
            select(ParticipantRole).where(
                ParticipantRole.role_name == role,
                ParticipantRole.is_active == True,
            )
        )
        participant_roles = list(role_result.scalars().all())

        for pr in participant_roles:
            p_result = await db.execute(
                select(Participant).where(
                    Participant.id == pr.participant_id,
                    Participant.tenant_id == tenant_id,
                    Participant.is_active == True,
                )
            )
            participant = p_result.scalar_one_or_none()
            if not participant:
                continue

            # Load profile
            prof_result = await db.execute(
                select(ParticipantProfile).where(
                    ParticipantProfile.participant_id == participant.id
                )
            )
            profile_orm = prof_result.scalar_one_or_none()

            # Build profile dict for scorer
            participant_profile: dict = {
                "profile_completeness_score": participant.profile_completeness_score,
                "country": participant.country,
            }
            if profile_orm:
                participant_profile.update({
                    "product_categories": profile_orm.product_categories,
                    "fabric_capabilities": profile_orm.fabric_capabilities,
                    "moq": profile_orm.moq,
                    "quantity_range_max": profile_orm.quantity_range_max,
                    "lead_time_days_min": profile_orm.lead_time_days_min,
                    "lead_time_days_max": profile_orm.lead_time_days_max,
                    "supported_trade_terms": profile_orm.supported_trade_terms,
                })

            supplier_memory = await _load_supplier_memory(db, participant.id)
            score_result = score_participant_for_section(
                participant_profile, form_fields, supplier_memory, section
            )
            risk_flags = compute_risk_flags(participant_profile, supplier_memory)

            # Determine matched/unmatched requirements from section form_fields
            matched: list[str] = []
            unmatched: list[str] = []
            for field in section["form_fields"]:
                if form_fields.get(field):
                    matched.append(field)
                else:
                    unmatched.append(field)

            recommendation_reason = (
                f"Score {score_result['match_score']:.2f} for {section['section']}. "
                f"Risk flags: {', '.join(risk_flags) if risk_flags else 'None'}."
            )

            match = ParticipantMatch(
                project_id=project_id,
                participant_id=participant.id,
                recommended_role=role,
                match_score=score_result["match_score"],
                score_breakdown=score_result["score_breakdown"],
                matched_requirements=matched,
                unmatched_requirements=unmatched,
                risk_flags=risk_flags,
                missing_participant_data=score_result["missing_participant_data"],
                recommendation_reason=recommendation_reason,
                requires_human_approval=True,
            )
            db.add(match)
            all_matches.append(match)

            # Track top per section
            key = section["section"]
            if key not in top_per_section or score_result["match_score"] > top_per_section[key]["score"]:
                top_per_section[key] = {
                    "score": score_result["match_score"],
                    "participant_id": str(participant.id),
                    "participant_name": participant.name,
                }

    await db.flush()

    await emit_event(
        db=db,
        event_type=PARTICIPANT_MATCHED,
        payload={"project_id": str(project_id), "top_per_section": top_per_section},
        tenant_id=tenant_id,
        project_id=project_id,
        triggered_by_user_id=user_id,
    )

    return all_matches


async def get_matches_for_project(
    db: AsyncSession, project_id: uuid.UUID
) -> list[ParticipantMatch]:
    result = await db.execute(
        select(ParticipantMatch).where(ParticipantMatch.project_id == project_id)
    )
    return list(result.scalars().all())
