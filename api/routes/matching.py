import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user
from src.matching.schemas import ParticipantMatchOut
from src.matching.service import run_participant_matching, get_matches_for_project
from src.db.models.participant import Participant

router = APIRouter()


@router.post(
    "/projects/{project_id}/run-participant-matching",
    response_model=list[ParticipantMatchOut],
)
async def run_matching(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    matches = await run_participant_matching(
        db=db,
        project_id=project_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await db.commit()

    # Build response with participant_name
    result = []
    for m in matches:
        participant = await db.get(Participant, m.participant_id)
        out = ParticipantMatchOut(
            id=m.id,
            participant_id=m.participant_id,
            participant_name=participant.name if participant else "Unknown",
            recommended_role=m.recommended_role,
            match_score=m.match_score,
            score_breakdown=m.score_breakdown,
            matched_requirements=m.matched_requirements,
            unmatched_requirements=m.unmatched_requirements,
            risk_flags=m.risk_flags,
            missing_participant_data=m.missing_participant_data,
            recommendation_reason=m.recommendation_reason,
            requires_human_approval=m.requires_human_approval,
            created_at=m.created_at,
        )
        result.append(out)
    return result


@router.get(
    "/projects/{project_id}/participant-matches",
    response_model=list[ParticipantMatchOut],
)
async def list_matches(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    matches = await get_matches_for_project(db, project_id)
    result = []
    for m in matches:
        participant = await db.get(Participant, m.participant_id)
        out = ParticipantMatchOut(
            id=m.id,
            participant_id=m.participant_id,
            participant_name=participant.name if participant else "Unknown",
            recommended_role=m.recommended_role,
            match_score=m.match_score,
            score_breakdown=m.score_breakdown,
            matched_requirements=m.matched_requirements,
            unmatched_requirements=m.unmatched_requirements,
            risk_flags=m.risk_flags,
            missing_participant_data=m.missing_participant_data,
            recommendation_reason=m.recommendation_reason,
            requires_human_approval=m.requires_human_approval,
            created_at=m.created_at,
        )
        result.append(out)
    return result
