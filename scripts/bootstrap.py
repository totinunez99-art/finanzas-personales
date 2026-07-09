"""Bootstrap one-shot del sistema (servicio 'bootstrap' de docker-compose).

Secuencia: esperar PostgreSQL → migrar (Alembic) → usuario por defecto.
Idempotente por diseño: Alembic no re-aplica revisiones; el seed no duplica.
Sale con código != 0 ante cualquier fallo → compose NO inicia api/worker
(service_completed_successfully).

Uso manual (dev local): python scripts/bootstrap.py
"""

import sys

from alembic import command
from alembic.config import Config

from finanzas.core.db import session_scope, wait_for_db
from finanzas.core.services.bootstrap import ensure_default_user
from finanzas.shared.config import get_settings
from finanzas.shared.errors import ConfigError
from finanzas.shared.logging import configure_logging, get_logger

logger = get_logger("bootstrap")


def main() -> int:
    settings = get_settings()
    configure_logging(settings)

    logger.info("bootstrap_started")
    try:
        wait_for_db(timeout_seconds=60)
        logger.info("db_ready")

        command.upgrade(Config("alembic.ini"), "head")
        logger.info("migrations_applied")

        with session_scope() as session:
            user = ensure_default_user(session, settings.default_user_email)
            logger.info("default_user_ready", email=user.email)
    except ConfigError as exc:
        logger.error("bootstrap_failed", detail=exc.message)
        print(f"\nBOOTSTRAP FALLÓ: {exc.message}\n", file=sys.stderr)
        return 1
    except Exception as exc:  # cualquier fallo debe bloquear el arranque, no esconderse
        logger.error("bootstrap_failed", error=str(exc), exc_info=True)
        print(
            f"\nBOOTSTRAP FALLÓ: {exc}\nVer: docs/15-instalacion-y-troubleshooting.md\n",
            file=sys.stderr,
        )
        return 1

    logger.info("bootstrap_completed")
    print("Bootstrap OK: base migrada y usuario por defecto listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
