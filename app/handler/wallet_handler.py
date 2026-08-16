"""HTTP layer for /wallets. Stays thin: request validation and transport
mapping only, no business logic — same rule as transfer_handler.py.
"""

from flask import Blueprint, jsonify, request

from ..domain import errors as domain_errors
from ..service.wallet_service import WalletService

bp = Blueprint("wallets", __name__)


def _service() -> WalletService:
    from flask import current_app

    return current_app.extensions["wallet_service"]


@bp.post("/wallets")
def create_wallet():
    body = request.get_json(silent=True)
    if body is None:
        return _error(400, "malformed request body")

    wallet_id = body.get("id") or ""
    balance = body.get("balance", 0)

    if not wallet_id:
        return _error(400, domain_errors.ErrWalletIdRequired().args[0])
    if not isinstance(balance, int) or isinstance(balance, bool) or balance < 0:
        return _error(400, domain_errors.ErrInvalidBalance().args[0])

    try:
        wallet = _service().create_wallet(wallet_id, balance)
    except domain_errors.ErrWalletAlreadyExists as err:
        return _error(409, str(err))
    except domain_errors.DomainError as err:
        return _error(400, str(err))

    return (
        jsonify(
            {
                "id": wallet.id,
                "balance": wallet.balance,
                "createdAt": wallet.created_at.isoformat(),
            }
        ),
        201,
    )


def _error(status: int, message: str):
    return jsonify({"error": message}), status
