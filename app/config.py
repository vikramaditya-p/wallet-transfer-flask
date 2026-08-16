"""Runtime configuration loaded from the environment, mirroring internal/config/config.go."""

import os
from dataclasses import dataclass


def _get_env(key: str, fallback: str) -> str:
    return os.environ.get(key) or fallback


@dataclass
class Config:
    server_port: str
    db_host: str
    db_port: str
    db_user: str
    db_password: str
    db_name: str
    db_sslmode: str

    @classmethod
    def load(cls) -> "Config":
        return cls(
            server_port=_get_env("SERVER_PORT", "8080"),
            db_host=_get_env("DB_HOST", "localhost"),
            db_port=_get_env("DB_PORT", "5432"),
            db_user=_get_env("DB_USER", "wallet"),
            db_password=_get_env("DB_PASSWORD", "wallet"),
            db_name=_get_env("DB_NAME", "wallet_transfer"),
            db_sslmode=_get_env("DB_SSLMODE", "disable"),
        )

    def dsn(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?sslmode={self.db_sslmode}"
        )
