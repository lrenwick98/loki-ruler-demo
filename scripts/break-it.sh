#!/bin/bash
# Chaos script — degrades the payment simulator to trigger Loki alerts

ROUTE=$(oc get route payment-simulator -n loki-ruler-demo -o jsonpath='{.spec.host}' 2>/dev/null)

if [ -z "$ROUTE" ]; then
    echo "Could not find payment-simulator route. Using localhost:8080"
    ROUTE="localhost:8080"
    SCHEME="http"
else
    SCHEME="http"
fi

echo "============================================"
echo "  CHAOS MODE — Degrading Payment Gateway"
echo "============================================"
echo ""
echo "Target: ${SCHEME}://${ROUTE}/admin/degrade"
echo ""

RESPONSE=$(curl -s "${SCHEME}://${ROUTE}/admin/degrade")
echo "Response: ${RESPONSE}"
echo ""
echo "Payment gateway is now returning 503s with 5s delays."
echo "The order-service will start logging errors."
echo "Watch for Loki AlertingRule to fire within ~2 minutes."
echo ""
echo "To recover manually: curl ${SCHEME}://${ROUTE}/admin/recover"
