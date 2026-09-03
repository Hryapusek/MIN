import pytest

from messanger.src.db.user import User

from .conftest import configure_database_mappers

from sqlalchemy import inspect

def test_users_table_attributes(configure_database_mappers):
  assert User.__table_args__["schema"] == "auth"
  user_mapper = inspect(User)
  relationship = user_mapper.relationships["device_sessions"]
  assert relationship.back_populates == "user"

  assert relationship.cascade.save_update is True
  assert relationship.cascade.delete is True
  assert relationship.cascade.delete_orphan is True
  assert relationship.cascade.expunge is True
  assert relationship.cascade.merge is True

  assert relationship.passive_deletes is True
