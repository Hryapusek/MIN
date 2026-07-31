import pytest

from sqlalchemy import inspect, Index

from messanger.src.db.device_session import DeviceSession

from .conftest import configure_database_mappers
from .utils import obtain_schema_from_table_args


def test_device_session_attributes(configure_database_mappers):
  assert obtain_schema_from_table_args(DeviceSession.__table_args__) == "auth"
  device_session_mapper = inspect(DeviceSession)

  relationship = device_session_mapper.relationships["user"]
  assert relationship.back_populates == "device_sessions"

  required_columns_indexes_tuples = (
    ["user_id",],
    ["user_id", "client_device_id"],
    ["idle_expires_at",]
  )

  index_columns = [sorted([column.name for column in index.columns]) for index in DeviceSession.__table_args__ if isinstance(index, Index)]

  for required_index in required_columns_indexes_tuples:
    assert sorted(required_index) in index_columns, f"Required index {required_index} not found in device session table indexes. All available indexes: {index_columns}"

  # TODO: add foreign key test
