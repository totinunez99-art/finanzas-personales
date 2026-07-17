"""Integración con PostgreSQL real: migraciones y anti-deriva modelos↔migración.

Requiere TEST_DATABASE_URL apuntando a una base VACÍA y desechable (la CI la
provee como service container). Se salta silenciosamente si no está definida.
"""

import os
import uuid
from datetime import date
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

TEST_URL = os.environ.get("TEST_DATABASE_URL", "")


@pytest.fixture(scope="module")
def migrated_engine():  # type: ignore[no-untyped-def]
    engine = create_engine(TEST_URL)
    # Base limpia y migrada.
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_URL)
    command.upgrade(cfg, "head")
    yield engine
    engine.dispose()


def test_upgrade_head_aplica(migrated_engine) -> None:  # type: ignore[no-untyped-def]
    with migrated_engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert version == "0005"


def test_sin_deriva_entre_modelos_y_migracion(migrated_engine) -> None:  # type: ignore[no-untyped-def]
    """La migración escrita a mano debe producir EXACTAMENTE el esquema de los
    modelos. Si autogenerate propone cambios, hay deriva y este test falla."""
    from alembic.autogenerate import compare_metadata
    from alembic.runtime.migration import MigrationContext

    from finanzas.core.models import Base

    with migrated_engine.connect() as conn:
        context = MigrationContext.configure(conn, opts={"compare_type": True})
        diff = compare_metadata(context, Base.metadata)

    # La reflexión de índices GIN con opclass (pg_trgm) es poco confiable en
    # autogenerate: se excluye ese índice puntual de la comparación. El resto
    # del esquema se compara completo.
    diff = [d for d in diff if "ix_transactions_description_norm_trgm" not in repr(d)]
    assert diff == [], f"Deriva modelos↔migración: {diff}"


def test_ciclo_basico_de_escritura(migrated_engine) -> None:  # type: ignore[no-untyped-def]
    """Round-trip mínimo: user → account → transaction, y unicidad de dedup_hash."""
    from sqlalchemy.exc import IntegrityError

    from finanzas.core.models import Account, Transaction, User
    from finanzas.core.services.dedup import compute_dedup_hash, normalize_description

    with Session(migrated_engine) as session:
        user = User(email=f"test-{uuid.uuid4().hex[:8]}@example.com")
        session.add(user)
        session.flush()
        account = Account(
            user_id=user.id, name="Cuenta test", bank="testbank", type="checking", currency="CLP"
        )
        session.add(account)
        session.flush()

        description = normalize_description("Compra Líder Ñuñoa")
        dedup = compute_dedup_hash(
            str(account.id), date(2026, 7, 1), Decimal("-12500"), "CLP", description
        )

        def make_tx() -> Transaction:
            return Transaction(
                user_id=user.id,
                account_id=account.id,
                posted_at=date(2026, 7, 1),
                amount=Decimal("-12500"),
                currency="CLP",
                description_raw="Compra Líder Ñuñoa",
                description_norm=description,
                status="confirmed",
                source="statement",
                source_ref="test:1",
                dedup_hash=dedup,
            )

        session.add(make_tx())
        session.commit()

        stored = session.execute(
            select(Transaction).where(Transaction.dedup_hash == dedup)
        ).scalar_one()
        assert stored.amount == Decimal("-12500")

        # El duplicado debe rebotar en la DB, no depender de la aplicación (docs/03 §4).
        session.add(make_tx())
        with pytest.raises(IntegrityError):
            session.commit()
