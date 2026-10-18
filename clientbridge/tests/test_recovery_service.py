
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from app.models.order import OrderStatus
from app.services import recovery_service


@pytest.mark.asyncio
async def test_recovery_returns_stale_processing_orders_to_pending():
    fake_session = MagicMock()
    fake_session.execute = AsyncMock()

    fake_result = MagicMock()
    fake_result.all.return_value = [("order-1",), ("order-2",)]
    fake_session.execute.return_value = fake_result

    fake_context = MagicMock()
    fake_context.__aenter__ = AsyncMock(return_value=fake_session)
    fake_context.__aexit__ = AsyncMock(return_value=None)

    with patch.object(
        recovery_service,
        "SessionLocal",
        return_value=fake_context,
    ):
        recovered = await recovery_service.recover_stale_orders()

    assert recovered == 2

    statement = fake_session.execute.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())

    sql = str(compiled).lower()
    params = compiled.params

    assert "update" in sql
    assert "last_heartbeat" in sql
    assert "lease_token" in sql
    assert OrderStatus.PROCESSING.value in params.values()
    assert OrderStatus.PENDING.value in params.values()
    assert any(
        value is None
        for key, value in params.items()
        if "lease_token" in key
    )
