import uuid
import hashlib
import random
import string
import datetime

from sqlalchemy import inspect

from messanger.src.db.refresh_token import RefreshToken

from .conftest import configure_database_mappers


def generate_random_string(n):
    # Define the character pool (letters and digits)
    characters = string.ascii_letters + string.digits
    
    # Randomly select 'n' characters and join them
    return ''.join(random.choices(characters, k=n))

def create_dummy_token():
  return RefreshToken(
    id=uuid.uuid4(),
    device_session_id=uuid.uuid4(),
    token_hash=hashlib.sha256(generate_random_string(50).encode("UTF-8")),
    family_id=uuid.uuid4(),
    expires_at=datetime.datetime.now() + datetime.timedelta(days=5)
  )

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

  index_columns = [[column.name for column in index.columns] for index in RefreshToken.__table__.indexes]

  for required_index in required_columns_indexes_tuples:
    assert sorted(required_index) in index_columns, f"Required index {required_index} not found in device session table indexes. All available indexes: {index_columns}"

  assert any(fk.column.table.name == "device_sessions" and fk.column.name == "id" and fk.ondelete == "CASCADE" for fk in RefreshToken.__table__.columns["device_session_id"].foreign_keys), "auth.device_sessions.id not found in foreign keys of RefreshToken device_session_id or its ondelete is not cascade"

  foreign_key = next(
    iter(RefreshToken.__table__.columns["replaced_by_id"].foreign_keys)
  )

  assert foreign_key.target_fullname == "auth.refresh_tokens.id"
  assert foreign_key.ondelete == "SET NULL"
  assert RefreshToken.__table__.c.replaced_by_id.unique is True

def test_refresh_token_rotation_relationship(configure_database_mappers):
  mapper = inspect(RefreshToken)
  replaced_by = mapper.relationships["replaced_by"]
  previous_token = mapper.relationships["previous_token"]

  assert replaced_by.back_populates == "previous_token"
  assert replaced_by.mapper.class_ is RefreshToken
  assert next(iter(replaced_by.remote_side)).name == "id"

  assert previous_token.mapper.class_ is RefreshToken
  assert previous_token.uselist is False
  assert previous_token.back_populates == "replaced_by"

def test_in_memory_synchronization_its_not_ai_btw(configure_database_mappers):
  old_token = create_dummy_token()
  new_token = create_dummy_token()

  old_token.replaced_by = new_token
  assert new_token.previous_token is old_token
