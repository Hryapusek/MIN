from enum import Enum


class SigningKeyStatus(str, Enum):
    STANDBY = "standby"
    ACTIVE = "active"
    RETIRING = "retiring"
    DISABLED = "disabled"
