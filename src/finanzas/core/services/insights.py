"""Motor de Insights: conclusiones automáticas por REGLAS de negocio (Sprint 3).

Núcleo del futuro Copiloto Financiero. Principios no negociables:
- Determinista: cero IA, cero inventos. Cada insight sale de una consulta SQL
  reproducible y su campo `explanation` describe exactamente cómo se calculó.
- Evidencia o silencio: si los datos no superan los umbrales (constantes abajo,
  visibles y auditables), el generador devuelve None y no se muestra nada.
- Una moneda por insight: jamás se mezclan monedas en un cálculo.

Agregar un insight nuevo = escribir un generador y sumarlo a GENERATORS.
"""

import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from finanzas.core.models import Transaction, User
from finanzas.core.services.reporting import fmt_amount, month_bounds
from finanzas.core.services.resolution.flow_stage import operational_condition


def _display(value: Decimal) -> str:
    """Formato chileno para títulos/descripciones: 22096.77 -> '22.097'."""
    return f"{value.quantize(Decimal('1')):,}".replace(",", ".")


# ---------------------------------------------------------------- umbrales
# Visibles a propósito: son la definición operativa de "evidencia suficiente".
MIN_CARGOS_CONCENTRACION = 5  # top-3 compras requiere al menos 5 cargos
MIN_CARGOS_DIA_CARO = 5
MIN_CARGOS_DIA_SEMANA = 10
MIN_APARICIONES_COMERCIO = 3
MIN_DIAS_PROMEDIO = 5  # promedio diario con <5 días transcurridos es ruido
MIN_TX_MES_ANTERIOR = 3  # comparar contra un mes anterior casi vacío engaña

_DOW_NAMES = {
    1: "lunes",
    2: "martes",
    3: "miércoles",
    4: "jueves",
    5: "viernes",
    6: "sábado",
    7: "domingo",
}


@dataclass(frozen=True)
class Insight:
    id: str  # estable e idempotente: tipo:período:moneda
    type: str  # comparison | average | concentration | pattern | frequency | alert
    title: str
    description: str
    severity: str  # info | notable | warning
    priority: int  # menor = más arriba en el dashboard
    currency: str
    data: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""  # fórmula + filtros, reproducible en SQL

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _Ctx:
    session: Session
    user: User
    period: str  # YYYY-MM
    start: date
    end: date  # exclusivo
    prev_period: str
    prev_start: date
    prev_end: date
    days_elapsed: int  # días del período con posibilidad de datos
    account_id: uuid.UUID | None
    currency: str


def _base_conditions(ctx: _Ctx, start: date, end: date) -> list[Any]:
    conditions = [
        Transaction.user_id == ctx.user.id,
        Transaction.currency == ctx.currency,
        Transaction.posted_at >= start,
        Transaction.posted_at < end,
        operational_condition(),
    ]
    if ctx.account_id is not None:
        conditions.append(Transaction.account_id == ctx.account_id)
    return conditions


def _expenses_sum_count(ctx: _Ctx, start: date, end: date) -> tuple[Decimal, int]:
    row = ctx.session.execute(
        select(
            func.coalesce(func.sum(-Transaction.amount), 0),
            func.count(),
        ).where(*_base_conditions(ctx, start, end), Transaction.amount < 0)
    ).one()
    return Decimal(row[0]), int(row[1])


# ---------------------------------------------------------------- generadores


