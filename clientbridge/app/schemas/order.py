from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class OrderItem(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    name: str | None = None
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class OrderWebhookRequest(BaseModel):
    order_id: str = Field(min_length=1, max_length=100)
    customer_email: EmailStr
    total_amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    items: list[OrderItem] = Field(min_length=1)


class WebhookAccepted(BaseModel):
    status: str = "accepted"
    order_id: str
