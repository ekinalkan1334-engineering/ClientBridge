import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SYNCED = "SYNCED"
    FAILED = "FAILED"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    order_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"),
        nullable=False,
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    worker_id: Mapped[str | None] = mapped_column(String(100))
    lease_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # Spec'te yok; exponential backoff'un "ne zaman tekrar denensin" bilgisini tutar.
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SyncAttempt(Base):
    __tablename__ = "sync_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    order_ref_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    # 0 = CRM'den HTTP yanıtı alınamadı (timeout / ağ hatası)
    response_code: Mapped[int] = mapped_column(Integer, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CRMLink(Base):
    __tablename__ = "crm_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    order_ref_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), unique=True, nullable=False
    )
    crm_customer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
