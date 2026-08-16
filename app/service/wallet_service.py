"""Wallet provisioning: creating a wallet with a starting balance.

Kept separate from TransferService — creating a wallet is a single insert
with no idempotency-key or locking concerns of its own.
"""

from psycopg.errors import UniqueViolation

from ..domain.errors import ErrWalletAlreadyExists
from ..domain.wallet import Wallet
from ..repository.db import Store
from ..repository.wallet_repo import WalletRepository


class WalletService:
    def __init__(self, store: Store, wallets: WalletRepository = None):
        self.store = store
        self.wallets = wallets or WalletRepository()

    def create_wallet(self, wallet_id: str, balance: int) -> Wallet:
        wallet = Wallet.new(wallet_id, balance)
        try:
            with self.store.connection() as conn:
                self.wallets.insert(conn, wallet)
        except UniqueViolation:
            raise ErrWalletAlreadyExists()
        return wallet
