# Integration Hub

Multi-tenant API that synchronizes data between simulated CRM and invoicing
systems.

## Run

Requires Python 3.14 and pip.

```sh
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --reload
```

The API responds at `http://127.0.0.1:8000/health`. OpenAPI docs are available
at `http://127.0.0.1:8000/docs`.

## Run with Docker Compose

```sh
docker compose up --build
```

The same API is available at `http://127.0.0.1:8000/health`.

## Quality checks

```sh
uvx --from ruff==0.16.9 ruff check .
uvx --from ruff==0.16.9 ruff format --check .
```
