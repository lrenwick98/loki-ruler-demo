import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI
from payment_client import PaymentClient
from models import Order, OrderResponse


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("event", "order_id", "downstream_status", "consecutive_failures"):
            val = getattr(record, key, None)
            if val is not None:
                log["msg" if key == "event" else key] = val
        return json.dumps(log)


handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("order-service")
logger.setLevel(logging.INFO)
logger.handlers = [handler]

app = FastAPI(title="Order Service")
payment_client = PaymentClient()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/orders", response_model=OrderResponse)
def create_order(order: Order):
    order_id = str(uuid.uuid4())[:8]

    logger.info(
        "Processing order %s for customer %s — %s ($%.2f)",
        order_id,
        order.customer_id,
        order.item,
        order.amount,
        extra={"event": "order_received", "order_id": order_id},
    )

    result = payment_client.process_payment(order_id, order.amount)

    if result.get("status") == "approved":
        logger.info(
            "Order %s payment approved",
            order_id,
            extra={"event": "payment_approved", "order_id": order_id},
        )
        return OrderResponse(order_id=order_id, status="confirmed", message="Payment approved")

    reason = result.get("reason", "unknown")
    logger.error(
        "Order %s payment failed — %s",
        order_id,
        reason,
        extra={"event": reason, "order_id": order_id},
    )
    return OrderResponse(order_id=order_id, status="failed", message=f"Payment failed: {reason}")
