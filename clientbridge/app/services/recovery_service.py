"""Lease doğrulaması, heartbeat yenileme ve çöken worker'ların kurtarılması.

Benzetme: Bir siparişi alan worker'a "kiralık anahtar" (lease_token) verilir.
Worker çökerse anahtar süresi dolar, Recovery Task kapıyı yeniden açar. Eski worker
sonradan uyanıp eski anahtarla gelirse kapı artık o anahtara uymaz.
"""
import asyncio
import contextlib
import logging
import uuid
from datetime import timedelta

from sqlalchemy import and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.order import Order, OrderStatus

log = logging.getLogger(__name__)


def lease_valid(order_pk: uuid.UUID, lease_token: uuid.UUID):
    """Her yazma işleminin WHERE koşuluna eklenen lease kontrolü.

    Kontrolü ayrı bir SELECT ile yapmak yerine UPDATE'in içine koyuyoruz; böylece
    "kontrol et -> sonra yaz" arasındaki boşlukta lease kaybolamaz (TOCTOU yok).
    """
    return and_(
        Order.id == order_pk,
        Order.lease_token == lease_token,
        Order.status == OrderStatus.PROCESSING,
    )


async def renew_heartbeat(session: AsyncSession, order_pk: uuid.UUID, lease_token: uuid.UUID) -> bool:
    """True: lease hâlâ bizde, heartbeat yenilendi. False: lease kaybedildi."""
    result = await session.execute(
        update(Order)
        .where(lease_valid(order_pk, lease_token))
        .values(last_heartbeat=func.now())
        .returning(Order.id)
        .execution_options(synchronize_session=False)
    )
    return result.scalar_one_or_none() is not None


async def recover_stale_orders() -> int:
    """Heartbeat'i 5 dakikadan eski PROCESSING kayıtları tekrar PENDING yapar."""
    threshold = func.now() - timedelta(seconds=settings.HEARTBEAT_TIMEOUT_SECONDS)
    async with SessionLocal() as session, session.begin():
        result = await session.execute(
            update(Order)
            .where(Order.status == OrderStatus.PROCESSING, Order.last_heartbeat < threshold)
            .values(
                status=OrderStatus.PENDING,
                lease_token=None,
                worker_id=None,
                locked_at=None,
                last_heartbeat=None,
            )
            .returning(Order.id)
            .execution_options(synchronize_session=False)
        )
        recovered = len(result.all())
    if recovered:
        log.warning("Recovery: %d takılı sipariş PENDING'e döndürüldü", recovered)
    return recovered


async def interruptible_sleep(stop: asyncio.Event, seconds: float) -> None:
    """Uyur ama stop sinyali gelirse hemen uyanır (graceful shutdown için)."""
    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout=seconds)


async def recovery_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await recover_stale_orders()
        except Exception:
            log.exception("Recovery task hata verdi")
        await interruptible_sleep(stop, settings.RECOVERY_INTERVAL_SECONDS)
