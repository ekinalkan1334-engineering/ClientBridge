"""initial schema: orders, sync_attempts, crm_links

Revision ID: 0001
Revises:
Create Date: 2026-10-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

order_status = postgresql.ENUM(
    "PENDING", "PROCESSING", "SYNCED", "FAILED", name="order_status", create_type=False
)
UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    order_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "orders",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id", sa.String(100), nullable=False),
        sa.Column("customer_email", sa.String(255), nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", order_status, nullable=False, server_default="PENDING"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True)),
        sa.Column("worker_id", sa.String(100)),
        sa.Column("lease_token", UUID),
        sa.Column("next_retry_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_orders_order_id", "orders", ["order_id"], unique=True)
    op.create_index("ix_orders_status", "orders", ["status"])

    op.create_table(
        "sync_attempts",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_ref_id", UUID, sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("response_code", sa.Integer, nullable=False),
        sa.Column("error_message", sa.Text),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "crm_links",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_ref_id", UUID, sa.ForeignKey("orders.id"), nullable=False, unique=True),
        sa.Column("crm_customer_id", sa.String(100), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("crm_links")
    op.drop_table("sync_attempts")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_order_id", table_name="orders")
    op.drop_table("orders")
    order_status.drop(op.get_bind(), checkfirst=True)
