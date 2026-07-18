from enum import Enum


class UserRole(str, Enum):
    """Single global role for the first version of the service."""

    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class SigningKeyStatus(str, Enum):
    STANDBY = "standby"
    ACTIVE = "active"
    RETIRING = "retiring"
    DISABLED = "disabled"
