# Loki Ruler Demo — Log-Driven Observability with EDA Self-Healing

## Scenario Recap

An **order-service** (Python FastAPI) processes customer orders and calls a downstream **payment-simulator** to authorize payments. Everything is deployed correctly in OpenShift — ArgoCD shows green, health probes pass, pods are running.

Then something goes wrong at runtime: the payment gateway starts failing. This is the kind of issue ArgoCD **cannot** detect — the deployment manifests haven't changed, the pods are healthy, the app is running. But orders are silently failing.

**This is where Loki Rulers come in.** Instead of waiting for a human to notice and manually search logs, a **Loki AlertingRule** continuously evaluates a LogQL query against the log stream. When the error rate crosses a threshold, it fires an alert to AlertManager, which sends a webhook to **Event-Driven Ansible (EDA)**. EDA automatically runs a remediation playbook that recovers the payment gateway — no human intervention required.

### The Flow

```
Orders flowing -> Payment simulator healthy -> All good
                           |
                    [run break-it.sh]
                           |
                  Payment simulator degraded
                           |
            Order-service logs errors (structured JSON)
                           |
              Loki AlertingRule evaluates LogQL
                           |
                 Alert fires -> AlertManager
                           |
                AlertManager webhook -> EDA
                           |
              EDA runs remediation playbook
                           |
                Payment simulator recovered
                           |
                    Orders flowing again
```

### Why ArgoCD Can't Catch This

- The Deployment spec hasn't changed — there's no config drift
- The pods are running and passing health checks
- The app itself is healthy — it's the downstream dependency that's failing
- This is a **runtime** failure, not a **deployment** failure

### Key Talking Points

1. **Loki Rulers bridge the gap between logging and monitoring** — they turn raw log patterns into real-time alerts without shipping logs to a separate metrics system
2. **Structured JSON logging is essential** — LogQL can parse JSON fields inline, enabling precise alerting on specific error types (not just "any ERROR")
3. **The circuit breaker pattern** makes the demo realistic — the order-service degrades gracefully before total failure, and the Loki ruler catches both the initial timeout errors AND the circuit breaker tripping
4. **EDA closes the loop** — this isn't just alerting, it's automated recovery using tools (AAP) that enterprise customers already own and trust

## Prerequisites

- OpenShift cluster with:
  - LokiStack operator installed and configured
  - Loki ruler enabled in the LokiStack CR
  - ClusterLogForwarder forwarding application logs to Loki
  - Ansible Automation Platform with EDA controller

## Setup

### 1. Deploy the application

```bash
# Create namespace and deploy payment simulator
oc apply -f openshift/payment-simulator.yaml

# Build and deploy order-service
oc new-build --binary --name=order-service -n loki-ruler-demo
oc start-build order-service --from-dir=. --follow -n loki-ruler-demo
oc apply -f openshift/deployment.yaml
```

### 2. Deploy Loki AlertingRule

```bash
oc apply -f openshift/loki-alerting-rule.yaml
```

### 3. Configure AlertManager

```bash
oc apply -f openshift/alertmanager-config.yaml
```

### 4. Set up EDA

Deploy the EDA rulebook and playbook to your AAP EDA controller, pointing at `eda/rulebook.yaml` and `eda/remediate-payment.yaml`.

## Running the Demo

### Terminal 1 — Start sending orders
```bash
./scripts/send-orders.sh
```

### Terminal 2 — Break the payment gateway
```bash
./scripts/break-it.sh
```

### What to watch

1. **Terminal 1**: Orders start failing ("FAILED" instead of "APPROVED")
2. **OpenShift Console > Observe > Logs**: Structured error logs appearing in Loki
3. **OpenShift Console > Observe > Alerting**: `PaymentGatewayErrorRate` and `CircuitBreakerOpen` alerts fire
4. **AAP EDA Controller**: Rulebook activation triggers, playbook runs
5. **Terminal 1**: Orders start succeeding again — auto-recovered

### Manual recovery (if not using EDA)
```bash
ROUTE=$(oc get route payment-simulator -n loki-ruler-demo -o jsonpath='{.spec.host}')
curl https://${ROUTE}/admin/recover
```
