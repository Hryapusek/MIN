from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.auth.key_utils import rsa_public_key_to_jwk
from app.auth.signing import SignatureResult, SigningKeyDescriptor, SigningProvider
from app.auth.types import InitialKeyActivationPolicy, SigningKeyPurpose
from app.models.enums import SigningKeyStatus
from app.models.signing_key import SigningKey


class SigningKeyRegistryError(RuntimeError):
    pass


class SigningKeyConflictError(SigningKeyRegistryError):
    pass


class ActiveSigningKeyNotFoundError(SigningKeyRegistryError):
    pass


class ActiveSigningKeyUnavailableError(SigningKeyRegistryError):
    pass


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    provider_name: str
    discovered: int
    inserted: int
    updated: int
    missing: int
    activated_kid: str | None


class SigningKeyRegistry:
    """Database-backed lifecycle policy for provider-owned signing keys."""

    def reconcile(
        self,
        session: Session,
        *,
        provider: SigningProvider,
        descriptors: Iterable[SigningKeyDescriptor],
        initial_activation_policy: InitialKeyActivationPolicy,
    ) -> ReconciliationResult:
        descriptor_list = list(descriptors)
        self._validate_descriptor_set(provider, descriptor_list)

        existing_registry_size = session.scalar(select(func.count()).select_from(SigningKey)) or 0
        now = datetime.now(timezone.utc)
        existing_rows = {
            (row.external_reference, row.provider_version): row
            for row in session.scalars(
                select(SigningKey).where(SigningKey.provider_name == provider.provider_name)
            )
        }

        inserted = 0
        updated = 0
        seen_identities: set[tuple[str, int]] = set()
        discovered_rows: list[SigningKey] = []

        for descriptor in descriptor_list:
            public_jwk = rsa_public_key_to_jwk(
                descriptor.public_key_pem,
                algorithm=descriptor.algorithm,
            )
            kid = str(public_jwk["kid"])
            identity = (descriptor.external_reference, descriptor.provider_version)
            seen_identities.add(identity)

            row = existing_rows.get(identity)
            if row is None:
                kid_owner = session.get(SigningKey, kid)
                if kid_owner is not None:
                    raise SigningKeyConflictError(
                        f"kid {kid!r} is already registered by provider {kid_owner.provider_name!r}"
                    )

                row = SigningKey(
                    kid=kid,
                    provider_name=descriptor.provider_name,
                    backend=descriptor.backend,
                    external_reference=descriptor.external_reference,
                    provider_version=descriptor.provider_version,
                    purpose=descriptor.purpose,
                    algorithm=descriptor.algorithm,
                    public_key_pem=descriptor.public_key_pem,
                    public_jwk=public_jwk,
                    status=SigningKeyStatus.STANDBY,
                    discovered_at=now,
                    last_seen_at=now,
                )
                session.add(row)
                existing_rows[identity] = row
                inserted += 1
            else:
                self._assert_immutable_metadata_matches(row, descriptor, kid, public_jwk)
                row.public_key_pem = descriptor.public_key_pem
                if row.public_jwk is None:
                    row.public_jwk = public_jwk
                row.last_seen_at = now
                row.unavailable_since = None
                updated += 1

            discovered_rows.append(row)

        missing = 0
        for identity, row in existing_rows.items():
            if identity not in seen_identities and row.unavailable_since is None:
                row.unavailable_since = now
                missing += 1

        session.flush()

        activated_kid: str | None = None
        if (
            initial_activation_policy == InitialKeyActivationPolicy.IF_REGISTRY_EMPTY
            and existing_registry_size == 0
            and len(discovered_rows) == 1
        ):
            row = discovered_rows[0]
            row.status = SigningKeyStatus.ACTIVE
            row.activated_at = now
            activated_kid = row.kid
            session.flush()

        return ReconciliationResult(
            provider_name=provider.provider_name,
            discovered=len(descriptor_list),
            inserted=inserted,
            updated=updated,
            missing=missing,
            activated_kid=activated_kid,
        )

    def resolve_active(
        self,
        session: Session,
        *,
        purpose: SigningKeyPurpose = SigningKeyPurpose.ACCESS_TOKEN,
        algorithm: str = "RS256",
    ) -> SigningKey:
        rows = list(session.scalars(self._active_query(purpose=purpose, algorithm=algorithm)))
        if not rows:
            raise ActiveSigningKeyNotFoundError(
                f"no active signing key for purpose={purpose.value!r}, algorithm={algorithm!r}"
            )
        if len(rows) != 1:
            raise SigningKeyRegistryError(
                f"multiple active signing keys for purpose={purpose.value!r}, algorithm={algorithm!r}"
            )

        row = rows[0]
        if row.unavailable_since is not None:
            raise ActiveSigningKeyUnavailableError(
                f"active signing key {row.kid!r} is unavailable since {row.unavailable_since.isoformat()}"
            )
        return row

    def activate(
        self,
        session: Session,
        *,
        kid: str,
        retirement_grace: timedelta | None = None,
    ) -> SigningKey:
        target = session.get(SigningKey, kid)
        if target is None:
            raise SigningKeyRegistryError(f"unknown signing key: {kid!r}")
        if target.unavailable_since is not None:
            raise ActiveSigningKeyUnavailableError(f"cannot activate unavailable signing key: {kid!r}")
        if target.status == SigningKeyStatus.DISABLED:
            raise SigningKeyRegistryError(f"cannot activate disabled signing key: {kid!r}")

        now = datetime.now(timezone.utc)
        retired_an_active_key = False
        for current in session.scalars(
            self._active_query(purpose=target.purpose, algorithm=target.algorithm)
        ):
            if current.kid == target.kid:
                return target
            current.status = SigningKeyStatus.RETIRING
            current.retiring_at = now
            current.retire_after = now + retirement_grace if retirement_grace is not None else None
            retired_an_active_key = True

        # Flush the old ACTIVE -> RETIRING transition first. This avoids a
        # transient violation of the partial unique index when the new key is
        # activated in the same transaction.
        if retired_an_active_key:
            session.flush()

        target.status = SigningKeyStatus.ACTIVE
        target.activated_at = now
        target.retiring_at = None
        target.retire_after = None
        target.disabled_at = None
        session.flush()
        return target

    def disable(self, session: Session, *, kid: str) -> SigningKey:
        row = session.get(SigningKey, kid)
        if row is None:
            raise SigningKeyRegistryError(f"unknown signing key: {kid!r}")
        if row.status == SigningKeyStatus.ACTIVE:
            raise SigningKeyRegistryError("activate another key before disabling the active key")

        row.status = SigningKeyStatus.DISABLED
        row.disabled_at = datetime.now(timezone.utc)
        session.flush()
        return row

    def publishable(self, session: Session) -> list[SigningKey]:
        return list(
            session.scalars(
                select(SigningKey)
                .where(
                    SigningKey.status.in_([SigningKeyStatus.ACTIVE, SigningKeyStatus.RETIRING]),
                    SigningKey.public_jwk.is_not(None),
                )
                .order_by(SigningKey.created_at.asc())
            )
        )

    def _active_query(self, *, purpose: SigningKeyPurpose, algorithm: str) -> Select[tuple[SigningKey]]:
        return select(SigningKey).where(
            SigningKey.purpose == purpose,
            SigningKey.algorithm == algorithm,
            SigningKey.status == SigningKeyStatus.ACTIVE,
        )

    def _validate_descriptor_set(
        self,
        provider: SigningProvider,
        descriptors: list[SigningKeyDescriptor],
    ) -> None:
        identities: set[tuple[str, int]] = set()
        for descriptor in descriptors:
            if descriptor.provider_name != provider.provider_name:
                raise SigningKeyConflictError("provider returned a descriptor with another provider_name")
            if descriptor.backend != provider.backend:
                raise SigningKeyConflictError("provider returned a descriptor with another backend")
            identity = (descriptor.external_reference, descriptor.provider_version)
            if identity in identities:
                raise SigningKeyConflictError(f"provider returned duplicate key identity: {identity!r}")
            identities.add(identity)

    def _assert_immutable_metadata_matches(
        self,
        row: SigningKey,
        descriptor: SigningKeyDescriptor,
        kid: str,
        public_jwk: dict[str, object],
    ) -> None:
        expected = (
            row.kid,
            row.backend,
            row.purpose,
            row.algorithm,
            row.public_jwk if row.public_jwk is not None else public_jwk,
        )
        actual = (
            kid,
            descriptor.backend,
            descriptor.purpose,
            descriptor.algorithm,
            public_jwk,
        )
        if expected != actual:
            raise SigningKeyConflictError(
                "provider key material or immutable metadata changed without a new provider version: "
                f"provider={descriptor.provider_name!r}, reference={descriptor.external_reference!r}, "
                f"version={descriptor.provider_version}"
            )


