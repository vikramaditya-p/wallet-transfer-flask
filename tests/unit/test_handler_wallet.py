"""Exercises the Flask wallet handler against a fake WalletService, without
touching a real database — same pattern as test_handler_transfer.py.
"""

from datetime import datetime, timezone

import pytest
from flask import Flask

from app.domain import errors as domain_errors
from app.domain.wallet import Wallet
from app.handler.wallet_handler import bp


class FakeWalletService:
    def __init__(self, wallet: Wallet = None, err: Exception = None):
        self.wallet = wallet
        self.err = err

    def create_wallet(self, wallet_id, balance):
        if self.err is not None:
            raise self.err
        return self.wallet


def make_client(fake_service):
    app = Flask(__name__)
    app.extensions["wallet_service"] = fake_service
    app.register_blueprint(bp)
    return app.test_client()


@pytest.mark.parametrize(
    "body",
    [
        '{"id":',  # malformed JSON
        '{"balance": 100}',  # missing id
        '{"id": "wallet_1", "balance": -1}',  # negative balance
        '{"id": "wallet_1", "balance": "abc"}',  # non-numeric balance
    ],
    ids=["malformed JSON", "missing id", "negative balance", "non-numeric balance"],
)
def test_create_wallet_validation_errors(body):
    client = make_client(FakeWalletService())
    resp = client.post("/wallets", data=body, content_type="application/json")
    assert resp.status_code == 400, resp.get_data(as_text=True)


def test_create_wallet_conflict():
    client = make_client(FakeWalletService(err=domain_errors.ErrWalletAlreadyExists()))
    resp = client.post(
        "/wallets", data='{"id": "wallet_1", "balance": 100}', content_type="application/json"
    )
    assert resp.status_code == 409, resp.get_data(as_text=True)


def test_create_wallet_success():
    wallet = Wallet(
        id="wallet_1",
        balance=100,
        created_at=datetime(2026, 8, 16, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 8, 16, 10, 0, 0, tzinfo=timezone.utc),
    )
    client = make_client(FakeWalletService(wallet=wallet))

    resp = client.post(
        "/wallets", data='{"id": "wallet_1", "balance": 100}', content_type="application/json"
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)

    got = resp.get_json()
    assert got["id"] == "wallet_1"
    assert got["balance"] == 100


def test_create_wallet_zero_balance_defaults():
    wallet = Wallet(id="wallet_1", balance=0, created_at=datetime.now(timezone.utc))
    client = make_client(FakeWalletService(wallet=wallet))

    resp = client.post("/wallets", data='{"id": "wallet_1"}', content_type="application/json")
    assert resp.status_code == 201, resp.get_data(as_text=True)
