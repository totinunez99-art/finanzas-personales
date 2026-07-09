"""Dependencias de FastAPI."""

from collections.abc import Iterator

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from finanzas.core.db import get_session_factory
from finanzas.core.models import User
from finanzas.shared.config import get_settings


def get_db() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_current_user(db: Session = Depends(get_db)) -> User:
    """Mono-usuario (ADR-002): el usuario llega por dependencia, nunca hardcodeado.
    En Fase 7 esta función se reemplaza por auth real sin tocar los routers."""
    email = get_settings().default_user_email
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=503,
            detail=(
                f"No existe el usuario por defecto ({email}). "
                "Ejecuta: python scripts/seed.py"
            ),
        )
    return user
