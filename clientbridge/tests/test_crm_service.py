
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import settings
from app.services.crm_service import CRMClient, compute_backoff


def test_backoff_never_exceeds_maximum():
    with patch(
        "app.services.crm_service.random.uniform",
        return_value=1.2,
    ):
        delay = compute_backoff(100)

    assert delay <= settings.BACKOFF_MAX_SECONDS


def test_backoff_starts_from_base_delay():
    with patch(
        "app.services.crm_service.random.uniform",
        return_value=1.0,
    ):
        delay = compute_backoff(1)

    assert delay == settings.BACKOFF_BASE_SECONDS


@pytest.mark.asyncio
async def test_crm_timeout_is_retryable():
    crm = CRMClient()

    try:
        with patch.object(
            crm._client,
            "post",
            new_callable=AsyncMock,
            side_effect=httpx.ReadTimeout("Simulated CRM timeout"),
        ):
            result = await crm.send_order(
                order_id="ORD-TIMEOUT-TEST-001",
                customer_email="timeout@example.com",
                total_amount=1500,
            )

        assert result.status_code == 0
        assert result.retryable is True
        assert result.crm_id is None
        assert "Timeout" in result.error
    finally:
        await crm.aclose()
