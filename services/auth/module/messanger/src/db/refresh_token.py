import uuid
from typing import Optional
from datetime import datetime

from messanger.src.db.base import Base

from sqlalchemy import (
    func,
    TIMESTAMP,
    UUID,
    ForeignKey,
    LargeBinary,
)
from sqlalchemy.orm import mapped_column, Mapped, relationship


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    __table_args__ = {"schema": "auth"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)

    device_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.device_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True, index=True)

    family_id: Mapped[uuid.UUID] = mapped_column(UUID(), nullable=False, index=True)

    issued_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.current_timestamp()
    )

    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )

    replaced_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("auth.refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )

    consumed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    device_session: Mapped["DeviceSession"] = relationship(
        back_populates="refresh_tokens"
    )

    replaced_by: Mapped[Optional["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="parent", remote_side=[id], uselist=False, foreign_keys=replaced_by_id
    )

    parent: Mapped[Optional["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="replaced_by",
        uselist=False
    )
