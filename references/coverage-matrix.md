# Endpoint Coverage Matrix

> **IMPORTANT: This matrix has NOT been validated against a live Ocrolus tenant.**
> All paths were inferred from public documentation scrapes, which returned
> inconsistent results for some endpoints. "Covered" means the SDK has a method
> and the reference doc has an entry -- it does NOT mean the path has been
> confirmed to return HTTP 200 on a real tenant.
>
> **Before treating this as production-ready**, run `scripts/validate_endpoints.py`
> against your Ocrolus credentials to confirm every path. See README for instructions.
>
> Last doc scrape: 2026-03-18 | Source: https://docs.ocrolus.com/reference

## Legend

| Symbol | Meaning |
|--------|---------|
| :white_check_mark: | SDK method + reference doc entry exist (path NOT yet live-validated) |
| :memo: | Documented in endpoint reference only (no SDK method) |
| :warning: | Conflicting doc signals -- path needs live validation before use |
| :x: | Not covered |

---

## Authentication

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Grant Token | `POST https://auth.ocrolus.com/oauth/token` | `_get_token()` (auto) | :white_check_mark: |

## Book Operations

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Create Book | `POST /v1/book/create` | `create_book()` | :warning: Conflicting docs |
| Delete Book | `POST /v1/book/delete` | `delete_book()` | :white_check_mark: |
| Update Book | `POST /v1/book/update` | `update_book()` | :white_check_mark: |
| Book Info | `GET /v1/book/{book_pk}` | `get_book()` | :white_check_mark: |
| List Books | `GET /v1/books` | `list_books()` | :white_check_mark: |
| Book Status | `GET /v1/book/status` | `get_book_status()` | :warning: Conflicting docs |
| Book from Loan | `GET /v1/book/loan/{loan_id}` | `get_book_from_loan()` | :white_check_mark: |
| Loan from Book | `GET /v1/book/{book_pk}/loan` | `get_loan_from_book()` | :white_check_mark: |

## Document Upload & Management

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Upload PDF | `POST /v1/book/upload` | `upload_pdf()` | :warning: Conflicting docs |
| Upload Mixed PDF | `POST /v1/book/upload/mixed` | `upload_mixed_pdf()` | :white_check_mark: |
| Upload Pay Stub | `POST /v1/book/upload/paystub` | `upload_paystub_pdf()` | :white_check_mark: |
| Upload Image | `POST /v1/book/upload/image` | `upload_image()` | :white_check_mark: |
| Finalize Image Group | `POST /v1/book/finalize-image-group` | `finalize_image_group()` | :white_check_mark: |
| Upload Plaid JSON | `POST /v1/book/upload/plaid` | `upload_plaid_json()` | :white_check_mark: |
| Import Plaid Asset | `POST /v1/book/import/plaid/asset` | `import_plaid_asset_report()` | :white_check_mark: |
| Cancel Document | `POST /v1/document/{doc_uuid}/cancel` | `cancel_document()` | :white_check_mark: |
| Delete Document | `POST /v1/document/{doc_uuid}/delete` | `delete_document()` | :white_check_mark: |
| Download Document | `GET /v1/document/{doc_uuid}/download` | `download_document()` | :white_check_mark: |
| Upgrade Document | `POST /v1/document/{doc_uuid}/upgrade` | `upgrade_document()` | :white_check_mark: |
| Upgrade Mixed Doc | `POST /v1/document/mixed/upgrade` | `upgrade_mixed_document()` | :white_check_mark: |
| Mixed Doc Status | `GET /v1/document/mixed/status` | `get_mixed_document_status()` | :white_check_mark: |

## Classification (Classify)

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Book Classification | `GET /v2/book/{uuid}/classification-summary` | `get_book_classification_summary()` | :white_check_mark: |
| Mixed Doc Classification | `GET /v2/mixed-document/{uuid}/classification-summary` | `get_mixed_doc_classification_summary()` | :white_check_mark: |
| Grouped Mixed Doc | `GET /v2/index/mixed-doc/{uuid}/summary` | `get_grouped_mixed_doc_summary()` | :white_check_mark: |

## Data Extraction (Capture)

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Book Forms | `GET /v1/book/{pk}/forms` | `get_book_forms()` | :white_check_mark: |
| Book Paystubs | `GET /v1/book/{pk}/paystubs` | `get_book_paystubs()` | :white_check_mark: |
| Document Forms | `GET /v1/document/{uuid}/forms` | `get_document_forms()` | :white_check_mark: |
| Document Paystubs | `GET /v1/document/{uuid}/paystubs` | `get_document_paystubs()` | :white_check_mark: |
| Form Fields | `GET /v1/form/{uuid}/fields` | `get_form_fields()` | :white_check_mark: |
| Pay Stub Data | `GET /v1/paystub/{uuid}` | `get_paystub()` | :white_check_mark: |
| Transactions | `GET /v1/book/{pk}/transactions` | `get_book_transactions()` | :warning: Verify path style |

