import asyncio
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from messenger.services.key_manager.providers import LocalKeyBootstrapper, LocalKeyDiscoveryProvider
from messenger.services.key_manager.service import KeyManagerService
from messenger.services.key_manager.models.enums import SigningKeyStatus
from messenger.services.key_manager.models.signing_key import SigningKey
from messenger.shared.signing.local_key_ring import LocalKeyRing
from messenger.shared.signing.types import InitialKeyActivationPolicy, LocalKeyBootstrapPolicy


def test_run_once_bootstraps_discovers_reconciles_and_commits(tmp_path: Path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SigningKey.__table__.create(engine)
    sessions = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    key_ring = LocalKeyRing(tmp_path)

    result = asyncio.run(
        KeyManagerService(
            session_factory=sessions,
            bootstrapper=LocalKeyBootstrapper(
                key_ring=key_ring,
                policy=LocalKeyBootstrapPolicy.GENERATE_IF_EMPTY,
            ),
            discovery_provider=LocalKeyDiscoveryProvider(
                provider_name="local-primary",
                key_ring=key_ring,
            ),
            initial_activation_policy=InitialKeyActivationPolicy.IF_REGISTRY_EMPTY,
        ).run_once()
    )

    assert result.bootstrap is not None
    assert result.bootstrap.generated is True
    assert result.reconciliation.inserted == 1

    with sessions() as session:
        [row] = list(session.scalars(select(SigningKey)))
        assert row.status == SigningKeyStatus.ACTIVE
