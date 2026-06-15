import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models.execution_graph import ExecutionEvent


async def get_events_for_project(db: AsyncSession, project_id: uuid.UUID) -> list[ExecutionEvent]:
    result = await db.execute(
        select(ExecutionEvent)
        .where(ExecutionEvent.project_id == project_id)
        .order_by(ExecutionEvent.occurred_at.asc())
    )
    return result.scalars().all()


async def get_events_for_order(db: AsyncSession, order_id: uuid.UUID) -> list[ExecutionEvent]:
    result = await db.execute(
        select(ExecutionEvent)
        .where(ExecutionEvent.order_id == order_id)
        .order_by(ExecutionEvent.occurred_at.asc())
    )
    return result.scalars().all()


async def get_events_for_participant(db: AsyncSession, participant_id: uuid.UUID) -> list[ExecutionEvent]:
    result = await db.execute(
        select(ExecutionEvent)
        .where(ExecutionEvent.participant_id == participant_id)
        .order_by(ExecutionEvent.occurred_at.asc())
    )
    return result.scalars().all()


async def get_event_by_id(db: AsyncSession, event_id: uuid.UUID) -> ExecutionEvent | None:
    result = await db.execute(
        select(ExecutionEvent).where(ExecutionEvent.id == event_id)
    )
    return result.scalar_one_or_none()
