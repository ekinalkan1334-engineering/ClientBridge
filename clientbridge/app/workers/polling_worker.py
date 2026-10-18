
import asyncio
import contextlib
import logging
import os
import signal
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models.order import CRMLink, Order, OrderStatus, SyncAttempt
from app.models.worker_heartbeat import WorkerHeartbeat
from app.services.crm_service import CRMClient, CRMResult, compute_backoff
from app.services.recovery_service import (
    interruptible_sleep,
    lease_valid,
    recovery_loop,
    renew_heartbeat,
)

log = logging.getLogger("worker")


@dataclass
class ClaimedOrder:
    pk: uuid.UUID
    order_id: str
    customer_email: str
    total_amount: Decimal
    retry_count: int
    lease_token: uuid.UUID


async def update_worker_heartbeat(worker_id: str) -> None:
    """Create or refresh the heartbeat for this worker process."""
    statement = (
        pg_insert(WorkerHeartbeat)
        .values(
            worker_id=worker_id,
            last_seen=func.now(),
        )
        .on_conflict_do_update(
            index_elements=[WorkerHeartbeat.worker_id],
            set_={"last_seen": func.now()},
        )
    )

    async with SessionLocal() as session, session.begin():
        await session.execute(statement)


async def worker_heartbeat_loop(
    worker_id: str,
    stop: asyncio.Event,
) -> None:
    """Publish a heartbeat periodically while the worker is running."""
    while not stop.is_set():
        try:
            await update_worker_heartbeat(worker_id)
        except Exception:
            log.exception(
                "Could not update worker heartbeat: %s",
                worker_id,
            )

        await interruptible_sleep(
            stop,
            settings.HEARTBEAT_INTERVAL_SECONDS,
        )


