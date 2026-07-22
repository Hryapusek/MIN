import asyncio
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from messenger.services.key_manager.providers import LocalKeyBootstrapper, LocalKeyDiscoveryProvider
from messenger.services.signer.providers import LocalRuntimeSigner
from messenger.shared.signing.contracts import SigningRequest
from messenger.shared.signing.key_utils import rsa_public_key_to_jwk
from messenger.shared.signing.local_key_ring import LocalKeyNotFoundError, LocalKeyRing
from messenger.shared.signing.types import LocalKeyBootstrapPolicy


def _bootstrap(tmp_path: Path) -> LocalKeyRing:
    key_ring = LocalKeyRing(tmp_path, strict_permissions=True)
    LocalKeyBootstrapper(
        key_ring=key_ring,
        policy=LocalKeyBootstrapPolicy.GENERATE_IF_EMPTY,
    ).ensure_ready()
    return key_ring


def test_local_bootstrap_is_persistent(tmp_path: Path) -> None:
    key_ring = LocalKeyRing(tmp_path, strict_permissions=True)
    bootstrapper = LocalKeyBootstrapper(
        key_ring=key_ring,
        policy=LocalKeyBootstrapPolicy.GENERATE_IF_EMPTY,
    )

    first = bootstrapper.ensure_ready()
    private_key_before = key_ring.read_private_key(key_ring.load_entries()[0]).private_numbers()
    second = bootstrapper.ensure_ready()
    private_key_after = key_ring.read_private_key(key_ring.load_entries()[0]).private_numbers()

    assert first.generated is True
    assert second.generated is False
    assert private_key_before == private_key_after


def test_local_discovery_returns_public_descriptor(tmp_path: Path) -> None:
    key_ring = _bootstrap(tmp_path)
    provider = LocalKeyDiscoveryProvider(provider_name="local-primary", key_ring=key_ring)

    [descriptor] = asyncio.run(provider.list_keys())
    jwk = rsa_public_key_to_jwk(descriptor.public_key_pem, algorithm=descriptor.algorithm)

    assert descriptor.provider_name == "local-primary"
    assert descriptor.external_reference == "access-token-001"
    assert descriptor.provider_version == 1
    assert descriptor.algorithm == "RS256"
    assert jwk["kid"]


def test_local_runtime_signer_uses_explicit_key(tmp_path: Path) -> None:
    key_ring = _bootstrap(tmp_path)
    [descriptor] = asyncio.run(
        LocalKeyDiscoveryProvider(provider_name="local-primary", key_ring=key_ring).list_keys()
    )
    signing_input = b"header.payload"

    result = asyncio.run(
        LocalRuntimeSigner(provider_name="local-primary", key_ring=key_ring).sign(
            SigningRequest(
                provider_name="local-primary",
                external_reference=descriptor.external_reference,
                provider_version=descriptor.provider_version,
                algorithm=descriptor.algorithm,
                signing_input=signing_input,
            )
        )
    )

    public_key = serialization.load_pem_public_key(descriptor.public_key_pem.encode("ascii"))
    public_key.verify(result.signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
    assert result.external_reference == descriptor.external_reference
    assert result.provider_version == descriptor.provider_version
    assert result.algorithm == "RS256"


def test_require_existing_rejects_empty_directory(tmp_path: Path) -> None:
    with pytest.raises(LocalKeyNotFoundError):
        LocalKeyBootstrapper(
            key_ring=LocalKeyRing(tmp_path),
            policy=LocalKeyBootstrapPolicy.REQUIRE_EXISTING,
        ).ensure_ready()
