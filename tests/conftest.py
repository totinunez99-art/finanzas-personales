"""Configuración compartida de tests."""

import os

import pytest

# Config mínima para que get_settings() no falle en tests unitarios.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Los tests de integración se saltan si no hay TEST_DATABASE_URL."""
    if os.environ.get("TEST_DATABASE_URL"):
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL no definida; requiere PostgreSQL real")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
