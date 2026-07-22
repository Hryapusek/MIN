from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from messenger.shared.signing.contracts import RuntimeSigner, SignatureResult, SigningRequest
from messenger.shared.signing.local_key_ring import LocalKeyConfigurationError, LocalKeyRing, SUPPORTED_LOCAL_ALGORITHM
from messenger.shared.signing.types import SigningBackend


class LocalRuntimeSigner(RuntimeSigner):
    backend = SigningBackend.LOCAL

    def __init__(self, *, provider_name: str, key_ring: LocalKeyRing) -> None:
        if not provider_name:
            raise ValueError("provider_name cannot be empty")
        self.provider_name = provider_name
        self.key_ring = key_ring

    async def sign(self, request: SigningRequest) -> SignatureResult:
        if request.provider_name != self.provider_name:
            raise LocalKeyConfigurationError(
                f"request targets provider {request.provider_name!r}, not {self.provider_name!r}"
            )
        if request.algorithm != SUPPORTED_LOCAL_ALGORITHM:
            raise LocalKeyConfigurationError(f"unsupported local signing algorithm: {request.algorithm}")

        entry = self.key_ring.find_entry(request.external_reference, request.provider_version)
        if entry.algorithm != request.algorithm:
            raise LocalKeyConfigurationError(
                f"requested algorithm {request.algorithm} does not match key algorithm {entry.algorithm}"
            )

        private_key = self.key_ring.read_private_key(entry)
        signature = private_key.sign(request.signing_input, padding.PKCS1v15(), hashes.SHA256())
        return SignatureResult(
            provider_name=self.provider_name,
            external_reference=entry.reference,
            provider_version=entry.version,
            algorithm=entry.algorithm,
            signature=signature,
        )


class VaultRuntimeSigner(RuntimeSigner):
    """Future Vault Transit runtime signer; no HTTP implementation yet."""

    backend = SigningBackend.VAULT

    def __init__(self, *, provider_name: str) -> None:
        self.provider_name = provider_name

    async def sign(self, request: SigningRequest) -> SignatureResult:
        raise NotImplementedError("Vault Transit signing is not implemented yet")
