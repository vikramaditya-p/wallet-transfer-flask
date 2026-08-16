"""Application factory, mirroring cmd/server/main.go's wiring."""

from flask import Flask

from .config import Config
from .handler.transfer_handler import bp as transfers_bp
from .handler.wallet_handler import bp as wallets_bp
from .repository.db import Store
from .service.transfer_service import TransferService
from .service.wallet_service import WalletService


def create_app(
    config: Config = None,
    store: Store = None,
    transfer_service: TransferService = None,
    wallet_service: WalletService = None,
) -> Flask:
    app = Flask(__name__)

    cfg = config or Config.load()
    store = store or Store(cfg.dsn())
    transfer_service = transfer_service or TransferService(store)
    wallet_service = wallet_service or WalletService(store)

    app.extensions["transfer_service"] = transfer_service
    app.extensions["wallet_service"] = wallet_service
    app.extensions["store"] = store

    app.register_blueprint(transfers_bp)
    app.register_blueprint(wallets_bp)

    return app
