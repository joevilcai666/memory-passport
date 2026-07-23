# Tenant webhooks

Memory Passport can deliver HMAC-signed lifecycle events to one HTTPS webhook
endpoint per tenant. This is the integration point for operators who want to
react to memory, migration, and device lifecycle changes in their own systems.

> V0.1 scope: at-least-once delivery via in-process background tasks. There is
> no durable outbox/queue yet — see "Delivery guarantees" below. The configured
> endpoint and signing secret are tenant-scoped and operator-managed.

## Configure an endpoint

An Owner or Admin registers a destination and receives a one-time signing
secret. The secret is shown **exactly once**; only its hash is stored.

```bash
curl -X POST http://127.0.0.1:8000/v1/webhooks \
  -H "Authorization: Bearer $MP_API_KEY" \
  -H "content-type: application/json" \
  -d '{
    "url": "https://your-receiver.example/webhooks/memory-passport",
    "events": [
      "memory.created",
      "memory.needs_confirmation",
      "memory.deleted",
      "migration.completed",
      "migration.failed",
      "device.bound",
      "device.unbound"
    ]
  }'
```

The response includes `signing_secret` (`whsec_…`). Store it securely — it is
never returned again. List reads return only safe metadata (URL, events, id).

## Event payload

Each delivery is a POST with this body:

```json
{
  "event_id": "evt_<unique>",
  "event_type": "memory.created",
  "tenant_id": "ten_luna",
  "timestamp": "2026-07-23T10:00:00Z",
  "data": { "memory_id": "mem_…", "user_id": "usr_…", ... }
}
```

`event_id` is globally unique. Under at-least-once delivery the same `event_id`
may be delivered more than once — your receiver **must** be idempotent (dedupe
on `event_id`).

## Verify the signature

Every request is signed so you can reject tampering and replay. The signature
is in the `mp-signature` header:

```
mp-signature: t=<unix-timestamp>,v1=<hex-hmac-sha256>
```

To verify:

1. Split the header into `t` (timestamp) and `v1` (signature).
2. Recompute `HMAC-SHA256(signing_secret, "<t>.<raw-body>")` as lowercase hex.
3. Compare it to `v1` using a constant-time compare.
4. Reject if the timestamp is outside your replay window (e.g. ±5 minutes).

Example (Python):

```python
import hmac, hashlib

def verify(signing_secret: str, header: str, body: bytes) -> bool:
    parts = dict(p.split("=", 1) for p in header.split(","))
    t, v1 = parts["t"], parts["v1"]
    expected = hmac.new(
        signing_secret.encode(), f"{t}.".encode() + body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, v1)
```

## Event types

| Event | When it fires | `data` fields |
|---|---|---|
| `memory.created` | A new memory is ingested (active) | `memory_id`, `user_id`, `agent_id`, `event_id`, `status` |
| `memory.needs_confirmation` | A memory enters the `candidate` state (S2/confirm) | same as above |
| `memory.deleted` | A memory is tombstoned | `memory_id`, `user_id` |
| `migration.completed` | A migration finishes (completed or with warnings) | `migration_id`, `migrated_count`, `failed_count`, `status` |
| `migration.failed` | A migration produces no successful moves | `migration_id`, `failed_count` |
| `device.bound` | A device is bound to a user via pairing code | `device_id`, `user_id` |
| `device.unbound` | A device is unbound | `device_id`, `user_id` |

## Delivery guarantees

- **At-least-once**: events are retried with bounded exponential backoff on
  non-2xx responses or timeouts. A dead/disabled endpoint cannot block the
  user-facing transaction — delivery runs after the response is sent.
- **Retry limit**: 4 attempts (configurable via `MP_WEBHOOK_MAX_ATTEMPTS`).
- **Timeout**: 10s per attempt (`MP_WEBHOOK_DELIVERY_TIMEOUT_SECONDS`).
- **V0.1 limitation**: delivery runs as an in-process background task. If the
  process restarts mid-delivery, a `pending` delivery is not automatically
  redriven (no durable outbox poller yet). Terminal status (`delivered` /
  `failed`) is persisted and observable.

## Observe delivery status

```bash
curl http://127.0.0.1:8000/v1/webhooks/wh_<id>/deliveries \
  -H "Authorization: Bearer $MP_API_KEY"
```

Returns the 100 most recent deliveries with `status`, `attempts`, `last_error`,
and timestamps — no secrets.

## Security

- Destinations must be HTTPS (SSRF defense rejects non-HTTPS/private hosts,
  except `localhost`/`127.0.0.1` for local-eval test receivers).
- Only Owner/Admin roles may register an endpoint (Support gets 403).
- The signing secret is never logged or returned after creation.
- Endpoints and deliveries are tenant-isolated.
