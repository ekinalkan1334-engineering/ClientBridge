from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.order import Order
from app.schemas.order import OrderWebhookRequest, WebhookAccepted

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/orders", status_code=status.HTTP_202_ACCEPTED, response_model=WebhookAccepted)
async def receive_order(payload: OrderWebhookRequest, session: AsyncSession = Depends(get_session)):
    session.add(
        Order(
            order_id=payload.order_id,
            customer_email=payload.customer_email,
            total_amount=payload.total_amount,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Order '{payload.order_id}' already exists")
    return WebhookAccepted(order_id=payload.order_id)
