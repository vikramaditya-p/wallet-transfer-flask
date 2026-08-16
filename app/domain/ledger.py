"""Ledger entry entity, mirroring internal/domain/ledger.go."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Tuple
from uuid import UUID


class LedgerEntryType(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


@dataclass
class LedgerEntry:
    id: UUID
    transfer_id: UUID
    wallet_id: str
    type: LedgerEntryType
    amount: int
    created_at: Optional[datetime] = None


def new_ledger_pair(
    transfer_id: UUID, from_wallet_id: str, to_wallet_id: str, amount: int
) -> Tuple[LedgerEntry, LedgerEntry]:
    now = datetime.now(timezone.utc)
    debit = LedgerEntry(
        id=uuid.uuid4(),
        transfer_id=transfer_id,
        wallet_id=from_wallet_id,
        type=LedgerEntryType.DEBIT,
        amount=amount,
        created_at=now,
    )
    credit = LedgerEntry(
        id=uuid.uuid4(),
        transfer_id=transfer_id,
        wallet_id=to_wallet_id,
        type=LedgerEntryType.CREDIT,
        amount=amount,
        created_at=now,
    )
    return debit, credit
