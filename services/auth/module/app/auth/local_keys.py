import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.auth.signing import SigningKeyDescriptor, SigningProvider
from app.auth.types import LocalKeyBootstrapPolicy, SigningBackend, SigningKeyPurpose


_MANIFEST_NAME = "keyset.json"
_MANIFEST_FORMAT_VERSION = 1
_SUPPORTED_ALGORITHM = "RS256"


class LocalKeyError(RuntimeError):
    pass


class LocalKeyConfigurationError(LocalKeyError):
    pass


class LocalKeyNotFoundError(LocalKeyError):
    pass


@dataclass(frozen=True, slots=True)
class LocalKeyEntry:
    reference: str
    version: int
    purpose: SigningKeyPurpose
    algorithm: str
    private_key_file: str
    created_at: str | None = None


@dataclass(frozen=True, slots=True)
class LocalKeyBootstrapResult:
    generated: bool
    manifest_path: Path
    key_reference: str | None = None
    provider_version: int | None = None


class LocalKeyRing:
    """Parser and validator for a persistent local signing-key directory."""

    def __init__(self, directory: Path, *, strict_permissions: bool = False) -> None:
        self.directory = directory.expanduser().resolve()
        self.manifest_path = self.directory / _MANIFEST_NAME
        self.strict_permissions = strict_permissions

    def load_entries(self) -> list[LocalKeyEntry]:
        if not self.manifest_path.is_file():
            raise LocalKeyNotFoundError(f"local key manifest not found: {self.manifest_path}")

        try:
            document = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LocalKeyConfigurationError(f"cannot read local key manifest: {self.manifest_path}") from exc

        if document.get("format_version") != _MANIFEST_FORMAT_VERSION:
            raise LocalKeyConfigurationError(
                f"unsupported local key manifest format: {document.get('format_version')!r}"
            )

        raw_keys = document.get("keys")
        if not isinstance(raw_keys, list) or not raw_keys:
            raise LocalKeyConfigurationError("local key manifest must contain at least one key")

        entries: list[LocalKeyEntry] = []
        identities: set[tuple[str, int]] = set()
        for raw in raw_keys:
            if not isinstance(raw, dict):
                raise LocalKeyConfigurationError("every local key entry must be an object")

            try:
                entry = LocalKeyEntry(
                    reference=str(raw["reference"]),
                    version=int(raw["version"]),
                    purpose=SigningKeyPurpose(raw.get("purpose", SigningKeyPurpose.ACCESS_TOKEN.value)),
                    algorithm=str(raw["algorithm"]),
                    private_key_file=str(raw["private_key_file"]),
                    created_at=str(raw["created_at"]) if raw.get("created_at") is not None else None,
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise LocalKeyConfigurationError(f"invalid local key entry: {raw!r}") from exc

            if not entry.reference or entry.version < 1:
                raise LocalKeyConfigurationError("key reference must be non-empty and version must be positive")
            if entry.algorithm != _SUPPORTED_ALGORITHM:
                raise LocalKeyConfigurationError(f"unsupported local signing algorithm: {entry.algorithm}")

            identity = (entry.reference, entry.version)
            if identity in identities:
                raise LocalKeyConfigurationError(f"duplicate local key identity: {identity!r}")
            identities.add(identity)

            self.resolve_private_key_path(entry)
            entries.append(entry)

        return entries

    def resolve_private_key_path(self, entry: LocalKeyEntry) -> Path:
        candidate = (self.directory / entry.private_key_file).resolve()
        try:
            candidate.relative_to(self.directory)
        except ValueError as exc:
            raise LocalKeyConfigurationError("private key path escapes the configured key directory") from exc

        if candidate == self.manifest_path:
            raise LocalKeyConfigurationError("private key file cannot be the manifest")
        return candidate

    def read_private_key(self, entry: LocalKeyEntry) -> rsa.RSAPrivateKey:
        path = self.resolve_private_key_path(entry)
        if not path.is_file():
            raise LocalKeyNotFoundError(f"private key file not found: {path}")

        self._validate_private_key_permissions(path)
        try:
            key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        except (OSError, TypeError, ValueError) as exc:
            raise LocalKeyConfigurationError(f"cannot load private key: {path}") from exc

        if not isinstance(key, rsa.RSAPrivateKey):
            raise LocalKeyConfigurationError("only RSA private keys are supported for RS256")
        return key

    def _validate_private_key_permissions(self, path: Path) -> None:
        if os.name != "posix":
            return

        mode = path.stat().st_mode & 0o777
        if self.strict_permissions and mode & 0o077:
            raise LocalKeyConfigurationError(
                f"unsafe private-key permissions for {path}: {oct(mode)}; expected no group/other access"
            )


class LocalKeyBootstrapper:
    """Creates the initial local key only when the configured policy permits it."""

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
            for entry in self.key_ring.load_entries():
                self.key_ring.read_private_key(entry)
            return LocalKeyBootstrapResult(False, self.key_ring.manifest_path)

        directory_has_files = self.key_ring.directory.exists() and any(self.key_ring.directory.iterdir())
        if directory_has_files:
            raise LocalKeyConfigurationError(
                f"local key directory is not empty but {_MANIFEST_NAME} is missing: {self.key_ring.directory}"
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

        created_at = datetime.now(timezone.utc).isoformat()
        manifest: dict[str, Any] = {
            "format_version": _MANIFEST_FORMAT_VERSION,
            "keys": [
                {
                    "reference": reference,
                    "version": provider_version,
                    "purpose": SigningKeyPurpose.ACCESS_TOKEN.value,
                    "algorithm": _SUPPORTED_ALGORITHM,
                    "private_key_file": private_key_filename,
                    "created_at": created_at,
                }
            ],
        }
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        try:
            self._atomic_write(self.key_ring.manifest_path, manifest_bytes, mode=0o600)
        except Exception:
            private_key_path.unlink(missing_ok=True)
            raise

        self.key_ring.load_entries()
        return LocalKeyBootstrapResult(
            True,
            self.key_ring.manifest_path,
            key_reference=reference,
            provider_version=provider_version,
        )

    def _atomic_write(self, destination: Path, content: bytes, *, mode: int) -> None:
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


class LocalFileSigningProvider(SigningProvider):
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

    async def sign(
        self,
        signing_input: bytes,
        *,
        external_reference: str,
        provider_version: int,
        algorithm: str,
    ) -> bytes:
        if algorithm != _SUPPORTED_ALGORITHM:
            raise LocalKeyConfigurationError(f"unsupported local signing algorithm: {algorithm}")

        entry = self._find_entry(external_reference, provider_version)
        if entry.algorithm != algorithm:
            raise LocalKeyConfigurationError(
                f"requested algorithm {algorithm} does not match key algorithm {entry.algorithm}"
            )

        private_key = self.key_ring.read_private_key(entry)
        return private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())

    def _find_entry(self, external_reference: str, provider_version: int) -> LocalKeyEntry:
        for entry in self.key_ring.load_entries():
            if entry.reference == external_reference and entry.version == provider_version:
                return entry
        raise LocalKeyNotFoundError(
            f"local signing key not found: reference={external_reference!r}, version={provider_version}"
        )