## Fraud Detection (Detect)

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Book Fraud Signals | `GET /v2/detect/book/{uuid}/signals` | `get_book_fraud_signals()` | :white_check_mark: |
| Doc Fraud Signals | `GET /v2/detect/document/{uuid}/signals` | `get_document_fraud_signals()` | :white_check_mark: |
| Signal Visualization | `GET /v2/detect/visualization/{viz_uuid}` | `get_fraud_visualization()` | :white_check_mark: |
| Suspicious Activity (LEGACY) | `GET /v1/book/{uuid}/suspicious-activity-flags` | -- | :memo: Deprecated, documented only |

**Detect coverage notes:**
- Authenticity scores (0-100) documented in `references/detect.md`
- Reason codes (e.g., `110-H`) with confidence levels documented
- File Origin vs File Tampering signal types documented
- Score thresholds and interpretation guidance included

## Cash Flow Analytics

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Book Summary | `GET /v2/book/{uuid}/summary` | `get_book_summary()` | :white_check_mark: |
| Cash Flow Features | `GET /v2/book/{uuid}/cash_flow_features` | `get_cashflow_features()` | :white_check_mark: |
| Enriched Transactions | `GET /v2/book/{uuid}/enriched_txns` | `get_enriched_transactions()` | :white_check_mark: |
| Risk Score | `GET /v2/book/{uuid}/cash_flow_risk_score` | `get_risk_score()` | :white_check_mark: |
| Benchmarking (Beta) | `GET /v2/book/{uuid}/benchmarking` | `get_benchmarking()` | :white_check_mark: |
| SMB Analytics Excel | `GET /v2/book/{uuid}/lender_analytics/xlsx` | `get_analytics_excel()` | :white_check_mark: |

## Income Calculations

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Income Calculations | `GET /v2/book/{uuid}/income-calculations` | `get_income_calculations()` | :white_check_mark: |
| Income Summary | `GET /v2/book/{uuid}/income-summary` | `get_income_summary()` | :white_check_mark: |
| Configure Entity | `POST /v2/book/{uuid}/income-entity` | `configure_income_entity()` | :white_check_mark: |
| Save Guideline | `PUT /v2/book/{uuid}/income-guideline` | `save_income_guideline()` | :white_check_mark: |
| Self-Employed (Fannie Mae) | `POST /v2/book/{uuid}/self-employed-income` | `calculate_self_employed_income()` | :white_check_mark: |
| BSIC | `GET /v2/book/{uuid}/bsic` | `get_bsic()` | :white_check_mark: |
| BSIC Excel | `GET /v2/book/{uuid}/bsic` (Accept: xlsx) | `get_bsic_excel()` | :white_check_mark: |

## Tag Management (Beta)

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Create Tag | `POST /v2/analytics/tags` | `create_tag()` | :white_check_mark: |
| Retrieve Tag | `GET /v2/analytics/tags/{uuid}` | `get_tag()` | :white_check_mark: |
| Modify Tag | `PUT /v2/analytics/tags/{uuid}` | `modify_tag()` | :white_check_mark: |
| Delete Tag | `DELETE /v2/analytics/tags/{uuid}` | `delete_tag()` | :white_check_mark: |
| List All Tags | `GET /v2/analytics/tags` | `list_tags()` | :white_check_mark: |
| Revenue Deduction Tags | `GET /v2/analytics/revenue-deduction-tags` | `get_revenue_deduction_tags()` | :white_check_mark: |
| Update Rev Deduction | `PUT /v2/analytics/revenue-deduction-tags` | `update_revenue_deduction_tags()` | :white_check_mark: |
| Override Txn Tag | `PUT /v2/analytics/book/{uuid}/transactions` | `override_transaction_tag()` | :white_check_mark: |

## Encore / Book Copy

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Create Copy Jobs | `POST /v1/book/copy-jobs` | `create_book_copy_jobs()` | :white_check_mark: |
| List Copy Jobs | `GET /v1/book/copy-jobs` | `list_book_copy_jobs()` | :white_check_mark: |
| Accept Copy Job | `POST /v1/book/copy-jobs/{id}/accept` | `accept_book_copy_job()` | :white_check_mark: |
| Reject Copy Job | `POST /v1/book/copy-jobs/{id}/reject` | `reject_book_copy_job()` | :white_check_mark: |
| Run Kick-Outs | `POST /v1/book/copy-jobs/run-kickouts` | `run_book_copy_kickouts()` | :white_check_mark: |
| Copy Settings | `GET /v1/settings/book-copy` | `get_book_copy_settings()` | :white_check_mark: |

