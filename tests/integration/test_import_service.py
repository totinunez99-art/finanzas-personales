"""Ciclo completo del Import Wizard contra PostgreSQL real (docs/14).

Cubre el criterio de éxito del sprint a nivel de servicio: preview → confirmar
→ dedup en reimportación → archivo desconocido registrado.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

TEST_URL = os.environ.get("TEST_DATABASE_URL", "")

CSV = (
    b"fecha;descripcion;monto\n"
    b"2026-06-01;COMPRA SUPERMERCADO;-45.990\n"
    b"2026-06-07;CAFE STARBUCKS;-4.500\n"
    b"2026-06-07;CAFE STARBUCKS;-4.500\n"
)

CSV_SEGUNDO_MES = (
    b"fecha;descripcion;monto\n"
    b"2026-06-07;CAFE STARBUCKS;-4.500\n"  # ya existe (seq 0) → duplicado
    b"2026-07-01;PAGO SUELDO;1.000.000\n"  # nuevo
)


@pytest.fixture()
def session(migrated_engine) -> Session:  # type: ignore[no-untyped-def]
    with Session(migrated_engine) as s:
        yield s


@pytest.fixture(scope="module")
def migrated_engine():  # type: ignore[no-untyped-def]
    # Reusa el esquema migrado por tests/integration/test_schema.py si corre antes;
    # si corre solo, migra desde cero.
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    engine = create_engine(TEST_URL)
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_URL)
    command.upgrade(cfg, "head")
    yield engine
    engine.dispose()


@pytest.fixture()
def user_account(session: Session):  # type: ignore[no-untyped-def]
    from finanzas.core.models import Account, User

    user = User(email=f"wizard-{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    session.flush()
    account = Account(
        user_id=user.id, name="Corriente", bank="generic", type="checking", currency="CLP"
    )
    session.add(account)
    session.flush()
    return user, account


def test_flujo_completo_con_dedup(session: Session, user_account) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.models import Transaction
    from finanzas.core.services import import_service
    from finanzas.shared.errors import AlreadyImportedError

    user, account = user_account

    # 1. Preview: reconoce, muestra, no escribe transacciones.
    result = import_service.preview(session, user, "junio.csv", CSV, account.id)
    assert result.recognized and result.total_rows == 3 and result.duplicates_in_db == 0
    assert session.execute(select(Transaction)).scalars().first() is None

    # 2. Confirmar: inserta 3 (los dos cafés idénticos entran por intra_day_seq).
    batch = import_service.import_statement(session, user, account.id, "junio.csv", CSV)
    assert (batch.rows_read, batch.rows_inserted, batch.rows_duplicated) == (3, 3, 0)
    # Trazabilidad de parser (sesión 11): versión, formato y validación registrados.
    assert batch.parser_version == "1.1.0"
    assert batch.detected_format == "generic_csv_v1"
    assert batch.validation is not None and batch.validation["passed"] is True
    assert batch.extraction_confidence is not None

    # 3. Reimportar el MISMO archivo: rechazado explícito, no silencioso.
    with pytest.raises(AlreadyImportedError):
        import_service.import_statement(session, user, account.id, "junio.csv", CSV)

    # 4. Archivo distinto con una fila ya existente: dedup por transacción.
    batch2 = import_service.import_statement(
        session, user, account.id, "julio.csv", CSV_SEGUNDO_MES
    )
    assert (batch2.rows_read, batch2.rows_inserted, batch2.rows_duplicated) == (2, 1, 1)

    total = session.execute(select(Transaction)).scalars().all()
    assert len(total) == 4


def test_formato_desconocido_no_falla_y_se_registra(session: Session, user_account) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.models import UnrecognizedFile
    from finanzas.core.services import import_service

    user, _account = user_account
    content = b"col1,col2\n1,2\n"
    result = import_service.preview(session, user, "misterio.csv", content)
    assert not result.recognized
    assert "no es compatible" in result.message

    registered = session.execute(select(UnrecognizedFile)).scalars().all()
    assert len(registered) == 1
    # Reintento: no duplica el registro.
    import_service.preview(session, user, "misterio.csv", content)
    assert len(session.execute(select(UnrecognizedFile)).scalars().all()) == 1
