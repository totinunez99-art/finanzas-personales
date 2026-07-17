"""Motor de Insights y financial_summary contra PostgreSQL real (Sprint 3, B1).

Dataset determinista: abril y mayo 2026 (meses CERRADOS → días fijos).
Los valores esperados están calculados a mano; el test NO acepta la salida
del motor como verdad (docs/13 §5.1 aplicado a lógica de negocio).
"""

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
    from finanzas.core.models import Account, Transaction, User
    from finanzas.core.services.dedup import compute_dedup_hash, normalize_description

    with Session(migrated_engine) as session:
        user = User(email=f"ins-{uuid.uuid4().hex[:8]}@example.com")
        session.add(user)
        session.flush()
        account = Account(
            user_id=user.id, name="Cta", bank="edwards", type="checking", currency="CLP"
        )
        session.add(account)
        session.flush()

        def add(posted: date, amount: str, desc: str, merchant: str | None = None) -> None:
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
                    merchant=merchant,
                    status="confirmed",
                    source="statement",
                    source_ref=f"t:{desc}:{posted}",
                    dedup_hash=compute_dedup_hash(
                        str(account.id), posted, Decimal(amount), "CLP", norm
                    ),
                )
            )

        # MARZO: 3 cargos, cero abonos (para flujo_negativo)
        add(date(2026, 3, 5), "-10000", "CARGO A")
        add(date(2026, 3, 10), "-20000", "CARGO B")
        add(date(2026, 3, 15), "-30000", "CARGO C")

        # ABRIL (mes base de comparación): abono 800.000, cargos 500.000 en 3 movs
        add(date(2026, 4, 1), "800000", "SUELDO ABRIL")
        add(date(2026, 4, 5), "-100000", "GASTO ABRIL 1")
        add(date(2026, 4, 12), "-200000", "GASTO ABRIL 2")
        add(date(2026, 4, 20), "-200000", "GASTO ABRIL 3")

        # MAYO (mes objetivo): abono 1.000.000, 12 cargos = 685.000
        add(date(2026, 5, 1), "1000000", "SUELDO MAYO")
        add(date(2026, 5, 1), "-200000", "ARRIENDO")
        add(date(2026, 5, 3), "-20000", "GASTO X")
        add(date(2026, 5, 6), "-5000", "UBER VIAJE", merchant="UBER")
        add(date(2026, 5, 9), "-40000", "GASTO Y")
        add(date(2026, 5, 10), "-30000", "RESTAURANT Z")
        add(date(2026, 5, 13), "-5000", "UBER VIAJE 2", merchant="UBER")
        add(date(2026, 5, 15), "-300000", "COMPRA GRANDE LIDER")
        add(date(2026, 5, 18), "-15000", "GASTO W")
        add(date(2026, 5, 20), "-5000", "UBER VIAJE 3", merchant="UBER")
        add(date(2026, 5, 24), "-25000", "GASTO V")
        add(date(2026, 5, 27), "-5000", "UBER VIAJE 4", merchant="UBER")
        add(date(2026, 5, 30), "-35000", "GASTO U")
        session.commit()
        yield session, user, account


def _by_id(insights, prefix):  # type: ignore[no-untyped-def]
    return {i.id.split(":")[0]: i for i in insights}


def test_insights_mayo_valores_exactos(dataset) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.services.insights import generate_insights

    session, user, _ = dataset
    insights = generate_insights(session, user, period="2026-05")
    by_kind = _by_id(insights, "")

    # Gasto vs mes anterior: (685000-500000)/500000 = +37% → warning (>=25)
    g = by_kind["gasto_vs_mes_anterior"]
    assert g.severity == "warning" and g.data["delta_pct"] == "37.0"
    assert g.data["actual"] == "685000" and g.data["anterior"] == "500000"

    # Promedio diario: 685000/31 = 22096.77 → 22097 (mes cerrado = 31 días)
    p = by_kind["promedio_diario"]
    assert p.data["dias"] == 31 and "22.097" in p.title

    # Concentración top-3: (300000+200000+40000)/685000 = 78.8% → notable (>=50)
    c = by_kind["concentracion_top3"]
    assert c.data["pct"] == "78.8" and c.severity == "notable"

    # Comercio frecuente: UBER 4 veces, $20.000
    f = by_kind["comercio_frecuente"]
    assert f.data["comercio"] == "UBER" and f.data["apariciones"] == 4

    # Día más caro: 15/05 con 300.000
    d = by_kind["dia_mas_caro"]
    assert d.data["fecha"] == "2026-05-15" and d.data["total"] == "300000"

    # Día de la semana: presente (12 cargos >= umbral 10) y con total coherente
    assert "dia_semana_gasto" in by_kind

    # Compras vs mes anterior: 12 vs 3 → "más"
    assert by_kind["compras_vs_mes_anterior"].data == {"n_actual": 12, "n_anterior": 3}

    # NO debe haber flujo negativo (ingresos 1M > gastos 685k) ni insights inventados
    assert "flujo_negativo" not in by_kind
    # Cada insight es explicable y de una sola moneda
    assert all(i.explanation and i.currency == "CLP" for i in insights)


def test_flujo_negativo_y_meses_sin_evidencia(dataset) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.services.insights import generate_insights

    session, user, _ = dataset
    marzo = generate_insights(session, user, period="2026-03")
    kinds = {i.id.split(":")[0] for i in marzo}
    assert "flujo_negativo" in kinds  # 60.000 en cargos, 0 ingresos → warning
    # y NO hay comparación (febrero vacío) ni concentración (solo 3 cargos < 5)
    assert "gasto_vs_mes_anterior" not in kinds
    assert "concentracion_top3" not in kinds

    # Mes sin datos: silencio total, jamás inventar
    assert generate_insights(session, user, period="2026-01") == []


def test_financial_summary_deltas_honestos(dataset) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.services.reporting import financial_summary

    session, user, _ = dataset
    s = financial_summary(session, user, period="2026-05")
    clp = next(c for c in s["by_currency"] if c["currency"] == "CLP")
    assert clp["expense"] == "685000" and clp["income"] == "1000000"
    assert clp["net"] == "315000" and clp["savings_rate_pct"] == "31.5"
    assert clp["expense_delta_pct"] == "37.0" and clp["income_delta_pct"] == "25.0"
    assert clp["count_delta"] == 13 - 4
    assert clp["avg_daily_expense"] == "22097" and s["days_in_scope"] == 31

    # Abril no tiene base (marzo sin abonos): income_delta debe ser None, no infinito
    s_abril = financial_summary(session, user, period="2026-04")
    clp_abril = next(c for c in s_abril["by_currency"] if c["currency"] == "CLP")
    assert clp_abril["income_delta_pct"] is None
    assert clp_abril["expense_delta_pct"] is not None  # marzo sí tuvo cargos
