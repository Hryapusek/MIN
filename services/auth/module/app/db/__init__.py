"""Database package.

Import concrete engine/session objects from ``app.db.session`` explicitly so
that importing ORM models does not open or configure a database connection.
"""

from app.db.base import Base

__all__ = ["Base"]
