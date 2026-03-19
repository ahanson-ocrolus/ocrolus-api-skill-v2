# Ocrolus API Integration Toolkit

A complete integration toolkit for the Ocrolus Document Automation Platform API.
Includes a Python SDK, webhook handling, fraud detection support, widget embedding,
and test fixtures.

---

## What's Included

```
ocrolus-api/
  SKILL.md                              # Skill definition (for Claude Code)
  README.md                             # This file
  references/
    endpoints.md                        # Full endpoint inventory
    detect.md                           # Fraud detection: signals, scores, reason codes
    webhooks.md                         # Webhook setup, signature verification, events
    coverage-matrix.md                  # Endpoint coverage tracking
  scripts/
    ocrolus_client.py                   # Python SDK -- importable module, 74 methods
    webhook_verifier.py                 # Webhook receiver with HMAC-SHA256 verification
    test_fixtures.py                    # pytest suite for integration testing
    validate_endpoints.py               # Endpoint validation against your live tenant
  examples/
    widget_app.py                       # Widget embedding sample (Flask)
```

---

## Before You Start: What You Need

| Requirement | Where to Get It |
|------------|----------------|
| Ocrolus API credentials (`client_id`, `client_secret`) | Ocrolus Dashboard > Account & Settings > API Credentials |
| Python 3.9+ | https://python.org |
| `requests` library | `pip install requests` |
| `flask` library (for webhooks and widget) | `pip install flask` |
| `pytest` library (for tests) | `pip install pytest` |

### Install dependencies

```bash
pip install requests flask pytest
```

### Set environment variables

```bash
export OCROLUS_CLIENT_ID="your_client_id"
export OCROLUS_CLIENT_SECRET="your_client_secret"

# Only if using webhooks:
export OCROLUS_WEBHOOK_SECRET="your_webhook_secret"

# Only if using the widget:
export OCROLUS_WIDGET_CLIENT_ID="your_widget_client_id"
export OCROLUS_WIDGET_CLIENT_SECRET="your_widget_client_secret"
```

---

## Required Setup: Two Validation Steps

This toolkit was built from Ocrolus public documentation, which returned
inconsistent results for some endpoint paths and webhook event names.
**Before using this in production, you must run two validation steps against
your live Ocrolus tenant.** This takes about 5 minutes.

### Step 1: Validate Endpoint Paths

Some endpoint paths have conflicting documentation (e.g., `/v1/book/create`
vs `POST /v1/books`, query-param vs path-param styles). The validation script
probes your tenant to determine which paths actually work.

```bash
# Basic validation (read-only, no side effects):
python scripts/validate_endpoints.py

# Example output:
#   [OK]  200          /v1/books                                    List Books
#   [OK]  400  [POST]  /v1/book/create                              Create Book  (route exists, rejected empty payload)
#   [XX]  404  [POST]  /v1/books                                    (alt)
#   [OK]  200          /v1/book/status                               Book Status (query param)
#   [XX]  404          /v1/book/1/status                             Book Status (path param)
#   ...
#   PATH CONFLICTS:
#     Create Book:  ** BOTH paths responded -- use --write-paths to disambiguate **
#       /v1/book/create     -> YES
#       /v1/books            -> YES (may be the list endpoint, not create)

# Full validation (creates + deletes a test book to definitively resolve write paths):
python scripts/validate_endpoints.py --write-paths

# Example output:
#   --- LIVE WRITE-PATH PROBING ---
#   Creating test book...
#   [OK] 201  /v1/book/create -- book created
#   [XX] 400  /v1/books -- {"error": "..."}
#   Test book: pk=67890, uuid=abc-123-...
#   [OK] 200  /v1/book/status?book_pk=67890
#   [XX] 404  /v1/book/67890/status
#   Cleaning up test book...
#   [OK] Test book deleted
```

