"""Consultas de lectura para el dashboard financiero (Sprint 2).

La lógica vive aquí (no en routers) para ser testeable contra PG real y
reutilizable por futuros consumidores (reportes, jobs).
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from finanzas.core.models import ImportBatch, Transaction, User
from finanzas.core.services.dedup import normalize_description
from finanzas.core.services.resolution.flow_stage import operational_condition


@dataclass(frozen=True)
class TransactionFilters:
    account_id: uuid.UUID | None = None
    q: str | None = None  # búsqueda en descripción (insensible a tildes)
    date_from: date | None = None
    date_to: date | None = None
    amount_min: Decimal | None = None  # sobre el VALOR ABSOLUTO (intuición del usuario)
    amount_max: Decimal | None = None
    kind: str | None = None  # cargo | abono
    limit: int = 200
    offset: int = 0


def _apply_filters(
    query: "Select[tuple[Transaction]]", user: User, f: TransactionFilters
) -> "Select[tuple[Transaction]]":
    query = query.where(Transaction.user_id == user.id)
    if f.account_id is not None:
        query = query.where(Transaction.account_id == f.account_id)
    if f.q:
        # description_norm ya está en mayúsculas y sin tildes: normalizar la
        # búsqueda igual → búsqueda insensible a tildes/caso sin extensiones.
        query = query.where(Transaction.description_norm.contains(normalize_description(f.q)))
    if f.date_from is not None:
        query = query.where(Transaction.posted_at >= f.date_from)
    if f.date_to is not None:
        query = query.where(Transaction.posted_at <= f.date_to)
    if f.amount_min is not None:
        query = query.where(func.abs(Transaction.amount) >= f.amount_min)
    if f.amount_max is not None:
        query = query.where(func.abs(Transaction.amount) <= f.amount_max)
    if f.kind == "cargo":
        query = query.where(Transaction.amount < 0)
    elif f.kind == "abono":
        query = query.where(Transaction.amount > 0)
    return query


def list_transactions(
    session: Session, user: User, f: TransactionFilters
) -> tuple[int, list[Transaction]]:
    base = _apply_filters(select(Transaction), user, f)
    total = session.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    rows = session.execute(
        base.order_by(Transaction.posted_at.desc(), Transaction.created_at.desc())
        .limit(f.limit)
        .offset(f.offset)
    ).scalars()
    return total, list(rows)


def fmt_amount(value: Decimal) -> str:
    """Canonico sin ceros espurios: '1000000', '45.9'. La UI re-formatea al mostrar."""
    return format(value.normalize(), "f")


_fmt_amount = fmt_amount  # compatibilidad interna


def month_bounds(period: str | None) -> tuple[date, date]:
    """period 'YYYY-MM' → [inicio, fin] inclusivo del mes. None = mes actual."""
    if period:
        year, month = int(period[:4]), int(period[5:7])
    else:
        today = date.today()
        year, month = today.year, today.month
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def stats_summary(
    session: Session,
    user: User,
    period: str | None = None,
    account_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    start, end = month_bounds(period)
    conditions = [
        Transaction.user_id == user.id,
        Transaction.posted_at >= start,
        Transaction.posted_at < end,
        operational_condition(),  # docs/23: internos fuera de KPIs
    ]
    if account_id is not None:
        conditions.append(Transaction.account_id == account_id)

    rows = session.execute(
        select(
            Transaction.currency,
            func.coalesce(
                func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)), 0
            ).label("income"),
            func.coalesce(
                func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)), 0
            ).label("expense"),
            func.count().label("count"),
        )
        .where(*conditions)
        .group_by(Transaction.currency)
    ).all()

    by_currency = [
        {
            "currency": r.currency,
            "income": _fmt_amount(r.income),
            "expense": _fmt_amount(-r.expense),  # se expone como magnitud positiva
            "net": _fmt_amount(r.income + r.expense),
            "count": r.count,
        }
        for r in rows
    ]

    last_batch = session.execute(
        select(ImportBatch)
        .where(ImportBatch.user_id == user.id)
        .order_by(
            ImportBatch.created_at.desc(),
            ImportBatch.period_end.desc().nulls_last(),
        )
        .limit(1)
    ).scalar_one_or_none()

    return {
        "period": f"{start:%Y-%m}",
        "by_currency": by_currency,
        "total_count": sum(r.count for r in rows),
        "last_import": (
            {
                "connector": last_batch.connector,
                "filename": last_batch.filename,
                "created_at": last_batch.created_at.isoformat(),
                "status": last_batch.status,
            }
            if last_batch is not None
            else None
        ),
    }


def _previous_period(start: date) -> str:
    prev = date(start.year - 1, 12, 1) if start.month == 1 else date(start.year, start.month - 1, 1)
    return f"{prev:%Y-%m}"


def financial_summary(
    session: Session,
    user: User,
    period: str | None = None,
    account_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """KPIs del período con comparación honesta contra el período anterior.

    Reglas anti-engaño (Sprint 3): un delta solo existe si el período anterior
    tiene base comparable (>0 en esa métrica y moneda); si no, es None y la UI
    muestra "sin base de comparación". Promedio diario = gasto / días
    transcurridos (mes en curso) o días del mes (mes cerrado). Tasa de ahorro =
    neto/ingresos, solo si hubo ingresos.
    """
    start, end = month_bounds(period)
    current = stats_summary(session, user, period=period, account_id=account_id)
    prev = stats_summary(session, user, period=_previous_period(start), account_id=account_id)
    prev_by_currency = {c["currency"]: c for c in prev["by_currency"]}

    today = date.today()
    if end <= today:
        days = (end - start).days
    elif start > today:
        days = 0
    else:
        days = today.day

    for entry in current["by_currency"]:
        expense = Decimal(entry["expense"])
        income = Decimal(entry["income"])
        net = Decimal(entry["net"])
        entry["avg_daily_expense"] = (
            fmt_amount((expense / days).quantize(Decimal("1"))) if days > 0 else None
        )
        entry["savings_rate_pct"] = f"{(net / income * 100):.1f}" if income > 0 else None
        previous = prev_by_currency.get(entry["currency"])
        entry["prev"] = previous
        prev_expense = Decimal(previous["expense"]) if previous else Decimal(0)
        prev_income = Decimal(previous["income"]) if previous else Decimal(0)
        entry["expense_delta_pct"] = (
            f"{((expense - prev_expense) / prev_expense * 100):.1f}" if prev_expense > 0 else None
        )
        entry["income_delta_pct"] = (
            f"{((income - prev_income) / prev_income * 100):.1f}" if prev_income > 0 else None
        )
        entry["count_delta"] = (entry["count"] - previous["count"]) if previous else None

    current["previous_period"] = prev["period"]
    current["days_in_scope"] = days
    return current
