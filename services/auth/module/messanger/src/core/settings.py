from pydantic import Field, field_validator
from typing import Literal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class MainSettings(BaseSettings):
  model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra="ignore")

  ENVIRONMENT: Literal["development", "production", "test"]

  DB_DATABASE: str
  DB_DRIVER: str
  DB_USERNAME: str
  DB_PASSWORD: str
  DB_HOST: str
  DB_PORT: int
  
  REFRESH_TOKEN_EXPIRE_PERIOD_DAYS: int

  @property
  def database_url(self) -> str:
    return f"{self.DB_DRIVER}://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}"

@lru_cache(maxsize=1)
def get_settings() -> MainSettings:
  return MainSettings()