class SigningService:
    """Uses database policy to choose a key and a provider to perform signing."""

    def __init__(self, *, providers: Iterable[SigningProvider], registry: SigningKeyRegistry | None = None) -> None:
        provider_list = list(providers)
        self.providers = {provider.provider_name: provider for provider in provider_list}
        if len(self.providers) != len(provider_list):
            raise ValueError("signing provider names must be unique")
        self.registry = registry or SigningKeyRegistry()

    async def sign(
        self,
        session: Session,
        signing_input: bytes,
        *,
        purpose: SigningKeyPurpose = SigningKeyPurpose.ACCESS_TOKEN,
        algorithm: str = "RS256",
    ) -> SignatureResult:
        key = self.registry.resolve_active(session, purpose=purpose, algorithm=algorithm)
        provider = self.providers.get(key.provider_name)
        if provider is None:
            raise ActiveSigningKeyUnavailableError(
                f"provider {key.provider_name!r} for active key {key.kid!r} is not configured"
            )
        if provider.backend != key.backend:
            raise SigningKeyConflictError("configured provider backend does not match registry metadata")

        signature = await provider.sign(
            signing_input,
            external_reference=key.external_reference,
            provider_version=key.provider_version,
            algorithm=key.algorithm,
        )
        return SignatureResult(kid=key.kid, algorithm=key.algorithm, signature=signature)
