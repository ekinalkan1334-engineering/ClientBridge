
import asyncio
import random
import string

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/mock/crm", tags=["mock-crm"])

_seen: dict[str, str] = {}
_request_counts: dict[str, int] = {}
_in_progress: dict[str, asyncio.Event] = {}


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

    order_id = payload.get("order_id", "")

    _request_counts[idempotency_key] = (
        _request_counts.get(idempotency_key, 0) + 1
    )

    if idempotency_key in _seen:
        return {
            "status": "SUCCESS",
            "crm_id": _seen[idempotency_key],
        }

    # If another request with the same key is processing,
    # wait for its result instead of creating another CRM order.
    existing_request = _in_progress.get(idempotency_key)

    if existing_request is not None:
        await existing_request.wait()

        if idempotency_key in _seen:
            return {
                "status": "SUCCESS",
                "crm_id": _seen[idempotency_key],
            }

        return JSONResponse(
            status_code=503,
            content={"detail": "Previous CRM request did not complete"},
        )

    request_finished = asyncio.Event()
    _in_progress[idempotency_key] = request_finished

    try:
        # Dedicated test order: keep the CRM request in progress
        # long enough to test worker termination and recovery.
        if order_id.startswith("ORD-CRASH-RECOVERY-"):
            await asyncio.sleep(120)
            crm_id = "CRM-CRASH-TEST-001"
            _seen[idempotency_key] = crm_id
            return {"status": "SUCCESS", "crm_id": crm_id}

        roll = random.random()

        if roll < 0.80:
            crm_id = "CRM-" + "".join(
                random.choices(
                    string.ascii_uppercase + string.digits,
                    k=5,
                )
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

    finally:
        _in_progress.pop(idempotency_key, None)
        request_finished.set()
