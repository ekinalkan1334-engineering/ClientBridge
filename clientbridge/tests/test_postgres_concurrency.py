
import asyncio
import os
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.order import Order, OrderStatus
from app.workers import polling_worker


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://clientbridge:clientbridge"
    "@localhost:5432/clientbridge_concurrency_test",
)


@pytest.mark.asyncio
async def test_two_workers_cannot_claim_the_same_order(monkeypatch):
    # Only allow the isolated test database.
    assert TEST_DATABASE_URL.endswith("/clientbridge_concurrency_test"), (
        "Refusing to run against a non-test database."
    )

    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    test_session = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
    )

    try:
        # Create the tables required by this test database.
        async with test_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        # Make both workers use the isolated test database.
        monkeypatch.setattr(
            polling_worker,
            "SessionLocal",
            test_session,
        )

        order_id = f"ORD-REAL-CONCURRENCY-{uuid.uuid4().hex[:12]}"

        try:
            # Create a unique pending order.
            async with test_session() as session, session.begin():
                session.add(
                    Order(
                        order_id=order_id,
                        customer_email="concurrency-test@example.com",
                        total_amount=Decimal("25.00"),
                        status=OrderStatus.PENDING,
                    )
                )

            # Two workers try to claim an order simultaneously.
            first, second = await asyncio.gather(
                polling_worker.claim_next_order("integration-worker-1"),
                polling_worker.claim_next_order("integration-worker-2"),
            )

            claimed_orders = [
                claimed
                for claimed in (first, second)
                if claimed is not None
            ]

            claimed_ids = [
                claimed.order_id for claimed in claimed_orders
            ]

            # The test order must be claimed exactly once.
            assert claimed_ids.count(order_id) == 1, (
                f"Expected exactly one claim for {order_id}; "
                f"got {claimed_ids}"
            )

            assert len(claimed_orders) == 1, (
                f"Expected one claimed order; got {len(claimed_orders)}"
            )

            # Verify the saved order state and worker ownership.
            async with test_session() as session:
                result = await session.execute(
                    select(Order).where(Order.order_id == order_id)
                )
                order = result.scalar_one()

                assert order.status == OrderStatus.PROCESSING
                assert order.worker_id in {
                    "integration-worker-1",
                    "integration-worker-2",
                }
                assert order.lease_token is not None

        finally:
            # Delete only the order created by this test.
            async with test_session() as session, session.begin():
                result = await session.execute(
                    select(Order).where(Order.order_id == order_id)
                )
                order = result.scalar_one_or_none()

                if order is not None:
                    await session.delete(order)

    finally:
        await test_engine.dispose()
