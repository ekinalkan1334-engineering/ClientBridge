
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from app.models.order import Order, OrderStatus, SyncAttempt
from app.services.crm_service import CRMResult
from app.services.recovery_service import lease_valid
from app.workers import polling_worker


def test_lease_valid_checks_order_token_and_status():
    order_pk = uuid.uuid4()
    stale_token = uuid.uuid4()

    condition = lease_valid(order_pk, stale_token)
    compiled = condition.compile(dialect=postgresql.dialect())

    sql = str(compiled).lower()
    params = compiled.params

    assert "lease_token" in sql
    assert "status" in sql
    assert "id" in sql
    assert stale_token in params.values()
    assert OrderStatus.PROCESSING.value in params.values()


@pytest.mark.asyncio
async def test_mark_synced_returns_false_when_lease_is_lost():
    claimed = polling_worker.ClaimedOrder(
        pk=uuid.uuid4(),
        order_id="ORD-STALE-TEST",
        customer_email="test@example.com",
        total_amount=Decimal("10.00"),
        retry_count=0,
        lease_token=uuid.uuid4(),
    )

    fake_session = MagicMock()
    fake_session.execute = AsyncMock()

    fake_result = MagicMock()
    fake_result.scalar_one_or_none.return_value = None
    fake_session.execute.return_value = fake_result

    fake_context = MagicMock()
    fake_context.__aenter__ = AsyncMock(return_value=fake_session)
    fake_context.__aexit__ = AsyncMock(return_value=None)

    crm_result = CRMResult(status_code=200, crm_id="CRM-TEST-1")

    with patch.object(
        polling_worker, "SessionLocal", return_value=fake_context
    ):
        saved = await polling_worker.mark_synced(claimed, crm_result)

    assert saved is False
    fake_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_mark_failed_attempt_returns_false_when_lease_is_lost():
    claimed = polling_worker.ClaimedOrder(
        pk=uuid.uuid4(),
        order_id="ORD-STALE-FAIL-TEST",
        customer_email="test@example.com",
        total_amount=Decimal("10.00"),
        retry_count=0,
        lease_token=uuid.uuid4(),
    )

    fake_session = MagicMock()
    fake_session.execute = AsyncMock()

    fake_result = MagicMock()
    fake_result.scalar_one_or_none.return_value = None
    fake_session.execute.return_value = fake_result

    fake_context = MagicMock()
    fake_context.__aenter__ = AsyncMock(return_value=fake_session)
    fake_context.__aexit__ = AsyncMock(return_value=None)

    crm_result = CRMResult(
        status_code=500,
        error="Test error",
        retryable=True,
    )

    with patch.object(
        polling_worker, "SessionLocal", return_value=fake_context
    ):
        saved = await polling_worker.mark_failed_attempt(claimed, crm_result)

    assert saved is False
    fake_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_fifth_retryable_failure_marks_order_failed():
    claimed = polling_worker.ClaimedOrder(
        pk=uuid.uuid4(),
        order_id="ORD-FIFTH-FAIL-TEST",
        customer_email="test@example.com",
        total_amount=Decimal("10.00"),
        retry_count=4,
        lease_token=uuid.uuid4(),
    )

    fake_session = MagicMock()
    fake_session.execute = AsyncMock()

    fake_result = MagicMock()
    fake_result.scalar_one_or_none.return_value = claimed.pk
    fake_session.execute.return_value = fake_result

    fake_context = MagicMock()
    fake_context.__aenter__ = AsyncMock(return_value=fake_session)
    fake_context.__aexit__ = AsyncMock(return_value=None)

    crm_result = CRMResult(
        status_code=503,
        error="Service unavailable",
        retryable=True,
    )

    with patch.object(
        polling_worker, "SessionLocal", return_value=fake_context
    ):
        saved = await polling_worker.mark_failed_attempt(claimed, crm_result)

    assert saved is True

    statement = fake_session.execute.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())

    sql = str(compiled).lower()
    params = compiled.params

    assert "update" in sql
    assert "retry_count" in sql
    assert "status" in sql
    assert "next_retry_at" in sql
    assert 5 in params.values()
    assert OrderStatus.FAILED.value in params.values()
    assert any(
        value is None
        for key, value in params.items()
        if "next_retry_at" in key
    )

    fake_session.add.assert_called_once()
    assert isinstance(fake_session.add.call_args.args[0], SyncAttempt)


@pytest.mark.asyncio
async def test_retryable_failure_returns_order_to_pending():
    claimed = polling_worker.ClaimedOrder(
        pk=uuid.uuid4(),
        order_id="ORD-RETRY-TEST",
        customer_email="test@example.com",
        total_amount=Decimal("10.00"),
        retry_count=0,
        lease_token=uuid.uuid4(),
    )

    fake_session = MagicMock()
    fake_session.execute = AsyncMock()

    fake_result = MagicMock()
    fake_result.scalar_one_or_none.return_value = claimed.pk
    fake_session.execute.return_value = fake_result

    fake_context = MagicMock()
    fake_context.__aenter__ = AsyncMock(return_value=fake_session)
    fake_context.__aexit__ = AsyncMock(return_value=None)

    crm_result = CRMResult(
        status_code=0,
        error="Timeout: simulated timeout",
        retryable=True,
    )

    with patch.object(
        polling_worker, "SessionLocal", return_value=fake_context
    ), patch.object(
        polling_worker, "compute_backoff", return_value=2.0
    ):
        saved = await polling_worker.mark_failed_attempt(claimed, crm_result)

    assert saved is True

    statement = fake_session.execute.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())

    sql = str(compiled).lower()
    params = compiled.params

    assert "retry_count" in sql
    assert "next_retry_at" in sql
    assert 1 in params.values()
    assert OrderStatus.PENDING.value in params.values()
    assert any(
        value is not None
        for key, value in params.items()
        if "next_retry_at" in key
    )

    fake_session.add.assert_called_once()
    assert isinstance(fake_session.add.call_args.args[0], SyncAttempt)
