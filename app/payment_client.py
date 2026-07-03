import os
import time
import logging
import httpx

logger = logging.getLogger("order-service")

PAYMENT_GATEWAY_URL = os.environ.get("PAYMENT_GATEWAY_URL", "http://payment-simulator:8080")
PAYMENT_TIMEOUT = float(os.environ.get("PAYMENT_TIMEOUT", "3"))

CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_RESET_TIMEOUT = 30


class PaymentClient:
    def __init__(self):
        self._consecutive_failures = 0
        self._circuit_open_since = None

    def _is_circuit_open(self) -> bool:
        if self._circuit_open_since is None:
            return False
        elapsed = time.time() - self._circuit_open_since
        if elapsed > CIRCUIT_BREAKER_RESET_TIMEOUT:
            logger.info("Circuit breaker half-open, allowing probe request",
                        extra={"msg": "circuit_breaker_half_open"})
            return False
        return True

    def _record_success(self):
        self._consecutive_failures = 0
        self._circuit_open_since = None

    def _record_failure(self):
        self._consecutive_failures += 1
        if self._consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD and self._circuit_open_since is None:
            self._circuit_open_since = time.time()
            logger.error(
                "Circuit breaker OPEN after %d consecutive failures",
                self._consecutive_failures,
                extra={"msg": "circuit_breaker_open", "consecutive_failures": self._consecutive_failures},
            )

    def process_payment(self, order_id: str, amount: float) -> dict:
        if self._is_circuit_open():
            logger.error(
                "Payment rejected — circuit breaker is open for order %s",
                order_id,
                extra={"msg": "circuit_breaker_open", "order_id": order_id},
            )
            return {"status": "failed", "reason": "circuit_breaker_open"}

        try:
            resp = httpx.post(
                f"{PAYMENT_GATEWAY_URL}/pay",
                json={"order_id": order_id, "amount": amount},
                timeout=PAYMENT_TIMEOUT,
            )
            if resp.status_code == 200:
                self._record_success()
                return resp.json()

            logger.error(
                "Payment gateway returned %d for order %s",
                resp.status_code,
                order_id,
                extra={
                    "msg": "payment_gateway_error",
                    "order_id": order_id,
                    "downstream_status": resp.status_code,
                },
            )
            self._record_failure()
            return {"status": "failed", "reason": "payment_gateway_error"}

        except httpx.TimeoutException:
            logger.error(
                "Payment gateway timeout for order %s",
                order_id,
                extra={"msg": "payment_gateway_timeout", "order_id": order_id},
            )
            self._record_failure()
            return {"status": "failed", "reason": "payment_gateway_timeout"}

        except httpx.ConnectError:
            logger.error(
                "Payment gateway connection refused for order %s",
                order_id,
                extra={"msg": "payment_gateway_connection_refused", "order_id": order_id},
            )
            self._record_failure()
            return {"status": "failed", "reason": "payment_gateway_connection_refused"}
