"""HTTP layer for /transfers, mirroring internal/handler/handler.go and
router.go. Stays thin: request validation and transport mapping only, no
business logic.
"""

from flask import Blueprint, jsonify, request

from ..domain import errors as domain_errors
from ..service.transfer_service import CreateTransferRequest, TransferService

bp = Blueprint("transfers", __name__)


def _service() -> TransferService:
    from flask import current_app

    return current_app.extensions["transfer_service"]


@bp.get("/healthz")
def health_check():
    return jsonify({"status": "ok"}), 200


@bp.post("/transfers")
def create_transfer():
    body = request.get_json(silent=True)
    if body is None:
        return _error(400, "malformed request body")

    idempotency_key = body.get("idempotencyKey") or ""
    from_wallet_id = body.get("fromWalletId") or ""
    to_wallet_id = body.get("toWalletId") or ""
    amount = body.get("amount")

    if not idempotency_key:
        return _error(400, domain_errors.ErrIdempotencyKeyRequired().args[0])
    if not from_wallet_id or not to_wallet_id:
        return _error(400, domain_errors.ErrWalletIdRequired().args[0])
    if from_wallet_id == to_wallet_id:
        return _error(400, domain_errors.ErrSameWallet().args[0])
    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
        return _error(400, domain_errors.ErrInvalidAmount().args[0])

    req = CreateTransferRequest(
        idempotency_key=idempotency_key,
        from_wallet_id=from_wallet_id,
        to_wallet_id=to_wallet_id,
        amount=amount,
    )

    try:
        transfer = _service().create_transfer(req)
    except domain_errors.DomainError as err:
        return _domain_error_response(err)

    return (
        jsonify(
            {
                "transferId": str(transfer.id),
                "status": transfer.status.value,
                "fromWalletId": transfer.from_wallet_id,
                "toWalletId": transfer.to_wallet_id,
                "amount": transfer.amount,
                "failureReason": transfer.failure_reason,
                "createdAt": transfer.created_at.isoformat(),
            }
        ),
        201,
    )


def _domain_error_response(err: domain_errors.DomainError):
    if isinstance(
        err,
        (
            domain_errors.ErrSameWallet,
            domain_errors.ErrInvalidAmount,
            domain_errors.ErrWalletIdRequired,
            domain_errors.ErrIdempotencyKeyRequired,
        ),
    ):
        return _error(400, str(err))
    if isinstance(err, domain_errors.ErrWalletNotFound):
        return _error(404, str(err))
    if isinstance(err, domain_errors.ErrIdempotencyKeyConflict):
        return _error(409, str(err))
    return _error(500, "internal server error")


def _error(status: int, message: str):
    return jsonify({"error": message}), status
