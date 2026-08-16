"""Domain errors, mirroring internal/domain/errors.go.

Each is a distinct exception type (rather than one exception with a string
code) so handler-layer error mapping can dispatch on type, the same way the
Go handler dispatches on errors.Is.
"""


class DomainError(Exception):
    """Base class for all domain errors."""


class ErrSameWallet(DomainError):
    def __init__(self):
        super().__init__("cannot transfer to the same wallet")


class ErrInvalidAmount(DomainError):
    def __init__(self):
        super().__init__("transfer amount must be greater than zero")


class ErrInvalidTransition(DomainError):
    def __init__(self):
        super().__init__("invalid state transition")


class ErrIdempotencyKeyRequired(DomainError):
    def __init__(self):
        super().__init__("idempotencyKey is required")


class ErrWalletIdRequired(DomainError):
    def __init__(self):
        super().__init__("WalletId cannot be empty")


class ErrWalletNotFound(DomainError):
    def __init__(self):
        super().__init__("wallet not found")


class ErrInvalidBalance(DomainError):
    def __init__(self):
        super().__init__("initial balance must be zero or greater")


class ErrWalletAlreadyExists(DomainError):
    def __init__(self):
        super().__init__("a wallet with this id already exists")


class ErrIdempotencyKeyConflict(DomainError):
    def __init__(self):
        super().__init__(
            "idempotency key conflict: a transfer with the same idempotency key already exists"
        )


class ErrIdempotencyRecordNotFound(DomainError):
    def __init__(self):
        super().__init__("idempotency record not found")


class ErrTransferNotFound(DomainError):
    def __init__(self):
        super().__init__("transfer not found")
