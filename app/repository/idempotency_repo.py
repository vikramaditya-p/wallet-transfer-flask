"""Idempotency record persistence, mirroring internal/repository/idempotency.go."""

from ..domain.errors import ErrIdempotencyRecordNotFound
from ..domain.idempotency import IdempotencyRecord


class IdempotencyRepository:
    def insert(self, conn, record: IdempotencyRecord) -> None:
        conn.execute(
            "INSERT INTO idempotency_records (idempotency_key, request_hash, transfer_id, created_at) "
            "VALUES (%s,%s,%s,%s)",
            (record.idempotency_key, record.request_hash, record.transfer_id, record.created_at),
        )

    def get(self, conn, idempotency_key: str) -> IdempotencyRecord:
        row = conn.execute(
            "SELECT idempotency_key, request_hash, transfer_id, created_at "
            "FROM idempotency_records WHERE idempotency_key = %s",
            (idempotency_key,),
        ).fetchone()
        if row is None:
            raise ErrIdempotencyRecordNotFound()
        return IdempotencyRecord(
            idempotency_key=row[0], request_hash=row[1], transfer_id=row[2], created_at=row[3]
        )
