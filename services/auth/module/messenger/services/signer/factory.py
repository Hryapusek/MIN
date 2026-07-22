from pathlib import Path
from typing import Protocol

from messenger.services.signer.providers import LocalRuntimeSigner, VaultRuntimeSigner
from messenger.shared.signing.contracts import RuntimeSigner
from messenger.shared.signing.local_key_ring import LocalKeyRing
from messenger.shared.signing.types import SigningBackend


class RuntimeSignerSettings(Protocol):
    """Small configuration surface required by the signer composition root."""

    token_signing_backend: SigningBackend
    signing_provider_name: str
    local_signing_strict_permissions: bool

    @property
    def resolved_local_signing_key_directory(self) -> Path: ...


def build_configured_runtime_signer(settings: RuntimeSignerSettings) -> RuntimeSigner:
    if settings.token_signing_backend == SigningBackend.LOCAL:
        return LocalRuntimeSigner(
            provider_name=settings.signing_provider_name,
            key_ring=LocalKeyRing(
                settings.resolved_local_signing_key_directory,
                strict_permissions=settings.local_signing_strict_permissions,
            ),
        )

    if settings.token_signing_backend == SigningBackend.VAULT:
        return VaultRuntimeSigner(provider_name=settings.signing_provider_name)

    raise ValueError(f"unsupported signing backend: {settings.token_signing_backend}")
