import asyncio
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from messenger.services.key_manager.providers import LocalKeyBootstrapper, LocalKeyDiscoveryProvider
from messenger.services.key_manager.registry import ActiveSigningKeyUnavailableError, SigningKeyRegistry
from messenger.services.key_manager.models.signing_key import SigningKey
from messenger.shared.signing.local_key_ring import LocalKeyRing
from messenger.shared.signing.types import InitialKeyActivationPolicy, LocalKeyBootstrapPolicy


def _provider(tmp_path: Path) -> LocalKeyDiscoveryProvider:
    key_ring = LocalKeyRing(tmp_path)
    LocalKeyBootstrapper(
        key_ring=key_ring,
        policy=LocalKeyBootstrapPolicy.GENERATE_IF_EMPTY,
    ).ensure_ready()
    return LocalKeyDiscoveryProvider(provider_name="local-primary", key_ring=key_ring)


def test_reconcile_activates_only_first_registry_key_and_preserves_it(tmp_path: Path) -> None:
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
        active_kid = registry.resolve_active(session).kid

        repeated = registry.reconcile(
            session,
            provider=provider,
            descriptors=descriptors,
            initial_activation_policy=InitialKeyActivationPolicy.IF_REGISTRY_EMPTY,
        )
        session.commit()

        assert repeated.inserted == 0
        assert repeated.activated_kid is None
        assert registry.resolve_active(session).kid == active_kid


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
