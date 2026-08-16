"""Mirrors internal/domain/transfer_test.go."""

import uuid

import pytest

from app.domain.errors import (
    ErrInvalidAmount,
    ErrInvalidTransition,
    ErrSameWallet,
    ErrWalletIdRequired,
)
from app.domain.transfer import Transfer, TransferStatus


def test_new_pending_transfer():
    transfer_id = uuid.uuid4()
    transfer = Transfer.new_pending(transfer_id, "wallet_1", "wallet_2", 100)

    assert transfer.id == transfer_id
    assert transfer.from_wallet_id == "wallet_1"
    assert transfer.to_wallet_id == "wallet_2"
    assert transfer.amount == 100
    assert transfer.status == TransferStatus.PENDING
    assert transfer.failure_reason is None


@pytest.mark.parametrize(
    "from_wallet_id,to_wallet_id,amount,want_err",
    [
        ("", "wallet_2", 100, ErrWalletIdRequired),
        ("wallet_1", "", 100, ErrWalletIdRequired),
        ("wallet_1", "wallet_1", 100, ErrSameWallet),
        ("wallet_1", "wallet_2", 0, ErrInvalidAmount),
        ("wallet_1", "wallet_2", -100, ErrInvalidAmount),
    ],
    ids=[
        "empty from wallet id",
        "empty to wallet id",
        "same wallet",
        "zero amount",
        "negative amount",
    ],
)
def test_new_pending_transfer_validation(from_wallet_id, to_wallet_id, amount, want_err):
    with pytest.raises(want_err):
        Transfer.new_pending(uuid.uuid4(), from_wallet_id, to_wallet_id, amount)


@pytest.mark.parametrize(
    "start_status,want_err,want_status",
    [
        (TransferStatus.PENDING, None, TransferStatus.PROCESSED),
        (TransferStatus.PROCESSED, ErrInvalidTransition, TransferStatus.PROCESSED),
        (TransferStatus.FAILED, ErrInvalidTransition, TransferStatus.FAILED),
    ],
    ids=["from pending succeeds", "from processed", "from failed rejected"],
)
def test_mark_processed(start_status, want_err, want_status):
    transfer = Transfer.new_pending(uuid.uuid4(), "wallet_1", "wallet_2", 100)
    transfer.status = start_status

    if want_err is not None:
        with pytest.raises(want_err):
            transfer.mark_processed()
    else:
        transfer.mark_processed()

    assert transfer.status == want_status


@pytest.mark.parametrize(
    "start_status,reason,want_err,want_status,want_reason",
    [
        (TransferStatus.PENDING, "insufficient funds", None, TransferStatus.FAILED, "insufficient funds"),
        (TransferStatus.PENDING, "", None, TransferStatus.FAILED, "unspecified"),
        (TransferStatus.PROCESSED, "insufficient funds", ErrInvalidTransition, TransferStatus.PROCESSED, None),
        (TransferStatus.FAILED, "insufficient funds", ErrInvalidTransition, TransferStatus.FAILED, None),
    ],
    ids=[
        "from pending with reason succeeds",
        "from pending with empty reason defaults",
        "from processed rejected",
        "from failed rejected",
    ],
)
def test_mark_failed(start_status, reason, want_err, want_status, want_reason):
    transfer = Transfer.new_pending(uuid.uuid4(), "wallet_1", "wallet_2", 100)
    transfer.status = start_status

    if want_err is not None:
        with pytest.raises(want_err):
            transfer.mark_failed(reason)
        assert transfer.failure_reason is None
    else:
        transfer.mark_failed(reason)
        assert transfer.failure_reason == want_reason

    assert transfer.status == want_status
