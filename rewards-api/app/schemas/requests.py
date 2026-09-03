from datetime import datetime

from pydantic import BaseModel, Field


class CheckoutStartIn(BaseModel):
    product_id: str = Field(default="reward_box", description="Key into app.products.PRODUCTS")


class CheckoutStartResponse(BaseModel):
    checkout_url: str
    token: str


class ProductOut(BaseModel):
    id: str
    name: str
    description: str
    price_cents: int
    variants: list[str] | None = None


class FulfillmentIn(BaseModel):
    token: str = Field(..., description="Token from /checkout/start, only valid once payment completes")
    recipient_name: str = Field(..., min_length=1, max_length=120)
    child_first_name: str | None = Field(default=None, max_length=60)
    variant: str | None = Field(default=None, max_length=80, description="Size/color, if the product has one")
    address_line1: str = Field(..., min_length=1, max_length=200)
    address_line2: str | None = Field(default=None, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(default="US", min_length=2, max_length=2)


class FulfillmentOut(BaseModel):
    id: int
    recipient_name: str
    child_first_name: str | None
    variant: str | None
    address_line1: str
    address_line2: str | None
    city: str
    state: str
    postal_code: str
    country: str
    created_at: datetime
    sent_at: datetime | None
    # Set once a made-to-order Shop item has gone to Printify; None means
    # the reward box or a Printify order that needs manual handling.
    printify_order_id: str | None = None
    # Populated by the admin list endpoint (joins back to Order) so the
    # dashboard shows what to actually pack, not just where to send it.
    product_id: str | None = None
    product_name: str | None = None

    model_config = {"from_attributes": True}
