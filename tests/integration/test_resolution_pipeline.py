"""Resolution Pipeline: contrato único, orden, dry-run, ADR-008 (Sprint 3 B3)."""

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
    from finanzas.core.models import Account, Transaction, User
    from finanzas.core.services.dedup import compute_dedup_hash, normalize_description

    with Session(migrated_engine) as session:
        user = User(email=f"rp-{uuid.uuid4().hex[:8]}@example.com")
        session.add(user)
        session.flush()
        account = Account(
            user_id=user.id, name="Cta", bank="edwards", type="checking", currency="CLP"
        )
        session.add(account)
        session.flush()

        def add(desc: str) -> None:
            norm = normalize_description(desc)
            session.add(
                Transaction(
                    user_id=user.id,
                    account_id=account.id,
                    posted_at=date(2026, 6, 10),
                    amount=Decimal("-5000"),
                    currency="CLP",
                    description_raw=desc,
                    description_norm=norm,
                    status="confirmed",
                    source="statement",
                    source_ref=f"t:{desc}",
                    intra_day_seq=hash(desc) % 1000,
                    dedup_hash=compute_dedup_hash(
                        str(account.id),
                        date(2026, 6, 10),
                        Decimal("-5000"),
                        "CLP",
                        norm,
                        hash(desc) % 1000,
                    ),
                )
            )

        add("PAGO:COPEC APP BQUE MONTEMAR")  # merchant→COPEC, category→Combustible
        add("ARRIENDO DEPTO CENTRO")  # sin merchant; category por descripción
        add("COMPRA MISTERIOSA XYZ")  # nada resuelve
        session.commit()
        yield session, user, account


def test_encadenamiento_merchant_luego_categoria(dataset) -> None:  # type: ignore[no-untyped-def]
    """La etapa category usa el merchant resuelto por la etapa ANTERIOR en la
    MISMA corrida: la tubería enriquece incrementalmente (requisito central)."""
    from finanzas.core.models import Category, ClassificationDecision, Transaction
    from finanzas.core.services.resolution import pipeline

    session, user, _ = dataset
    report = pipeline.run(session, user)  # orden por flag: merchant,category
    session.commit()

    assert report["order"] == ["merchant", "category", "flow"]
    tx = session.execute(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.description_norm == "PAGO:COPEC APP BQUE MONTEMAR",
        )
    ).scalar_one()
    assert tx.merchant == "COPEC" and tx.classified_by == "rule"
    category = session.get(Category, tx.category_id)
    assert category.name == "Combustible"

    # Auditoría ADR-008: decisión vigente con rule_id y confianza
    decision = session.execute(
        select(ClassificationDecision).where(
            ClassificationDecision.transaction_id == tx.id,
            ClassificationDecision.is_current,
        )
    ).scalar_one()
    assert decision.decided_by == "rule" and decision.rule_id is not None
    assert decision.confidence == Decimal("0.95")  # seed merchant_exact

    arriendo = session.execute(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.description_norm == "ARRIENDO DEPTO CENTRO",
        )
    ).scalar_one()
    cat2 = session.get(Category, arriendo.category_id)
    assert cat2.name == "Arriendo y Vivienda"

    misterio = session.execute(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.description_norm == "COMPRA MISTERIOSA XYZ",
        )
    ).scalar_one()
    assert misterio.category_id is None and misterio.merchant is None


def test_dry_run_no_escribe_y_reporta(dataset) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.models import ClassificationDecision, Transaction
    from finanzas.core.services.resolution import pipeline

    session, user, _ = dataset
    report = pipeline.run(session, user, dry_run=True)
    session.commit()

    assert report["dry_run"] is True
    assert report["stages"]["merchant"]["applied"] >= 1
    assert report["samples"], "dry-run debe mostrar propuestas"
    assert all("duration_ms" in s for s in report["samples"])

    # NADA escrito
    txs = session.execute(select(Transaction).where(Transaction.user_id == user.id)).scalars().all()
    assert all(t.category_id is None for t in txs)
    decisions = (
        session.execute(
            select(ClassificationDecision).where(ClassificationDecision.user_id == user.id)
        )
        .scalars()
        .all()
    )
    assert decisions == []


def test_orden_configurable_y_resolver_unico(dataset) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.models import Transaction
    from finanzas.core.services.resolution import pipeline
    from finanzas.shared.errors import ConfigError

    session, user, _ = dataset
    # Solo category, sin merchant previo: COPEC no clasifica (regla es merchant_exact)
    report = pipeline.run(session, user, resolvers=["category"])
    session.commit()
    tx = session.execute(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.description_norm == "PAGO:COPEC APP BQUE MONTEMAR",
        )
    ).scalar_one()
    assert tx.category_id is None  # sin etapa merchant, la evidencia no existe
    assert report["order"] == ["category"]

    # Stubs ejecutables sin efectos y orden inválido rechazado explícitamente
    report2 = pipeline.run(session, user, resolvers=["anomaly", "ai"])
    assert report2["stages"]["ai"]["skipped"] == report2["transactions"]
    with pytest.raises(ConfigError):
        pipeline.run(session, user, resolvers=["inexistente"])


def test_decision_usuario_protegida_e_idempotencia(dataset) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.models import Category, ClassificationDecision, Transaction
    from finanzas.core.services.resolution import pipeline

    session, user, _ = dataset
    pipeline.run(session, user)
    session.commit()

    # Re-run: idempotente (no nuevas decisiones)
    before = len(
        session.execute(
            select(ClassificationDecision).where(ClassificationDecision.user_id == user.id)
        )
        .scalars()
        .all()
    )
    pipeline.run(session, user)
    session.commit()
    after = len(
        session.execute(
            select(ClassificationDecision).where(ClassificationDecision.user_id == user.id)
        )
        .scalars()
        .all()
    )
    assert after == before

    # Decisión del usuario: intocable aunque la regla diga otra cosa
    tx = session.execute(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.description_norm == "PAGO:COPEC APP BQUE MONTEMAR",
        )
    ).scalar_one()
    otra = session.execute(
        select(Category).where(Category.user_id == user.id, Category.name == "Otros Gastos")
    ).scalar_one()
    old = session.execute(
        select(ClassificationDecision).where(
            ClassificationDecision.transaction_id == tx.id, ClassificationDecision.is_current
        )
    ).scalar_one()
    old.is_current = False
    user_decision = ClassificationDecision(
        user_id=user.id,
        transaction_id=tx.id,
        decided_by="user",
        category_id=otra.id,
        is_current=True,
    )
    session.add(user_decision)
    session.flush()
    old.superseded_by_id = user_decision.id
    tx.category_id = otra.id
    tx.classified_by = "user"
    session.commit()

    pipeline.run(session, user)
    session.commit()
    session.refresh(tx)
    assert tx.category_id == otra.id and tx.classified_by == "user"  # la regla NO la pisó
