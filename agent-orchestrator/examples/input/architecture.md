# Payment Service Architecture

## Overview

The payment service handles all monetary transactions for the platform. It is
responsible for processing card payments, managing refunds, and reconciling
ledger entries at end of day. The service is implemented as a REST API deployed
on Kubernetes and communicates with three external providers: Stripe, PayPal,
and an internal fraud-detection system.

## Components

### API Gateway

All external requests enter through the API gateway. The gateway performs TLS
termination, rate limiting (100 req/s per client), and routes to the payment
processor. Authentication is handled via API keys passed in the `X-API-Key`
header. Keys are validated against a Redis cache with a 5-minute TTL.

Note: the gateway currently does not validate the key format before querying
Redis, which may allow cache poisoning via specially crafted key strings.

### Payment Processor

The payment processor is a stateless Go service. It receives a payment intent
from the gateway, selects a payment provider based on currency and region, and
delegates to the appropriate provider adapter (Stripe or PayPal).

Provider selection logic is hardcoded in a switch statement. Adding a new
provider requires modifying the core processor file.

### Fraud Detection Bridge

Before authorising any transaction above $500, the processor calls the
internal fraud-detection service synchronously over HTTP. The fraud service
has a p99 latency of 800 ms. No circuit breaker or timeout is configured on
this call, so a slow fraud service will block the payment processor indefinitely.

### Ledger Service

All completed transactions are written to a PostgreSQL ledger. Writes happen
synchronously in the request path. There is no retry logic for failed writes;
a database failure during write will return a 500 error to the caller even
though the payment may have already been authorised by the provider.

## Data Flow

1. Client sends `POST /v1/payments` with card token and amount.
2. Gateway validates API key and applies rate limit.
3. Processor selects provider and calls provider API.
4. If amount > $500, fraud check is called before provider authorisation.
5. On success, ledger write is attempted.
6. Response returned to client.

## Deployment

The service runs as three replicas in Kubernetes. Horizontal pod autoscaling
is configured to scale to 10 replicas under load. Secrets (provider API keys,
database credentials) are stored in Kubernetes Secrets and mounted as
environment variables.

## Known Issues

- No dead-letter queue for failed ledger writes (issue #142).
- Fraud detection timeout not implemented (issue #89).
- Provider selection is not configurable at runtime (issue #201).
