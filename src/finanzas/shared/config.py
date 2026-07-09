"""Configuración estática de la aplicación (nivel 1, docs/11 §2).

Única puerta de entrada a variables de entorno. Ningún módulo usa os.environ
directamente (docs/08 §2). Config inválida => el proceso no arranca.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["dev", "prod"] = "dev"
    timezone: str = "America/Santiago"

    database_url: str
    """DSN SQLAlchemy, ej: postgresql+psycopg://user:pass@host:5432/db"""

    log_level: str = "INFO"
    log_json: bool = True

    default_user_email: str = "user@example.com"
    """Mono-usuario (ADR-002): email del único usuario, creado por scripts/seed.py."""

    api_base_url: str = "http://localhost:8000"
    """Usada solo por el dashboard para hablar con la API (ADR-006)."""

    settings_cache_ttl_seconds: int = 30
    """TTL del caché de flags dinámicos (docs/11 §2)."""


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # database_url llega por entorno
