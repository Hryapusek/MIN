from abc import ABC, abstractmethod
from dataclasses import dataclass

from messenger.shared.signing.types import SigningBackend, SigningKeyPurpose


@dataclass(frozen=True, slots=True)
class SigningKeyDescriptor:
    """Public and routing metadata discovered by the key manager."""

    provider_name: str
    backend: SigningBackend
    external_reference: str
    provider_version: int
    purpose: SigningKeyPurpose
    algorithm: str
    public_key_pem: str


@dataclass(frozen=True, slots=True)
class SigningRequest:
    """An explicit runtime signing request.

    The caller chooses the exact provider key. The signer does not query
    lifecycle state or decide which key is active.
    """

    provider_name: str
    external_reference: str
    provider_version: int
    algorithm: str
    signing_input: bytes


@dataclass(frozen=True, slots=True)
class SignatureResult:
    provider_name: str
    external_reference: str
    provider_version: int
    algorithm: str
    signature: bytes


class KeyDiscoveryProvider(ABC):
    """Lists public descriptors for keys visible to one backend."""

    provider_name: str
    backend: SigningBackend

    @abstractmethod
    async def list_keys(self) -> list[SigningKeyDescriptor]:
        raise NotImplementedError


class RuntimeSigner(ABC):
    """Signs bytes with a caller-selected provider key version."""

    provider_name: str
    backend: SigningBackend

    @abstractmethod
    async def sign(self, request: SigningRequest) -> SignatureResult:
        raise NotImplementedError
