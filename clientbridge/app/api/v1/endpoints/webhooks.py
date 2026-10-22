
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.order import Order
from app.schemas.order import OrderWebhookRequest, WebhookAccepted

router = APIRouter(tags=["webhooks"])


@router.post(
    "/webhooks/orders",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=WebhookAccepted,
)
async def receive_order(
    payload: OrderWebhookRequest,
    session: AsyncSession = Depends(get_session),
):
    order = Order(
        order_id=payload.order_id,
        customer_email=str(payload.customer_email),
        total_amount=payload.total_amount,
    )

    session.add(order)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()

        result = await session.execute(
            select(Order).where(Order.order_id == payload.order_id)
        )
        existing_order = result.scalar_one_or_none()

        if existing_order is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database integrity error while accepting order.",
            )

        same_stored_data = (
            existing_order.customer_email == str(payload.customer_email)
            and existing_order.total_amount == payload.total_amount
        )

        if not same_stored_data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Order '{payload.order_id}' already exists "
                    "with different stored data."
                ),
            )

        return WebhookAccepted(
            status="accepted",
            order_id=existing_order.order_id,
        )

    return WebhookAccepted(order_id=payload.order_id)
