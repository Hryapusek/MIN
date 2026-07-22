from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Index, Integer, JSON, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from messenger.shared.signing.types import SigningBackend, SigningKeyPurpose
from messenger.shared.db.base import Base
from messenger.services.key_manager.models.enums import SigningKeyStatus


class SigningKey(Base):
    """Database registry row for provider-owned access-token signing material.

    The provider owns the private key. This table stores lifecycle policy,
    provider routing information, and safe public material used for JWKS.
    """

    __tablename__ = "signing_keys"
    __table_args__ = (
        UniqueConstraint(
            "provider_name",
            "external_reference",
            "provider_version",
            name="uq_signing_keys_provider_reference_version",
        ),
        Index(
            "uq_signing_keys_one_active_per_purpose_algorithm",
            "purpose",
            "algorithm",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    kid: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider_name: Mapped[str] = mapped_column(String(64), index=True)
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
    external_reference: Mapped[str] = mapped_column(String(255))
    provider_version: Mapped[int] = mapped_column(Integer)
    purpose: Mapped[SigningKeyPurpose] = mapped_column(
        Enum(
            SigningKeyPurpose,
            name="signing_key_purpose",
            native_enum=False,
            length=32,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        default=SigningKeyPurpose.ACCESS_TOKEN,
        server_default=SigningKeyPurpose.ACCESS_TOKEN.value,
        index=True,
    )
    algorithm: Mapped[str] = mapped_column(String(32))

    # Public material is safe to persist and allows JWKS publication even when
    # the signing provider is temporarily unavailable.
    public_key_pem: Mapped[str] = mapped_column(Text)
    public_jwk: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

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
        default=SigningKeyStatus.STANDBY,
        server_default=SigningKeyStatus.STANDBY.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    unavailable_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retiring_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retire_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
