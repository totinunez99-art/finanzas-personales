"""Configuración estática (docs/11 nivel 1)."""

import pytest
from pydantic import ValidationError

from finanzas.shared.config import Settings


def test_carga_desde_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/db")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.database_url == "postgresql+psycopg://u:p@h:5432/db"
    assert settings.log_level == "DEBUG"
    assert settings.timezone == "America/Santiago"


def test_environment_invalido_no_arranca(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/db")
    monkeypatch.setenv("ENVIRONMENT", "staging")  # no permitido: dev | prod
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]
