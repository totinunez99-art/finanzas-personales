"""Merchant Resolver: cascada, memoria y no-invención (Sprint 3 B2, docs/21)."""

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
        user = User(email=f"mr-{uuid.uuid4().hex[:8]}@example.com")
        session.add(user)
        session.flush()
        account = Account(
            user_id=user.id, name="Cta", bank="edwards", type="checking", currency="CLP"
        )
        session.add(account)
        session.flush()

        def add(desc: str, merchant: str | None = None, source: str | None = None) -> None:
            norm = normalize_description(desc)
            session.add(
                Transaction(
                    user_id=user.id,
                    account_id=account.id,
                    posted_at=date(2026, 6, 10),
                    amount=Decimal("-1000"),
                    currency="CLP",
                    description_raw=desc,
                    description_norm=norm,
                    merchant=merchant,
                    merchant_source=source,
                    status="confirmed",
                    source="statement",
                    source_ref=f"t:{desc}",
                    intra_day_seq=hash(desc) % 1000,
                    dedup_hash=compute_dedup_hash(
                        str(account.id),
                        date(2026, 6, 10),
                        Decimal("-1000"),
                        "CLP",
                        norm,
                        hash(desc) % 1000,
                    ),
                )
            )

        add("PAGO:COPEC APP BQUE MONTEMAR")  # semilla contains → COPEC
        add("COMPRA SUPERMERCADO LIDER STGO")  # semilla → LIDER
        add("TRASPASO A:JUAN PEREZ", "Juan Perez", None)  # hint sin regla → conserva
        add("TRANSBANK STARBUCKS 00123")  # lo captura la regla semilla contains STARBUCKS
        add("COMPRA FERRETERIA LOCAL DESCONOCIDA")  # sin evidencia → None
        add("SUSCRIPCION RARA XYZ", "MI CLUB", "user")  # corregido por usuario → intocable
        session.commit()
        yield session, user, account


def test_cascada_y_no_invencion(dataset) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.models import Transaction
    from finanzas.core.services import merchant_resolver

    session, user, _ = dataset
    stats = merchant_resolver.backfill(session, user)
    session.commit()

    by_desc = {t.description_norm: t for t in session.execute(select(Transaction)).scalars()}

    copec = by_desc["PAGO:COPEC APP BQUE MONTEMAR"]
    assert copec.merchant == "COPEC" and copec.merchant_source == "rule"
    assert copec.merchant_confidence == Decimal("0.90")  # contains de semilla
    assert copec.merchant_rule_id is not None

    lider = by_desc["COMPRA SUPERMERCADO LIDER STGO"]
    assert lider.merchant == "LIDER" and lider.merchant_rule_id is not None

    hint = by_desc["TRASPASO A:JUAN PEREZ"]
    assert hint.merchant == "Juan Perez" and hint.merchant_source == "hint"
    assert hint.merchant_confidence == Decimal("0.90")

    # TRANSBANK + STARBUCKS: la regla semilla contains lo captura directamente
    tb = by_desc["TRANSBANK STARBUCKS 00123"]
    assert tb.merchant == "STARBUCKS"

    # Sin evidencia → sigue NULL (jamás inventar)
    unknown = by_desc["COMPRA FERRETERIA LOCAL DESCONOCIDA"]
    assert unknown.merchant is None and stats["unresolved"] >= 1

    # Corrección del usuario: intocable
    protected = by_desc["SUSCRIPCION RARA XYZ"]
    assert protected.merchant == "MI CLUB" and protected.merchant_source == "user"
    assert stats["untouched_user"] == 1


def test_backfill_idempotente_y_eventos_explicables(dataset) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.models import DomainEvent
    from finanzas.core.services import merchant_resolver

    session, user, _ = dataset
    merchant_resolver.backfill(session, user)
    session.commit()
    events_1 = len(
        session.execute(select(DomainEvent).where(DomainEvent.event_type == "merchant.resolved"))
        .scalars()
        .all()
    )

    stats2 = merchant_resolver.backfill(session, user)  # segunda pasada: sin cambios
    session.commit()
    events_2 = len(
        session.execute(select(DomainEvent).where(DomainEvent.event_type == "merchant.resolved"))
        .scalars()
        .all()
    )
    assert events_2 == events_1  # idempotencia: nada nuevo que auditar
    assert stats2["resolved"] == 0

    # Toda resolución auditada lleva explicación con factores
    event = session.execute(
        select(DomainEvent).where(DomainEvent.event_type == "merchant.resolved").limit(1)
    ).scalar_one()
    assert event.payload["explanation"] and event.payload["confidence"]


def test_teach_crea_regla_y_aprende(dataset) -> None:  # type: ignore[no-untyped-def]
    from finanzas.core.models import MerchantRule, Transaction
    from finanzas.core.services import merchant_resolver

    session, user, _ = dataset
    merchant_resolver.backfill(session, user)
    result = merchant_resolver.teach(
        session, user, "COMPRA FERRETERIA LOCAL DESCONOCIDA", "FERRETERIA LOCAL"
    )
    session.commit()
    assert result["applied_to"] == 1

    rule = session.execute(
        select(MerchantRule).where(MerchantRule.origin == "user", MerchantRule.user_id == user.id)
    ).scalar_one()
    assert rule.merchant == "FERRETERIA LOCAL" and rule.priority == 10

    tx = session.execute(
        select(Transaction).where(
            Transaction.description_norm == "COMPRA FERRETERIA LOCAL DESCONOCIDA",
            Transaction.user_id == user.id,
        )
    ).scalar_one()
    assert tx.merchant == "FERRETERIA LOCAL"
    assert tx.merchant_confidence == Decimal("0.99")  # regla enseñada por el usuario
    assert tx.merchant_rule_id == rule.id
