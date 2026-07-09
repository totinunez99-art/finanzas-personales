"""Seed idempotente: crea el usuario por defecto (ADR-002).

Uso: python scripts/seed.py
"""

from finanzas.core.db import session_scope
from finanzas.core.services.bootstrap import ensure_default_user
from finanzas.shared.config import get_settings
from finanzas.shared.logging import configure_logging, get_logger

logger = get_logger("seed")


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    from finanzas.core.db import assert_migrated, wait_for_db

    wait_for_db(timeout_seconds=15)
    assert_migrated()
    with session_scope() as session:
        user = ensure_default_user(session, settings.default_user_email)
        logger.info("seed_done", user=user.email)
    print(f"Usuario por defecto listo: {settings.default_user_email}")


if __name__ == "__main__":
    main()
