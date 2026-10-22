
import asyncio
import random
import string

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/mock/crm", tags=["mock-crm"])

_seen: dict[str, str] = {}


@router.post("/orders")
async def mock_create_order(
    payload: dict,
    idempotency_key: str | None = Header(default=None),
):
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header is required",
        )

    if idempotency_key in _seen:
        return {
            "status": "SUCCESS",
            "crm_id": _seen[idempotency_key],
        }

    # Controlled crash-recovery test:
    # Only dedicated test orders receive a delayed response.
    order_id = payload.get("order_id", "")

    if order_id.startswith("ORD-CRASH-RECOVERY-"):
        crm_id = "CRM-CRASH-TEST-001"
        _seen[idempotency_key] = crm_id
        await asyncio.sleep(120)
        return {"status": "SUCCESS", "crm_id": crm_id}

    roll = random.random()

    if roll < 0.80:
        crm_id = "CRM-" + "".join(
            random.choices(string.ascii_uppercase + string.digits, k=5)
        )
        _seen[idempotency_key] = crm_id
        return {"status": "SUCCESS", "crm_id": crm_id}

    if roll < 0.90:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too Many Requests"},
            headers={"Retry-After": "2"},
        )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal CRM error"},
    )
