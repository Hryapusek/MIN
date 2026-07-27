from pydantic import Field, field_validator
from typing import Literal, Optional
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class MainSettings(BaseSettings):
  model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra="allow")

  ENVIRONMENT: str

  DB_DATABASE: str
  DB_DRIVER: str
  DB_USERNAME: str
  DB_PASSWORD: str
  DB_HOST: str
  DB_PORT: str

  @field_validator("ENVIRONMENT")
  @classmethod
  def environment_one_of(cls, v: str) -> str:
    correct_values = ("development", "production", "test")
    if v not in correct_values:
      raise ValueError(f"Given value for environment does not match any of required values: {v}. Must be one of {correct_values}")
    return v

  @property
  def database_url(self) -> str:
    return f"{self.DB_DRIVER}://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}"

@lru_cache(maxsize=1)
def get_settings() -> MainSettings:
  return MainSettings()
