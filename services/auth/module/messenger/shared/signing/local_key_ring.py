import json
import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from messenger.shared.signing.types import SigningKeyPurpose


MANIFEST_NAME = "keyset.json"
MANIFEST_FORMAT_VERSION = 1
SUPPORTED_LOCAL_ALGORITHM = "RS256"


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


class LocalKeyRing:
    """Reads and validates a persistent local signing-key directory."""

    def __init__(self, directory: Path, *, strict_permissions: bool = False) -> None:
        self.directory = directory.expanduser().resolve()
        self.manifest_path = self.directory / MANIFEST_NAME
        self.strict_permissions = strict_permissions

    def load_entries(self) -> list[LocalKeyEntry]:
        if not self.manifest_path.is_file():
            raise LocalKeyNotFoundError(f"local key manifest not found: {self.manifest_path}")

        try:
            document = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LocalKeyConfigurationError(f"cannot read local key manifest: {self.manifest_path}") from exc

        if document.get("format_version") != MANIFEST_FORMAT_VERSION:
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
            if entry.algorithm != SUPPORTED_LOCAL_ALGORITHM:
                raise LocalKeyConfigurationError(f"unsupported local signing algorithm: {entry.algorithm}")

            identity = (entry.reference, entry.version)
            if identity in identities:
                raise LocalKeyConfigurationError(f"duplicate local key identity: {identity!r}")
            identities.add(identity)

            self.resolve_private_key_path(entry)
            entries.append(entry)

        return entries

    def find_entry(self, external_reference: str, provider_version: int) -> LocalKeyEntry:
        for entry in self.load_entries():
            if entry.reference == external_reference and entry.version == provider_version:
                return entry
        raise LocalKeyNotFoundError(
            f"local signing key not found: reference={external_reference!r}, version={provider_version}"
        )

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

    def validate_all(self) -> list[LocalKeyEntry]:
        entries = self.load_entries()
        for entry in entries:
            self.read_private_key(entry)
        return entries

    def _validate_private_key_permissions(self, path: Path) -> None:
        if os.name != "posix":
            return

        mode = path.stat().st_mode & 0o777
        if self.strict_permissions and mode & 0o077:
            raise LocalKeyConfigurationError(
                f"unsafe private-key permissions for {path}: {oct(mode)}; expected no group/other access"
            )
