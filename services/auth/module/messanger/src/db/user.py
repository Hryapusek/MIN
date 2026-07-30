import enum
import uuid
from datetime import datetime
from typing import Optional

from messanger.src.db.base import Base

from sqlalchemy import String, TIMESTAMP, UUID, Enum, func
from sqlalchemy.orm import mapped_column, Mapped

class UserRole(enum.Enum):
  USER = "user",
  MODERATOR = "moderator",
  ADMIN = "admin",

class User(Base):
  __tablename__ = "users"

  __table_args__ = { "schema": "auth" }

  id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True)
  username: Mapped[str] = mapped_column(String(50))
  name: Mapped[str] = mapped_column(String(50))
  surname: Mapped[str] = mapped_column(String(50))
  email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
  role: Mapped[UserRole] = mapped_column(Enum(UserRole))
  is_active: Mapped[bool] = mapped_column(default=True)
  password_hash: Mapped[str] = mapped_column(nullable=False)
  created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=False), server_default=func.current_timestamp())
  updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=False), onupdate=func.current_timestamp())
  banned_at: Mapped[Optional[bool]] = mapped_column(default=False)
