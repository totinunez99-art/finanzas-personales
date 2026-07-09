"""Filtros y estadísticas del dashboard contra PostgreSQL real (Sprint 2)."""

import os
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

TEST_URL = os.environ.get("TEST_DATABASE_URL", "")


@pytest.fixture(scope="module")
def migrated_engine():  # type: ignore[no-untyped-def]
    from alembic import command
    from alembic.config import Config

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
def dataset(migrated_engine):  # type: ignore[no-untyped-def]
    """Usuario con 5 movimientos de junio 2026 (4 CLP + 1 USD) y 1 de julio."""
    from finanzas.core.models import Account, Transaction, User
    from finanzas.core.services.dedup import compute_dedup_hash, normalize_description

    with Session(migrated_engine) as session:
        user = User(email=f"rep-{uuid.uuid4().hex[:8]}@example.com")
        session.add(user)
        session.flush()
        account = Account(
            user_id=user.id, name="Cta", bank="edwards", type="checking", currency="CLP"
        )
        session.add(account)
        session.flush()

        def add(posted: date, amount: str, desc: str, currency: str = "CLP") -> None:
            norm = normalize_description(desc)
            session.add(
                Transaction(
                    user_id=user.id,
                    account_id=account.id,
                    posted_at=posted,
                    amount=Decimal(amount),
                    currency=currency,
                    description_raw=desc,
                    description_norm=norm,
                    status="confirmed",
                    source="statement",
                    source_ref=f"t:{desc}:{posted}",
                    dedup_hash=compute_dedup_hash(
                        str(account.id), posted, Decimal(amount), currency, norm
                    ),
                )
            )

        add(date(2026, 6, 1), "1000000", "SUELDO EMPRESA")
        add(date(2026, 6, 5), "-45990", "COMPRA SUPERMERCADO LÍDER")
        add(date(2026, 6, 10), "-4500", "CAFÉ ÑUÑOA")
        add(date(2026, 6, 20), "-350000", "PAGO ARRIENDO")
        add(date(2026, 6, 15), "-45.90", "COMPRA AMAZON", currency="USD")
        add(date(2026, 7, 2), "-9990", "SUSCRIPCION JULIO")
        session.commit()
        yield session, user, account


def test_filtros(dataset) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.services.reporting import TransactionFilters, list_transactions

    session, user, _account = dataset

    total, _ = list_transactions(session, user, TransactionFilters())
    assert total == 6

    # Búsqueda insensible a tildes y caso: "cafe nunoa" encuentra "CAFÉ ÑUÑOA".
    total, rows = list_transactions(session, user, TransactionFilters(q="cafe nunoa"))
    assert total == 1 and rows[0].description_raw == "CAFÉ ÑUÑOA"

    # Tipo cargo/abono.
    total, _ = list_transactions(session, user, TransactionFilters(kind="abono"))
    assert total == 1
    total, _ = list_transactions(session, user, TransactionFilters(kind="cargo"))
    assert total == 5

    # Rango de fechas (solo junio).
    total, _ = list_transactions(
        session,
        user,
        TransactionFilters(date_from=date(2026, 6, 1), date_to=date(2026, 6, 30)),
    )
    assert total == 5

    # Monto por magnitud: entre 10.000 y 100.000 → solo el supermercado (45.990).
    total, rows = list_transactions(
        session,
        user,
        TransactionFilters(amount_min=Decimal("10000"), amount_max=Decimal("100000")),
    )
    assert total == 1 and "SUPERMERCADO" in rows[0].description_norm

    # Combinación: cargos de junio bajo $10.000 → solo el café.
    total, rows = list_transactions(
        session,
        user,
        TransactionFilters(
            kind="cargo",
            date_from=date(2026, 6, 1),
            date_to=date(2026, 6, 30),
            amount_max=Decimal("10000"),
        ),
    )
    assert total == 2  # café CLP (4.500) y Amazon USD (45.90): la magnitud no distingue moneda
    # ^ comportamiento documentado: el filtro de monto es ciego a la moneda (ver docs/17)


def test_stats_por_moneda(dataset) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.services.reporting import stats_summary

    session, user, _account = dataset
    stats = stats_summary(session, user, period="2026-06")

    assert stats["period"] == "2026-06"
    assert stats["total_count"] == 5
    clp = next(c for c in stats["by_currency"] if c["currency"] == "CLP")
    assert clp["income"] == "1000000"
    assert clp["expense"] == "400490"  # 45990 + 4500 + 350000
    assert clp["net"] == "599510"
    assert clp["count"] == 4
    usd = next(c for c in stats["by_currency"] if c["currency"] == "USD")
    assert usd["expense"] == "45.9" and usd["count"] == 1  # canonico sin cero final

    # Mes sin movimientos: vacío pero válido.
    empty = stats_summary(session, user, period="2025-01")
    assert empty["by_currency"] == [] and empty["total_count"] == 0

    # last_import: aún sin batches en este dataset.
    assert stats["last_import"] is None
