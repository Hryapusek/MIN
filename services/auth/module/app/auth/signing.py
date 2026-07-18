from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from app.auth.types import SigningBackend


class AccessTokenSigner(ABC):
    """Boundary between OAuth token issuance and the signing implementation.

    Both implementations must eventually produce the same JWT access-token
    format. Only the place where the private-key operation happens differs.
    """

    backend: SigningBackend

    @abstractmethod
    async def sign(self, claims: Mapping[str, Any], *, key_id: str) -> str:
        """Return a signed access token for the supplied claims."""
        raise NotImplementedError


class LocalAccessTokenSigner(AccessTokenSigner):
    """Development signer using a locally supplied private key.

    The private key should later come from an environment variable, mounted
    secret, or protected file. It must not be stored in the application DB.
    """

    backend = SigningBackend.LOCAL

    async def sign(self, claims: Mapping[str, Any], *, key_id: str) -> str:
        raise NotImplementedError("Local JWT signing will be implemented in a later batch")


class VaultTransitAccessTokenSigner(AccessTokenSigner):
    """Production-oriented signer delegating the private operation to Vault Transit."""

    backend = SigningBackend.VAULT

    async def sign(self, claims: Mapping[str, Any], *, key_id: str) -> str:
        raise NotImplementedError("Vault Transit JWT signing will be implemented in a later batch")
