
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.models.worker_heartbeat import WorkerHeartbeat

logger = logging.getLogger(__name__)

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

    # 1. Database connection
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        logger.exception("Readiness check failed: database")

    # 2. CRM connectivity
    try:
        checks["crm"] = await request.app.state.crm_client.is_reachable()
        if not checks["crm"]:
            logger.error("Readiness check failed: CRM is unreachable")
    except Exception:
        logger.exception("Readiness check failed: CRM")

    # 3. Worker heartbeat freshness
    try:
        latest_heartbeat = await session.scalar(
            select(func.max(WorkerHeartbeat.last_seen))
        )

        if latest_heartbeat is None:
            logger.warning("Readiness check failed: no worker heartbeat")
        else:
            if latest_heartbeat.tzinfo is None:
                latest_heartbeat = latest_heartbeat.replace(
                    tzinfo=timezone.utc
                )

            now = datetime.now(timezone.utc)
            timeout = timedelta(
                seconds=settings.HEARTBEAT_TIMEOUT_SECONDS
            )

            checks["worker"] = now - latest_heartbeat <= timeout

            if not checks["worker"]:
                logger.warning(
                    "Readiness check failed: worker heartbeat is stale. "
                    "Last heartbeat: %s; timeout: %s seconds",
                    latest_heartbeat,
                    settings.HEARTBEAT_TIMEOUT_SECONDS,
                )
    except Exception:
        logger.exception("Readiness check failed: worker heartbeat")

    ok = all(checks.values())

    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "status": "ok" if ok else "unavailable",
            "checks": checks,
        },
    )