def _gasto_vs_mes_anterior(ctx: _Ctx) -> Insight | None:
    actual, n_actual = _expenses_sum_count(ctx, ctx.start, ctx.end)
    anterior, n_prev = _expenses_sum_count(ctx, ctx.prev_start, ctx.prev_end)
    if n_prev < MIN_TX_MES_ANTERIOR or anterior == 0 or n_actual == 0:
        return None  # sin base de comparación honesta
    delta_pct = (actual - anterior) / anterior * 100
    direction = "más" if delta_pct > 0 else "menos"
    severity = "warning" if delta_pct >= 25 else ("notable" if abs(delta_pct) >= 10 else "info")
    return Insight(
        id=f"gasto_vs_mes_anterior:{ctx.period}:{ctx.currency}",
        type="comparison",
        title=f"Gastaste {abs(delta_pct):.0f}% {direction} que el mes anterior",
        description=(
            f"Gasto de {ctx.period}: ${_display(actual)} vs "
            f"${_display(anterior)} en {ctx.prev_period} ({ctx.currency})."
        ),
        severity=severity,
        priority=10,
        currency=ctx.currency,
        data={
            "actual": fmt_amount(actual),
            "anterior": fmt_amount(anterior),
            "delta_pct": f"{delta_pct:.1f}",
            "n_actual": n_actual,
            "n_anterior": n_prev,
        },
        explanation=(
            "SUM(-amount) de cargos (amount<0) del período vs período anterior, "
            "misma moneda y cuenta; delta = (actual-anterior)/anterior*100."
        ),
    )


def _cantidad_movimientos(ctx: _Ctx) -> Insight | None:
    _, n_actual = _expenses_sum_count(ctx, ctx.start, ctx.end)
    _, n_prev = _expenses_sum_count(ctx, ctx.prev_start, ctx.prev_end)
    if n_prev < MIN_TX_MES_ANTERIOR or n_actual == 0 or n_actual == n_prev:
        return None
    direction = "más" if n_actual > n_prev else "menos"
    return Insight(
        id=f"compras_vs_mes_anterior:{ctx.period}:{ctx.currency}",
        type="comparison",
        title=f"Este mes hiciste {direction} compras que el anterior",
        description=f"{n_actual} cargos en {ctx.period} vs {n_prev} en {ctx.prev_period}.",
        severity="info",
        priority=40,
        currency=ctx.currency,
        data={"n_actual": n_actual, "n_anterior": n_prev},
        explanation="COUNT(*) de cargos (amount<0) por período, misma moneda y cuenta.",
    )


def _promedio_diario(ctx: _Ctx) -> Insight | None:
    if ctx.days_elapsed < MIN_DIAS_PROMEDIO:
        return None
    total, n = _expenses_sum_count(ctx, ctx.start, ctx.end)
    if n == 0:
        return None
    avg = total / ctx.days_elapsed
    return Insight(
        id=f"promedio_diario:{ctx.period}:{ctx.currency}",
        type="average",
        title=f"Tu gasto promedio diario fue de ${_display(avg)}",
        description=(
            f"${_display(total)} en {ctx.days_elapsed} días del período "
            f"({n} cargos, {ctx.currency})."
        ),
        severity="info",
        priority=30,
        currency=ctx.currency,
        data={"total": fmt_amount(total), "dias": ctx.days_elapsed, "n_cargos": n},
        explanation=(
            "SUM(-amount) de cargos del período dividido por días transcurridos "
            "(mes en curso: hasta hoy; mes cerrado: todos sus días)."
        ),
    )


def _top3_concentracion(ctx: _Ctx) -> Insight | None:
    total, n = _expenses_sum_count(ctx, ctx.start, ctx.end)
    if n < MIN_CARGOS_CONCENTRACION or total == 0:
        return None
    top3 = ctx.session.execute(
        select(-Transaction.amount, Transaction.description_raw)
        .where(*_base_conditions(ctx, ctx.start, ctx.end), Transaction.amount < 0)
        .order_by(Transaction.amount.asc())
        .limit(3)
    ).all()
    suma_top3 = sum((row[0] for row in top3), Decimal(0))
    pct = suma_top3 / total * 100
    if pct < 30:
        return None  # sin concentración relevante no hay observación útil
    return Insight(
        id=f"concentracion_top3:{ctx.period}:{ctx.currency}",
        type="concentration",
        title=f"Tus 3 mayores compras concentran el {pct:.0f}% del gasto",
        description="; ".join(f"${_display(m)} {d[:40]}" for m, d in top3),
        severity="notable" if pct >= 50 else "info",
        priority=20,
        currency=ctx.currency,
        data={
            "suma_top3": fmt_amount(suma_top3),
            "total": fmt_amount(total),
            "pct": f"{pct:.1f}",
            "n_cargos": n,
        },
        explanation=(
            "3 cargos de mayor magnitud del período (ORDER BY amount ASC LIMIT 3) "
            "sobre SUM de todos los cargos; se emite solo si pct >= 30%."
        ),
    )


