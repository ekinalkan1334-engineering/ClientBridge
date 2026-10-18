from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.order import Order

router = APIRouter(tags=["orders"])


@router.get("/orders")
async def list_orders(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Order).order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    return [
        {
            "order_id": order.order_id,
            "customer_email": order.customer_email,
            "total_amount": float(order.total_amount),
            "status": order.status.value,
            "retry_count": order.retry_count,
            "created_at": order.created_at.isoformat(),
        }
        for order in orders
    ]