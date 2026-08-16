"""Mirrors internal/domain/ledger_test.go."""

import uuid

from app.domain.ledger import LedgerEntryType, new_ledger_pair


def test_new_ledger_pair():
    transfer_id = uuid.uuid4()
    debit, credit = new_ledger_pair(transfer_id, "wallet_1", "wallet_2", 100)

    assert debit.transfer_id == transfer_id
    assert debit.wallet_id == "wallet_1"
    assert debit.type == LedgerEntryType.DEBIT
    assert debit.amount == 100

    assert credit.transfer_id == transfer_id
    assert credit.wallet_id == "wallet_2"
    assert credit.type == LedgerEntryType.CREDIT
    assert credit.amount == 100

    assert debit.id != credit.id
