from sqlalchemy import inspect

from messanger.src.db.refresh_token import RefreshToken

from .conftest import configure_database_mappers


def test_refresh_token_attributes(configure_database_mappers):
  assert RefreshToken.__table__.schema == "auth"
  refresh_token_mapper = inspect(RefreshToken)

  relationship = refresh_token_mapper.relationships["device_session"]
  assert relationship.back_populates == "refresh_tokens"

  required_columns_indexes_tuples = (
    ["device_session_id",],
    ["family_id",],
    ["expires_at",]
  )

  index_columns = [sorted([column.name for column in index.columns]) for index in RefreshToken.__table__.indexes]

  for required_index in required_columns_indexes_tuples:
    assert sorted(required_index) in index_columns, f"Required index {required_index} not found in device session table indexes. All available indexes: {index_columns}"

  assert any(fk.column.table.name == "device_sessions" and fk.column.name == "id" and fk.ondelete == "CASCADE" for fk in RefreshToken.__table__.columns["device_session_id"].foreign_keys), "auth.device_sessions.id not found in foreign keys of RefreshToken device_session_id or its ondelete is not cascade"