def _dia_mas_caro(ctx: _Ctx) -> Insight | None:
    _, n = _expenses_sum_count(ctx, ctx.start, ctx.end)
    if n < MIN_CARGOS_DIA_CARO:
        return None
    row = ctx.session.execute(
        select(Transaction.posted_at, func.sum(-Transaction.amount).label("total"))
        .where(*_base_conditions(ctx, ctx.start, ctx.end), Transaction.amount < 0)
        .group_by(Transaction.posted_at)
        .order_by(func.sum(-Transaction.amount).desc())
        .limit(1)
    ).one_or_none()
    if row is None:
        return None
    return Insight(
        id=f"dia_mas_caro:{ctx.period}:{ctx.currency}",
        type="pattern",
        title=f"El {row.posted_at:%d/%m} fue tu día más caro",
        description=f"${_display(Decimal(row.total))} en cargos ese día ({ctx.currency}).",
        severity="info",
        priority=50,
        currency=ctx.currency,
        data={
            "fecha": row.posted_at.isoformat(),
            "total": fmt_amount(Decimal(row.total)),
            "n_cargos": n,
        },
        explanation="SUM(-amount) de cargos GROUP BY posted_at, máximo del período.",
    )


def _dia_semana_mayor_gasto(ctx: _Ctx) -> Insight | None:
    _, n = _expenses_sum_count(ctx, ctx.start, ctx.end)
    if n < MIN_CARGOS_DIA_SEMANA:
        return None
    dow = func.extract("isodow", Transaction.posted_at)
    row = ctx.session.execute(
        select(dow.label("dow"), func.sum(-Transaction.amount).label("total"))
        .where(*_base_conditions(ctx, ctx.start, ctx.end), Transaction.amount < 0)
        .group_by(dow)
        .order_by(func.sum(-Transaction.amount).desc())
        .limit(1)
    ).one_or_none()
    if row is None:
        return None
    name = _DOW_NAMES.get(int(row.dow), "?")
    return Insight(
        id=f"dia_semana_gasto:{ctx.period}:{ctx.currency}",
        type="pattern",
        title=f"El {name} es tu día de la semana con mayor gasto",
        description=(
            f"${_display(Decimal(row.total))} acumulados en {name} durante "
            f"{ctx.period} ({ctx.currency})."
        ),
        severity="info",
        priority=60,
        currency=ctx.currency,
        data={"dia_semana": name, "total": fmt_amount(Decimal(row.total)), "n_cargos": n},
        explanation="SUM(-amount) de cargos GROUP BY EXTRACT(isodow FROM posted_at), máximo.",
    )


def _comercio_frecuente(ctx: _Ctx) -> Insight | None:
    row = ctx.session.execute(
        select(
            Transaction.merchant,
            func.count().label("n"),
            func.sum(-Transaction.amount).label("total"),
        )
        .where(
            *_base_conditions(ctx, ctx.start, ctx.end),
            Transaction.amount < 0,
            Transaction.merchant.is_not(None),
        )
        .group_by(Transaction.merchant)
        .order_by(func.count().desc())
        .limit(1)
    ).one_or_none()
    if row is None or row.n < MIN_APARICIONES_COMERCIO:
        return None
    return Insight(
        id=f"comercio_frecuente:{ctx.period}:{ctx.currency}",
        type="frequency",
        title=f"{row.merchant} aparece {row.n} veces este mes",
        description=(
            f"Total gastado ahí: ${_display(Decimal(row.total))} ({ctx.currency}). "
            "Solo cuenta movimientos con comercio identificado."
        ),
        severity="info",
        priority=45,
        currency=ctx.currency,
        data={
            "comercio": row.merchant,
            "apariciones": row.n,
            "total": fmt_amount(Decimal(row.total)),
        },
        explanation=(
            "COUNT(*) de cargos GROUP BY merchant (solo merchant IS NOT NULL), máximo; "
            "requiere >= 3 apariciones."
        ),
    )


