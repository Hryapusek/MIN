from dataclasses import dataclass

from messenger.shared.core.config import Settings
from messenger.services.key_manager.providers import (
    LocalKeyBootstrapper,
    LocalKeyDiscoveryProvider,
    VaultKeyDiscoveryProvider,
)
from messenger.shared.signing.contracts import KeyDiscoveryProvider
from messenger.shared.signing.local_key_ring import LocalKeyRing
from messenger.shared.signing.types import SigningBackend


@dataclass(frozen=True, slots=True)
class ConfiguredKeyManager:
    discovery_provider: KeyDiscoveryProvider
    bootstrapper: LocalKeyBootstrapper | None


def build_configured_key_manager(settings: Settings) -> ConfiguredKeyManager:
    if settings.token_signing_backend == SigningBackend.LOCAL:
        key_ring = LocalKeyRing(
            settings.resolved_local_signing_key_directory,
            strict_permissions=settings.local_signing_strict_permissions,
        )
        return ConfiguredKeyManager(
            discovery_provider=LocalKeyDiscoveryProvider(
                provider_name=settings.signing_provider_name,
                key_ring=key_ring,
            ),
            bootstrapper=LocalKeyBootstrapper(
                key_ring=key_ring,
                policy=settings.local_key_bootstrap_policy,
                rsa_key_size=settings.local_rsa_key_size,
            ),
        )

    if settings.token_signing_backend == SigningBackend.VAULT:
        return ConfiguredKeyManager(
            discovery_provider=VaultKeyDiscoveryProvider(provider_name=settings.signing_provider_name),
            bootstrapper=None,
        )

    raise ValueError(f"unsupported signing backend: {settings.token_signing_backend}")
