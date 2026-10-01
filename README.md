# Integration Hub

Multi-tenant API that synchronizes data between simulated CRM and invoicing
systems.

## Run

Requires Python 3.14.

```sh
python3 main.py
```

## Quality checks

```sh
uvx --from ruff==0.16.9 ruff check .
uvx --from ruff==0.16.9 ruff format --check .
```