async def claim_next_order(worker_id: str) -> ClaimedOrder | None:
    """Atomically claim one pending order using SKIP LOCKED."""
    lease_token = uuid.uuid4()

    async with SessionLocal() as session, session.begin():
        stmt = (
            select(Order)
            .where(
                Order.status == OrderStatus.PENDING,
                or_(
                    Order.next_retry_at.is_(None),
                    Order.next_retry_at <= func.now(),
                ),
            )
            .order_by(Order.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        order = (await session.execute(stmt)).scalar_one_or_none()

        if order is None:
            return None

        order.status = OrderStatus.PROCESSING
        order.locked_at = func.now()
        order.last_heartbeat = func.now()
        order.worker_id = worker_id
        order.lease_token = lease_token
        order.next_retry_at = None

        return ClaimedOrder(
            pk=order.id,
            order_id=order.order_id,
            customer_email=order.customer_email,
            total_amount=order.total_amount,
            retry_count=order.retry_count,
            lease_token=lease_token,
        )


async def heartbeat_loop(
    claimed: ClaimedOrder,
    lease_lost: asyncio.Event,
) -> None:
    while True:
        await asyncio.sleep(settings.HEARTBEAT_INTERVAL_SECONDS)

        try:
            async with SessionLocal() as session, session.begin():
                still_ours = await renew_heartbeat(
                    session,
                    claimed.pk,
                    claimed.lease_token,
                )
        except Exception:
            log.exception(
                "Heartbeat write failed for order=%s; will retry",
                claimed.order_id,
            )
            continue

        if not still_ours:
            log.warning("Lease lost for order=%s", claimed.order_id)
            lease_lost.set()
            return


async def mark_synced(
    claimed: ClaimedOrder,
    result: CRMResult,
) -> bool:
    async with SessionLocal() as session, session.begin():
        res = await session.execute(
            update(Order)
            .where(lease_valid(claimed.pk, claimed.lease_token))
            .values(
                status=OrderStatus.SYNCED,
                lease_token=None,
                locked_at=None,
                last_heartbeat=None,
                worker_id=None,
            )
            .returning(Order.id)
            .execution_options(synchronize_session=False)
        )

        if res.scalar_one_or_none() is None:
            return False

        session.add(
            SyncAttempt(
                order_ref_id=claimed.pk,
                response_code=result.status_code,
            )
        )
        session.add(
            CRMLink(
                order_ref_id=claimed.pk,
                crm_customer_id=result.crm_id,
            )
        )

    log.info("Order synced successfully: %s", claimed.order_id)
    return True


async def mark_failed_attempt(
    claimed: ClaimedOrder,
    result: CRMResult,
) -> bool:
    new_count = claimed.retry_count + 1
    give_up = (
        not result.retryable
        or new_count >= settings.MAX_RETRIES
    )

    values = {
        "retry_count": new_count,
        "lease_token": None,
        "worker_id": None,
        "locked_at": None,
        "last_heartbeat": None,
    }

    if give_up:
        values.update(
            status=OrderStatus.FAILED,
            next_retry_at=None,
        )
    else:
        delay = compute_backoff(new_count)
        values.update(
            status=OrderStatus.PENDING,
            next_retry_at=(
                datetime.now(timezone.utc)
                + timedelta(seconds=delay)
            ),
        )

    async with SessionLocal() as session, session.begin():
        res = await session.execute(
            update(Order)
            .where(lease_valid(claimed.pk, claimed.lease_token))
            .values(**values)
            .returning(Order.id)
            .execution_options(synchronize_session=False)
        )

        if res.scalar_one_or_none() is None:
            return False

        session.add(
            SyncAttempt(
                order_ref_id=claimed.pk,
                response_code=result.status_code,
                error_message=result.error,
            )
        )

    log.warning(
        "CRM request failed: order=%s code=%s retry=%d status=%s",
        claimed.order_id,
        result.status_code,
        new_count,
        "FAILED" if give_up else "PENDING",
    )
    return True


async def process_one(worker_id: str, crm: CRMClient) -> bool:
    """Process one order. Return False if the queue is empty."""
    claimed = await claim_next_order(worker_id)

    if claimed is None:
        return False

    lease_lost = asyncio.Event()
    heartbeat_task = asyncio.create_task(
        heartbeat_loop(claimed, lease_lost)
    )

    try:
        result = await crm.send_order(
            claimed.order_id,
            claimed.customer_email,
            claimed.total_amount,
        )

        if lease_lost.is_set():
            log.warning(
                "Ignoring result because lease was lost: order=%s",
                claimed.order_id,
            )
            return True

        if result.ok:
            written = await mark_synced(claimed, result)
        else:
            written = await mark_failed_attempt(claimed, result)

        if not written:
            log.warning(
                "Lease validation failed; result not saved: order=%s",
                claimed.order_id,
            )

    finally:
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task

    return True


async def poll_loop(
    worker_id: str,
    crm: CRMClient,
    stop: asyncio.Event,
) -> None:
    log.info("Worker started: %s", worker_id)

    while not stop.is_set():
        try:
            found = await process_one(worker_id, crm)
        except Exception:
            log.exception("Unexpected error in worker loop")
            found = False

        if not found:
            await interruptible_sleep(
                stop,
                settings.POLL_INTERVAL_SECONDS,
            )


async def run_worker() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_shutdown(*_args) -> None:
        loop.call_soon_threadsafe(stop.set)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            if os.name == "nt":
                signal.signal(sig, request_shutdown)
            else:
                loop.add_signal_handler(sig, stop.set)
        except (NotImplementedError, OSError, ValueError):
            log.debug("Could not register signal handler for %s", sig)

    crm = CRMClient()
    base = f"{socket.gethostname()}-{os.getpid()}"

    tasks = [
        asyncio.create_task(
            poll_loop(f"{base}-{i}", crm, stop)
        )
        for i in range(settings.WORKER_CONCURRENCY)
    ]

    tasks.append(asyncio.create_task(recovery_loop(stop)))
    tasks.append(asyncio.create_task(worker_heartbeat_loop(base, stop)))

    try:
        await stop.wait()
        log.info("Shutdown requested; waiting for worker tasks...")
    finally:
        stop.set()

        for task in tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        async with SessionLocal() as session, session.begin():
            await session.execute(
                update(WorkerHeartbeat)
                .where(WorkerHeartbeat.worker_id == base)
                .values(last_seen=datetime.now(timezone.utc))
            )

        await crm.aclose()
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass
