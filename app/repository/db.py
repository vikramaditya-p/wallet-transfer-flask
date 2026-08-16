"""Connection pool and transaction helper, mirroring internal/repository/repository.go.

Store.within_tx is the equivalent of Go's Store.WithinTx: it wraps a block of
work in a single transaction, committing on success and rolling back if the
block raises. Repository methods below take a plain psycopg connection
(``Executor``-equivalent) so they can run standalone (against a pooled
connection) or as part of an in-flight transaction, exactly like the Go
repositories accept either *pgxpool.Pool or pgx.Tx.
"""

from contextlib import contextmanager

from psycopg_pool import ConnectionPool


class Store:
    def __init__(self, dsn: str):
        self.pool = ConnectionPool(dsn, open=True)

    def close(self) -> None:
        self.pool.close()

    @contextmanager
    def connection(self):
        with self.pool.connection() as conn:
            yield conn

    @contextmanager
    def within_tx(self):
        """Run a block of repository calls in a single transaction.

        psycopg's ``conn.transaction()`` context manager commits on clean
        exit and rolls back if the body raises, matching WithinTx's
        defer-based commit/rollback in Go.
        """
        with self.pool.connection() as conn:
            with conn.transaction():
                yield conn
