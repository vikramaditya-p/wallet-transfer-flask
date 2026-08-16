"""Integration test fixtures, mirroring internal/testutil/db.go.

These tests run against a real Postgres instance the same way the Go
integration suite does (`docker compose up -d postgres && make migrate-up`).
If the database isn't reachable, every test in this package is skipped
rather than failing, so the unit suite stays runnable standalone.
"""

import psycopg
import pytest

from app.config import Config
from app.repository.db import Store


@pytest.fixture
def store():
    cfg = Config.load()
    try:
        # Fast reachability probe with a short timeout before handing off to
        # the connection pool, which otherwise retries for a long time on an
        # unreachable host.
        with psycopg.connect(cfg.dsn(), connect_timeout=2) as probe:
            probe.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"postgres not reachable ({exc}); run `docker compose up -d postgres && make migrate-up`")
        return

    s = Store(cfg.dsn())
    truncate_all(s)
    yield s
    s.close()


def truncate_all(store: Store) -> None:
    with store.connection() as conn:
        conn.execute(
            "TRUNCATE TABLE ledger_entries, idempotency_records, transfers, wallets RESTART IDENTITY CASCADE"
        )


def seed_wallet(store: Store, wallet_id: str, balance: int) -> None:
    with store.connection() as conn:
        conn.execute("INSERT INTO wallets (id, balance) VALUES (%s, %s)", (wallet_id, balance))


def scan_one(store: Store, query: str, params=()):
    with store.connection() as conn:
        return conn.execute(query, params).fetchone()
