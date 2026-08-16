"""Transfer orchestration, mirroring internal/service/service.go.

TransferService.create_transfer validates the request, then either replays
an existing transfer for the given idempotency key or creates a new PENDING
one, and finally drives it to a terminal state (PROCESSED/FAILED) under a
single locked transaction.
"""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from psycopg.errors import UniqueViolation

from ..domain.errors import (
    ErrIdempotencyKeyConflict,
    ErrIdempotencyKeyRequired,
    ErrIdempotencyRecordNotFound,
    ErrInvalidAmount,
    ErrSameWallet,
    ErrWalletIdRequired,
)
from ..domain.ledger import new_ledger_pair
from ..domain.transfer import Transfer, TransferStatus
from ..domain.idempotency import IdempotencyRecord
from ..repository.db import Store
from ..repository.idempotency_repo import IdempotencyRepository
from ..repository.ledger_repo import LedgerRepository
from ..repository.transfer_repo import TransferRepository
from ..repository.wallet_repo import WalletRepository


@dataclass
class CreateTransferRequest:
    idempotency_key: str
    from_wallet_id: str
    to_wallet_id: str
    amount: int


class TransferService:
    def __init__(
        self,
        store: Store,
        wallets: WalletRepository = None,
        idempotency: IdempotencyRepository = None,
        transfers: TransferRepository = None,
        ledger: LedgerRepository = None,
    ):
        self.store = store
        self.wallets = wallets or WalletRepository()
        self.idempotency = idempotency or IdempotencyRepository()
        self.transfers = transfers or TransferRepository()
        self.ledger = ledger or LedgerRepository()

    def create_transfer(self, req: CreateTransferRequest) -> Transfer:
        if not req.from_wallet_id or not req.to_wallet_id:
            raise ErrWalletIdRequired()
        if req.from_wallet_id == req.to_wallet_id:
            raise ErrSameWallet()
        if req.amount <= 0:
            raise ErrInvalidAmount()
        if not req.idempotency_key:
            raise ErrIdempotencyKeyRequired()

        with self.store.connection() as conn:
            self.wallets.get_by_id(conn, req.from_wallet_id)
            self.wallets.get_by_id(conn, req.to_wallet_id)

        request_hash = _compute_request_hash(req.from_wallet_id, req.to_wallet_id, req.amount)

        transfer_id = self._find_or_create_transfer(req, request_hash)
        return self._process_transfer(transfer_id)

    def _find_or_create_transfer(self, req: CreateTransferRequest, request_hash: str) -> uuid.UUID:
        try:
            record = self._get_idempotency_record(req.idempotency_key)
            if record.request_hash != request_hash:
                raise ErrIdempotencyKeyConflict()
            return record.transfer_id
        except ErrIdempotencyRecordNotFound:
            pass

        transfer_id = uuid.uuid4()
        transfer = Transfer.new_pending(transfer_id, req.from_wallet_id, req.to_wallet_id, req.amount)

        try:
            with self.store.within_tx() as tx:
                self.transfers.insert(tx, transfer)
                self.idempotency.insert(
                    tx,
                    IdempotencyRecord(
                        idempotency_key=req.idempotency_key,
                        request_hash=request_hash,
                        transfer_id=transfer_id,
                        created_at=datetime.now(timezone.utc),
                    ),
                )
            return transfer_id
        except UniqueViolation:
            record = self._get_idempotency_record(req.idempotency_key)
            if record.request_hash != request_hash:
                raise ErrIdempotencyKeyConflict()
            return record.transfer_id

    def _get_idempotency_record(self, key: str) -> IdempotencyRecord:
        with self.store.connection() as conn:
            return self.idempotency.get(conn, key)

    def _process_transfer(self, transfer_id: uuid.UUID) -> Transfer:
        with self.store.within_tx() as tx:
            transfer = self.transfers.lock_for_update(tx, transfer_id)
            if transfer.status != TransferStatus.PENDING:
                return transfer

            wallets = self.wallets.lock_for_update(
                tx, [transfer.from_wallet_id, transfer.to_wallet_id]
            )
            from_wallet = wallets[transfer.from_wallet_id]
            to_wallet = wallets[transfer.to_wallet_id]

            if not from_wallet.has_sufficient_funds(transfer.amount):
                transfer.mark_failed("insufficient balance")
                self.transfers.update_status(
                    tx, transfer.id, transfer.status, transfer.failure_reason
                )
                return transfer

            self.wallets.update_balance(tx, from_wallet.id, from_wallet.balance - transfer.amount)
            self.wallets.update_balance(tx, to_wallet.id, to_wallet.balance + transfer.amount)

            debit, credit = new_ledger_pair(
                transfer.id, transfer.from_wallet_id, transfer.to_wallet_id, transfer.amount
            )
            self.ledger.insert_entries(tx, debit, credit)

            transfer.mark_processed()
            self.transfers.update_status(tx, transfer.id, transfer.status, transfer.failure_reason)
            return transfer


def _compute_request_hash(from_wallet_id: str, to_wallet_id: str, amount: int) -> str:
    raw = f"{len(from_wallet_id)}:{from_wallet_id},{len(to_wallet_id)}:{to_wallet_id},{amount}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
