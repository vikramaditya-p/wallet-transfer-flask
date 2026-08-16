"""Wallet entity, mirroring internal/domain/wallet.go."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .errors import ErrInvalidBalance, ErrWalletIdRequired


@dataclass
class Wallet:
    id: str
    balance: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def new(cls, id: str, balance: int) -> "Wallet":
        if not id:
            raise ErrWalletIdRequired()
        if balance < 0:
            raise ErrInvalidBalance()
        now = datetime.now(timezone.utc)
        return cls(id=id, balance=balance, created_at=now, updated_at=now)

    def has_sufficient_funds(self, amount: int) -> bool:
        return self.balance >= amount
