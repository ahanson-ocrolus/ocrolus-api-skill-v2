# Ocrolus API — Endpoint Inventory

A capability-organized inventory of Ocrolus API endpoints, grouped to mirror the structure at <https://docs.ocrolus.com/reference>. Endpoint names follow the actual URL path segment (e.g., `book/add`) rather than the human-readable name on docs.ocrolus.com.

For interactive exploration, see the [Ocrolus Postman collection](https://docs.ocrolus.com/reference).

---

## Authentication

| Endpoint | Method | Path | Input | Notes |
|----------|--------|------|-------|-------|
| `oauth/token` | POST | `https://auth.ocrolus.com/oauth/token` | **Body (form-encoded):** `grant_type`, `client_id`, `client_secret` | OAuth 2.0 client_credentials grant; returns JWT; 24h expiry |

The auth body must be form-encoded (`application/x-www-form-urlencoded`). Do not include an `audience` parameter — including it returns 403.

**Response:** `{ "access_token": "...", "token_type": "Bearer", "expires_in": 86400 }`
**All subsequent requests:** `Authorization: Bearer <access_token>`

---

## Books

Create, update, delete, list, and look up books.

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `book/add` | POST | `/v1/book/add` | **Body (JSON):** `name`, `book_type` |
| `book/remove` | POST | `/v1/book/remove` | **Body (JSON):** `book_id` (integer) OR `book_uuid` (UUID) |
| `book/update` | POST | `/v1/book/update` | **Body (JSON):** `pk` (integer) OR `book_uuid` (UUID), `name` |
| `book/{pk}` | GET | `/v1/book/{pk}` | **Path:** `pk` (integer) |
| `books` | GET | `/v1/books` | **Query (optional):** `page`, `per_page` |
| `book/status` | GET | `/v1/book/status?book_pk={pk}` | **Query:** `book_pk` (integer). Path-style `/v1/book/{pk}/status` also works. |
| `book/loan/{loan_id}` | GET | `/v1/book/loan/{loan_id}` | **Path:** `loan_id` (string) |
| `book/{pk}/loan` | GET | `/v1/book/{pk}/loan` | **Path:** `pk` (integer) |

`/v1/book/add` returns both `pk` and `uuid`. Persist both — `pk` is used by v1 endpoints, `uuid` by v2 endpoints. Field naming varies across write endpoints: `book/remove` accepts `book_id`, `book/update` accepts `pk`.

---

## Document Upload

Upload documents, pay stubs, images, and Plaid data to a book.

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `book/upload` | POST | `/v1/book/upload` | **Form (multipart):** `pk` (integer) OR `book_uuid` (UUID), `upload` (file), `form_type` (optional), `doc_name` (optional) |
| `book/upload/mixed` | POST | `/v1/book/upload/mixed` | **Form (multipart):** `pk` OR `book_uuid`, `upload` (file) |
| `book/upload/paystub` | POST | `/v1/book/upload/paystub` | **Form (multipart):** `pk` OR `book_uuid`, `upload` (file) |
| `book/upload/image` | POST | `/v1/book/upload/image` | **Form (multipart):** `pk` OR `book_uuid`, `upload` (file), `image_group` (string) |
| `book/finalize-image-group` | POST | `/v1/book/finalize-image-group` | **Body (JSON):** `pk` OR `book_uuid`, `image_group` (string) |
| `book/upload/plaid` | POST | `/v1/book/upload/plaid` | **Body (JSON):** `pk` OR `book_uuid` |
| `book/import/plaid/asset` | POST | `/v1/book/import/plaid/asset` | **Body (JSON):** `audit_copy_token` (string). Production only. |

The form field is `pk` (integer) or `book_uuid` (UUID) — not `book_pk`. Maximum file size: **200 MB**. `form_type` is optional and cannot be used for bank statements.

### Document operations

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `document/cancel` | POST | `/v1/document/{doc_uuid}/cancel` | **Path:** `doc_uuid`; **Body (JSON, optional):** `doc_pk` OR `doc_uuid`, `accept_charges` (boolean) |
| `document/remove` | POST | `/v1/document/{doc_uuid}/delete` | **Path:** `doc_uuid`; **Body (JSON):** `doc_id` (integer) OR `doc_uuid` |
| `document/download` | GET | `/v1/document/{doc_uuid}/download` | **Path:** `doc_uuid`. Returns binary. |
| `document/upgrade` | POST | `/v1/document/{doc_uuid}/upgrade` | **Path:** `doc_uuid`; **Body (JSON):** `doc_pk` OR `doc_uuid`, `upgrade_type` (string) |
| `document/mixed/upgrade` | POST | `/v1/document/mixed/upgrade` | **Body (JSON):** `mixed_doc_pk` OR `mixed_doc_uuid`, `upgrade_type` |
| `document/mixed/status` | GET | `/v1/document/mixed/status` | **Query:** one of `pk` (integer), `doc_uuid`, or `mixed_doc_uuid` |

Field naming notes: `document/cancel` and `document/upgrade` use `doc_pk`; `document/remove` uses `doc_id`; `document/mixed/upgrade` uses `mixed_doc_pk`.

---

## Classify

Identify document types with confidence scores. Uses `book_uuid`.

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `book/{book_uuid}/classification-summary` | GET | `/v2/book/{book_uuid}/classification-summary` | **Path:** `book_uuid` |
| `mixed-document/{mixed_doc_uuid}/classification-summary` | GET | `/v2/mixed-document/{mixed_doc_uuid}/classification-summary` | **Path:** `mixed_doc_uuid` |
| `index/mixed-doc/{mixed_doc_uuid}/summary` | GET | `/v2/index/mixed-doc/{mixed_doc_uuid}/summary` | **Path:** `mixed_doc_uuid` |

- Identifies 300+ document types with confidence scores (0–1).
- Uniqueness Values (UV): extracts key fields during classification (e.g., employer + employee name from pay stubs).
- The grouped summary organizes forms into logical groups.
- Webhook events: `document.classification_succeeded`, `document.classification_failed`.

---

## Capture

Extract structured data from documents (forms, pay stubs, transactions). Uses `pk`.

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `book/{pk}/forms` | GET | `/v1/book/{pk}/forms` | **Path:** `pk` (integer) |
| `book/{pk}/paystubs` | GET | `/v1/book/{pk}/paystubs` | **Path:** `pk` (integer) |
| `document/{doc_uuid}/forms` | GET | `/v1/document/{doc_uuid}/forms` | **Path:** `doc_uuid` |
| `document/{doc_uuid}/paystubs` | GET | `/v1/document/{doc_uuid}/paystubs` | **Path:** `doc_uuid` |
| `form/{form_uuid}/fields` | GET | `/v1/form/{form_uuid}/fields` | **Path:** `form_uuid` |
| `paystub/{paystub_uuid}` | GET | `/v1/paystub/{paystub_uuid}` | **Path:** `paystub_uuid` |
| `book/{pk}/transactions` | GET | `/v1/book/{pk}/transactions` | **Path:** `pk`; **Query (optional):** `uploaded_doc_pk`, `uploaded_doc_uuid`, `only_tagged`, `distinct_fields` |

- Per-field confidence scores (0 = no confidence, 1 = very high).
- Transactions are also available via query param style: `/v1/transaction?book_pk=X`.
- Scope transactions to a single document with `uploaded_doc_pk` or `uploaded_doc_uuid`.

---

## Detect

Fraud detection signals, authenticity scores, and reason codes. Uses `book_uuid` / `doc_uuid`.

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `detect/book/{book_uuid}/signals` | GET | `/v2/detect/book/{book_uuid}/signals` | **Path:** `book_uuid` |
| `detect/document/{doc_uuid}/signals` | GET | `/v2/detect/document/{doc_uuid}/signals` | **Path:** `doc_uuid` |
| `detect/visualization/{visualization_uuid}` | GET | `/v2/detect/visualization/{visualization_uuid}` | **Path:** `visualization_uuid`. Returns a binary image. |

Use the v2 `/v2/detect/...` endpoints for current fraud detection. See `references/detect.md` for the authenticity score scale, reason code taxonomy, and signal interpretation.

---

## Analyze (Cash Flow)

Cash flow analytics, enriched transactions, and risk scoring. Uses `book_uuid`.

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `book/{book_uuid}/summary` | GET | `/v2/book/{book_uuid}/summary` | **Path:** `book_uuid` |
| `book/{book_uuid}/cash_flow_features` | GET | `/v2/book/{book_uuid}/cash_flow_features` | **Path:** `book_uuid`; **Query (optional):** `min_days_to_include` (integer, default 0) |
| `book/{book_uuid}/enriched_txns` | GET | `/v2/book/{book_uuid}/enriched_txns` | **Path:** `book_uuid` |
| `book/{book_uuid}/cash_flow_risk_score` | GET | `/v2/book/{book_uuid}/cash_flow_risk_score` | **Path:** `book_uuid` |
| `book/{book_uuid}/benchmarking` | GET | `/v2/book/{book_uuid}/benchmarking` | **Path:** `book_uuid`. Beta. |
| `book/{book_uuid}/lender_analytics/xlsx` | GET | `/v2/book/{book_uuid}/lender_analytics/xlsx` | **Path:** `book_uuid`. Returns `.xlsx` binary. |

`cash_flow_features` accepts `min_days_to_include` (default 0); set to 32 to limit output to complete months only.

---

## Income

Income calculations, BSIC, and self-employed income. Uses `book_uuid`.

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `book/{book_uuid}/income-calculations` | GET | `/v2/book/{book_uuid}/income-calculations` | **Path:** `book_uuid`; **Query (optional):** `guideline` (`FANNIE_MAE`, `FREDDIE_MAC`, `FHA`, `VA`, `USDA`) |
| `book/{book_uuid}/income-summary` | GET | `/v2/book/{book_uuid}/income-summary` | **Path:** `book_uuid` |
| `book/{book_uuid}/income-entity` | POST | `/v2/book/{book_uuid}/income-entity` | **Path:** `book_uuid`; **Body (JSON):** config object |
| `book/{book_uuid}/income-guideline` | PUT | `/v2/book/{book_uuid}/income-guideline` | **Path:** `book_uuid`; **Body (JSON):** guideline object |
| `book/{book_uuid}/self-employed-income` | POST | `/v2/book/{book_uuid}/self-employed-income` | **Path:** `book_uuid`; **Body (JSON):** params object |
| `book/{book_uuid}/bsic` | GET | `/v2/book/{book_uuid}/bsic` | **Path:** `book_uuid` |
| `book/{book_uuid}/bsic` (Excel) | GET | `/v2/book/{book_uuid}/bsic` | **Path:** `book_uuid`; **Header:** `Accept: application/xlsx` |

---

## Transaction Tags (Beta)

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `analytics/tags` (create) | POST | `/v2/analytics/tags` | **Body (JSON):** `name` (string) |
| `analytics/tags/{tag_uuid}` | GET | `/v2/analytics/tags/{tag_uuid}` | **Path:** `tag_uuid` |
| `analytics/tags/{tag_uuid}` (modify) | PUT | `/v2/analytics/tags/{tag_uuid}` | **Path:** `tag_uuid`; **Body (JSON):** `name` |
| `analytics/tags/{tag_uuid}` (delete) | DELETE | `/v2/analytics/tags/{tag_uuid}` | **Path:** `tag_uuid` |
| `analytics/tags` (list) | GET | `/v2/analytics/tags` | **Query (optional):** `is_system_tag` (boolean) |
| `analytics/revenue-deduction-tags` | GET | `/v2/analytics/revenue-deduction-tags` | None |
| `analytics/revenue-deduction-tags` (update) | PUT | `/v2/analytics/revenue-deduction-tags` | **Body (JSON):** `tag_names` (array) |
| `analytics/book/{book_uuid}/transactions` | PUT | `/v2/analytics/book/{book_uuid}/transactions` | **Path:** `book_uuid`; **Body (JSON):** `txn_pk`, `tag_uuids` |

---

## Encore (Book Copy)

Organization-to-organization book sharing.

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `book/copy-jobs` (create) | POST | `/v1/book/copy-jobs` | **Body (JSON):** `jobs` (array, max 50) |
| `book/copy-jobs` (list) | GET | `/v1/book/copy-jobs` | **Query (optional):** `direction` (`outbound` or `inbound`) |
| `book/copy-jobs/{job_id}/accept` | POST | `/v1/book/copy-jobs/{job_id}/accept` | **Path:** `job_id`; **Body (JSON):** `name` |
| `book/copy-jobs/{job_id}/reject` | POST | `/v1/book/copy-jobs/{job_id}/reject` | **Path:** `job_id` |
| `book/copy-jobs/run-kickouts` | POST | `/v1/book/copy-jobs/run-kickouts` | None |
| `settings/book-copy` | GET | `/v1/settings/book-copy` | None |

---

## Webhooks

### Organization-level (recommended)

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `account/settings/webhook` | POST | `/v1/account/settings/webhook` | **Body (JSON):** `url`, `events` (array) |
| `account/settings/webhooks` | GET | `/v1/account/settings/webhooks` | None |
| `account/settings/webhooks/{webhook_id}` | GET | `/v1/account/settings/webhooks/{webhook_id}` | **Path:** `webhook_id` |
| `account/settings/webhooks/{webhook_id}` (update) | PUT | `/v1/account/settings/webhooks/{webhook_id}` | **Path:** `webhook_id`; **Body (JSON):** `url`, `events` |
| `account/settings/webhooks/{webhook_id}` (delete) | DELETE | `/v1/account/settings/webhooks/{webhook_id}` | **Path:** `webhook_id` |
| `account/settings/webhooks/events` | GET | `/v1/account/settings/webhooks/events` | None |
| `account/settings/webhooks/{webhook_id}/test` | POST | `/v1/account/settings/webhooks/{webhook_id}/test` | **Path:** `webhook_id` |
| `account/settings/webhooks/secret` | POST | `/v1/account/settings/webhooks/secret` | **Body (JSON):** `secret` (string, 16–128 chars) |

### Account-level

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `webhook/configure` | POST | `/v1/webhook/configure` | **Body (JSON):** `url`, `events` (array) |
| `webhook/configuration` | GET | `/v1/webhook/configuration` | None |
| `webhook/test` | POST | `/v1/webhook/test` | None |
| `webhook/secret` | POST | `/v1/webhook/secret` | **Body (JSON):** `secret` (string) |

Only one webhook type can be active per tenant — organization-level or account-level, not both. See `references/webhooks.md` for event names, payloads, and signature verification.

---

## Input Type Legend

| Label | Meaning |
|-------|---------|
| **Path:** | URL path parameter — value is embedded in the URL (e.g., `/v1/book/{pk}`) |
| **Query:** | URL query parameter — appended as `?key=value` |
| **Query (optional):** | Optional URL query parameter |
| **Body (JSON):** | Request body sent as `application/json` |
| **Body (form-encoded):** | Request body sent as `application/x-www-form-urlencoded` |
| **Body (raw):** | Request body sent as raw binary with appropriate Content-Type |
| **Form (multipart):** | Request body sent as `multipart/form-data` (file uploads) |
| **Header:** | Custom request header |
| None | No parameters required |
