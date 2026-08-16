"""WalletService.create_wallet against a real Postgres instance."""

import pytest

from app.domain.errors import ErrWalletAlreadyExists
from app.repository.db import Store
from app.service.wallet_service import WalletService

from .conftest import scan_one


def _service(store: Store) -> WalletService:
    return WalletService(store)


def test_create_wallet_persists_balance(store):
    svc = _service(store)

    wallet = svc.create_wallet("wallet_new", 250)

    assert wallet.balance == 250
    row = scan_one(store, "SELECT balance FROM wallets WHERE id = %s", ("wallet_new",))
    assert row[0] == 250


def test_create_wallet_defaults_to_zero(store):
    svc = _service(store)

    wallet = svc.create_wallet("wallet_zero", 0)

    assert wallet.balance == 0
    row = scan_one(store, "SELECT balance FROM wallets WHERE id = %s", ("wallet_zero",))
    assert row[0] == 0


def test_create_wallet_duplicate_id_rejected(store):
    svc = _service(store)
    svc.create_wallet("wallet_dup", 100)

    with pytest.raises(ErrWalletAlreadyExists):
        svc.create_wallet("wallet_dup", 999)

    row = scan_one(store, "SELECT COUNT(*) FROM wallets WHERE id = %s", ("wallet_dup",))
    assert row[0] == 1
