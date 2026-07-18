from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.auth.types import SigningBackend
from app.db.base import Base
from app.models.enums import SigningKeyStatus


class SigningKey(Base):
    """Public metadata and backend-specific reference for an access-token key.

    ``key_reference`` may be a Vault Transit key name or a reference to a local
    secret source. It must never contain the private key itself.
    """

    __tablename__ = "signing_keys"

    kid: Mapped[str] = mapped_column(String(128), primary_key=True)
    backend: Mapped[SigningBackend] = mapped_column(
        Enum(
            SigningBackend,
            name="signing_backend",
            native_enum=False,
            length=16,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        index=True,
    )
    algorithm: Mapped[str] = mapped_column(String(32))
    key_reference: Mapped[str] = mapped_column(String(255))
    public_key_pem: Mapped[str] = mapped_column(Text)
    status: Mapped[SigningKeyStatus] = mapped_column(
        Enum(
            SigningKeyStatus,
            name="signing_key_status",
            native_enum=False,
            length=16,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        default=SigningKeyStatus.ACTIVE,
        server_default=SigningKeyStatus.ACTIVE.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
