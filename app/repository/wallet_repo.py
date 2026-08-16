"""Wallet persistence, mirroring internal/repository/wallet.go."""

from typing import Dict, List

from ..domain.errors import ErrWalletNotFound
from ..domain.wallet import Wallet


class WalletRepository:
    def insert(self, conn, wallet: Wallet) -> None:
        conn.execute(
            "INSERT INTO wallets (id, balance, created_at, updated_at) VALUES (%s,%s,%s,%s)",
            (wallet.id, wallet.balance, wallet.created_at, wallet.updated_at),
        )

    def get_by_id(self, conn, wallet_id: str) -> Wallet:
        row = conn.execute(
            "SELECT id, balance, created_at, updated_at FROM wallets WHERE id = %s",
            (wallet_id,),
        ).fetchone()
        if row is None:
            raise ErrWalletNotFound()
        return Wallet(id=row[0], balance=row[1], created_at=row[2], updated_at=row[3])

    def lock_for_update(self, tx, wallet_ids: List[str]) -> Dict[str, Wallet]:
        # Lock in a stable (sorted) order across every call site so two
        # concurrent transfers touching the same pair of wallets always
        # acquire row locks in the same order, avoiding deadlocks.
        result: Dict[str, Wallet] = {}
        for wallet_id in sorted(wallet_ids):
            row = tx.execute(
                "SELECT id, balance, created_at, updated_at FROM wallets "
                "WHERE id = %s FOR UPDATE",
                (wallet_id,),
            ).fetchone()
            if row is None:
                raise ErrWalletNotFound()
            result[row[0]] = Wallet(id=row[0], balance=row[1], created_at=row[2], updated_at=row[3])
        return result

    def update_balance(self, conn, wallet_id: str, new_balance: int) -> None:
        conn.execute(
            "UPDATE wallets SET balance = %s, updated_at = NOW() WHERE id = %s",
            (new_balance, wallet_id),
        )