**What this does:**
- Authenticates against your tenant
- **GET endpoints:** sends GET, checks response
- **POST/PUT/DELETE endpoints:** sends the actual HTTP method with an empty body.
  A 400 "bad request" means the route exists (it tried to process your request).
  A 404 means the route doesn't exist. This correctly distinguishes write paths.
- For endpoints with conflicting docs, tests BOTH variants
- With `--write-paths`: creates ONE test book to definitively resolve create/status/transactions
  path conflicts, then deletes it

**After running:**
1. Open `references/endpoints.md`
2. For any row marked `# NEEDS LIVE VALIDATION`, update the path to whichever
   variant the script confirmed
3. Open `scripts/ocrolus_client.py` and update the corresponding method's path
4. Open `references/coverage-matrix.md` and change the `:warning:` rows to
   `:white_check_mark:` with the confirmed path
5. Save the raw output for your records:
   ```bash
   python scripts/validate_endpoints.py --output validation_results.json
   ```

### Step 2: Validate Webhook Event Names

The webhook event names in this toolkit (e.g., `document.verification_complete`,
`book.processing_complete`) were assembled from scattered documentation references.
**If the actual event names differ, your webhook handlers will silently ignore
real traffic.** This step discovers the canonical names from your tenant.

```bash
# Run with --webhooks flag
python scripts/validate_endpoints.py --webhooks

# Example output:
#   WEBHOOK EVENT DISCOVERY
#   Canonical event names from /v1/account/settings/webhooks/events:
#     - document.verification_complete
#     - document.classification_complete
#     - book.complete
#     ...
#   ** Use these exact strings in your webhook handlers **
```

**What this does:**
- Calls the List Webhook Events endpoint on your tenant
- Returns the exact event type strings that Ocrolus will send in production payloads
- Does NOT register or modify any webhooks

**After running:**
1. Open `references/webhooks.md` > "Event Types" section
2. Replace the unvalidated event names with the canonical names from the output
3. Open `scripts/webhook_verifier.py` and update the `@handler.on("...")` decorators
   with the validated event strings
4. If the validation output reports a different event type field name (e.g., `event_name`
   instead of `event_type`), set `OCROLUS_EVENT_TYPE_FIELD` accordingly -- the handler
   and reference doc patterns already read from this env var

**Note:** If the List Events endpoint returns empty or errors, you may need to
register at least one webhook first (via Dashboard or API) before events are listed.

---

## Quick Start

### 1. Basic API Usage

```python
from scripts.ocrolus_client import OcrolusClient

client = OcrolusClient()  # reads from OCROLUS_CLIENT_ID/SECRET env vars

# Create a book
book = client.create_book("Loan Application #12345")
book_pk = book["pk"]       # integer -- used by v1 endpoints
book_uuid = book["uuid"]   # UUID string -- used by v2 endpoints

# Upload documents
client.upload_pdf(book_pk, "bank_statement.pdf")
client.upload_mixed_pdf(book_pk, "loan_package.pdf")

# Wait for processing (or use webhooks -- see below)
client.wait_for_book(book_pk, timeout=600)

# Get results
forms = client.get_book_forms(book_pk)                   # Capture
fraud = client.get_book_fraud_signals(book_uuid)         # Detect
summary = client.get_book_summary(book_uuid)             # Analyze
income = client.get_income_calculations(book_uuid)       # Income
```

### 2. Fraud Detection with Authenticity Scores

```python
signals = client.get_book_fraud_signals(book_uuid)

for doc in signals.get("documents", []):
    score = doc.get("authenticity_score")
    if score is not None and score < 61:
        print(f"LOW AUTHENTICITY ({score}/100) -- review required")
        for code in doc.get("reason_codes", []):
            print(f"  {code['code']}: {code['description']} ({code['confidence']})")

        # Get visual overlay for fraud analysts
        for signal in doc.get("signals", []):
            viz_uuid = signal.get("visualization_uuid")
            if viz_uuid:
                image = client.get_fraud_visualization(viz_uuid)
                with open(f"fraud_{viz_uuid}.png", "wb") as f:
                    f.write(image)
```

