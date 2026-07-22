import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from messenger.shared.signing.contracts import KeyDiscoveryProvider, SigningKeyDescriptor
from messenger.shared.signing.local_key_ring import (
    MANIFEST_FORMAT_VERSION,
    MANIFEST_NAME,
    SUPPORTED_LOCAL_ALGORITHM,
    LocalKeyConfigurationError,
    LocalKeyNotFoundError,
    LocalKeyRing,
)
from messenger.shared.signing.types import LocalKeyBootstrapPolicy, SigningBackend, SigningKeyPurpose


@dataclass(frozen=True, slots=True)
class LocalKeyBootstrapResult:
    generated: bool
    manifest_path: Path
    key_reference: str | None = None
    provider_version: int | None = None


class LocalKeyBootstrapper:
    """Creates the initial local key only when key-manager policy permits it."""

    def __init__(
        self,
        *,
        key_ring: LocalKeyRing,
        policy: LocalKeyBootstrapPolicy,
        rsa_key_size: int = 2048,
    ) -> None:
        if rsa_key_size < 2048:
            raise ValueError("RSA signing keys must be at least 2048 bits")
        self.key_ring = key_ring
        self.policy = policy
        self.rsa_key_size = rsa_key_size

    def ensure_ready(self) -> LocalKeyBootstrapResult:
        if self.key_ring.manifest_path.exists():
            self.key_ring.validate_all()
            return LocalKeyBootstrapResult(False, self.key_ring.manifest_path)

        directory_has_files = self.key_ring.directory.exists() and any(self.key_ring.directory.iterdir())
        if directory_has_files:
            raise LocalKeyConfigurationError(
                f"local key directory is not empty but {MANIFEST_NAME} is missing: {self.key_ring.directory}"
            )

        if self.policy == LocalKeyBootstrapPolicy.DISABLED:
            return LocalKeyBootstrapResult(False, self.key_ring.manifest_path)
        if self.policy == LocalKeyBootstrapPolicy.REQUIRE_EXISTING:
            raise LocalKeyNotFoundError(f"an existing local key ring is required: {self.key_ring.directory}")

        self.key_ring.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name == "posix":
            os.chmod(self.key_ring.directory, 0o700)

        reference = "access-token-001"
        provider_version = 1
        private_key_filename = f"{reference}-private.pem"
        private_key_path = self.key_ring.directory / private_key_filename

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=self.rsa_key_size)
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        self._atomic_write(private_key_path, private_key_pem, mode=0o600)

        manifest: dict[str, Any] = {
            "format_version": MANIFEST_FORMAT_VERSION,
            "keys": [
                {
                    "reference": reference,
                    "version": provider_version,
                    "purpose": SigningKeyPurpose.ACCESS_TOKEN.value,
                    "algorithm": SUPPORTED_LOCAL_ALGORITHM,
                    "private_key_file": private_key_filename,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        }
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        try:
            self._atomic_write(self.key_ring.manifest_path, manifest_bytes, mode=0o600)
        except Exception:
            private_key_path.unlink(missing_ok=True)
            raise

        self.key_ring.validate_all()
        return LocalKeyBootstrapResult(
            True,
            self.key_ring.manifest_path,
            key_reference=reference,
            provider_version=provider_version,
        )

    @staticmethod
    def _atomic_write(destination: Path, content: bytes, *, mode: int) -> None:
        if destination.exists():
            raise LocalKeyConfigurationError(f"refusing to overwrite existing key material: {destination}")

        fd, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if os.name == "posix":
                os.chmod(temporary_path, mode)
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)


class LocalKeyDiscoveryProvider(KeyDiscoveryProvider):
    backend = SigningBackend.LOCAL

    def __init__(self, *, provider_name: str, key_ring: LocalKeyRing) -> None:
        if not provider_name:
            raise ValueError("provider_name cannot be empty")
        self.provider_name = provider_name
        self.key_ring = key_ring

    async def list_keys(self) -> list[SigningKeyDescriptor]:
        descriptors: list[SigningKeyDescriptor] = []
        for entry in self.key_ring.load_entries():
            private_key = self.key_ring.read_private_key(entry)
            public_key_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode("ascii")
            descriptors.append(
                SigningKeyDescriptor(
                    provider_name=self.provider_name,
                    backend=self.backend,
                    external_reference=entry.reference,
                    provider_version=entry.version,
                    purpose=entry.purpose,
                    algorithm=entry.algorithm,
                    public_key_pem=public_key_pem,
                )
            )
        return descriptors


class VaultKeyDiscoveryProvider(KeyDiscoveryProvider):
    """Future Vault Transit discovery boundary; no HTTP implementation yet."""

    backend = SigningBackend.VAULT

    def __init__(self, *, provider_name: str) -> None:
        self.provider_name = provider_name

    async def list_keys(self) -> list[SigningKeyDescriptor]:
        raise NotImplementedError("Vault Transit key discovery is not implemented yet")
