"""Idempotency record entity, mirroring internal/domain/idempotency.go."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class IdempotencyRecord:
    idempotency_key: str
    request_hash: str
    transfer_id: UUID
    created_at: Optional[datetime] = None
