
import asyncio

from sqlalchemy import text
from app.core.database import engine


async def main():
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            print("PostgreSQL bağlantısı başarılı:", result.scalar())
    except Exception as exc:
        print("PostgreSQL bağlantısı başarısız.")
        print(type(exc).__name__, str(exc))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
