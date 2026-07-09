"""Demo Mode: puebla el sistema con datos 100% FICTICIOS en minutos.

Idempotente: correrlo N veces deja el mismo estado (dedup por archivo y por
transacción). Demuestra además el dedup real: demo_julio.csv trae una fila que
ya existe en junio y debe reportarse como duplicada.

Uso (con la DB migrada y accesible):
    python scripts/demo.py
Luego abre el dashboard y arrastra scripts/demo_data/demo_agosto_para_wizard.csv
en la página Importar para probar el flujo manual completo.
"""

from pathlib import Path

from finanzas.core.db import session_scope
from finanzas.core.services import import_service
from finanzas.core.services.bootstrap import ensure_account, ensure_default_user
from finanzas.shared.config import get_settings
from finanzas.shared.errors import AlreadyImportedError
from finanzas.shared.logging import configure_logging, get_logger

logger = get_logger("demo")

DEMO_ACCOUNT_NAME = "Cuenta Demo (datos ficticios)"
DEMO_FILES = ("demo_junio.csv", "demo_julio.csv")  # demo_agosto queda para el wizard manual


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    from finanzas.core.db import assert_migrated, wait_for_db

    wait_for_db(timeout_seconds=15)
    assert_migrated()  # nunca asumir tablas existentes: mensaje claro si falta migrar
    data_dir = Path(__file__).resolve().parent / "demo_data"

    with session_scope() as session:
        user = ensure_default_user(session, settings.default_user_email)
        account, created = ensure_account(
            session, user, DEMO_ACCOUNT_NAME, bank="demo", account_type="checking", currency="CLP"
        )
        print(f"Cuenta demo {'creada' if created else 'ya existía'}: {account.name}")

        for filename in DEMO_FILES:
            content = (data_dir / filename).read_bytes()
            try:
                batch = import_service.import_statement(
                    session, user, account.id, filename, content
                )
                print(
                    f"  {filename}: {batch.rows_inserted} insertados, "
                    f"{batch.rows_duplicated} duplicados omitidos"
                )
            except AlreadyImportedError:
                print(f"  {filename}: ya estaba importado (idempotencia OK)")

    print(
        "\nDemo lista. Abre http://localhost:8501 → Movimientos.\n"
        "Prueba manual del wizard: arrastra scripts/demo_data/demo_agosto_para_wizard.csv\n"
        "en la página Importar (cuenta: Cuenta Demo)."
    )


if __name__ == "__main__":
    main()
