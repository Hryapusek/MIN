from dataclasses import dataclass
from typing import Callable

from sqlalchemy.orm import Session

from messenger.services.key_manager.providers import LocalKeyBootstrapResult, LocalKeyBootstrapper
from messenger.services.key_manager.registry import ReconciliationResult, SigningKeyRegistry
from messenger.shared.signing.contracts import KeyDiscoveryProvider
from messenger.shared.signing.types import InitialKeyActivationPolicy


@dataclass(frozen=True, slots=True)
class KeyManagerRunResult:
    bootstrap: LocalKeyBootstrapResult | None
    reconciliation: ReconciliationResult


class KeyManagerService:
    """Runs one complete key bootstrap/discovery/reconciliation transaction."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        discovery_provider: KeyDiscoveryProvider,
        initial_activation_policy: InitialKeyActivationPolicy,
        bootstrapper: LocalKeyBootstrapper | None = None,
        registry: SigningKeyRegistry | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.discovery_provider = discovery_provider
        self.initial_activation_policy = initial_activation_policy
        self.bootstrapper = bootstrapper
        self.registry = registry or SigningKeyRegistry()

    async def run_once(self) -> KeyManagerRunResult:
        bootstrap_result = self.bootstrapper.ensure_ready() if self.bootstrapper is not None else None
        descriptors = await self.discovery_provider.list_keys()

        session = self.session_factory()
        try:
            reconciliation = self.registry.reconcile(
                session,
                provider=self.discovery_provider,
                descriptors=descriptors,
                initial_activation_policy=self.initial_activation_policy,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        return KeyManagerRunResult(
            bootstrap=bootstrap_result,
            reconciliation=reconciliation,
        )
