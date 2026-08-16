"""Mirrors internal/handler/handler_test.go: exercises the Flask handler
against a fake TransferService, without touching a real database.
"""

import uuid
from datetime import datetime, timezone

import pytest
from flask import Flask

from app.domain import errors as domain_errors
from app.domain.transfer import Transfer, TransferStatus
from app.handler.transfer_handler import bp


class FakeTransferService:
    def __init__(self, transfer: Transfer = None, err: Exception = None):
        self.transfer = transfer
        self.err = err

    def create_transfer(self, req):
        if self.err is not None:
            raise self.err
        return self.transfer


def make_client(fake_service):
    app = Flask(__name__)
    app.extensions["transfer_service"] = fake_service
    app.register_blueprint(bp)
    return app.test_client()


@pytest.mark.parametrize(
    "body",
    [
        '{"idempotencyKey":',  # malformed JSON
        '{"idempotencyKey":"k1","fromWalletId":"a","toWalletId":"b","amount":"abc"}',  # non-numeric amount
        '{"fromWalletId":"a","toWalletId":"b","amount":100}',  # missing idempotencyKey
        '{"idempotencyKey":"k1","toWalletId":"b","amount":100}',  # missing fromWalletId
        '{"idempotencyKey":"k1","fromWalletId":"a","amount":100}',  # missing toWalletId
        '{"idempotencyKey":"k1","fromWalletId":"a","toWalletId":"a","amount":100}',  # same wallet
        '{"idempotencyKey":"k1","fromWalletId":"a","toWalletId":"b","amount":0}',  # zero amount
        '{"idempotencyKey":"k1","fromWalletId":"a","toWalletId":"b","amount":-1}',  # negative amount
    ],
    ids=[
        "malformed JSON",
        "non-numeric amount",
        "missing idempotencyKey",
        "missing fromWalletId",
        "missing toWalletId",
        "same wallet",
        "zero amount",
        "negative amount",
    ],
)
def test_create_transfer_validation_errors(body):
    client = make_client(FakeTransferService())
    resp = client.post("/transfers", data=body, content_type="application/json")
    assert resp.status_code == 400, resp.get_data(as_text=True)


@pytest.mark.parametrize(
    "err,want_status",
    [
        (domain_errors.ErrWalletNotFound(), 404),
        (domain_errors.ErrIdempotencyKeyConflict(), 409),
        (RuntimeError("boom"), 500),
    ],
    ids=["wallet not found", "idempotency conflict", "unexpected error"],
)
def test_create_transfer_service_error_mapping(err, want_status):
    valid_body = '{"idempotencyKey":"k1","fromWalletId":"wallet_1","toWalletId":"wallet_2","amount":100}'
    client = make_client(FakeTransferService(err=err))
    resp = client.post("/transfers", data=valid_body, content_type="application/json")
    assert resp.status_code == want_status, resp.get_data(as_text=True)


def test_create_transfer_success():
    transfer_id = uuid.uuid4()
    transfer = Transfer(
        id=transfer_id,
        from_wallet_id="wallet_1",
        to_wallet_id="wallet_2",
        amount=100,
        status=TransferStatus.PROCESSED,
        failure_reason=None,
        created_at=datetime(2026, 7, 4, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 4, 10, 0, 0, tzinfo=timezone.utc),
    )
    client = make_client(FakeTransferService(transfer=transfer))

    resp = client.post(
        "/transfers",
        data='{"idempotencyKey":"k1","fromWalletId":"wallet_1","toWalletId":"wallet_2","amount":100}',
        content_type="application/json",
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)

    got = resp.get_json()
    assert got["transferId"] == str(transfer_id)
    assert got["status"] == "PROCESSED"
    assert got["fromWalletId"] == "wallet_1"
    assert got["toWalletId"] == "wallet_2"
    assert got["failureReason"] is None


def test_create_transfer_business_failure_returns_201():
    """A business failure (e.g. insufficient balance) is still a
    successfully-created transfer resource: the outcome lives in
    status/failureReason, not the HTTP status code."""
    transfer = Transfer(
        id=uuid.uuid4(),
        from_wallet_id="wallet_1",
        to_wallet_id="wallet_2",
        amount=100,
        status=TransferStatus.FAILED,
        failure_reason="insufficient balance",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    client = make_client(FakeTransferService(transfer=transfer))

    resp = client.post(
        "/transfers",
        data='{"idempotencyKey":"k1","fromWalletId":"wallet_1","toWalletId":"wallet_2","amount":100}',
        content_type="application/json",
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)

    got = resp.get_json()
    assert got["status"] == "FAILED"
    assert got["failureReason"] == "insufficient balance"


def test_health_check():
    client = make_client(FakeTransferService())
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}
