from enum import Enum


class SigningBackend(str, Enum):
    """Where the private signing operation is performed."""

    LOCAL = "local"
    VAULT = "vault"


class SigningKeyPurpose(str, Enum):
    """Logical purpose of a signing key inside this authorization service."""

    ACCESS_TOKEN = "access_token"


class LocalKeyBootstrapPolicy(str, Enum):
    """How a local key directory is prepared before the provider is used."""

    GENERATE_IF_EMPTY = "generate_if_empty"
    REQUIRE_EXISTING = "require_existing"
    DISABLED = "disabled"


class InitialKeyActivationPolicy(str, Enum):
    """Whether the first discovered key may be activated automatically."""

    IF_REGISTRY_EMPTY = "if_registry_empty"
    MANUAL = "manual"
