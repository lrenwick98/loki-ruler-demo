#!/bin/bash
# Load generator — sends orders to the order-service every 2 seconds

ROUTE=$(oc get route order-service -n loki-ruler-demo -o jsonpath='{.spec.host}' 2>/dev/null)

if [ -z "$ROUTE" ]; then
    echo "Could not find order-service route. Using localhost:8080"
    ROUTE="localhost:8080"
    SCHEME="http"
else
    SCHEME="https"
fi

ITEMS=("laptop" "keyboard" "monitor" "headset" "webcam" "docking-station" "mouse" "usb-hub")
CUSTOMERS=("cust-001" "cust-002" "cust-003" "cust-004" "cust-005")

echo "============================================"
echo "  Order Generator — Sending to ${ROUTE}"
echo "============================================"
echo ""

ORDER_NUM=0
while true; do
    ORDER_NUM=$((ORDER_NUM + 1))
    ITEM=${ITEMS[$((RANDOM % ${#ITEMS[@]}))]}
    CUSTOMER=${CUSTOMERS[$((RANDOM % ${#CUSTOMERS[@]}))]}
    AMOUNT=$(( (RANDOM % 500) + 50 ))

    echo -n "[Order #${ORDER_NUM}] ${CUSTOMER} -> ${ITEM} (\$${AMOUNT}) ... "

    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${SCHEME}://${ROUTE}/orders" \
        -H "Content-Type: application/json" \
        -d "{\"customer_id\": \"${CUSTOMER}\", \"item\": \"${ITEM}\", \"amount\": ${AMOUNT}}")

    BODY=$(echo "$RESPONSE" | head -1)
    STATUS=$(echo "$RESPONSE" | tail -1)

    ORDER_STATUS=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null || echo "?")

    if [ "$ORDER_STATUS" = "confirmed" ]; then
        echo "APPROVED"
    else
        echo "FAILED ($ORDER_STATUS)"
    fi

    sleep 2
done
