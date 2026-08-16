"""Mirrors internal/service/service_integration_test.go against a real
Postgres instance."""

import pytest

from app.domain.errors import (
    ErrIdempotencyKeyConflict,
    ErrInvalidAmount,
    ErrSameWallet,
    ErrWalletNotFound,
)
from app.domain.transfer import TransferStatus
from app.repository.db import Store
from app.service.transfer_service import CreateTransferRequest, TransferService

from .conftest import scan_one, seed_wallet


def _service(store: Store) -> TransferService:
    return TransferService(store)


def test_sufficient_balance_processes(store):
    seed_wallet(store, "wallet_1", 500)
    seed_wallet(store, "wallet_2", 0)
    svc = _service(store)

    transfer = svc.create_transfer(
        CreateTransferRequest("key-sufficient", "wallet_1", "wallet_2", 200)
    )

    assert transfer.status == TransferStatus.PROCESSED
    assert scan_one(store, "SELECT balance FROM wallets WHERE id = %s", ("wallet_1",))[0] == 300
    assert scan_one(store, "SELECT balance FROM wallets WHERE id = %s", ("wallet_2",))[0] == 200
    assert (
        scan_one(store, "SELECT COUNT(*) FROM ledger_entries WHERE transfer_id = %s", (transfer.id,))[0]
        == 2
    )


def test_insufficient_balance_fails(store):
    seed_wallet(store, "wallet_1", 50)
    seed_wallet(store, "wallet_2", 0)
    svc = _service(store)

    transfer = svc.create_transfer(
        CreateTransferRequest("key-insufficient", "wallet_1", "wallet_2", 200)
    )

    assert transfer.status == TransferStatus.FAILED
    assert transfer.failure_reason == "insufficient balance"
    assert scan_one(store, "SELECT balance FROM wallets WHERE id = %s", ("wallet_1",))[0] == 50
    assert scan_one(store, "SELECT balance FROM wallets WHERE id = %s", ("wallet_2",))[0] == 0
    assert (
        scan_one(store, "SELECT COUNT(*) FROM ledger_entries WHERE transfer_id = %s", (transfer.id,))[0]
        == 0
    )


def test_same_wallet_rejected(store):
    seed_wallet(store, "wallet_1", 100)
    svc = _service(store)

    with pytest.raises(ErrSameWallet):
        svc.create_transfer(CreateTransferRequest("key-same-wallet", "wallet_1", "wallet_1", 50))

    assert scan_one(store, "SELECT COUNT(*) FROM transfers")[0] == 0


def test_unknown_wallet_rejected(store):
    seed_wallet(store, "wallet_1", 100)
    svc = _service(store)

    with pytest.raises(ErrWalletNotFound):
        svc.create_transfer(
            CreateTransferRequest("key-unknown-wallet", "wallet_1", "does-not-exist", 50)
        )

    assert scan_one(store, "SELECT COUNT(*) FROM transfers")[0] == 0


@pytest.mark.parametrize("amount", [0, -50], ids=["zero amount", "negative amount"])
def test_non_positive_amount_rejected(store, amount):
    seed_wallet(store, "wallet_1", 100)
    seed_wallet(store, "wallet_2", 0)
    svc = _service(store)

    with pytest.raises(ErrInvalidAmount):
        svc.create_transfer(CreateTransferRequest(f"key-{amount}", "wallet_1", "wallet_2", amount))


def test_idempotent_replay_same_body(store):
    seed_wallet(store, "wallet_1", 500)
    seed_wallet(store, "wallet_2", 0)
    svc = _service(store)
    req = CreateTransferRequest("key-replay", "wallet_1", "wallet_2", 100)

    first = svc.create_transfer(req)
    second = svc.create_transfer(req)

    assert second.id == first.id
    assert second.status == TransferStatus.PROCESSED
    assert scan_one(store, "SELECT balance FROM wallets WHERE id = %s", ("wallet_1",))[0] == 400
    assert (
        scan_one(store, "SELECT COUNT(*) FROM ledger_entries WHERE transfer_id = %s", (first.id,))[0]
        == 2
    )


def test_idempotency_conflict_different_body(store):
    seed_wallet(store, "wallet_1", 500)
    seed_wallet(store, "wallet_2", 0)
    svc = _service(store)
    key = "key-conflict"

    svc.create_transfer(CreateTransferRequest(key, "wallet_1", "wallet_2", 100))

    with pytest.raises(ErrIdempotencyKeyConflict):
        svc.create_transfer(CreateTransferRequest(key, "wallet_1", "wallet_2", 999))

    assert scan_one(store, "SELECT COUNT(*) FROM transfers")[0] == 1


def test_idempotent_replay_failed_transfer(store):
    """Replaying the same key for a transfer that resolved to FAILED
    (insufficient balance) must return the same FAILED transfer again, not
    attempt to reprocess it or return an error."""
    seed_wallet(store, "wallet_1", 50)
    seed_wallet(store, "wallet_2", 0)
    svc = _service(store)
    req = CreateTransferRequest("key-replay-failed", "wallet_1", "wallet_2", 200)

    first = svc.create_transfer(req)
    assert first.status == TransferStatus.FAILED

    second = svc.create_transfer(req)

    assert second.id == first.id
    assert second.status == TransferStatus.FAILED
    assert second.failure_reason == "insufficient balance"
    assert scan_one(store, "SELECT balance FROM wallets WHERE id = %s", ("wallet_1",))[0] == 50
    assert scan_one(store, "SELECT balance FROM wallets WHERE id = %s", ("wallet_2",))[0] == 0
    assert scan_one(store, "SELECT COUNT(*) FROM transfers")[0] == 1
