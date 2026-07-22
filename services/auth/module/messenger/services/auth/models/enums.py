from enum import Enum


class UserRole(str, Enum):
    """Single global role for the first version of the auth service."""

    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