See `references/detect.md` for the full authenticity score reference (0-100 scale,
reason code format, signal types, threshold guidance).

### 3. Webhook Receiver

```bash
# STEP 1: Discover your tenant's actual event names and payload field
python scripts/validate_endpoints.py --webhooks
# This prints the canonical event names and the JSON field they use.
# Example output:
#   Event type field name in payloads: "event_type"
#   Extracted event names:
#     - document.verification_complete
#     - book.processing_complete
#     - ...

# STEP 2: Update the event names in webhook_verifier.py to match
# (Replace the PLACEHOLDER strings with the exact names from Step 1)

# STEP 3: Start the webhook receiver
export OCROLUS_WEBHOOK_SECRET="your-secret"
export OCROLUS_EVENT_TYPE_FIELD="event_type"  # from Step 1 output
python scripts/webhook_verifier.py

# STEP 4: Register your webhook URL with Ocrolus (one-time):
# Use the EXACT event names from Step 1 in the events list below:
python -c "
from scripts.ocrolus_client import OcrolusClient
client = OcrolusClient()
# List available events first:
print(client.list_org_webhook_events())
# Then register with the actual event names:
client.add_org_webhook(
    url='https://your-domain.com/webhooks/ocrolus',
    events=['...']  # paste actual event names from list above
)
"
```

The webhook verifier includes:
- HMAC-SHA256 signature verification
- Timestamp freshness checking (rejects replays > 5 min old)
- Configurable event type field name (not hardcoded to "event_type")
- Fallback detection if the field name doesn't match (logs a warning with the correct field)
- Event routing with `@handler.on("event_name")` decorators
- Default handler that catches and logs unrecognized events (safety net during initial rollout)
- Secret rotation support (validate against old + new during rotation)

See `references/webhooks.md` for the full webhook reference.

### 4. Widget Embedding

```bash
export OCROLUS_WIDGET_CLIENT_ID="widget_id"
export OCROLUS_WIDGET_CLIENT_SECRET="widget_secret"
python examples/widget_app.py
# Open http://localhost:5000
```

**Important:** The widget app requires one manual step -- you must paste your
widget `<script>` tag from the Ocrolus Dashboard into the HTML template.
The script URL is unique to your account and cannot be retrieved programmatically.
See the `MANUAL STEP REQUIRED` comment in `examples/widget_app.py`.

### 5. Run Tests

```bash
# Run webhook signature tests (no credentials needed):
pytest scripts/test_fixtures.py::TestWebhookVerification -v

# Run API integration tests (requires credentials):
export OCROLUS_CLIENT_ID="your_id"
export OCROLUS_CLIENT_SECRET="your_secret"
pytest scripts/test_fixtures.py -v

# Run specific test categories:
pytest scripts/test_fixtures.py::TestBookOperations -v
pytest scripts/test_fixtures.py::TestDocumentUpload -v
pytest scripts/test_fixtures.py::TestTagManagement -v
```

---

## SDK Reference

The Python SDK (`scripts/ocrolus_client.py`) covers 74 methods across all
Ocrolus API capabilities:

| Category | Methods | ID Type |
|----------|---------|---------|
| Book Operations | 8 | `book_pk` (int) |
| Document Upload & Management | 13 | `book_pk` / `doc_uuid` |
| Classification (Classify) | 3 | `book_uuid` |
| Data Extraction (Capture) | 7 | `book_pk` / `doc_uuid` |
| Fraud Detection (Detect) | 3 | `book_uuid` / `doc_uuid` |
| Cash Flow Analytics | 6 | `book_uuid` |
| Income Calculations | 7 | `book_uuid` |
| Tag Management | 8 | `tag_uuid` / `book_uuid` |
| Encore / Book Copy | 6 | `book_pk` / `job_id` |
| Webhooks (Org-Level) | 8 | `webhook_id` |
| Webhooks (Account-Level) | 4 | -- |
| Helpers | 1 | `book_pk` |

