
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import health, mock_crm, orders, webhooks
from app.core.config import settings
from app.core.database import engine
from app.services.crm_service import CRMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.crm_client = CRMClient()
    yield
    await app.state.crm_client.aclose()
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# React frontend'in backend API'ye erişmesine izin ver.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(health.router)
app.include_router(mock_crm.router)
app.include_router(orders.router)
