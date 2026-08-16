"""Transfer entity and state machine, mirroring internal/domain/transfer.go."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

from .errors import (
    ErrInvalidAmount,
    ErrInvalidTransition,
    ErrSameWallet,
    ErrWalletIdRequired,
)


class TransferStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


def _now():
    return datetime.now(timezone.utc)


@dataclass
class Transfer:
    id: UUID
    from_wallet_id: str
    to_wallet_id: str
    amount: int
    status: TransferStatus
    failure_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def new_pending(cls, id: UUID, from_wallet_id: str, to_wallet_id: str, amount: int) -> "Transfer":
        if not from_wallet_id or not to_wallet_id:
            raise ErrWalletIdRequired()
        if from_wallet_id == to_wallet_id:
            raise ErrSameWallet()
        if amount <= 0:
            raise ErrInvalidAmount()
        now = _now()
        return cls(
            id=id,
            from_wallet_id=from_wallet_id,
            to_wallet_id=to_wallet_id,
            amount=amount,
            status=TransferStatus.PENDING,
            failure_reason=None,
            created_at=now,
            updated_at=now,
        )

    def mark_processed(self) -> None:
        if self.status != TransferStatus.PENDING:
            raise ErrInvalidTransition()
        self.status = TransferStatus.PROCESSED
        self.updated_at = _now()

    def mark_failed(self, reason: str = "") -> None:
        if self.status != TransferStatus.PENDING:
            raise ErrInvalidTransition()
        self.status = TransferStatus.FAILED
        self.failure_reason = reason or "unspecified"
        self.updated_at = _now()
