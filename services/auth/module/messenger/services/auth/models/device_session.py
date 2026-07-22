import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from messenger.shared.db.base import Base


class DeviceSession(Base):
    """One authenticated browser or application installation.

    The UUID is suitable for the JWT ``sid`` claim. A null ``revoked_at`` means
    that the session is active. Current access tokens can remain valid until
    their short expiry unless an online revocation check is added later.
    """

    __tablename__ = "device_sessions"
    __table_args__ = (
        Index("ix_device_sessions_user_device", "user_id", "device_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    device_id: Mapped[str] = mapped_column(String(128), index=True)
    device_name: Mapped[str | None] = mapped_column(String(200))
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(INET)
    client_version: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped["User"] = relationship(back_populates="device_sessions")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="device_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="RefreshToken.device_session_id",
    )
