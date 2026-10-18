
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.models.worker_heartbeat import WorkerHeartbeat

router = APIRouter(tags=["health"])


@router.get("/health/ready")
async def ready(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    checks = {
        "database": False,
        "crm": False,
        "worker": False,
    }

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass

    try:
        checks["crm"] = await request.app.state.crm_client.is_reachable()
    except Exception:
        checks["crm"] = False

    try:
        latest_heartbeat = await session.scalar(
            select(func.max(WorkerHeartbeat.last_seen))
        )

        if latest_heartbeat is not None:
            now = datetime.now(timezone.utc)
            timeout = timedelta(
                seconds=settings.HEARTBEAT_TIMEOUT_SECONDS
            )

            if latest_heartbeat.tzinfo is None:
                latest_heartbeat = latest_heartbeat.replace(
                    tzinfo=timezone.utc
                )

            checks["worker"] = now - latest_heartbeat <= timeout

    except Exception:
        checks["worker"] = False

    ok = all(checks.values())

    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "status": "ok" if ok else "unavailable",
            "checks": checks,
        },
    )
