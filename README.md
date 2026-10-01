# Integration Hub

Small multi-tenant integration service. Simulated CRM owns customer profiles;
simulated billing owns invoices and payments. PostgreSQL stores webhook events,
sync status, and the worker queue.

## Run locally

Requires Docker Compose.

```sh
docker compose up --build
```

Compose starts PostgreSQL, applies migrations, then starts the API and worker.
The API listens at `http://127.0.0.1:8000`. PostgreSQL has no host port and is
available only to Compose services. Seed tenants: `acme` and `globex`.

Stop services with `docker compose down`. The named database volume remains so
local state persists between runs. Delete it with `docker compose down -v` to
reset the demo.

## Send a simulated event

The seeded HMAC values are public demo strings, not credentials. Sign the exact
request body with SHA-256:

```sh
body='{"id":"evt-local-001","type":"customer.updated","data":{"id":"customer_002","name":"Ada Lovelace","email":"ada@example.test"}}'
signature=$(printf '%s' "$body" | openssl dgst -sha256 -hmac 'demo-acme-crm-secret' -hex | awk '{print $2}')

curl -i http://127.0.0.1:8000/webhooks/crm \
  -H 'X-Tenant-ID: acme' \
  -H "X-Signature-SHA256: $signature" \
  -H 'Content-Type: application/json' \
  --data "$body"
```

Successful requests return `202` with a `sync_id`. Repeating the same event
returns the original ID and `duplicate: true`. The worker retries failures up to
five times with exponential delays, then marks the sync `dead_letter`.

## Check sync status

Every status request requires the owning tenant header. List returns at most
100 newest syncs; `limit` can be set from 1 to 100.

```sh
curl -H 'X-Tenant-ID: acme' http://127.0.0.1:8000/syncs
curl -H 'X-Tenant-ID: acme' http://127.0.0.1:8000/syncs/<sync_id>
```

Unknown sync IDs and IDs owned by another tenant both return `404`.

## API reference

FastAPI serves interactive OpenAPI docs at `/docs` and the schema at
`/openapi.json`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Process health |
| `POST` | `/webhooks/{source}` | Accept signed `crm` or `billing` events |
| `GET` | `/syncs` | List tenant syncs |
| `GET` | `/syncs/{sync_id}` | Read one tenant sync |

Webhook bodies are limited to 1 MiB. Supported events: `customer.updated` from
CRM; `invoice.updated` and `payment.updated` from billing.

## Code layout

- `src/integration_hub/main.py`: HTTP routes, request limits, and HTTP error mapping.
- `src/integration_hub/services/webhooks.py`: signature and payload validation, event persistence,
  deduplication, and job enqueueing.
- `src/integration_hub/services/syncs.py`: tenant-scoped status queries.
- `src/integration_hub/worker.py`: claims jobs, tracks attempts, and applies status transitions.
- `src/integration_hub/services/delivery.py`: routes supported events to simulated connectors.
- `src/integration_hub/connectors/simulated.py`: process-local in-memory CRM and billing simulators.
- `src/integration_hub/models.py`, `migrations/`: PostgreSQL schema and migrations.
- `tests/unit/`, `tests/integration/`: tests grouped by database requirement.

## Checks

CI runs Ruff, format checks, PostgreSQL migrations, schema drift checks, and
pytest. To run tests after `docker compose up`, use a temporary test dependency
directory inside the API container:

```sh
docker compose run --rm --no-deps --entrypoint sh api -c \
  'pip install --target /tmp/pydeps -r requirements-dev.txt && PYTHONPATH=/tmp/pydeps python -m pytest -W error -p no:cacheprovider'
```

## Deployment boundary

This repository is a local simulation, not production-ready configuration.
Compose uses PostgreSQL trust authentication and seeded public HMAC strings.
Connector data lives in process memory and resets when the worker restarts.
Before connecting real systems, replace demo secrets and local database
authentication, configure managed secret storage and PostgreSQL credentials,
and implement authenticated CRM and billing clients.
