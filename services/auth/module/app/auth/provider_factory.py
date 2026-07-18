from dataclasses import dataclass

from app.auth.local_keys import LocalFileSigningProvider, LocalKeyBootstrapResult, LocalKeyBootstrapper, LocalKeyRing
from app.auth.signing import SigningProvider, VaultTransitSigningProvider
from app.auth.types import SigningBackend
from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class ConfiguredSigningProvider:
    provider: SigningProvider
    bootstrap_result: LocalKeyBootstrapResult | None


def build_configured_signing_provider(
    settings: Settings,
    *,
    run_bootstrap: bool = True,
) -> ConfiguredSigningProvider:
    if settings.token_signing_backend == SigningBackend.LOCAL:
        key_ring = LocalKeyRing(
            settings.resolved_local_signing_key_directory,
            strict_permissions=settings.local_signing_strict_permissions,
        )
        bootstrap_result = None
        if run_bootstrap:
            bootstrap_result = LocalKeyBootstrapper(
                key_ring=key_ring,
                policy=settings.local_key_bootstrap_policy,
                rsa_key_size=settings.local_rsa_key_size,
            ).ensure_ready()

        return ConfiguredSigningProvider(
            provider=LocalFileSigningProvider(
                provider_name=settings.signing_provider_name,
                key_ring=key_ring,
            ),
            bootstrap_result=bootstrap_result,
        )

    if settings.token_signing_backend == SigningBackend.VAULT:
        return ConfiguredSigningProvider(
            provider=VaultTransitSigningProvider(provider_name=settings.signing_provider_name),
            bootstrap_result=None,
        )

    raise ValueError(f"unsupported signing backend: {settings.token_signing_backend}")
