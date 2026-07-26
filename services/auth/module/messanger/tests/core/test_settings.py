
from src.core.settings import MainSettings
from pytest import MonkeyPatch

def test_database_url():
  monkeypatch = MonkeyPatch()
  monkeypatch.setenv("ENVIRONMENT", "development")
  monkeypatch.setenv("DB_DATABASE", "messenger")
  monkeypatch.setenv("DB_DRIVER", "postgresql+psycopg")
  monkeypatch.setenv("DB_USERNAME", "messenger")
  monkeypatch.setenv("DB_PASSWORD", "change-me")
  monkeypatch.setenv("DB_HOST", "localhost")
  monkeypatch.setenv("DB_PORT", "5432")
  settings = MainSettings()

  assert settings.database_url == "postgresql+psycopg://messenger:change-me@localhost:5432/messenger"
