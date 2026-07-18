"""Authentication-domain interfaces.

Concrete token signing and OAuth flows are intentionally left for later batches.
"""

from app.auth.signing import AccessTokenSigner, LocalAccessTokenSigner, VaultTransitAccessTokenSigner
from app.auth.types import SigningBackend

__all__ = [
    "AccessTokenSigner",
    "LocalAccessTokenSigner",
    "SigningBackend",
    "VaultTransitAccessTokenSigner",
]