def _flujo_negativo(ctx: _Ctx) -> Insight | None:
    row = ctx.session.execute(
        select(
            func.coalesce(func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)), 0),
            func.coalesce(
                func.sum(case((Transaction.amount < 0, -Transaction.amount), else_=0)), 0
            ),
            func.count(),
        ).where(*_base_conditions(ctx, ctx.start, ctx.end))
    ).one()
    income, expense, n = Decimal(row[0]), Decimal(row[1]), int(row[2])
    if n < MIN_TX_MES_ANTERIOR or expense <= income:
        return None
    deficit = expense - income
    return Insight(
        id=f"flujo_negativo:{ctx.period}:{ctx.currency}",
        type="alert",
        title="Este mes gastaste más de lo que ingresó",
        description=(
            f"Cargos ${_display(expense)} vs abonos ${_display(income)}: "
            f"déficit de ${_display(deficit)} ({ctx.currency})."
        ),
        severity="warning",
        priority=5,
        currency=ctx.currency,
        data={
            "ingresos": fmt_amount(income),
            "gastos": fmt_amount(expense),
            "deficit": fmt_amount(deficit),
        },
        explanation="SUM de abonos vs SUM de magnitud de cargos del período, misma moneda.",
    )


GENERATORS: list[Callable[[_Ctx], Insight | None]] = [
    _flujo_negativo,
    _gasto_vs_mes_anterior,
    _top3_concentracion,
    _promedio_diario,
    _cantidad_movimientos,
    _comercio_frecuente,
    _dia_mas_caro,
    _dia_semana_mayor_gasto,
]


def generate_insights(
    session: Session,
    user: User,
    period: str | None = None,
    account_id: uuid.UUID | None = None,
) -> list[Insight]:
    start, end = month_bounds(period)
    period_str = f"{start:%Y-%m}"
    prev_end = start
    prev_start = (
        date(start.year - 1, 12, 1) if start.month == 1 else date(start.year, start.month - 1, 1)
    )

    today = date.today()
    if end <= today:
        days_elapsed = (end - start).days  # mes cerrado: todos sus días
    elif start > today:
        days_elapsed = 0  # mes futuro: sin datos posibles
    else:
        days_elapsed = today.day  # mes en curso: días transcurridos

    # Monedas presentes en el período (un contexto por moneda: jamás se mezclan)
    currencies = (
        session.execute(
            select(Transaction.currency)
            .where(
                Transaction.user_id == user.id,
                Transaction.posted_at >= start,
                Transaction.posted_at < end,
                *([Transaction.account_id == account_id] if account_id else []),
            )
            .distinct()
        )
        .scalars()
        .all()
    )

    insights: list[Insight] = []
    for currency in currencies:
        ctx = _Ctx(
            session=session,
            user=user,
            period=period_str,
            start=start,
            end=end,
            prev_period=f"{prev_start:%Y-%m}",
            prev_start=prev_start,
            prev_end=prev_end,
            days_elapsed=days_elapsed,
            account_id=account_id,
            currency=currency,
        )
        for generator in GENERATORS:
            insight = generator(ctx)
            if insight is not None:
                insights.append(insight)
    order = {"warning": 0, "notable": 1, "info": 2}
    insights.sort(key=lambda i: (i.priority, order.get(i.severity, 9)))
    return insights
