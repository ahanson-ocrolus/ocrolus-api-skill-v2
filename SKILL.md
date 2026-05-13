---
name: ocrolus-api
description: Build integrations against the Ocrolus document automation API. Use this skill when an application uploads documents (bank statements, pay stubs, tax forms, W-2s) to Ocrolus and reads back classification, captured fields, fraud signals, cash flow analytics, or income calculations. Triggers include "Ocrolus", "ocrolus api", "ocrolus webhook", "ocrolus widget", and references to Ocrolus capabilities: Classify, Capture, Detect, Analyze, Income, Encore, or transaction tags. Skip for generic document/OCR work not specifically targeting Ocrolus.
---

# Ocrolus API

Ocrolus turns financial documents into structured, decision-ready data. Integrations are built around five capabilities:

| Capability | What it gives you |
|------------|-------------------|
| **Classify** | Identify 300+ document types with confidence scores |
| **Capture** | Extract structured fields and transactions |
| **Detect** | Fraud signals, authenticity scores, and reason codes |
| **Analyze** | Cash flow features, enriched transactions, risk scoring |
| **Income** | Income calculations, BSIC, self-employed income |

Most workflows: create a **Book**, upload documents, wait for processing (webhooks recommended), then read results.

Reference: <https://docs.ocrolus.com/reference> · API Guide: <https://docs.ocrolus.com/docs/guide>

## Hosts and Authentication

| Purpose | Base URL |
|---------|----------|
| API | `https://api.ocrolus.com` |
| OAuth token | `https://auth.ocrolus.com/oauth/token` |
| Widget token | `https://widget.ocrolus.com/v1/widget/{uuid}/token` |

OAuth 2.0 client credentials → JWT bearer (24-hour expiry). The token request is **form-encoded** and does **not** take an `audience` parameter:

```bash
curl -X POST https://auth.ocrolus.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=$OCROLUS_CLIENT_ID" \
  -d "client_secret=$OCROLUS_CLIENT_SECRET"
```

```python
import requests
token = requests.post(
    "https://auth.ocrolus.com/oauth/token",
    data={
        "grant_type": "client_credentials",
        "client_id": OCROLUS_CLIENT_ID,
        "client_secret": OCROLUS_CLIENT_SECRET,
    },
).json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
```

Every other request sends `Authorization: Bearer <token>`.

## Book Identifiers

A Book is the container for documents in a single application/case. When you create one, Ocrolus returns two identifiers:

| Identifier | Type | Used by |
|------------|------|---------|
| `pk` | Integer | v1 endpoints (uploads, forms, transactions, status) |
| `uuid` | UUID string | v2 endpoints (Classify, Detect, Analyze, Income) |

Persist both. v1 endpoints reject UUIDs; v2 endpoints reject integer pks. Where v1 endpoints accept either, the form/JSON field is named `pk` (integer) or `book_uuid` (UUID).

## 5-Minute Quick Start

```bash
# 1. Create a book
curl -X POST https://api.ocrolus.com/v1/book/add \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Application #12345", "book_type": "individual"}'
# → {"pk": 71250194, "uuid": "09c52985-...", ...}

# 2. Upload a PDF (multipart; field is `pk`, not `book_pk`)
curl -X POST https://api.ocrolus.com/v1/book/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "pk=71250194" \
  -F "upload=@bank_statement.pdf"

# 3. Poll status (or, preferred: use webhooks — see below)
curl "https://api.ocrolus.com/v1/book/status?book_pk=71250194" \
  -H "Authorization: Bearer $TOKEN"

# 4. Read results (use the UUID for v2 capabilities)
curl "https://api.ocrolus.com/v2/book/$BOOK_UUID/summary" \
  -H "Authorization: Bearer $TOKEN"
curl "https://api.ocrolus.com/v2/detect/book/$BOOK_UUID/signals" \
  -H "Authorization: Bearer $TOKEN"
```

The same flow using the included Python SDK:

```python
from ocrolus_client import OcrolusClient

client = OcrolusClient()  # reads OCROLUS_CLIENT_ID / OCROLUS_CLIENT_SECRET

book = client.create_book("Application #12345")
client.upload_pdf(book["pk"], "bank_statement.pdf")
client.wait_for_book(book["pk"], timeout=600)

summary  = client.get_book_summary(book["uuid"])
fraud    = client.get_book_fraud_signals(book["uuid"])
income   = client.get_income_calculations(book["uuid"])
```

## Capability Reference

Endpoints below mirror the structure at <https://docs.ocrolus.com/reference>. Prefer v2/UUID endpoints when both exist.

### Books

| Operation | Method & Path | Notes |
|-----------|---------------|-------|
| Create Book | `POST /v1/book/add` | Body: `name`, `book_type`. Returns `pk` and `uuid`. |
| Get Book | `GET /v1/book/{pk}` | |
| List Books | `GET /v1/books` | Supports `page`, `per_page`. |
| Update Book | `POST /v1/book/update` | Body: `pk` or `book_uuid`, `name`. |
| Delete Book | `POST /v1/book/remove` | Body: `book_id` or `book_uuid`. |
| Book Status | `GET /v1/book/status?book_pk={pk}` | Path-style `/v1/book/{pk}/status` also works. |
| Book ↔ Loan | `GET /v1/book/loan/{loan_id}` · `GET /v1/book/{pk}/loan` | |

