"""Analytics + naturaleza del movimiento contra PostgreSQL real (docs/23 · docs/25).

Valores esperados calculados A MANO. Verifica además que los movimientos que NO
cambian el patrimonio (nature=internal/debt/lending/asset) quedan fuera de KPIs.
"""

import os
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select, text
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
    """Mayo 2026 con pipeline completo (merchant→category→nature) sobre datos crudos."""
    from finanzas.core.models import Account, Transaction, User
    from finanzas.core.services.dedup import compute_dedup_hash, normalize_description
    from finanzas.core.services.resolution import pipeline

    with Session(migrated_engine) as session:
        user = User(email=f"an-{uuid.uuid4().hex[:8]}@example.com")
        session.add(user)
        session.flush()
        account = Account(
            user_id=user.id, name="Cta", bank="edwards", type="checking", currency="CLP"
        )
        session.add(account)
        session.flush()

        def add(posted: date, amount: str, desc: str) -> None:
            norm = normalize_description(desc)
            session.add(
                Transaction(
                    user_id=user.id,
                    account_id=account.id,
                    posted_at=posted,
                    amount=Decimal(amount),
                    currency="CLP",
                    description_raw=desc,
                    description_norm=norm,
                    status="confirmed",
                    source="statement",
                    source_ref=f"t:{desc}:{posted}",
                    intra_day_seq=hash(desc) % 997,
                    dedup_hash=compute_dedup_hash(
                        str(account.id),
                        posted,
                        Decimal(amount),
                        "CLP",
                        norm,
                        hash(desc) % 997,
                    ),
                )
            )

        # ABRIL (base): supermercado 100.000
        add(date(2026, 4, 10), "-100000", "COMPRA SUPERMERCADO LIDER ABR")
        add(date(2026, 4, 1), "800000", "SUELDO ABRIL EMPRESA")
        # MAYO: operacionales
        add(date(2026, 5, 1), "1000000", "SUELDO MAYO EMPRESA")  # income (SUELDO)
        add(date(2026, 5, 5), "-150000", "COMPRA SUPERMERCADO LIDER STGO")  # LIDER→Supermercado
        add(date(2026, 5, 12), "-50000", "PAGO:COPEC APP LOCAL")  # COPEC→Combustible
        add(date(2026, 5, 20), "-30000", "COMPRA FARMACIA CRUZ VERDE")  # →Salud
        # MAYO: INTERNO — pago de tarjeta NO debe contar como gasto
        add(date(2026, 5, 22), "-500000", "CARGO POR PAGO TC")
        session.commit()

        pipeline.run(session, user)  # merchant → category → nature
        session.commit()
        yield session, user, account


def test_flujo_interno_excluido_de_kpis(dataset) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.models import Transaction
    from finanzas.core.services.reporting import financial_summary

    session, user, _ = dataset
    pago_tc = session.execute(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.description_norm == "CARGO POR PAGO TC",
        )
    ).scalar_one()
    assert pago_tc.nature == "internal"  # asignado por NatureStage (ADR-011)

    s = financial_summary(session, user, period="2026-05")
    clp = next(c for c in s["by_currency"] if c["currency"] == "CLP")
    # Gasto = 150.000+50.000+30.000 = 230.000 (SIN los 500.000 del pago TC)
    assert clp["expense"] == "230000"
    assert clp["income"] == "1000000"
    assert clp["count"] == 4  # 3 cargos operacionales + sueldo


def test_analytics_responde_las_preguntas(dataset) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.services.analytics import overview

    session, user, _ = dataset
    data = overview(session, user, period="2026-05")

    assert data["total_operational_expense"] == "230000"

    categories = {c["category"]: c for c in data["categories"]}
    assert categories["Supermercado"]["total"] == "150000"
    assert categories["Supermercado"]["pct"] == "65.2"  # 150000/230000
    assert categories["Combustible"]["pct"] == "21.7"
    assert "Pago de Tarjeta" not in categories  # interno: fuera

    merchants = {m["merchant"]: m for m in data["merchants"]}
    assert merchants["LIDER"]["total"] == "150000"
    assert merchants["COPEC"]["count"] == 1

    assert data["most_expensive_day"]["date"] == "2026-05-05"
    assert data["most_expensive_day"]["expense"] == "150000"

    # Crecimiento: Supermercado 100.000 → 150.000 = +50%
    grew = {d["category"]: d for d in data["grew"]}
    assert grew["Supermercado"]["delta_pct"] == "50.0"

    # Comercios nuevos en mayo: COPEC y CRUZ VERDE (LIDER ya existía en abril)
    news = {n["merchant"] for n in data["new_merchants"]}
    assert "COPEC" in news and "CRUZ VERDE" in news and "LIDER" not in news

    # Anomalías: historia (abril) tiene 1 cargo < 10 → honestidad, no inventar
    assert data["anomalies"] == [] and "insuficiente" in data["anomalies_note"]

    # Flujo de caja acumulado del último día = ingresos - gastos operacionales
    assert data["daily"][-1]["cumulative_net"] == "770000"  # 1.000.000 - 230.000


