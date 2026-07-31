import pytest

from messanger.src.db import user
from messanger.src.db import device_session

from sqlalchemy.orm import configure_mappers

@pytest.fixture
def configure_database_mappers():
  configure_mappers()

