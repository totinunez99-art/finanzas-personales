"""Centro de Inteligencia Financiera: respuestas, no gráficos (S3-B4, docs/23).

Cada función responde UNA pregunta concreta del dueño, sobre flujo OPERACIONAL
(los movimientos internos ya fueron normalizados por FlowStage y se excluyen
vía operational_condition: única fuente, sin lógica duplicada). Todo por
moneda, todo reproducible en SQL, evidencia insuficiente => listas vacías con
la razón explícita.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from finanzas.core.models import Category, Transaction, User
from finanzas.core.services.reporting import fmt_amount, month_bounds
from finanzas.core.services.resolution.flow_stage import operational_condition

MIN_HISTORY_FOR_ANOMALIES = 10
ANOMALY_FACTOR = Decimal("2.5")


def _conditions(
    user: User, start: date, end: date, currency: str, account_id: uuid.UUID | None
) -> list[Any]:
    conditions = [
        Transaction.user_id == user.id,
        Transaction.currency == currency,
        Transaction.posted_at >= start,
        Transaction.posted_at < end,
        operational_condition(),
    ]
    if account_id is not None:
        conditions.append(Transaction.account_id == account_id)
    return conditions


def _expenses_by_category(
    session: Session,
    user: User,
    start: date,
    end: date,
    currency: str,
    account_id: uuid.UUID | None,
) -> dict[str, Decimal]:
    rows = session.execute(
        select(Category.name, func.sum(-Transaction.amount))
        .join(Category, Transaction.category_id == Category.id)
        .where(*_conditions(user, start, end, currency, account_id), Transaction.amount < 0)
        .group_by(Category.name)
    ).all()
    result = {name: Decimal(total) for name, total in rows}
    unclassified = session.execute(
        select(func.coalesce(func.sum(-Transaction.amount), 0)).where(
            *_conditions(user, start, end, currency, account_id),
            Transaction.amount < 0,
            Transaction.category_id.is_(None),
        )
    ).scalar_one()
    if unclassified:
        result["Sin clasificar"] = Decimal(unclassified)
    return result


def overview(
    session: Session,
    user: User,
    period: str | None = None,
    account_id: uuid.UUID | None = None,
    currency: str = "CLP",
) -> dict[str, Any]:
    start, end = month_bounds(period)
    prev_start = (
        date(start.year - 1, 12, 1) if start.month == 1 else date(start.year, start.month - 1, 1)
    )
    base = _conditions(user, start, end, currency, account_id)

    # ¿Qué categorías consumen más dinero? ¿Qué % representa cada una?
    by_category = _expenses_by_category(session, user, start, end, currency, account_id)
    total_expense = sum(by_category.values(), Decimal(0))
    categories = sorted(
        (
            {
                "category": name,
                "total": fmt_amount(total),
                "pct": f"{(total / total_expense * 100):.1f}" if total_expense else "0",
            }
            for name, total in by_category.items()
        ),
        key=lambda c: Decimal(c["total"]),
        reverse=True,
    )

    # ¿Qué comercios reciben más dinero mío? (solo comercio identificado)
    merchants = [
        {"merchant": m, "total": fmt_amount(Decimal(t)), "count": int(n)}
        for m, t, n in session.execute(
            select(Transaction.merchant, func.sum(-Transaction.amount), func.count())
            .where(*base, Transaction.amount < 0, Transaction.merchant.is_not(None))
            .group_by(Transaction.merchant)
            .order_by(func.sum(-Transaction.amount).desc())
            .limit(10)
        ).all()
    ]

    # ¿Cuáles fueron mis mayores gastos?
    top_expenses = [
        {
            "date": d.isoformat(),
            "description": desc[:60],
            "merchant": m or "",
            "amount": fmt_amount(Decimal(a)),
        }
        for d, desc, m, a in session.execute(
            select(
                Transaction.posted_at,
                Transaction.description_raw,
                Transaction.merchant,
                -Transaction.amount,
            )
            .where(*base, Transaction.amount < 0)
            .order_by(Transaction.amount.asc())
            .limit(10)
        ).all()
    ]

    # ¿Cuál es mi flujo de caja? (diario + acumulado) / ¿día más caro?
    daily_rows = session.execute(
        select(
            Transaction.posted_at,
            func.coalesce(
                func.sum(case((Transaction.amount < 0, -Transaction.amount), else_=0)), 0
            ),
            func.coalesce(func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)), 0),
        )
        .where(*base)
        .group_by(Transaction.posted_at)
        .order_by(Transaction.posted_at)
    ).all()
    cumulative = Decimal(0)
    daily = []
    for d, exp, inc in daily_rows:
        net = Decimal(inc) - Decimal(exp)
        cumulative += net
        daily.append(
            {
                "date": d.isoformat(),
                "expense": fmt_amount(Decimal(exp)),
                "income": fmt_amount(Decimal(inc)),
                "net": fmt_amount(net),
                "cumulative_net": fmt_amount(cumulative),
            }
        )
    most_expensive_day = max(daily, key=lambda x: Decimal(x["expense"]), default=None)

    # ¿Qué semanas fueron más costosas?
    week = func.to_char(Transaction.posted_at, "IYYY-IW")
    weekly = [
        {"week": w, "expense": fmt_amount(Decimal(t))}
        for w, t in session.execute(
            select(week, func.sum(-Transaction.amount))
            .where(*base, Transaction.amount < 0)
            .group_by(week)
            .order_by(week)
        ).all()
    ]

    # ¿Qué gastos crecieron/disminuyeron? (por categoría vs mes anterior)
    prev = _expenses_by_category(session, user, prev_start, start, currency, account_id)
    deltas = []
    for name in sorted(set(by_category) | set(prev)):
        current_total = by_category.get(name, Decimal(0))
        prev_total = prev.get(name, Decimal(0))
        if prev_total == 0 and current_total == 0:
            continue
        deltas.append(
            {
                "category": name,
                "current": fmt_amount(current_total),
                "previous": fmt_amount(prev_total),
                "delta_pct": (
                    f"{((current_total - prev_total) / prev_total * 100):.1f}"
                    if prev_total > 0
                    else None  # sin base: honesto, no infinito
                ),
            }
        )
    with_delta = [d for d in deltas if d["delta_pct"] is not None]
    grew = sorted(
        (d for d in with_delta if Decimal(str(d["delta_pct"])) > 0),
        key=lambda d: Decimal(str(d["delta_pct"])),
        reverse=True,
    )
    declined = sorted(
        (d for d in with_delta if Decimal(str(d["delta_pct"])) < 0),
        key=lambda d: Decimal(str(d["delta_pct"])),
    )

    # ¿Qué comercios aparecen por primera vez?
    first_seen = (
        select(Transaction.merchant, func.min(Transaction.posted_at).label("first"))
        .where(
            Transaction.user_id == user.id,
            Transaction.currency == currency,
            Transaction.merchant.is_not(None),
        )
        .group_by(Transaction.merchant)
        .subquery()
    )
    new_merchants = [
        {"merchant": m, "first_seen": f.isoformat()}
        for m, f in session.execute(
            select(first_seen.c.merchant, first_seen.c.first).where(
                first_seen.c.first >= start, first_seen.c.first < end
            )
        ).all()
    ]

    # ¿Qué gastos parecen anormales? Regla: cargo > 2.5x el promedio de los
    # cargos operacionales de los 90 días previos al período (historia >= 10).
    history_start = start - timedelta(days=90)
    history = session.execute(
        select(func.avg(-Transaction.amount), func.count()).where(
            *_conditions(user, history_start, start, currency, account_id),
            Transaction.amount < 0,
        )
    ).one()
    anomalies: list[dict[str, Any]] = []
    anomalies_note = None
    if history[1] is not None and int(history[1]) >= MIN_HISTORY_FOR_ANOMALIES:
        threshold = (Decimal(history[0]) * ANOMALY_FACTOR).quantize(Decimal("1"))
        anomalies = [
            {
                "date": d.isoformat(),
                "description": desc[:60],
                "amount": fmt_amount(Decimal(a)),
                "threshold": fmt_amount(threshold),
            }
            for d, desc, a in session.execute(
                select(Transaction.posted_at, Transaction.description_raw, -Transaction.amount)
                .where(*base, Transaction.amount < 0, -Transaction.amount > threshold)
                .order_by(Transaction.amount.asc())
            ).all()
        ]
    else:
        anomalies_note = (
            f"Historia insuficiente para detectar anomalías: se requieren "
            f">= {MIN_HISTORY_FOR_ANOMALIES} cargos en los 90 días previos "
            f"(hay {int(history[1] or 0)})."
        )

    return {
        "period": f"{start:%Y-%m}",
        "currency": currency,
        "total_operational_expense": fmt_amount(total_expense),
        "categories": categories,
        "merchants": merchants,
        "top_expenses": top_expenses,
        "daily": daily,
        "most_expensive_day": most_expensive_day,
        "weekly": weekly,
        "grew": grew[:8],
        "declined": declined[:8],
        "new_merchants": new_merchants,
        "anomalies": anomalies,
        "anomalies_note": anomalies_note,
        "method_notes": {
            "alcance": "solo flujo operacional (internos excluidos por FlowStage, docs/23)",
            "anomalias": f"cargo > {ANOMALY_FACTOR}x promedio de cargos de 90 días previos",
            "deltas": "por categoría vs mes anterior; sin base previa => delta None",
        },
    }
