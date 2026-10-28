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


@router.get("/health/live")
async def live():
    return {"status": "ok"}


async def check_dependencies(request: Request, session: AsyncSession):
    checks = {
        "database": False,
        "crm": False,
    }

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        logger.exception("Health check failed: database")

    try:
        checks["crm"] = await request.app.state.crm_client.is_reachable()
        if not checks["crm"]:
            logger.error("Health check failed: CRM is unreachable")
    except Exception:
        logger.exception("Health check failed: CRM")

    return checks


async def check_worker(session: AsyncSession) -> bool:
    try:
        latest_heartbeat = await session.scalar(
            select(func.max(WorkerHeartbeat.last_seen))
        )

        if latest_heartbeat is None:
            logger.warning("System health check failed: no worker heartbeat")
            return False

        if latest_heartbeat.tzinfo is None:
            latest_heartbeat = latest_heartbeat.replace(tzinfo=timezone.utc)

        timeout = timedelta(seconds=settings.HEARTBEAT_TIMEOUT_SECONDS)
        is_healthy = datetime.now(timezone.utc) - latest_heartbeat <= timeout

        if not is_healthy:
            logger.warning(
                "System health check failed: worker heartbeat is stale. "
                "Last heartbeat: %s; timeout: %s seconds",
                latest_heartbeat,
                settings.HEARTBEAT_TIMEOUT_SECONDS,
            )

        return is_healthy
    except Exception:
        logger.exception("System health check failed: worker heartbeat")
        return False


@router.get("/health/ready")
async def ready(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    checks = await check_dependencies(request, session)
    ok = all(checks.values())

    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "status": "ok" if ok else "unavailable",
            "checks": checks,
        },
    )


@router.get("/health/system")
async def system_health(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    checks = await check_dependencies(request, session)
    checks["worker"] = await check_worker(session)
    ok = all(checks.values())

    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "status": "ok" if ok else "unavailable",
            "checks": checks,
        },
    )