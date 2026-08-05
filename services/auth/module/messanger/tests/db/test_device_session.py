from sqlalchemy import inspect

from messanger.src.db.device_session import DeviceSession

from .conftest import configure_database_mappers


def test_device_session_attributes(configure_database_mappers):
  assert DeviceSession.__table__.schema == "auth"
  device_session_mapper = inspect(DeviceSession)

  relationship = device_session_mapper.relationships["user"]
  assert relationship.back_populates == "device_sessions"

  required_columns_indexes_tuples = (
    ["user_id",],
    ["user_id", "client_device_id"],
    ["idle_expires_at",]
  )

  index_columns = [sorted([column.name for column in index.columns]) for index in DeviceSession.__table__.indexes]

  for required_index in required_columns_indexes_tuples:
    assert sorted(required_index) in index_columns, f"Required index {required_index} not found in device session table indexes. All available indexes: {index_columns}"

  assert any(fk.column.table.name == "users" and fk.column.name == "id" and fk.ondelete == "CASCADE" for fk in DeviceSession.__table__.columns["user_id"].foreign_keys), "auth.users.id not found in foreign keys of DeviceSession user_id or its ondelete is not cascade"
