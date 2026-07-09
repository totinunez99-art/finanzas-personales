"""Motor, fábrica de sesiones y guardas de arranque (docs/15 §Flujo)."""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from finanzas.shared.config import get_settings
from finanzas.shared.errors import ConfigError


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def wait_for_db(timeout_seconds: int = 60) -> None:
    """Bloquea hasta que PostgreSQL acepte conexiones o expire el timeout.

    Defensa en profundidad: el orden de compose ya lo garantiza, pero ningún
    proceso debe depender SOLO del orquestador (arranques manuales, dev local).
    """
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError as exc:
            last_error = exc
            time.sleep(2)
    raise ConfigError(
        f"PostgreSQL no respondió en {timeout_seconds}s. "
        f"¿Está corriendo el servicio db y es correcto DATABASE_URL? Último error: {last_error}"
    )


def assert_migrated() -> None:
    """Falla con mensaje accionable si las migraciones no se han aplicado.

    Ningún servicio debe tocar tablas de dominio sin esta garantía (docs/15).
    """
    try:
        with get_engine().connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception as exc:
        raise ConfigError(
            "La base de datos no está migrada (no existe alembic_version). "
            "En Docker: el servicio 'bootstrap' debe completarse primero "
            "(docker compose logs bootstrap). En local: alembic upgrade head."
        ) from exc
    if version is None:
        raise ConfigError("alembic_version está vacía: migración interrumpida; revisar logs.")


@contextmanager
def session_scope() -> Iterator[Session]:
    """Sesión transaccional: commit al salir bien, rollback ante error."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
