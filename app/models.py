from pydantic import BaseModel


class Order(BaseModel):
    customer_id: str
    item: str
    amount: float


class OrderResponse(BaseModel):
    order_id: str
    status: str
    message: str
