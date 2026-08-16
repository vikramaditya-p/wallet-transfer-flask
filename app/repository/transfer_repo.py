"""Transfer persistence, mirroring internal/repository/transfer.go."""

from typing import Optional
from uuid import UUID

from ..domain.errors import ErrTransferNotFound
from ..domain.transfer import Transfer, TransferStatus


def _row_to_transfer(row) -> Transfer:
    return Transfer(
        id=row[0],
        from_wallet_id=row[1],
        to_wallet_id=row[2],
        amount=row[3],
        status=TransferStatus(row[4]),
        failure_reason=row[5],
        created_at=row[6],
        updated_at=row[7],
    )


class TransferRepository:
    def get_by_id(self, conn, transfer_id: UUID) -> Transfer:
        row = conn.execute(
            "SELECT id, from_wallet_id, to_wallet_id, amount, status, failure_reason, "
            "created_at, updated_at FROM transfers WHERE id = %s",
            (transfer_id,),
        ).fetchone()
        if row is None:
            raise ErrTransferNotFound()
        return _row_to_transfer(row)

    def insert(self, conn, transfer: Transfer) -> None:
        conn.execute(
            "INSERT INTO transfers (id, from_wallet_id, to_wallet_id, amount, status, "
            "failure_reason, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                transfer.id,
                transfer.from_wallet_id,
                transfer.to_wallet_id,
                transfer.amount,
                transfer.status.value,
                transfer.failure_reason,
                transfer.created_at,
                transfer.updated_at,
            ),
        )

    def update_status(
        self, conn, transfer_id: UUID, new_status: TransferStatus, failure_reason: Optional[str]
    ) -> None:
        conn.execute(
            "UPDATE transfers SET status = %s, failure_reason = %s, updated_at = NOW() WHERE id = %s",
            (new_status.value, failure_reason, transfer_id),
        )

    def lock_for_update(self, tx, transfer_id: UUID) -> Transfer:
        row = tx.execute(
            "SELECT id, from_wallet_id, to_wallet_id, amount, status, failure_reason, "
            "created_at, updated_at FROM transfers WHERE id = %s FOR UPDATE",
            (transfer_id,),
        ).fetchone()
        if row is None:
            raise ErrTransferNotFound()
        return _row_to_transfer(row)
