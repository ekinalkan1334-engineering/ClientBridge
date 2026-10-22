
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.v1.endpoints.webhooks import receive_order
from app.schemas.order import OrderWebhookRequest


def make_payload(
    order_id="ORD-WEBHOOK-TEST-001",
    customer_email="test@example.com",
    total_amount="150.00",
):
    return OrderWebhookRequest(
        order_id=order_id,
        customer_email=customer_email,
        total_amount=total_amount,
        currency="TRY",
        items=[
            {
                "sku": "SKU-001",
                "name": "Test product",
                "quantity": 1,
                "unit_price": "150.00",
            }
        ],
    )


def make_session():
    session = Mock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()

    result = Mock()
    result.scalar_one_or_none = Mock(return_value=None)
    session.execute.return_value = result

    return session


@pytest.mark.asyncio
async def test_new_webhook_order_is_accepted():
    session = make_session()

    response = await receive_order(make_payload(), session)

    assert response.order_id == "ORD-WEBHOOK-TEST-001"
    assert response.status == "accepted"
    session.add.assert_called_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_duplicate_webhook_with_same_stored_data_is_accepted():
    session = make_session()
    session.commit.side_effect = IntegrityError(
        "INSERT", {}, Exception("duplicate order_id")
    )

    session.execute.return_value.scalar_one_or_none.return_value = (
        SimpleNamespace(
            order_id="ORD-WEBHOOK-TEST-001",
            customer_email="test@example.com",
            total_amount=Decimal("150.00"),
        )
    )

    response = await receive_order(make_payload(), session)

    assert response.order_id == "ORD-WEBHOOK-TEST-001"
    assert response.status == "accepted"
    session.rollback.assert_awaited_once()
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_duplicate_order_id_with_different_stored_data_returns_409():
    session = make_session()
    session.commit.side_effect = IntegrityError(
        "INSERT", {}, Exception("duplicate order_id")
    )

    session.execute.return_value.scalar_one_or_none.return_value = (
        SimpleNamespace(
            order_id="ORD-WEBHOOK-TEST-001",
            customer_email="other@example.com",
            total_amount=Decimal("150.00"),
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        await receive_order(make_payload(), session)

    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail
    session.rollback.assert_awaited_once()
    session.execute.assert_awaited_once()
