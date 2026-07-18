from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.auth.types import SigningBackend, SigningKeyPurpose


@dataclass(frozen=True, slots=True)
class SigningKeyDescriptor:
    """Public description of one provider-owned signing-key version.

    The descriptor deliberately contains no private material. PostgreSQL stores
    a normalized version of this data, while the provider remains the source of
    truth for the private signing operation.
    """

    provider_name: str
    backend: SigningBackend
    external_reference: str
    provider_version: int
    purpose: SigningKeyPurpose
    algorithm: str
    public_key_pem: str


@dataclass(frozen=True, slots=True)
class SignatureResult:
    kid: str
    algorithm: str
    signature: bytes


class SigningProvider(ABC):
    """Provider boundary shared by local files and Vault Transit."""

    provider_name: str
    backend: SigningBackend

    @abstractmethod
    async def list_keys(self) -> list[SigningKeyDescriptor]:
        """Return all key versions currently visible to this provider."""
        raise NotImplementedError

    @abstractmethod
    async def sign(
        self,
        signing_input: bytes,
        *,
        external_reference: str,
        provider_version: int,
        algorithm: str,
    ) -> bytes:
        """Sign bytes with an explicitly selected provider key version."""
        raise NotImplementedError


class VaultTransitSigningProvider(SigningProvider):
    """Reserved Vault Transit implementation boundary.

    Keeping the stub behind the same provider contract lets the registry and
    OAuth/JWT layer remain unchanged when Vault support is added.
    """

    backend = SigningBackend.VAULT

    def __init__(self, *, provider_name: str) -> None:
        self.provider_name = provider_name

    async def list_keys(self) -> list[SigningKeyDescriptor]:
        raise NotImplementedError("Vault Transit key discovery is not implemented yet")

    async def sign(
        self,
        signing_input: bytes,
        *,
        external_reference: str,
        provider_version: int,
        algorithm: str,
    ) -> bytes:
        raise NotImplementedError("Vault Transit signing is not implemented yet")
