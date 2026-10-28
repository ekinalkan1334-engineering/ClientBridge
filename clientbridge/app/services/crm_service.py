
import random
from dataclasses import dataclass
from decimal import Decimal

import httpx

from app.core.config import settings


@dataclass
class CRMResult:
    status_code: int
    crm_id: str | None = None
    error: str | None = None
    retryable: bool = False

    @property
    def ok(self) -> bool:
        return self.crm_id is not None and self.error is None


def compute_backoff(retry_count: int) -> float:
    """Calculate exponential backoff with jitter."""
    base_delay = min(
        settings.BACKOFF_BASE_SECONDS
        * (2 ** max(retry_count - 1, 0)),
        settings.BACKOFF_MAX_SECONDS,
    )

    jittered_delay = base_delay * random.uniform(0.8, 1.2)

    return min(
        jittered_delay,
        settings.BACKOFF_MAX_SECONDS,
    )


class CRMClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.CRM_BASE_URL,
            timeout=httpx.Timeout(settings.CRM_TIMEOUT_SECONDS),
        )

    async def send_order(
        self,
        order_id: str,
        customer_email: str,
        total_amount: Decimal,
    ) -> CRMResult:
        payload = {
            "order_id": order_id,
            "customer_email": customer_email,
            "total_amount": str(total_amount),
        }

        try:
            response = await self._client.post(
                settings.CRM_ORDERS_PATH,
                json=payload,
                headers={"Idempotency-Key": order_id},
            )
        except httpx.TimeoutException as exc:
            return CRMResult(
                status_code=0,
                error=f"Timeout: {exc!r}",
                retryable=True,
            )
        except httpx.HTTPError as exc:
            return CRMResult(
                status_code=0,
                error=f"Network error: {exc!r}",
                retryable=True,
            )

        code = response.status_code

        if 200 <= code < 300:
            try:
                crm_id = response.json().get("crm_id")
            except ValueError:
                crm_id = None

            if crm_id:
                return CRMResult(
                    status_code=code,
                    crm_id=crm_id,
                )

            return CRMResult(
                status_code=code,
                error="CRM response did not contain crm_id.",
                retryable=True,
            )

        retryable = code == 429 or code >= 500

        return CRMResult(
            status_code=code,
            error=response.text[:500],
            retryable=retryable,
        )

    async def is_reachable(self) -> bool:
        """Check whether the CRM server responds to HTTP requests."""
        try:
            response = await self._client.options(
                settings.CRM_ORDERS_PATH,
                timeout=3.0,
            )

            return response.status_code < 500

        except httpx.HTTPError:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()
