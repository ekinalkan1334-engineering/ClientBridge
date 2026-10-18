
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings


async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT order_id, status, retry_count
                    FROM orders
                    WHERE order_id = :oid
                """),
                {"oid": "ORD-2026-002"},
            )
            print(result.fetchone())
    finally:
        await engine.dispose()


asyncio.run(main())
