import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_db, get_current_user
from src.execution_graph import service
from src.execution_graph.schemas import ExecutionEventOut

router = APIRouter()


@router.get("/execution-graph/projects/{project_id}", response_model=list[ExecutionEventOut])
async def get_project_events(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    events = await service.get_events_for_project(db, project_id)
    return events


@router.get("/execution-graph/orders/{order_id}", response_model=list[ExecutionEventOut])
async def get_order_events(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    events = await service.get_events_for_order(db, order_id)
    return events


@router.get("/execution-graph/participants/{participant_id}", response_model=list[ExecutionEventOut])
async def get_participant_events(
    participant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    events = await service.get_events_for_participant(db, participant_id)
    return events


@router.get("/execution-graph/events/{event_id}", response_model=ExecutionEventOut)
async def get_single_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    event = await service.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
