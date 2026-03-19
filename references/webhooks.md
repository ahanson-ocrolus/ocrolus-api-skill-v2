# Ocrolus Webhooks -- Production Reference

> Source: https://docs.ocrolus.com/docs/webhook-overview, secure-webhook-urls

## Overview

Ocrolus delivers event notifications via HTTP POST to your configured endpoint(s). Use webhooks instead of polling for efficient, real-time processing updates.

**Key constraints:**
- Webhook requests have a **5-second timeout** -- handlers must respond quickly
- Only ONE webhook type can be active: **org-level OR account-level**, not both
- Return HTTP `200 OK` to acknowledge receipt

## Webhook Types

| Feature | Organization-Level | Account-Level |
|---------|-------------------|---------------|
| Configuration | Dashboard + API | API only |
| Multiple webhooks | Yes (per org) | No (one per account) |
| Testing via API | Yes | Yes |
| Dashboard visibility | Yes | No |
| Recommended | **Yes** | Legacy |

## API Endpoints

### Organization-Level (recommended)

| Operation | Method | Path |
|-----------|--------|------|
| Add Webhook | POST | `/v1/account/settings/webhook` |
| List Webhooks | GET | `/v1/account/settings/webhooks` |
| Retrieve Webhook | GET | `/v1/account/settings/webhooks/{webhook_id}` |
| Update Webhook | PUT | `/v1/account/settings/webhooks/{webhook_id}` |
| Delete Webhook | DELETE | `/v1/account/settings/webhooks/{webhook_id}` |
| List Events | GET | `/v1/account/settings/webhooks/events` |
| Test Webhook | POST | `/v1/account/settings/webhooks/{webhook_id}/test` |
| Configure Secret | POST | `/v1/account/settings/webhooks/secret` |

### Account-Level

| Operation | Method | Path |
|-----------|--------|------|
| Configure | POST | `/v1/webhook/configure` |
| Get Config | GET | `/v1/webhook/configuration` |
| Test | GET/POST | `/v1/webhook/test` |
| Configure Secret | POST | `/v1/webhook/secret` |

## Event Types

> **# NEEDS LIVE VALIDATION**
> The event names below were assembled from scattered doc references and may not match
> the exact strings Ocrolus sends in production payloads. **Before deploying**, call
> `list_org_webhook_events()` against your tenant and replace this list with the actual
> response. If event names don't match, your handlers will silently ignore real traffic.
> See README section "Step 2: Validate Webhook Event Names" for instructions.

### Document Events (unvalidated -- verify against your tenant)
- `document.classification_succeeded` -- classification complete
- `document.classification_failed` -- classification failed
- `document.capture_succeeded` -- data extraction complete
- `document.capture_failed` -- data extraction failed
- `document.detect_succeeded` -- fraud detection complete
- `document.detect_failed` -- fraud detection failed
- `document.verification_complete` -- full processing complete (status = VERIFICATION_COMPLETE)

### Book Events (unvalidated)
- `book.processing_complete` -- all documents in book finished processing

### Encore / Book Copy Events (unvalidated)
- `book.copy.request_accepted` -- recipient accepted book copy
- `book.copy.request_rejected` -- recipient rejected book copy
- `book.copy.kickout_evaluated` -- automated kick-out evaluation complete

> **CRITICAL:** Use the List Events endpoint (`GET /v1/account/settings/webhooks/events`)
> to get the canonical event names from your tenant. The names above are best-effort
> inferences and may differ from actual production payloads.

## Signature Verification (HMAC-SHA256)

**Every webhook request includes three headers:**

| Header | Content |
|--------|---------|
| `Webhook-Signature` | HMAC-SHA256 hex digest of the signed message |
| `Webhook-Timestamp` | Unix timestamp (seconds) when the webhook was sent |
| `Webhook-Request-Id` | Unique identifier for this request |

### Signed Message Format

The signature covers a message constructed as:

```
{timestamp}.{request_id}.{body}
```

Where:
- `{timestamp}` = value from `Webhook-Timestamp` header
- `{request_id}` = value from `Webhook-Request-Id` header
- `{body}` = raw request body bytes (NOT parsed JSON)

