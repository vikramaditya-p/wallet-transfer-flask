"""Ledger entry persistence, mirroring internal/repository/ledger.go."""

from ..domain.ledger import LedgerEntry


class LedgerRepository:
    def insert_entries(self, conn, *entries: LedgerEntry) -> None:
        for entry in entries:
            conn.execute(
                "INSERT INTO ledger_entries (id, transfer_id, wallet_id, type, amount, created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    entry.id,
                    entry.transfer_id,
                    entry.wallet_id,
                    entry.type.value,
                    entry.amount,
                    entry.created_at,
                ),
            )
