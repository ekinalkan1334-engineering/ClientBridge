
import asyncio

from sqlalchemy import select

from app.core.database import SessionLocal, engine
from app.models.order import Order


ORDER_ID = "ORD-E2E-20261017-01"


async def main():
    try:
        async with SessionLocal() as session:
            result = await session.execute(
                select(Order).where(Order.order_id == ORDER_ID)
            )

            order = result.scalar_one_or_none()

            if order is None:
                print(f"Sipariş bulunamadı: {ORDER_ID}")
                return

            print("\n--- CLIENTBRIDGE SIPARIS KONTROLU ---")
            print(f"Sipariş ID:       {order.order_id}")
            print(f"Durum:            {order.status.value}")
            print(f"Deneme sayısı:    {order.retry_count}")
            print(f"Worker ID:        {order.worker_id}")
            print(f"Son heartbeat:    {order.last_heartbeat}")

            if order.status.value == "SYNCED":
                print("\nSONUC: Sipariş başarıyla senkronize edilmiş.")
            elif order.status.value == "PROCESSING":
                print("\nSONUC: Worker siparişi şu anda işliyor.")
            elif order.status.value == "PENDING":
                print("\nSONUC: Sipariş henüz işlenmeyi bekliyor.")
            elif order.status.value == "FAILED":
                print("\nSONUC: Sipariş işlenirken başarısız olmuş.")

    except Exception as exc:
        print("Sipariş kontrolü sırasında hata oluştu.")
        print(f"{type(exc).__name__}: {exc}")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
