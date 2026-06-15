import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.order import Order


async def get_order(db: AsyncSession, order_id: uuid.UUID) -> Order | None:
    return await db.get(Order, order_id)


async def list_orders_for_project(
    db: AsyncSession, project_id: uuid.UUID
) -> list[Order]:
    result = await db.execute(
        select(Order).where(Order.project_id == project_id)
    )
    return list(result.scalars().all())
