"""Mirrors internal/domain/wallet_test.go."""

import pytest

from app.domain.errors import ErrInvalidBalance, ErrWalletIdRequired
from app.domain.wallet import Wallet


def test_has_sufficient_funds_true():
    wallet = Wallet(id="wallet_1", balance=100)
    assert wallet.has_sufficient_funds(100) is True
    assert wallet.has_sufficient_funds(50) is True


def test_has_sufficient_funds_false():
    wallet = Wallet(id="wallet_1", balance=100)
    assert wallet.has_sufficient_funds(101) is False


def test_new_wallet():
    wallet = Wallet.new("wallet_1", 100)
    assert wallet.id == "wallet_1"
    assert wallet.balance == 100
    assert wallet.created_at is not None
    assert wallet.updated_at is not None


def test_new_wallet_zero_balance_allowed():
    wallet = Wallet.new("wallet_1", 0)
    assert wallet.balance == 0


@pytest.mark.parametrize(
    "wallet_id,balance,want_err",
    [
        ("", 100, ErrWalletIdRequired),
        ("wallet_1", -1, ErrInvalidBalance),
    ],
    ids=["empty id", "negative balance"],
)
def test_new_wallet_validation(wallet_id, balance, want_err):
    with pytest.raises(want_err):
        Wallet.new(wallet_id, balance)