def test_dry_run_encadena_gracias_al_savepoint(dataset) -> None:  # type: ignore[no-untyped-def]
    """La revisión de sesión 17: en dry-run, category VE el merchant propuesto."""
    from finanzas.core.models import Account, ClassificationDecision, Transaction, User
    from finanzas.core.services.dedup import compute_dedup_hash, normalize_description
    from finanzas.core.services.resolution import pipeline

    session, _user, _ = dataset
    # usuario nuevo, transacción cruda: nada resuelto aún
    u2 = User(email=f"an2-{uuid.uuid4().hex[:8]}@example.com")
    session.add(u2)
    session.flush()
    a2 = Account(user_id=u2.id, name="C2", bank="edwards", type="checking", currency="CLP")
    session.add(a2)
    session.flush()
    norm = normalize_description("PAGO:COPEC APP X")
    session.add(
        Transaction(
            user_id=u2.id,
            account_id=a2.id,
            posted_at=date(2026, 5, 3),
            amount=Decimal("-9000"),
            currency="CLP",
            description_raw="PAGO:COPEC APP X",
            description_norm=norm,
            status="confirmed",
            source="statement",
            source_ref="t:x",
            dedup_hash=compute_dedup_hash(
                str(a2.id), date(2026, 5, 3), Decimal("-9000"), "CLP", norm
            ),
        )
    )
    session.commit()

    report = pipeline.run(session, u2, dry_run=True)
    session.commit()
    # category y nature aplicaron EN LA SIMULACIÓN (encadenado con merchant)
    assert report["stages"]["category"]["applied"] == 1
    assert report["stages"]["nature"]["applied"] == 1
    # ...y NADA persistió (savepoint revertido): ni cambios ni decisiones ni semillas
    tx = session.execute(select(Transaction).where(Transaction.user_id == u2.id)).scalar_one()
    assert tx.merchant is None and tx.category_id is None and tx.nature is None
    assert (
        session.execute(
            select(ClassificationDecision).where(ClassificationDecision.user_id == u2.id)
        )
        .scalars()
        .all()
        == []
    )


def test_linea_de_credito_no_es_ingreso_ni_gasto(migrated_engine):  # type: ignore[no-untyped-def]
    """Sprint 4 F1 (ADR-011): el caso REAL que refutó el modelo anterior.

    Un giro de línea de crédito ENTRA plata pero es deuda; su pago SALE plata pero
    extingue deuda. Con el flow binario ambos contaminaban ingreso y gasto
    (evidencia: docs/24 §6). Valores calculados a mano.
    """
    from finanzas.core.models import Account, Transaction, User
    from finanzas.core.services.dedup import compute_dedup_hash, normalize_description
    from finanzas.core.services.reporting import financial_summary
    from finanzas.core.services.resolution import pipeline

    with Session(migrated_engine) as session:
        user = User(email=f"linea-{uuid.uuid4().hex[:6]}@example.com", display_name="Linea")
        session.add(user)
        session.flush()
        account = Account(
            user_id=user.id, name="CC Edwards", bank="bancochile", type="checking", currency="CLP"
        )
        session.add(account)
        session.flush()

        movimientos = [
            ("TRANSFERENCIA DESDE LINEA DE CREDI", Decimal("300000")),  # deuda tomada
            ("PAGO LINEA DE CRED:012850313500", Decimal("-300000")),  # deuda pagada
            ("INTERESES LINEA DE CREDITO", Decimal("-5000")),  # costo financiero: SI es gasto
            ("PAGO:UNIMARC PIN DE MO", Decimal("-40000")),  # consumo real
        ]
        for index, (descripcion, monto) in enumerate(movimientos):
            norm = normalize_description(descripcion)
            session.add(
                Transaction(
                    user_id=user.id,
                    account_id=account.id,
                    posted_at=date(2026, 5, 10),
                    amount=monto,
                    currency="CLP",
                    description_raw=descripcion,
                    description_norm=norm,
                    status="confirmed",
                    source="statement",
                    source_ref=f"linea:{index}",
                    dedup_hash=compute_dedup_hash(
                        str(account.id), date(2026, 5, 10), monto, "CLP", norm, index
                    ),
                )
            )
        session.commit()

        pipeline.run(session, user)
        session.commit()

        naturalezas = {
            t.description_raw: t.nature
            for t in session.execute(
                select(Transaction).where(Transaction.user_id == user.id)
            ).scalars()
        }
        assert naturalezas["TRANSFERENCIA DESDE LINEA DE CREDI"] == "debt"
        assert naturalezas["PAGO LINEA DE CRED:012850313500"] == "debt"
        assert naturalezas["INTERESES LINEA DE CREDITO"] == "finance_cost"
        assert naturalezas["PAGO:UNIMARC PIN DE MO"] == "expense"

        resumen = financial_summary(session, user, period="2026-05")
        clp = next(c for c in resumen["by_currency"] if c["currency"] == "CLP")
        assert clp["income"] == "0"  # los 300.000 de la linea NO son ingreso
        assert clp["expense"] == "45000"  # 40.000 consumo + 5.000 costo financiero
