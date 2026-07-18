import asyncio
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth.key_registry import (
    ActiveSigningKeyUnavailableError,
    SigningKeyRegistry,
    SigningService,
)
from app.auth.local_keys import LocalFileSigningProvider, LocalKeyBootstrapper, LocalKeyRing
from app.auth.types import InitialKeyActivationPolicy, LocalKeyBootstrapPolicy
from app.models.signing_key import SigningKey


def _provider(tmp_path: Path) -> LocalFileSigningProvider:
    key_ring = LocalKeyRing(tmp_path)
    LocalKeyBootstrapper(
        key_ring=key_ring,
        policy=LocalKeyBootstrapPolicy.GENERATE_IF_EMPTY,
    ).ensure_ready()
    return LocalFileSigningProvider(provider_name="local-primary", key_ring=key_ring)


def test_reconcile_activates_only_first_registry_key_and_signs(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    descriptors = asyncio.run(provider.list_keys())
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SigningKey.__table__.create(engine)

    with Session(engine) as session:
        registry = SigningKeyRegistry()
        result = registry.reconcile(
            session,
            provider=provider,
            descriptors=descriptors,
            initial_activation_policy=InitialKeyActivationPolicy.IF_REGISTRY_EMPTY,
        )
        session.commit()

        assert result.inserted == 1
        assert result.activated_kid is not None
        active = registry.resolve_active(session)

        signature = asyncio.run(SigningService(providers=[provider]).sign(session, b"payload"))
        assert signature.kid == active.kid
        assert signature.algorithm == "RS256"

        repeated = registry.reconcile(
            session,
            provider=provider,
            descriptors=descriptors,
            initial_activation_policy=InitialKeyActivationPolicy.IF_REGISTRY_EMPTY,
        )
        session.commit()
        assert repeated.inserted == 0
        assert repeated.activated_kid is None


def test_missing_active_provider_key_is_marked_unavailable(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    descriptors = asyncio.run(provider.list_keys())
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SigningKey.__table__.create(engine)

    with Session(engine) as session:
        registry = SigningKeyRegistry()
        registry.reconcile(
            session,
            provider=provider,
            descriptors=descriptors,
            initial_activation_policy=InitialKeyActivationPolicy.IF_REGISTRY_EMPTY,
        )
        registry.reconcile(
            session,
            provider=provider,
            descriptors=[],
            initial_activation_policy=InitialKeyActivationPolicy.MANUAL,
        )
        session.commit()

        with pytest.raises(ActiveSigningKeyUnavailableError):
            registry.resolve_active(session)