The SDK also works as a CLI for quick testing:

```bash
python scripts/ocrolus_client.py list-books
python scripts/ocrolus_client.py create-book "Test Book"
python scripts/ocrolus_client.py book-status 12345
```

---

## Key Concepts

### Book Identifiers

Ocrolus uses two identifiers for Books. **Never mix them.**

| Identifier | Format | Used By |
|-----------|--------|---------|
| `book_pk` | Integer (e.g., `12345`) | v1 endpoints: upload, forms, transactions, status |
| `book_uuid` | UUID string | v2 endpoints: analytics, detect, income, classify |

Both are returned when you create a book:
```python
book = client.create_book("My Book")
book_pk = book["pk"]       # 12345
book_uuid = book["uuid"]   # "a1b2c3d4-..."
```

### Processing Modes

| Mode | Speed | Accuracy | Use Case |
|------|-------|----------|----------|
| Classify | Fastest | Classification only | Document triage |
| Instant | Fast | Good | High-volume automated processing |
| Instant Classify with UV | Fast | Classification + key fields | Dedup and grouping |
| Complete | Slowest | Highest (human review) | Mortgage, high-stakes decisions |

### Document Status Flow

```
UPLOADED -> PROCESSING -> CLASSIFICATION_COMPLETE -> CAPTURE_COMPLETE -> VERIFICATION_COMPLETE
```

Poll with `client.get_book_status(book_pk)` or use webhooks for real-time updates.

---

## File Reference

| File | What It's For |
|------|--------------|
| `references/endpoints.md` | Every API endpoint with path, method, and validation status |
| `references/detect.md` | Authenticity scores (0-100), reason codes, signal types, thresholds |
| `references/webhooks.md` | HMAC-SHA256 verification, event types, handler patterns, secret rotation |
| `references/coverage-matrix.md` | Tracks which endpoints are covered in SDK vs documented vs live-validated |
| `scripts/ocrolus_client.py` | Importable Python SDK with 74 methods and CLI entrypoint |
| `scripts/webhook_verifier.py` | Production-ready Flask webhook receiver with signature verification |
| `scripts/test_fixtures.py` | pytest suite with fixtures for uploads, Plaid, income, Detect, tags |
| `scripts/validate_endpoints.py` | Probes your tenant to confirm paths and discover webhook events |
| `examples/widget_app.py` | Flask app for embedding the Ocrolus widget (requires manual script tag) |

---

## Troubleshooting

**Authentication fails:**
- Verify `OCROLUS_CLIENT_ID` and `OCROLUS_CLIENT_SECRET` are set correctly
- Credentials are created in Dashboard > Account & Settings > API Credentials
- Basic Auth is deprecated -- use OAuth 2.0

**Endpoint returns 404:**
- Run `validate_endpoints.py` to check which path variant your tenant accepts
- Some paths differ between doc versions (query param vs path param)

**Webhook handler receives events but doesn't process them:**
- Event type strings may not match -- run `validate_endpoints.py --webhooks`
  to discover canonical event names
- Check logs for "Unhandled webhook event type" warnings

**Widget doesn't render:**
- You must insert the widget `<script>` tag from your Dashboard (see widget_app.py)
- Widget credentials are separate from API credentials
- Widget auth URL is `https://jwe-issuer.ocrolus.net/token` (not the main API auth URL)

---

## Ocrolus Documentation

- API Guide: https://docs.ocrolus.com/docs/guide
- API Reference: https://docs.ocrolus.com/reference
- Authentication: https://docs.ocrolus.com/docs/using-api-credentials
- Webhooks: https://docs.ocrolus.com/docs/webhook-overview
- Detect: https://docs.ocrolus.com/docs/detect
- Widget: https://docs.ocrolus.com/docs/widget
- Supported Documents: https://docs.ocrolus.com/docs/supported-document-types
