"""Entrypoint that starts the wallet transfer HTTP API, mirroring
cmd/server/main.go. Run with: python run.py
"""

from app import create_app
from app.config import Config

if __name__ == "__main__":
    cfg = Config.load()
    app = create_app(cfg)
    app.run(host="0.0.0.0", port=int(cfg.server_port))
