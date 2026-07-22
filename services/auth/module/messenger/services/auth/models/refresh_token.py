import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from messenger.shared.db.base import Base


class RefreshToken(Base):
    """Hashed opaque refresh token participating in a rotation family."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_session_family", "device_session_id", "family_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    device_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("device_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    family_id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        unique=True,
    )

    device_session: Mapped["DeviceSession"] = relationship(
        back_populates="refresh_tokens",
        foreign_keys=[device_session_id],
    )
    replaced_by: Mapped["RefreshToken | None"] = relationship(
        remote_side="RefreshToken.id",
        foreign_keys=[replaced_by_id],
        uselist=False,
        post_update=True,
    )
