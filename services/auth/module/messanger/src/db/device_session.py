import uuid
from typing import Optional
from datetime import datetime

from messanger.src.db.base import Base

from sqlalchemy import String, TIMESTAMP, UUID, func, ForeignKey, text, Index
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import mapped_column, Mapped, relationship


class DeviceSession(Base):
    __tablename__ = "device_sessions"

    __table_args__ = (
        Index("ix_device_sessions_user_id", "user_id"),
        Index("ix_device_sessions_user_id_client_device_id", "user_id", "client_device_id"),
        Index("ix_device_sessions_idle_expires_at", "idle_expires_at"),
        {"schema": "auth"}
        )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.users.id", ondelete="CASCADE"))
    client_device_id: Mapped[uuid.UUID] = mapped_column(UUID())
    device_name: Mapped[Optional[str]] = mapped_column(String(256))
    user_agent: Mapped[Optional[str]] = mapped_column(String(512))
    ip_address: Mapped[str | None] = mapped_column(INET())

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.current_timestamp()
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp()
    )

    idle_expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("NOW() + INTERVAL '180 days'")
    )

    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True)
    ) # instant killswitch for all refresh tokens belonging to the current device

    user: Mapped["User"] = relationship(back_populates="device_sessions")