### Verification Algorithm

```python
import hmac
import hashlib

def verify_webhook(headers: dict, body: bytes, secret: str) -> bool:
    timestamp = headers["Webhook-Timestamp"]
    request_id = headers["Webhook-Request-Id"]
    received_signature = headers["Webhook-Signature"]

    # Construct the signed message
    signed_message = f"{timestamp}.{request_id}.".encode() + body

    # Compute expected signature
    expected_signature = hmac.new(
        secret.encode(),
        signed_message,
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, received_signature)
```

### Secret Management

- Secrets must be **16-128 characters**, generated with a cryptographically secure random generator
- Configure unique secrets per webhook endpoint
- Store secrets in environment variables or a secrets manager -- never in code

### Secret Rotation (Zero-Downtime)

1. Generate a new secret
2. Update your handler to validate against **both** old and new secrets
3. Call the Configure Secret endpoint with the new secret
4. Remove old secret validation from your handler once confirmed

## Additional Security Options

### IP Allowlisting
Restrict inbound webhook traffic to Ocrolus infrastructure IPs. Contact your Account Manager for the current IP list.

### HTTP Basic Auth
Include credentials directly in the webhook URL:
```
https://username:password@your-domain.com/webhooks/ocrolus
```

## Production Handler Pattern

> **Before using this pattern**, run `validate_endpoints.py --webhooks` to discover
> your tenant's actual event type field name and event strings. Replace the
> placeholders below with the validated values.

```python
import logging
import os
from flask import Flask, request, jsonify

app = Flask(__name__)
logger = logging.getLogger("ocrolus-webhooks")
WEBHOOK_SECRET = os.environ["OCROLUS_WEBHOOK_SECRET"]

# Set this to the field name from: python validate_endpoints.py --webhooks
# Default "event_type" is a placeholder -- your tenant may use a different field.
EVENT_TYPE_FIELD = os.environ.get("OCROLUS_EVENT_TYPE_FIELD", "event_type")

@app.route("/webhooks/ocrolus", methods=["POST"])
def handle_ocrolus_webhook():
    # 1. Verify signature FIRST
    if not verify_webhook(request.headers, request.get_data(), WEBHOOK_SECRET):
        return jsonify({"error": "Invalid signature"}), 401

    # 2. Parse event and extract type using the configured field name
    event = request.get_json()
    event_type = event.get(EVENT_TYPE_FIELD, "")

    # 3. Log ALL events -- critical during initial integration to confirm
    #    the actual field name and event strings match your configuration
    logger.info(f"Webhook received: {EVENT_TYPE_FIELD}={event_type}, payload_keys={list(event.keys())}")

    # 4. Respond immediately (within 5s timeout)
    # Queue heavy work for async processing
    #
    # REPLACE these event name strings with the canonical names from
    # your validate_endpoints.py --webhooks output.
    if event_type == "document.verification_complete":   # REPLACE with validated name
        queue_document_processing(event)
    elif event_type == "book.processing_complete":       # REPLACE with validated name
        queue_book_finalization(event)
    elif event_type == "document.detect_succeeded":      # REPLACE with validated name
        queue_fraud_review(event)
    elif event_type.startswith("book.copy."):            # REPLACE with validated prefix
        queue_encore_handling(event)
    else:
        # Safety net: catches events whose names differ from placeholders above.
        # Check these logs after initial deployment and update the handlers.
        logger.warning(f"Unhandled webhook event: {EVENT_TYPE_FIELD}={event_type}")

    return jsonify({"status": "ok"}), 200
```

## Common Pitfalls

1. **Long-running handlers** -- Ocrolus times out at 5 seconds. Queue work and respond immediately.
2. **Not verifying signatures** -- Always verify before processing. Unsigned payloads could be spoofed.
3. **Mixing webhook types** -- Only org-level OR account-level can be active, not both.
4. **Parsing body before verification** -- Verify against raw bytes, then parse JSON.
5. **Hardcoded secrets** -- Use environment variables or a secrets manager.
