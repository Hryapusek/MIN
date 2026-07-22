from collections.abc import Iterable

from messenger.shared.signing.contracts import RuntimeSigner, SignatureResult, SigningRequest


class SignerNotConfiguredError(RuntimeError):
    pass


class SignerService:
    """Routes explicit signing requests without database access or key policy."""

    def __init__(self, *, signers: Iterable[RuntimeSigner]) -> None:
        signer_list = list(signers)
        self.signers = {signer.provider_name: signer for signer in signer_list}
        if len(self.signers) != len(signer_list):
            raise ValueError("runtime signer provider names must be unique")

    async def sign(self, request: SigningRequest) -> SignatureResult:
        signer = self.signers.get(request.provider_name)
        if signer is None:
            raise SignerNotConfiguredError(f"runtime signer is not configured: {request.provider_name!r}")
        return await signer.sign(request)
