# Tools & Supporting Resources

Optional utilities, examples, and specs that complement the core SDK and skill. **None of these are required** to use the Ocrolus API — they're here to help with setup, debugging, and integration work.

## Operational Tools

| Tool | What It Does | When to Use |
|------|--------------|-------------|
| `health_check.py` | Probes the Ocrolus API endpoints and generates HTML/JSON/CSV reports | Sanity-check before go-live, or periodic monitoring |
| `webhook_setup.py` | Local webhook listener + ngrok tunnel + auto-registration with Ocrolus | Setting up real-time event processing during development |
| `webhook_verifier.py` | Production webhook receiver with HMAC-SHA256 signature verification | Copy into your project for production use |

```bash
# Probe API endpoints
python tools/health_check.py

# Spin up a webhook listener (requires ngrok)
python tools/webhook_setup.py auto
```

All tools read credentials from `OCROLUS_CLIENT_ID` / `OCROLUS_CLIENT_SECRET`.

## Widget Quickstart (`widget-quickstart/`)

A Python/Flask implementation of the [Ocrolus embeddable widget](https://docs.ocrolus.com/docs/widget), mirroring the official [widget-quickstart](https://github.com/Ocrolus/widget-quickstart) (which ships Node.js and PHP backends).

```bash
cd tools/widget-quickstart
cp .env.example .env  # fill in credentials
pip install flask requests python-dotenv
python widget_app.py
```

See [`widget-quickstart/README.md`](widget-quickstart/README.md) for full setup.

## API Specs (`docs/`)

| File | Description |
|------|-------------|
| `docs/ocrolus-api-official-openapi3.yaml` | Official Ocrolus OpenAPI 3 specification |
| `docs/generated/ocrolus-api.postman_collection.json` | Postman collection for interactive API exploration |