## Webhooks -- Org-Level

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Add Webhook | `POST /v1/account/settings/webhook` | `add_org_webhook()` | :white_check_mark: |
| List Webhooks | `GET /v1/account/settings/webhooks` | `list_org_webhooks()` | :white_check_mark: |
| Retrieve Webhook | `GET /v1/account/settings/webhooks/{id}` | `get_org_webhook()` | :white_check_mark: |
| Update Webhook | `PUT /v1/account/settings/webhooks/{id}` | `update_org_webhook()` | :white_check_mark: |
| Delete Webhook | `DELETE /v1/account/settings/webhooks/{id}` | `delete_org_webhook()` | :white_check_mark: |
| List Events | `GET /v1/account/settings/webhooks/events` | `list_org_webhook_events()` | :white_check_mark: |
| Test Webhook | `POST /v1/account/settings/webhooks/{id}/test` | `test_org_webhook()` | :white_check_mark: |
| Configure Secret | `POST /v1/account/settings/webhooks/secret` | `configure_org_webhook_secret()` | :white_check_mark: |

## Webhooks -- Account-Level

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Configure | `POST /v1/webhook/configure` | `configure_account_webhook()` | :white_check_mark: |
| Get Config | `GET /v1/webhook/configuration` | `get_account_webhook_config()` | :white_check_mark: |
| Test | `POST /v1/webhook/test` | `test_account_webhook()` | :white_check_mark: |
| Configure Secret | `POST /v1/webhook/secret` | `configure_account_webhook_secret()` | :white_check_mark: |

---

## Coverage Summary

| Category | Total Endpoints | SDK Methods | Ref Documented | Live Validated |
|----------|----------------|------------|----------------|---------------|
| Authentication | 1 | 1 | 1 | **No** |
| Book Operations | 8 | 8 | 8 | **No** (2 have conflicting docs) |
| Document Upload | 13 | 13 | 13 | **No** (1 has conflicting docs) |
| Classification | 3 | 3 | 3 | **No** |
| Data Extraction | 7 | 7 | 7 | **No** (1 has conflicting docs) |
| Fraud Detection | 4 | 3 (+1 legacy) | 4 | **No** |
| Cash Flow Analytics | 6 | 6 | 6 | **No** |
| Income Calculations | 7 | 7 | 7 | **No** |
| Tag Management | 8 | 8 | 8 | **No** |
| Encore / Book Copy | 6 | 6 | 6 | **No** |
| Webhooks (Org) | 8 | 8 | 8 | **No** |
| Webhooks (Account) | 4 | 4 | 4 | **No** |
| **TOTAL** | **75** | **74** | **75** | **0** |

> **The "Live Validated" column is the gap.** Every row reads "No" because this
> matrix was built from doc scrapes, not from confirmed API responses. The validation
> script in the README will flip these to "Yes" once run against your tenant.

## Known Conflicts & Open Questions

1. **Book Create path**: Docs show both `/v1/book/create` and possibly `POST /v1/books` -- need live test
2. **Book Status path**: Docs conflict between `/v1/book/status?book_pk=X` (query param) and `/v1/book/{book_pk}/status` (path param)
3. **Upload PDF path**: One page says `/v1/book/upload` with book_pk in form data; other examples imply book_pk in path
4. **Transactions path**: Same query-param vs path-param ambiguity as Book Status
5. **Webhook event names**: Assembled from scattered references, NOT confirmed from List Events endpoint. Production webhooks may use different strings.
6. **Cash flow paths**: Inferred as `cash_flow_features`, `enriched_txns`, `cash_flow_risk_score` from API reference pages -- plausible but not confirmed
7. **Detect paths**: `/v2/detect/book/{uuid}/signals` seen on one reference page; needs confirmation
8. **Webhook paths**: `/v1/account/settings/webhook(s)` seen on reference page; needs confirmation vs earlier `/v1/org/webhooks`
9. **Docs-to-Digital matching**: Dashboard feature; no standalone API endpoint identified
10. **Reason code full list**: Not publicly published; codes returned dynamically in Detect responses
11. **Widget script URL**: Must be obtained from Dashboard; not a static public URL

## How to Validate

See **README.md > Required Setup > Step 1 and Step 2** for the validation process.
The short version:
1. Run `python scripts/validate_endpoints.py` with your credentials
2. Run `python scripts/validate_endpoints.py --webhooks` to discover canonical event names
3. Update this matrix and the SDK with confirmed paths
