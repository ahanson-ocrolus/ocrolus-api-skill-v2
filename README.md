# Ocrolus API Skill

An AI-agent-ready skill for building [Ocrolus](https://www.ocrolus.com/) integrations. Drop `SKILL.md` into your project and your AI coding assistant gets the right endpoints, auth patterns, webhook events, and a validated Python SDK — no trial-and-error needed.

## What's Here

```
SKILL.md             ← The skill — feed this to your AI agent
ocrolus_client.py    ← Python SDK (CLI included)
requirements.txt
references/          ← Endpoint inventory, webhook events, fraud detection
tools/               ← Health check, webhook setup, widget quickstart, OpenAPI spec, Postman collection
```

## Quick Start

### Use with an AI agent

Point your AI assistant at `SKILL.md`:

- **Claude Code** — place this repo in your project; the skill activates on Ocrolus-related prompts.
- **Other agents** — include `SKILL.md` as context when asking for Ocrolus integration help.

The skill covers authentication, capability-organized endpoints (Classify, Capture, Detect, Analyze, Income), webhooks, and the things developers commonly miss.

### Use the SDK directly

```bash
pip install -r requirements.txt
export OCROLUS_CLIENT_ID="your_client_id"
export OCROLUS_CLIENT_SECRET="your_client_secret"
```

```python
from ocrolus_client import OcrolusClient

client = OcrolusClient()

book = client.create_book("Application #12345")
client.upload_pdf(book["pk"], "bank_statement.pdf")
client.wait_for_book(book["pk"], timeout=600)

summary = client.get_book_summary(book["uuid"])
fraud   = client.get_book_fraud_signals(book["uuid"])
income  = client.get_income_calculations(book["uuid"])
```

The SDK also runs as a CLI:

```bash
python ocrolus_client.py list-books
python ocrolus_client.py create-book "Test Book"
python ocrolus_client.py book-status 12345
```

## Key Concepts

**Book identifiers** — Ocrolus uses two IDs. v1 endpoints take the integer `pk`; v2 endpoints take the `uuid`. They are not interchangeable.

| Identifier | Format | Used by |
|------------|--------|---------|
| `pk` | Integer | v1 endpoints (uploads, forms, transactions, status) |
| `uuid` | UUID string | v2 endpoints (Classify, Detect, Analyze, Income) |

**Processing modes:** Classify (fastest, classification only) → Instant (fast, good accuracy) → Complete (slowest, human-verified, highest accuracy).

## Tools & Extras

The `tools/` directory has optional utilities — see [`tools/README.md`](tools/README.md):

- **Health check** — probes API endpoints on your tenant.
- **Webhook setup** — local listener + ngrok tunnel + auto-registration.
- **Webhook verifier** — drop-in HMAC-SHA256 verification for production handlers.
- **Widget quickstart** — Python/Flask implementation of the Ocrolus embeddable upload widget.
- **OpenAPI spec** — `tools/docs/ocrolus-api-official-openapi3.yaml`.
- **Postman collection** — `tools/docs/generated/ocrolus-api.postman_collection.json`.

## Ocrolus Documentation

- [API Reference](https://docs.ocrolus.com/reference)
- [API Guide](https://docs.ocrolus.com/docs/guide)
- [Authentication](https://docs.ocrolus.com/docs/using-api-credentials)
- [Webhooks](https://docs.ocrolus.com/docs/webhook-overview)
- [Fraud Detection](https://docs.ocrolus.com/docs/detect)
- [Widget](https://docs.ocrolus.com/docs/widget)
