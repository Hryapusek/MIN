import asyncio
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.auth.key_utils import rsa_public_key_to_jwk
from app.auth.local_keys import (
    LocalFileSigningProvider,
    LocalKeyBootstrapper,
    LocalKeyNotFoundError,
    LocalKeyRing,
)
from app.auth.types import LocalKeyBootstrapPolicy


def test_local_bootstrap_is_persistent_and_signs(tmp_path: Path) -> None:
    key_ring = LocalKeyRing(tmp_path, strict_permissions=True)
    bootstrapper = LocalKeyBootstrapper(
        key_ring=key_ring,
        policy=LocalKeyBootstrapPolicy.GENERATE_IF_EMPTY,
    )

    first = bootstrapper.ensure_ready()
    second = bootstrapper.ensure_ready()

    assert first.generated is True
    assert second.generated is False

    provider = LocalFileSigningProvider(provider_name="local-primary", key_ring=key_ring)
    [descriptor] = asyncio.run(provider.list_keys())
    jwk = rsa_public_key_to_jwk(descriptor.public_key_pem, algorithm=descriptor.algorithm)
    assert jwk["kid"]

    signing_input = b"header.payload"
    signature = asyncio.run(
        provider.sign(
            signing_input,
            external_reference=descriptor.external_reference,
            provider_version=descriptor.provider_version,
            algorithm=descriptor.algorithm,
        )
    )

    public_key = serialization.load_pem_public_key(descriptor.public_key_pem.encode("ascii"))
    public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())


def test_require_existing_rejects_empty_directory(tmp_path: Path) -> None:
    with pytest.raises(LocalKeyNotFoundError):
        LocalKeyBootstrapper(
            key_ring=LocalKeyRing(tmp_path),
            policy=LocalKeyBootstrapPolicy.REQUIRE_EXISTING,
        ).ensure_ready()