### Document

| Operation | Method & Path | Notes |
|-----------|---------------|-------|
| Upload PDF | `POST /v1/book/upload` | Multipart: `pk` or `book_uuid`, `upload` (file), optional `form_type`, `doc_name`. 200 MB max. |
| Upload Mixed PDF | `POST /v1/book/upload/mixed` | Multiple doc types in a single PDF. |
| Upload Pay Stub | `POST /v1/book/upload/paystub` | |
| Upload Image | `POST /v1/book/upload/image` | Multipart: `pk` or `book_uuid`, `upload`, `image_group`. |
| Finalize Image Group | `POST /v1/book/finalize-image-group` | Closes an image group so processing can start. |
| Upload Plaid JSON | `POST /v1/book/upload/plaid` | |
| Import Plaid Asset Report | `POST /v1/book/import/plaid/asset` | Production only. |
| Cancel / Download | `POST /v1/document/{doc_uuid}/cancel` · `GET /v1/document/{doc_uuid}/download` | |
| Delete Document | `POST /v1/document/remove` | Body: exactly one of `doc_id` (integer) or `doc_uuid` (UUID). ([docs](https://docs.ocrolus.com/reference/delete-a-file)) |
| Delete Mixed Document | `POST /v1/document/mixed/remove` | Body: exactly one of `pk` (integer) or `doc_uuid` (UUID). |
| Upgrade Document | `POST /v1/document/{doc_uuid}/upgrade` | Body: `upgrade_type`. Move a doc to a higher processing mode. |

`form_type` is optional and cannot be used for bank statements.

### Classify

| Operation | Method & Path |
|-----------|---------------|
| Book classification summary | `GET /v2/book/{book_uuid}/classification-summary` |
| Mixed-document classification | `GET /v2/mixed-document/{mixed_doc_uuid}/classification-summary` |
| Grouped mixed-doc summary | `GET /v2/index/mixed-doc/{mixed_doc_uuid}/summary` |

Each classification carries a confidence score (0–1). Uniqueness Values (UV) extract key fields during classification (e.g., employer + employee name from a pay stub).

### Capture

| Operation | Method & Path |
|-----------|---------------|
| Book forms | `GET /v1/book/{pk}/forms` |
| Book pay stubs | `GET /v1/book/{pk}/paystubs` |
| Document forms | `GET /v1/document/{doc_uuid}/forms` |
| Document pay stubs | `GET /v1/document/{doc_uuid}/paystubs` |
| Form fields | `GET /v1/form/{form_uuid}/fields` |
| Pay stub | `GET /v1/paystub/{paystub_uuid}` |
| Book transactions | `GET /v1/book/{pk}/transactions` |

Per-field confidence scores (0 = no confidence, 1 = very high). Filter transactions to a single document with `uploaded_doc_pk` or `uploaded_doc_uuid`.

### Detect (Fraud)

| Operation | Method & Path |
|-----------|---------------|
| Book signals | `GET /v2/detect/book/{book_uuid}/signals` |
| Document signals | `GET /v2/detect/document/{doc_uuid}/signals` |
| Signal visualization (image) | `GET /v2/detect/visualization/{visualization_uuid}` |

Each processed document carries an **Authenticity Score** (0–100; <61 is "low authenticity") and **Reason Codes** (e.g., `110-H` "bank statement account info tampered", with HIGH/MEDIUM/LOW confidence). Supported document types: bank statements, pay stubs, W-2s. See `references/detect.md` for the full signal taxonomy.

### Analyze (Cash Flow)

| Operation | Method & Path |
|-----------|---------------|
| Book summary | `GET /v2/book/{book_uuid}/summary` |
| Cash flow features | `GET /v2/book/{book_uuid}/cash_flow_features` |
| Enriched transactions | `GET /v2/book/{book_uuid}/enriched_txns` |
| Cash flow risk score | `GET /v2/book/{book_uuid}/cash_flow_risk_score` |
| Benchmarking (beta) | `GET /v2/book/{book_uuid}/benchmarking` |
| Lender analytics (XLSX) | `GET /v2/book/{book_uuid}/lender_analytics/xlsx` |

`cash_flow_features` accepts `min_days_to_include` (default 0; set to 32 for completed months only).

### Income

| Operation | Method & Path |
|-----------|---------------|
| Income calculations | `GET /v2/book/{book_uuid}/income-calculations` |
| Income summary | `GET /v2/book/{book_uuid}/income-summary` |
| Configure income entity | `POST /v2/book/{book_uuid}/income-entity` |
| Set income guideline | `PUT /v2/book/{book_uuid}/income-guideline` |
| Self-employed income | `POST /v2/book/{book_uuid}/self-employed-income` |
| BSIC | `GET /v2/book/{book_uuid}/bsic` (use `Accept: application/xlsx` for Excel) |

`income-calculations` accepts `guideline=FANNIE_MAE | FREDDIE_MAC | FHA | VA | USDA`.

### Transaction Tags (beta)

| Operation | Method & Path |
|-----------|---------------|
| Create / Get / Update / Delete tag | `POST /v2/analytics/tags` · `GET|PUT|DELETE /v2/analytics/tags/{tag_uuid}` |
| List tags | `GET /v2/analytics/tags` (optional `is_system_tag`) |
| Revenue / deduction tag config | `GET|PUT /v2/analytics/revenue-deduction-tags` |
| Tag transactions on a book | `PUT /v2/analytics/book/{book_uuid}/transactions` |

### Encore (Book Copy)

For organization-to-organization sharing of a completed book.

| Operation | Method & Path |
|-----------|---------------|
| Create copy jobs | `POST /v1/book/copy-jobs` (up to 50 per request) |
| List copy jobs | `GET /v1/book/copy-jobs?direction=inbound|outbound` |
| Accept / Reject | `POST /v1/book/copy-jobs/{job_id}/accept` · `POST /v1/book/copy-jobs/{job_id}/reject` |
| Run kick-outs | `POST /v1/book/copy-jobs/run-kickouts` |
| Org settings | `GET /v1/settings/book-copy` |

### Webhooks

Use webhooks instead of polling status endpoints.

| Operation | Method & Path |
|-----------|---------------|
| Add webhook | `POST /v1/account/settings/webhook` (Body: `url`, `events[]`) |
| List | `GET /v1/account/settings/webhooks` |
| Get / Update / Delete | `GET|PUT|DELETE /v1/account/settings/webhooks/{webhook_id}` |
| Available event types | `GET /v1/account/settings/webhooks/events` |
| Test delivery | `POST /v1/account/settings/webhooks/{webhook_id}/test` |
| Set signing secret | `POST /v1/account/settings/webhooks/secret` |

After registering the URL, **subscribe to event types** in the Ocrolus dashboard (Settings → Webhooks → Edit). API registration alone delivers zero events until events are selected.

Event payloads use `event_name` (not `event_type`). Common events:

- `document.upload_succeeded` — accepted into the pipeline
- `document.verification_succeeded` — OCR/processing complete
- `book.verified` — all docs verified
- `book.analytics_v2.generated` — cash flow analytics ready
- `document.detect.signal_found` / `book.detect.signal_found` — fraud signals
- `book.completed` — final event; all tasks done

Signatures are HMAC-SHA256 over `{Webhook-Timestamp}.{Webhook-Request-Id}.{raw_body}` with your configured secret, delivered in `Webhook-Signature`. Verify against raw bytes before parsing JSON. Handlers must respond within **5 seconds** — queue heavy work asynchronously.

See `references/webhooks.md` for full event reference and a verification snippet.

### Widget (embeddable upload UI)

Generate a short-lived widget token server-side, then mount the widget in your frontend:

```
POST https://widget.ocrolus.com/v1/widget/{widget_uuid}/token
```

Widget auth uses separate credentials (`OCROLUS_WIDGET_CLIENT_ID` / `OCROLUS_WIDGET_CLIENT_SECRET`). See `tools/widget-quickstart/` for a working Python/Flask example.

## What to Read Next

| If you are… | Read |
|-------------|------|
| Trying endpoints interactively | The Ocrolus Postman collection (linked from <https://docs.ocrolus.com/reference>) |
| Looking up a single endpoint signature | `references/endpoints.md` |
| Building fraud workflows | `references/detect.md` |
| Building a webhook handler | `references/webhooks.md` |
| Working in Python | `ocrolus_client.py` — SDK + CLI |
| Embedding the widget | `tools/widget-quickstart/README.md` |
| Validating against your tenant | `tools/health_check.py` |

## Environment Variables

```bash
OCROLUS_CLIENT_ID=...
OCROLUS_CLIENT_SECRET=...
OCROLUS_WEBHOOK_SECRET=...          # if using webhooks
OCROLUS_WIDGET_CLIENT_ID=...        # if using the widget
OCROLUS_WIDGET_CLIENT_SECRET=...
```

## Things People Miss

- **Auth body must be form-encoded.** JSON-encoded bodies — or adding an `audience` parameter — return `403 unauthorized_client`.
- **Upload form field is `pk` (or `book_uuid`)** — not `book_pk`. Using `book_pk` returns "Required pk or book uuid".
- **`pk` and `uuid` are not interchangeable.** v1 endpoints take the integer `pk`; v2 endpoints take the `uuid`. Mismatches return 404 or empty results.
- **Webhook events must be selected in the dashboard** after API registration, or no events deliver.
- **Webhook field is `event_name`**, not `event_type`. Parsing the wrong field returns `None`.
- **Verify webhook signatures against the raw request body**, before JSON parsing, or the HMAC will not match.
- **Authenticity Scores are only available for documents processed after Nov 15, 2023**; older books lack them.
