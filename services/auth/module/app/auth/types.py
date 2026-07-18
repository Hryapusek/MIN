from enum import Enum


class SigningBackend(str, Enum):
    """Where the private signing operation is performed."""

    LOCAL = "local"
    VAULT = "vault"
