import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user
from src.orders.schemas import OrderOut, CreateOrderRequest
from src.orders.service import get_order, list_orders_for_project
from src.order_confirmation.service import (
    create_order_from_approved_option,
    confirm_order,
    buyer_sign_off,
)

router = APIRouter()


@router.post(
    "/projects/{project_id}/orders/from-approved-option",
    status_code=201,
    response_model=OrderOut,
)
async def create_order(
    project_id: uuid.UUID,
    body: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = await create_order_from_approved_option(
        db=db,
        project_id=project_id,
        packet_id=body.packet_id,
        option_id=body.option_id,
        approval_id=body.approval_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(order)
    return order


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order_route(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = await get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/orders/{order_id}/confirm", response_model=OrderOut)
async def confirm_order_route(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = await confirm_order(db, order_id, current_user.tenant_id, current_user.id)
    await db.commit()
    await db.refresh(order)
    return order


@router.post("/orders/{order_id}/buyer-sign-off", response_model=OrderOut)
async def buyer_sign_off_route(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = await buyer_sign_off(db, order_id, current_user.tenant_id, current_user.id)
    await db.commit()
    await db.refresh(order)
    return order
