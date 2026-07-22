import importlib
import inspect
from pathlib import Path

import messenger.services.auth.main as auth_main
import messenger.services.signer.factory as signer_factory
import messenger.services.signer.providers as signer_providers
import messenger.services.signer.service as signer_service
from messenger.services.key_manager.providers import LocalKeyBootstrapper
from messenger.services.key_manager.registry import SigningKeyRegistry


def test_signer_package_has_no_database_dependency() -> None:
    modules = [signer_factory, signer_providers, signer_service]
    forbidden = (
        "sqlalchemy",
        "messenger.shared.db",
        "messenger.shared.core.config",
        "messenger.services.auth.models",
        "messenger.services.key_manager.models",
        "SigningKeyRegistry",
    )

    for module in modules:
        source = inspect.getsource(module)
        assert all(value not in source for value in forbidden)


def test_auth_startup_does_not_bootstrap_or_reconcile(monkeypatch) -> None:
    def fail(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("auth startup touched key-management logic")

    monkeypatch.setattr(LocalKeyBootstrapper, "ensure_ready", fail)
    monkeypatch.setattr(SigningKeyRegistry, "reconcile", fail)
    importlib.reload(auth_main)


def test_services_have_separate_application_folders() -> None:
    services_directory = Path(auth_main.__file__).parents[1]

    assert (services_directory / "auth" / "main.py").is_file()
    assert (services_directory / "key_manager" / "main.py").is_file()
    assert (services_directory / "signer" / "service.py").is_file()


def test_auth_package_does_not_import_key_manager_or_signer() -> None:
    auth_directory = Path(auth_main.__file__).parent
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in auth_directory.rglob("*.py")
    )

    assert "messenger.services.key_manager" not in source
    assert "messenger.services.signer" not in source
