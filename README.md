# wallet-transfer (Flask port)

A Flask/psycopg port of the Go `wallet-transfer-assignment` service, kept in
the same `handler → service → repository → domain` layering as the original
(see `../internal/`). Raw SQL via `psycopg`, no ORM — mirrors the Go code's
use of `pgx` directly.

## Layout

```
app/
  domain/       entities + invariants (Transfer, Wallet, LedgerEntry, errors) — no DB/HTTP deps
  repository/   raw SQL against a psycopg connection or transaction
  service/      TransferService: idempotency + locked balance transfer orchestration
  handler/      Flask blueprint: request validation, response/error mapping
  config.py     env-driven config (same DB_* vars as the Go service)
  __init__.py   create_app() factory
run.py          entrypoint: python run.py
migrations/     copy of the Go service's schema (wallets, transfers, ledger_entries, idempotency_records)
tests/
  unit/         domain + handler tests, no DB required
  integration/  TransferService tests against a real Postgres (auto-skip if unreachable)
```

## Setup

```bash
cd flask-port
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

Requires Postgres reachable via the same `DB_*` env vars as the Go service
(see `.env.example`). Reuse the repo root's `docker-compose.yml`:

```bash
cd .. && docker compose up -d postgres && docker compose --profile tools run --rm migrate
cd flask-port && python run.py
```

## Test

```bash
pytest                      # unit tests only need no DB; integration tests
                             # auto-skip if Postgres isn't reachable
```
