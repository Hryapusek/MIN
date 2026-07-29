from datetime import datetime
from typing import Optional

from messanger.src.db.base import Base

from sqlalchemy import String, TIMESTAMP
from sqlalchemy.orm import mapped_column, Mapped


class User(Base):
  __tablename__ = "users"

  __table_args__ = { "schema": "auth" }

  id: Mapped[int] = mapped_column(primary_key=True)
  username: Mapped[str] = mapped_column(String(50))
  name: Mapped[str]
  surname: Mapped[str]
  created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=False))
  banned_at: Mapped[Optional[bool]] = mapped_column(default=False)
